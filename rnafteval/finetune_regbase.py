"""Per-base 回归任务 runner：degradation (OpenVaccine) / ssi (结构得分插补)。

8 任务扩展（用户 10-18 指令第 1 条的第 4 类任务——碱基级回归）。
复用 finetune_base 的全部策略/ledger/资源记录协议，仅把头从 BCE 换成 per-token MSE、
监督 mask 支持部分打分窗口（degradation：前 seq_scored 位）。

Usage:
  python -m rnafteval.finetune_regbase --model RiNALMo-micro --task degradation \
      --strategy frozen --seed 17 --split random --device 0 --epochs 3

Metrics: per-base PCC（主指标，对齐 BEACON 回归口径）+ MCRMSE 汇总（记录进 ledger）。
"""
from __future__ import annotations

import argparse
import json
import os
import random
import time

import numpy as np
import torch

from . import ledger
from .base_alignment import align_base_labels
from .tasks import degradation as deg_task
from .tasks import ssi as ssi_task

ROOT = "/root/rna-ft-eval"


def encode_seqs(tok, seqs, device, max_len=192):
    enc = tok(seqs, padding=True, truncation=True, max_length=max_len,
              return_tensors="pt")
    if not torch.is_tensor(enc["input_ids"]):
        ii = enc["input_ids"]
        if len(ii) and hasattr(ii[0], "ids"):
            ii = [e.ids for e in ii]
        enc["input_ids"] = torch.tensor([list(x) for x in ii],
                                        dtype=torch.long)
        am = enc.get("attention_mask")
        if not torch.is_tensor(am):
            enc["attention_mask"] = torch.tensor(
                [list(x) for x in (am or [[1] * len(ii[0])] * len(ii))],
                dtype=torch.long)
    return {k: v.to(device) for k, v in enc.items()
            if k in ("input_ids", "attention_mask")}


def batches(rows, bs):
    for i in range(0, len(rows), bs):
        yield rows[i:i + bs]


