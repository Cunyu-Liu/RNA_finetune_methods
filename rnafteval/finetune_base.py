"""Per-base task runner: modification (m6A-style) — token head + BCE.

Usage:
  python -m rnafteval.finetune_base --model RNA-Sc-10M --task modification \
      --strategy frozen --seed 17 --split random --device 6 --epochs 3

Eval metric: AUC over all base positions (BEACON official), plus
per-sequence mean AUC fallback if needed.
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
from .tasks import modification as mod_task

ROOT = "/mnt/cunyuliu/rna-ft-eval"


def encode_seqs(tok, seqs, device, max_len=128):
    enc = tok(seqs, padding=True, truncation=True, max_length=max_len,
              return_tensors="pt")
    return {k: v.to(device) for k, v in enc.items()}


def batches(rows, bs):
    for i in range(0, len(rows), bs):
        yield rows[i:i + bs]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--task", default="modification")
    ap.add_argument("--strategy", required=True,
                    choices=["frozen", "lora", "head-only", "full",
                             "dora", "ia3", "prefix"])
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--split", required=True, choices=["random", "family"])
    ap.add_argument("--device", type=int, required=True)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--batch-size", type=int, default=32)
    ap.add_argument("--n-train", type=int, default=20000,
                    help="subsample of train for wall-time control")
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()

    if not torch.cuda.is_available():
        print(json.dumps({"event": "CUDA_UNAVAILABLE_ABORT"}), flush=True)
        return 2
    torch.cuda.set_device(args.device)
    device = "cuda:%d" % args.device
    torch.manual_seed(args.seed)
    random.seed(args.seed)

    rid = ledger.run_id(args.model, args.task, args.strategy, args.seed,
                        args.split, "_smoke" if args.smoke else "")
    out_dir = os.path.join(ROOT, "artifacts", rid)
    os.makedirs(out_dir, exist_ok=True)
    claim = ledger.claim(args.model, args.task, args.strategy, args.seed,
                         args.split, device=args.device, out_dir=out_dir,
                         extra="_smoke" if args.smoke else "")
    if not claim["claimed"]:
        print("skip (already %s)" % claim["row"]["status"])
        return 0

    t0 = time.time()
    torch.cuda.reset_peak_memory_stats(args.device)

    if args.split == "family":
        # cluster-pure split (make_family_split_mod): host-transcript proxy
        # via MMseqs2 80-80 on overlapping 101-nt windows
        import pyarrow.parquet as pq
        fam = os.path.join(ROOT, "data", "family_splits", "modification.parquet")
        if not os.path.exists(fam):
            print("family split missing: %s" % fam, flush=True)
            ledger.update(rid, "failed", note="modification family parquet missing")
            return 3
        t = pq.read_table(fam).to_pydict()
        by_side = {}
        for seq, lab, sd in zip(t["seq"], t["labels"], t["split"]):
            if sd == "train":
                by_side.setdefault("train", []).append(
                    {"seq": seq, "labels": [int(x) for x in str(lab).split()],
                     "subset": "family_%s" % sd})
            elif sd == "test":
                by_side.setdefault("test", []).append(
                    {"seq": seq, "labels": [int(x) for x in str(lab).split()],
                     "subset": "family_%s" % sd})
        train, test = by_side["train"], by_side["test"]
        rng = random.Random(17)
        train = rng.sample(train, min(args.n_train, len(train)))
    else:
        sp = mod_task.load_official_split()
        train = sp["train"]
        test = sp["test"]
        rng = random.Random(17)
        train = rng.sample(train, min(args.n_train, len(train)))
    if args.smoke:
        train = train[:320]
        test = test[:320]

    from .models import load_model
    from .strategies import apply_strategy, TokenHead
    spec, tok, backbone = load_model(args.model, device)
    with torch.no_grad():
        probe = encode_seqs(tok, [train[0]["seq"]], device, 128)
        d = backbone(**probe).last_hidden_state.shape[-1]
    backbone, n_trainable = apply_strategy(backbone, args.strategy)
    # token-level BCE head: outputs 1 logit per token
    head = TokenHead(d, 1, hidden=32).to(device)
    train_params = [p for p in head.parameters() if p.requires_grad] + \
        [p for p in backbone.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(train_params, lr=args.lr)

    def make_batch(b):
        enc = encode_seqs(tok, [r["seq"] for r in b], device, 128)
        L = enc["input_ids"].shape[1]
        y = torch.zeros(len(b), L, device=device)
        for i, r in enumerate(b):
            labs = r["labels"][:L]
            y[i, :len(labs)] = torch.tensor(labs, dtype=torch.float32,
                                            device=device)
        return enc, y

    for ep in range(args.epochs):
        backbone.train(args.strategy in ("lora", "full"))
        head.train()
        tot, nb = 0.0, 0
        for b in batches(train, args.batch_size):
            enc, y = make_batch(b)
            no_grad = args.strategy in ("frozen", "head-only")
            import contextlib
            with contextlib.nullcontext() if not no_grad \
                    else torch.no_grad():
                h = backbone(**enc).last_hidden_state
            pad = enc["attention_mask"] == 0
            logits = head(h, pad).squeeze(-1)
            mask = enc["attention_mask"].float()
            loss = torch.nn.functional.binary_cross_entropy_with_logits(
                logits, y, reduction="none") * mask
            loss = loss.sum() / mask.sum().clamp(min=1)
            opt.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(train_params, 1.0)
            opt.step()
            tot += loss.item()
            nb += 1
        print("epoch %d loss %.4f" % (ep, tot / max(nb, 1)), flush=True)

    # --- eval: AUC over non-pad positions ---
    backbone.eval()
    head.eval()
    ys, ps = [], []
    with torch.no_grad():
        for b in batches(test, args.batch_size * 2):
            enc, y = make_batch(b)
            h = backbone(**enc).last_hidden_state
            pad = enc["attention_mask"] == 0
            logits = head(h, pad).squeeze(-1)
            m = enc["attention_mask"].bool()
            ys.append(y[m].cpu().numpy())
            ps.append(torch.sigmoid(logits[m]).cpu().numpy())
    from sklearn.metrics import roc_auc_score
    y_all = np.concatenate(ys)
    p_all = np.concatenate(ps)
    auc = float(roc_auc_score(y_all, p_all)) if len(set(y_all.tolist())) > 1 \
        else float("nan")

    wall = time.time() - t0
    peak = torch.cuda.max_memory_allocated(args.device) / (1 << 20)
    result = {
        "run_id": rid, "model": args.model, "task": args.task,
        "strategy": args.strategy, "seed": args.seed, "split": args.split,
        "metric": "AUC", "value": auc, "n_train": len(train),
        "n_test": len(test), "wall_sec": round(wall, 1),
        "peak_mem_mb": round(peak, 1),
        "backbone_trainable": n_trainable, "lr": args.lr,
        "epochs": args.epochs, "smoke": args.smoke,
    }
    with open(os.path.join(out_dir, "result.json"), "w") as fh:
        json.dump(result, fh, indent=2)
    ledger.update(rid, "done", **{k: v for k, v in result.items()
                                  if k != "run_id"})
    print(json.dumps(result, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
