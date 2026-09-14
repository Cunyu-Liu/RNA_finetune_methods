"""SSP finetune runner — pair-level F1, symmetric double-head scoring.

Usage:
  python -m rnafteval.finetune_ssp --model RNA-Sc-10M \
      --strategy frozen --seed 17 --split random --device 6 --epochs 3

Protocol (BEACON-aligned):
  - head: Linear(D, 1) applied to [h_i ; h_j ; h_i - h_j ; h_i * h_j]
    (pair representation, symmetric in (i, j) up to sign features)
  - scores S[i, j] for i < j (upper triangle); predict pair set {S > 0}
  - metric: pair-level precision / recall / F1 pooled over all sequences
    (official BEACON SSP口径)
  - split: random arm = official TR0/VL0/TS0; family arm = cluster split
    from make_family_split.py output (ssp_family_ids.json)
Discipline: GPU-only, ledger claim/update, wall/peak recorded.
"""
from __future__ import annotations

import argparse
import contextlib
import json
import os
import random
import time

import numpy as np
import torch
import torch.nn as nn

from . import ledger
from .tasks import ssp as ssp_task

ROOT = "/mnt/cunyuliu/rna-ft-eval"
FAMILY_IDS_PATH = os.path.join(ROOT, "artifacts", "ssp_family_ids.json")


class PairHead(nn.Module):
    """Symmetric pair scorer: s(i,j) = w·f(h_i, h_j), f built so that
    f(h_i,h_j) and f(h_j,h_i) give the same score (min/max canonical)."""

    def __init__(self, d_model: int, hidden: int = 32):
        super().__init__()
        self.proj = nn.Linear(d_model, hidden)
        self.pw = nn.Linear(4 * hidden, 1)

    def forward(self, h: torch.Tensor, pad: torch.Tensor) -> torch.Tensor:
        # h: (B, T, D); pad: (B, T) True at pad
        z = torch.nn.functional.gelu(self.proj(h))        # (B, T, H)
        B, T, H = z.shape
        # pair features via broadcasting; canonical order (i<j) only
        zi = z.unsqueeze(2).expand(B, T, T, H)
        zj = z.unsqueeze(1).expand(B, T, T, H)
        lo = torch.minimum(zi, zj)
        hi = torch.maximum(zi, zj)
        prod = zi * zj
        diff = hi - lo
        feats = torch.cat([lo, hi, prod, diff], dim=-1)    # (B, T, T, 4H)
        s = self.pw(feeds_core(feats)).squeeze(-1)         # (B, T, T)
        return s


def feeds_core(x):
    return x


def batchify(recs, bs):
    for i in range(0, len(recs), bs):
        yield recs[i:i + bs]


def make_target(rec, device) -> torch.Tensor:
    """(L, L) float target from dot-bracket pairs (i<j)."""
    L = rec["L"]
    y = torch.zeros(L, L, device=device)
    for i, j in rec.get("pairs", []):
        y[i, j] = 1.0
        y[j, i] = 1.0          # symmetric target; loss on upper triangle
    return y


def encode_one(tok, seqs, device, max_len):
    enc = tok(seqs, padding=True, truncation=True, max_length=max_len,
              return_tensors="pt")
    return {k: v.to(device) for k, v in enc.items()}


