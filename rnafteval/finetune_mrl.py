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

from . import ledger
from .strategies import apply_strategy, make_head

ROOT = "/mnt/cunyuliu/rna-ft-eval"


def encode_seqs(tok, seqs, device, max_len=64):
    enc = tok(seqs, padding=True, truncation=True, max_length=max_len,
              return_tensors="pt")
    return {k: v.to(device) for k, v in enc.items()}


def batches(rows, bs):
    for i in range(0, len(rows), bs):
        yield rows[i:i + bs]


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
    args = ap.parse_args()

    if not torch.cuda.is_available():
        print(json.dumps({"event": "CUDA_UNAVAILABLE_ABORT"}), flush=True)
        return 2
    torch.cuda.set_device(args.device)
    device = "cuda:%d" % args.device
    torch.manual_seed(args.seed)
    random.seed(args.seed)

    lr_tag = "" if abs(args.lr - 3e-4) < 1e-12 else "_lr%g" % args.lr
    e3_tag = ("_e3%d" % args.n_train) if args.n_train != 20000 else ""
    extra = ("_smoke" if args.smoke else "") + e3_tag + lr_tag
    rid = ledger.run_id(args.model, args.task, args.strategy, args.seed,
                        args.split, extra)
    out_dir = os.path.join(ROOT, "artifacts", rid)
    os.makedirs(out_dir, exist_ok=True)
    claim = ledger.claim(args.model, args.task, args.strategy, args.seed,
                         args.split, device=args.device, out_dir=out_dir,
                         extra=extra)
    if not claim["claimed"]:
        print("skip (already %s)" % claim["row"]["status"])
        return 0

    t0 = time.time()
    from .tasks import mrl as mrl_task

    if args.split == "family":
        import pyarrow.parquet as pq
        fam = os.path.join(ROOT, "data", "family_splits", "mrl.parquet")
        if not os.path.exists(fam):
            ledger.update(rid, "failed", note="mrl family parquet missing")
            return 3
        t = pq.read_table(fam).to_pydict()
        train = [{"seq": s, "label": float(l)}
                 for s, l, sd in zip(t["seq"], t["label"], t["split"])
                 if sd == "train"]
        test = [{"seq": s, "label": float(l)}
                for s, l, sd in zip(t["seq"], t["label"], t["split"])
                if sd == "test"]
        rng = random.Random(17)
        train = rng.sample(train, min(args.n_train, len(train)))
    else:
        sp = mrl_task.load_official_split(
            os.path.join(ROOT, "data", "beacon_raw",
                         "mean-ribosome-loading", "data"))
        train, test = sp["train"], sp["test"]
        rng = random.Random(17)
        train = rng.sample(train, min(args.n_train, len(train)))
    if args.smoke:
        train, test = train[:320], test[:320]

    from .models import load_model
    spec, tok, backbone = load_model(args.model, device)
    with torch.no_grad():
        probe = encode_seqs(tok, [train[0]["seq"]], device, args.max_len)
        d = backbone(**probe).last_hidden_state.shape[-1]
    backbone, n_trainable = apply_strategy(backbone, args.strategy)
    head = make_head("per-seq", d, 1).to(device)
    params = [p for p in head.parameters() if p.requires_grad] + \
        [p for p in backbone.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(params, lr=args.lr)
    lossf = torch.nn.MSELoss()

    def run_batch(b):
        enc = encode_seqs(tok, [r["seq"] for r in b], device, args.max_len)
        y = torch.tensor([r["label"] for r in b], dtype=torch.float32,
                         device=device)
        return enc, y

    for ep in range(args.epochs):
        backbone.train(args.strategy in ("lora", "full", "dora", "ia3"))
        head.train()
        tot, nb = 0.0, 0
        for b in batches(train, args.batch_size):
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
        print("epoch %d loss %.4f" % (ep, tot / max(nb, 1)), flush=True)

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

    ck_path = os.path.join(out_dir, "head.pt")
    torch.save(head.state_dict(), ck_path)
    ledger.update(rid, "done",
                  metric="PEARSON_R", value=r, mse=mse,
                  n_train=len(train), n_test=len(test),
                  epochs=args.epochs, lr=args.lr,
                  backbone_trainable=n_trainable,
                  wall_s=round(time.time() - t0, 1),
                  ckpt_bytes=os.path.getsize(ck_path))
    print(json.dumps({"run_id": rid, "pearson_r": round(r, 4),
                      "mse": round(mse, 4)}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
