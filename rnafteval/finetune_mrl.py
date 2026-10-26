"""Finetune MRL 回归（per-seq，BEACON MeanRibosomeLoading）——C4 per-seq 第二任务。

用法:
  python -m rnafteval.finetune_mrl --model RiNALMo-micro --strategy lora \
    --seed 17 --split random --device 4 --epochs 3 --n-train 20000
协议: 对齐 m6A 口径（epochs 3 / n-train 20000 / bs 32）；指标 = Pearson r。
"""
from __future__ import annotations

import argparse
import json
import os
import random
import time

import numpy as np
import torch

from . import ledger, valplateau as vp
from .splits import prepare_convergence_splits
from .strategies import apply_strategy, make_head

ROOT = "/root/rna-ft-eval"


def encode_seqs(tok, seqs, device, max_len=64):
    enc = tok(seqs, padding=True, truncation=True, max_length=max_len,
              return_tensors="pt")
    return {k: v.to(device) for k, v in enc.items()}


def batches(rows, bs):
    for i in range(0, len(rows), bs):
        yield rows[i:i + bs]


def _run_extra(args):
    lr_tag = "" if abs(args.lr - 3e-4) < 1e-12 else "_lr%g" % args.lr
    rank_tag = "" if args.rank == 8 else "_r%d" % args.rank
    e3_tag = ("_e3%d" % args.n_train) if args.n_train != 20000 else ""
    protocol_tag = vp.protocol_tag(args)
    return (("_smoke" if args.smoke else "") + e3_tag + lr_tag + rank_tag +
            protocol_tag)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--task", default="mrl")
    ap.add_argument("--strategy", required=True,
                    choices=["frozen", "lora", "head-only", "full",
                             "dora", "ia3"])
    ap.add_argument("--seed", type=int, default=17)
    ap.add_argument("--split", default="random", choices=["random", "family"])
    ap.add_argument("--device", type=int, required=True)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--batch-size", type=int, default=32)
    ap.add_argument("--max-len", type=int, default=64)
    ap.add_argument("--n-train", type=int, default=20000)
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--rank", type=int, default=8,
                    help="LoRA/DoRA rank (E2 sweep; default 8)")
    vp.add_convergence_args(ap)
    args = ap.parse_args()
    vp.validate_convergence_args(args)

    if not torch.cuda.is_available():
        print(json.dumps({"event": "CUDA_UNAVAILABLE_ABORT"}), flush=True)
        return 2
    torch.cuda.set_device(args.device)
    device = "cuda:%d" % args.device
    torch.manual_seed(args.seed)
    random.seed(args.seed)

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
        return 75  # EXIT_CLAIM_BLOCKED (fake-complete fix 1006b)

    t0 = time.time()
    from .tasks import mrl as mrl_task

    val = None
    if args.split == "family":
        import pyarrow.parquet as pq
        fam = os.path.join(ROOT, "data", "family_splits", "mrl.parquet")
        if not os.path.exists(fam):
            ledger.update(rid, "failed", note="mrl family parquet missing")
            return 3
        t = pq.read_table(fam).to_pydict()
        recs = [{"seq": s, "label": float(l), "cluster": c}
                for s, l, c in zip(t["seq"], t["label"], t["cluster_id"])]
        train = [r for r, sd in zip(recs, t["split"]) if sd == "train"]
        test = [r for r, sd in zip(recs, t["split"]) if sd == "test"]
        if args.converge:
            val = [r for r, sd in zip(recs, t["split"]) if sd == "val"] or None
        else:
            rng = random.Random(args.seed)
            train = rng.sample(train, min(args.n_train, len(train)))
    else:
        sp = mrl_task.load_official_split(
            os.path.join(ROOT, "data", "beacon_raw",
                         "mean-ribosome-loading", "data"))
        train, test = sp["train"], sp["test"]
        if args.converge:
            val = sp.get("validation")
        else:
            rng = random.Random(args.seed)
            train = rng.sample(train, min(args.n_train, len(train)))
    data_evidence = None
    if args.converge:
        train, val, test, data_evidence = prepare_convergence_splits(
            train, val, test, n_train=args.n_train, sample_seed=args.seed,
            family=args.split == "family",
            validation_source="official_validation" if args.split == "random"
            else "family_validation",
            evidence_path=os.path.join(out_dir, "split_evidence.json"))
        print("data: train %d val %d test %d" % (
            len(train), len(val), len(test)), flush=True)
    if args.smoke:
        train, test = train[:320], test[:320]
        if val is not None:
            val = val[:320]

    from .models import load_model
    spec, tok, backbone = load_model(args.model, device)
    with torch.no_grad():
        probe = encode_seqs(tok, [train[0]["seq"]], device, args.max_len)
        d = backbone(**probe).last_hidden_state.shape[-1]
    backbone, n_trainable = apply_strategy(backbone, args.strategy, lora_rank=args.rank)
    head = make_head("per-seq", d, 1).to(device)
    params = [p for p in head.parameters() if p.requires_grad] + \
        [p for p in backbone.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(params, lr=args.lr)
    lossf = torch.nn.MSELoss()
    torch.cuda.reset_peak_memory_stats(device)
    def save_best(epoch, val_loss):
        vp.save_best_checkpoint(
            os.path.join(out_dir, "best.ckpt"), backbone, head,
            epoch=epoch, best_epoch=epoch, best_val=val_loss)
    tracker = vp.make_tracker(out_dir, args, rid, save_best) \
        if args.converge else None
    runtime = vp.runtime_evidence(tok, device) if args.converge else None

    def run_batch(b):
        enc = encode_seqs(tok, [r["seq"] for r in b], device, args.max_len)
        y = torch.tensor([r["label"] for r in b], dtype=torch.float32,
                         device=device)
        return enc, y

    for ep in vp.training_epochs(args):
        import random as _rd
        _epshuf = _rd.Random(args.seed * 1000 + ep)
        _rows = list(train)
        _epshuf.shuffle(_rows)
        backbone.train(args.strategy in ("lora", "full", "dora", "ia3"))
        head.train()
        tot, nb = 0.0, 0
        for b in batches(_rows, args.batch_size):
            enc, y = run_batch(b)
            no_grad = args.strategy in ("frozen", "head-only")
            import contextlib
            with contextlib.nullcontext() if not no_grad \
                    else torch.no_grad():
                h = backbone(**enc).last_hidden_state
            pad = enc["attention_mask"] == 0
            pred = head(h, pad).squeeze(-1)
            loss = lossf(pred, y)
            opt.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(params, 1.0)
            opt.step()
            tot += loss.item()
            nb += 1
        epoch_loss = tot / max(nb, 1)
        print("epoch %d loss %.4f" % (ep, epoch_loss), flush=True)
        if args.converge:
            backbone.eval()
            head.eval()
            val_tot, val_nb = 0.0, 0
            with torch.no_grad():
                for b in batches(val, args.batch_size * 2):
                    enc, y = run_batch(b)
                    h = backbone(**enc).last_hidden_state
                    pad = enc["attention_mask"] == 0
                    pred = head(h, pad).squeeze(-1)
                    val_loss = lossf(pred, y)
                    val_tot += val_loss.item()
                    val_nb += 1
            val_epoch_loss = val_tot / max(val_nb, 1)
            print("epoch %d val_loss %.6f" % (ep, val_epoch_loss), flush=True)
            if tracker.record(ep, epoch_loss, val_epoch_loss):
                print("STOP %s epoch=%d epochs_trained=%d" % (
                    tracker.stop_reason, ep, ep + 1), flush=True)
                ledger.update(rid, "running", note=tracker.stop_reason)
                break
        ledger.update(rid, "running", note="epoch %d heartbeat" % ep)

    if args.converge and args.convergence_mode == "bestval":
        vp.restore_best_checkpoint(tracker, backbone, head, device)
    backbone.eval()
    head.eval()
    ys, ps = [], []
    with torch.no_grad():
        for b in batches(test, args.batch_size * 2):
            enc, y = run_batch(b)
            h = backbone(**enc).last_hidden_state
            pad = enc["attention_mask"] == 0
            pred = head(h, pad).squeeze(-1)
            ys.append(y.cpu().numpy())
            ps.append(pred.cpu().numpy())
    y_all = np.concatenate(ys)
    p_all = np.concatenate(ps)
    r = float(np.corrcoef(y_all, p_all)[0, 1])
    mse = float(np.mean((y_all - p_all) ** 2))

    if args.converge and not np.isfinite(r):
        raise FloatingPointError("non-finite primary metric: PEARSON_R")
    ck_path = os.path.join(out_dir, "head.pt")
    torch.save(head.state_dict(), ck_path)
    peak = torch.cuda.max_memory_allocated(device) / (1 << 20)
    wall = round(time.time() - t0, 1)
    result = {
        "run_id": rid, "model": args.model, "task": args.task,
        "strategy": args.strategy, "seed": args.seed, "split": args.split,
        "metric": "PEARSON_R", "value": r, "mse": mse,
        "n_train": len(train), "n_test": len(test), "epochs": args.epochs,
        "lr": args.lr, "backbone_trainable": n_trainable,
        "wall_sec": wall, "peak_mem_mb": round(peak, 1),
        "ckpt_bytes": os.path.getsize(ck_path), "smoke": args.smoke,
    }
    if args.converge:
        result.update(tracker.result_fields())
        result.update(n_val=len(val), runtime=runtime,
                      data_evidence=data_evidence,
                      acceptance_eligible=not args.smoke)
    result_path = os.path.join(out_dir, "result.json")
    with open(result_path + ".tmp", "w") as fh:
        json.dump(result, fh, indent=2)
    os.replace(result_path + ".tmp", result_path)
    if args.converge:
        ledger.update(rid, "done", **vp.result_ledger_fields(result))
    else:
        ledger.update(rid, "done",
                      metric="PEARSON_R", value=r, mse=mse,
                      n_train=len(train), n_test=len(test),
                      epochs=args.epochs, lr=args.lr,
                      backbone_trainable=n_trainable,
                      wall_sec=wall, peak_mem_mb=round(peak, 1),
                      ckpt_bytes=os.path.getsize(ck_path))
    print(json.dumps({"run_id": rid, "pearson_r": round(r, 4),
                      "mse": round(mse, 4)}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