def pair_f1(all_pred: list[set], all_gold: list[set]) -> dict:
    tp = fp = fn = 0
    for p, g in zip(all_pred, all_gold):
        tp += len(p & g)
        fp += len(p - g)
        fn += len(g - p)
    prec = tp / max(1, tp + fp)
    rec = tp / max(1, tp + fn)
    f1 = 2 * prec * rec / max(1e-9, prec + rec)
    return {"precision": round(prec, 4), "recall": round(rec, 4),
            "f1": round(f1, 4), "tp": tp, "fp": fp, "fn": fn}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--task", default="secondary-structure")
    ap.add_argument("--strategy", required=True,
                    choices=["frozen", "lora", "head-only", "full"])
    ap.add_argument("--seed", type=int, default=17)
    ap.add_argument("--split", default="random",
                    choices=["random", "family"])
    ap.add_argument("--device", type=int, required=True)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--batch-size", type=int, default=4)
    ap.add_argument("--max-len", type=int, default=192)
    ap.add_argument("--n-train", type=int, default=2000)
    ap.add_argument("--n-test", type=int, default=400)
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
        print("skip (already %s): %s" % (claim["row"]["status"], rid))
        return 0

    t0 = time.time()
    torch.cuda.reset_peak_memory_stats(args.device)

    # ---- data ----
    meta = ssp_task.load_metadata()
    if not meta:
        print(json.dumps({"event": "SSP_META_MISSING",
                          "path": ssp_task.BPRNA}), flush=True)
        ledger.update(rid, "failed", note="bpRNA.csv missing")
        return 3
    if args.split == "random":
        train = ssp_task.load_split("TR0", meta,
                                    max_len=args.max_len)
        test = ssp_task.load_split("TS0", meta, max_len=args.max_len)
    else:
        # family arm: cluster-based split over the union
        fam_ids = {}
        if os.path.exists(FAMILY_IDS_PATH):
            fam_ids = json.load(open(FAMILY_IDS_PATH))
        union = (ssp_task.load_split("TR0", meta, max_len=args.max_len) +
                 ssp_task.load_split("VL0", meta, max_len=args.max_len) +
                 ssp_task.load_split("TS0", meta, max_len=args.max_len))
        if fam_ids:
            for r in union:
                r["family"] = fam_ids.get(r["id"], r["family"])
        from .splits import family_split
        sp = family_split(union, family_key="family", seed=args.seed)
        train, test = sp["train"], sp["test"]

    rng = random.Random(args.seed)
    train = rng.sample(train, min(args.n_train, len(train)))
    test = rng.sample(test, min(args.n_test, len(test)))
    if args.smoke:
        train, test = train[:24], test[:24]

    from .models import load_model
    from .strategies import apply_strategy
    spec, tok, backbone = load_model(args.model, device)
    with torch.no_grad():
        probe = encode_one(tok, [train[0]["seq"]], device, args.max_len)
        d = backbone(**probe).last_hidden_state.shape[-1]
    backbone, n_trainable = apply_strategy(backbone, args.strategy)
    head = PairHead(d).to(device)
    params = [p for p in head.parameters() if p.requires_grad] + \
        [p for p in backbone.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(params, lr=args.lr)

    def run_batch(b, train_mode: bool):
        enc = encode_one(tok, [r["seq"] for r in b], device, args.max_len)
        L = enc["input_ids"].shape[1]
        no_grad = train_mode and args.strategy in ("frozen", "head-only")
        ctx = torch.no_grad() if no_grad else contextlib.nullcontext()
        with ctx:
            h = backbone(**enc).last_hidden_state
        pad = enc["attention_mask"] == 0
        S = head(h, pad)                     # (B, T, T)
        # loss over non-pad upper triangle
        total, n = 0.0, 0
        loss = torch.tensor(0.0, device=device)
        tri_masks = []
        for bi, r in enumerate(b):
            Lb = min(r["L"], L)
            m = torch.zeros(L, L, device=device, dtype=torch.bool)
            m[:Lb, :Lb] = torch.triu(
                torch.ones(Lb, Lb, device=device, dtype=torch.bool), 1)
            tri_masks.append(m)
            y = torch.zeros(L, L, device=device)
            for i, j in r.get("pairs", []):
                if i < L and j < L:
                    y[i, j] = 1.0
                    y[j, i] = 1.0
            loss = loss + torch.nn.functional.binary_cross_entropy_with_logits(
                S[bi], y, reduction="none")[m].mean()
        loss = loss / len(b)
        return enc, S, tri_masks, loss

    for ep in range(args.epochs):
        backbone.train(args.strategy in ("lora", "full"))
        head.train()
        tot, nb = 0.0, 0
        order = list(range(len(train)))
        rng.shuffle(order)
        for i in range(0, len(order), args.batch_size):
            b = [train[k] for k in order[i:i + args.batch_size]]
            enc, S, tm, loss = run_batch(b, True)
            opt.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(params, 1.0)
            opt.step()
            tot += float(loss.item())
            nb += 1
        print("epoch %d loss %.4f" % (ep, tot / max(nb, 1)), flush=True)

    # ---- eval: pair-level F1 ----
    backbone.eval()
    head.eval()
    preds, golds = [], []
    with torch.no_grad():
        for i in range(0, len(test), args.batch_size * 2):
            b = test[i:i + args.batch_size * 2]
            enc, S, tm, _ = run_batch(b, False)
            Ssm = torch.sigmoid(S)
            for bi, r in enumerate(b):
                Lb = r["L"]
                s = Ssm[bi, :Lb, :Lb].cpu().numpy()
                pred = {(i, j) for i in range(Lb) for j in range(i + 1, Lb)
                        if s[i, j] > 0.5}
                preds.append(pred)
                golds.append(set(map(tuple, r.get("pairs", []))))
    m = pair_f1(preds, golds)

    wall = time.time() - t0
    peak = torch.cuda.max_memory_allocated(args.device) / (1 << 20)
    result = {
        "run_id": rid, "model": args.model, "task": args.task,
        "strategy": args.strategy, "seed": args.seed, "split": args.split,
        "metric": "F1", "value": m["f1"], "precision": m["precision"],
        "recall": m["recall"], "n_train": len(train), "n_test": len(test),
        "wall_sec": round(wall, 1), "peak_mem_mb": round(peak, 1),
        "backbone_trainable": n_trainable, "lr": args.lr,
        "epochs": args.epochs, "max_len": args.max_len,
        "smoke": args.smoke,
    }
    with open(os.path.join(out_dir, "result.json"), "w") as fh:
        json.dump(result, fh, indent=2)
    ledger.update(rid, "done", **{k: v for k, v in result.items()
                                  if k != "run_id"})
    print(json.dumps(result, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