def _run_extra(args):
    lr_tag = "" if abs(args.lr - 3e-4) < 1e-12 else "_lr%g" % args.lr
    rank_tag = "" if args.rank == 8 else "_r%d" % args.rank
    n_tag = "" if args.n_train == 0 else "_e3%d" % args.n_train
    epoch_tag = "" if args.epochs == 3 else "_ep%d" % args.epochs
    return ("_b20fix" + ("_smoke" if args.smoke else "") + n_tag +
            lr_tag + rank_tag + epoch_tag)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--task", required=True,
                    choices=["degradation", "ssi"])
    ap.add_argument("--strategy", required=True,
                    choices=["frozen", "lora", "head-only", "full",
                             "dora", "ia3", "prefix"])
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--split", required=True, choices=["random", "family"])
    ap.add_argument("--device", type=int, required=True)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--batch-size", type=int, default=32)
    ap.add_argument("--n-train", type=int, default=0,
                    help="0 = all")
    ap.add_argument("--max-len", type=int, default=192)
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--rank", type=int, default=8)
    args = ap.parse_args()

    if not torch.cuda.is_available():
        print(json.dumps({"event": "CUDA_UNAVAILABLE_ABORT"}), flush=True)
        return 2
    torch.cuda.set_device(args.device)
    device = "cuda:%d" % args.device
    torch.manual_seed(args.seed)
    random.seed(args.seed)
    np.random.seed(args.seed)

    extra = _run_extra(args)
    rid = ledger.run_id(args.model, args.task, args.strategy, args.seed,
                        args.split, extra)
    out_dir = os.path.join(ROOT, "artifacts", rid)
    os.makedirs(out_dir, exist_ok=True)
    claim = ledger.claim(args.model, args.task, args.strategy, args.seed,
                         args.split, device=args.device, out_dir=out_dir,
                         extra=extra)
    if not claim["claimed"]:
        print("skip (already %s)" % claim["row"]["status"])
        return 75

    t0 = time.time()
    torch.cuda.reset_peak_memory_stats(args.device)

    # --- data ---
    if args.task == "degradation":
        if args.split == "family":
            import pyarrow.parquet as pq
            fam = os.path.join(ROOT, "data", "family_splits",
                               "degradation.parquet")
            assert os.path.exists(fam), "run make_family_split first"
            t = pq.read_table(fam).to_pydict()
            train, test = [], []
            for seq, lab, sd in zip(t["seq"], t["labels"], t["split"]):
                r = {"seq": seq,
                     "labels": np.asarray(lab, dtype=np.float32)}
                if sd == "train":
                    train.append(r)
                elif sd == "test":
                    test.append(r)
        else:
            sp = deg_task.load_official_split()
            train = sp["train"]
            test = sp["test"]
    else:  # ssi
        if args.split == "family":
            import pyarrow.parquet as pq
            fam = os.path.join(ROOT, "data", "family_splits", "ssi.parquet")
            assert os.path.exists(fam), "run make_family_split first"
            t = pq.read_table(fam).to_pydict()
            train, test = [], []
            for seq, lab, sd in zip(t["seq"], t["labels"], t["split"]):
                r = {"seq": seq,
                     "labels": np.asarray(lab, dtype=np.float32)}
                if sd == "train":
                    train.append(r)
                elif sd == "test":
                    test.append(r)
        else:
            sp = ssi_task.load_official_split()
            train = sp["train"]
            test = sp["test"]

    if args.n_train and args.n_train < len(train):
        train = train[:args.n_train]
    if args.smoke:
        train = train[:60]
        test = test[:60]
    print("data: train %d test %d" % (len(train), len(test)), flush=True)

    from .models import load_model
    from .strategies import apply_strategy, TokenHead
    spec, tok, backbone = load_model(args.model, device)
    with torch.no_grad():
        probe = encode_seqs(tok, [train[0]["seq"]], device, args.max_len)
        d = backbone(**probe).last_hidden_state.shape[-1]
    backbone, n_trainable = apply_strategy(backbone, args.strategy,
                                            lora_rank=args.rank)
    head = TokenHead(d, 1, hidden=32).to(device)
    train_params = [p for p in head.parameters() if p.requires_grad] + \
        [p for p in backbone.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(train_params, lr=args.lr)

    def make_batch(b):
        enc = encode_seqs(tok, [r["seq"] for r in b], device, args.max_len)
        y, m = align_base_labels(
            tok, enc, b, args.max_len,
            allow_short_labels=args.task == "degradation")
        return enc, y, m

    def _pad_mask(enc):
        am = enc.get("attention_mask")
        if am is None:
            return None
        return (am == 0)

    for ep in range(args.epochs):
        import random as _rd
        _epshuf = _rd.Random(args.seed * 1000 + ep)
        _rows = list(train)
        _epshuf.shuffle(_rows)
        backbone.train(args.strategy in ("lora", "full"))
        head.train()
        tot, nb = 0.0, 0
        import contextlib
        for b in batches(_rows, args.batch_size):
            enc, y, m = make_batch(b)
            no_grad = args.strategy in ("frozen", "head-only")
            with contextlib.nullcontext() if not no_grad \
                    else torch.no_grad():
                h = backbone(**enc).last_hidden_state
            logits = head(h, _pad_mask(enc)).squeeze(-1)
            loss = ((logits - y) ** 2 * m).sum() / m.sum().clamp(min=1)
            opt.zero_grad()
            loss.backward()
            opt.step()
            tot += loss.item()
            nb += 1
        print("epoch %d loss %.4f" % (ep, tot / max(nb, 1)), flush=True)
        ledger.update(rid, "running", note="epoch %d heartbeat" % ep)

    # --- eval: per-base PCC (primary) + MCRMSE ---
    backbone.eval()
    head.eval()
    preds, tgts, seqs_mse = [], [], []
    with torch.no_grad():
        for b in batches(test, args.batch_size):
            enc, y, m = make_batch(b)
            h = backbone(**enc).last_hidden_state
            logits = head(h, _pad_mask(enc)).squeeze(-1)
            for i in range(len(b)):
                if not m[i].any():
                    continue
                p = logits[i][m[i]].float().cpu().numpy()
                t = y[i][m[i]].float().cpu().numpy()
                preds.append(p)
                tgts.append(t)
                seqs_mse.append(float(((p - t) ** 2).mean()))
    allp = np.concatenate(preds) if preds else np.array([0.0])
    allt = np.concatenate(tgts) if tgts else np.array([0.0])
    pcc = float(np.corrcoef(allp, allt)[0, 1]) if preds else 0.0
    if not np.isfinite(pcc):
        raise FloatingPointError("non-finite primary metric: PCC")
    mcrmse = float(np.sqrt(np.mean(seqs_mse))) if seqs_mse else 0.0
    wall = time.time() - t0
    peak = torch.cuda.max_memory_allocated(args.device) / 1e6

    result = {
        "run_id": rid, "model": args.model, "task": args.task,
        "strategy": args.strategy, "seed": args.seed, "split": args.split,
        "metric": "PCC", "value": pcc, "mcrmse": mcrmse,
        "n_train": len(train), "n_test": len(test),
        "lr": args.lr, "epochs": args.epochs, "rank": args.rank,
        "wall_sec": round(wall, 1), "peak_mem_mb": round(peak, 1),
        "n_trainable": n_trainable, "smoke": args.smoke,
    }
    result_path = os.path.join(out_dir, "result.json")
    tmp_path = result_path + ".tmp"
    with open(tmp_path, "w") as f:
        json.dump(result, f, indent=1, default=str)
    os.replace(tmp_path, result_path)
    ledger.update(rid, "done", value=pcc, metric="PCC",
                  wall_sec=round(wall, 1), peak_mem_mb=round(peak, 1),
                  n_train=len(train), n_test=len(test))
    print(json.dumps(result, default=str)[:400], flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
