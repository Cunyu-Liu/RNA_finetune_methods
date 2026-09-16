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
FAMILY_PARQUET = os.path.join(ROOT, "data", "family_splits",
                              "secondary-structure.parquet")


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
                    choices=["frozen", "lora", "head-only", "full",
                             "dora", "ia3", "prefix"])
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

    # run_id 编码 LR 维度（A8 协议，与 finetune_one/base 一致）
    lr_tag = "" if abs(args.lr - 3e-4) < 1e-12 else "_lr%g" % args.lr
    extra = ("_smoke" if args.smoke else "") + lr_tag
    rid = ledger.run_id(args.model, args.task, args.strategy, args.seed,
                        args.split, extra)
    out_dir = os.path.join(ROOT, "artifacts", rid)
    os.makedirs(out_dir, exist_ok=True)
    claim = ledger.claim(args.model, args.task, args.strategy, args.seed,
                         args.split, device=args.device, out_dir=out_dir,
                         extra=extra)
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
        train = ssp_task.load_split("TR0", meta, max_len=args.max_len)
        val = ssp_task.load_split("VL0", meta, max_len=args.max_len)
        test = ssp_task.load_split("TS0", meta, max_len=args.max_len)
    else:
        # family arm: use precomputed MMseqs2 cluster split (make_family_split_ssp)
        if not os.path.exists(FAMILY_PARQUET):
            print(json.dumps({"event": "SSP_FAMILY_SPLIT_MISSING",
                              "path": FAMILY_PARQUET}), flush=True)
            ledger.update(rid, "failed", note="family split parquet missing")
            return 3
        import pyarrow.parquet as pq
        tbl = pq.read_table(FAMILY_PARQUET).to_pydict()
        side_of = dict(zip(tbl["id"], tbl["split"]))
        union = []
        for split_name in ("TR0", "VL0", "TS0"):
            union += ssp_task.load_split(split_name, meta,
                                         max_len=args.max_len)
        # dedup by id (union may contain duplicates)
        seen = set()
        uniq = [r for r in union if not (r["id"] in seen or seen.add(r["id"]))]
        train = [r for r in uniq if side_of.get(r["id"]) == "train"]
        val = [r for r in uniq if side_of.get(r["id"]) == "val"]
        test = [r for r in uniq if side_of.get(r["id"]) == "test"]

    rng = random.Random(args.seed)
    train = rng.sample(train, min(args.n_train, len(train)))
    val = rng.sample(val, min(args.n_test, len(val)))
    test = rng.sample(test, min(args.n_test, len(test)))
    if args.smoke:
        train, val, test = train[:24], val[:24], test[:24]

    from .models import load_model
    from .strategies import apply_strategy
    spec, tok, backbone = load_model(args.model, device)

    # class balance: candidate pairs >> real pairs (pos_rate ~1%) ->
    # pos_weight so positives actually drive gradients (root cause of
    # all-negative collapse at threshold 0.5)
    pos = tot = 0
    for r in train:
        Lb = r["L"]
        pos += len(r.get("pairs", []))
        tot += Lb * (Lb - 1) // 2
    pw = float(min(200.0, max(1.0, (tot - pos) / max(1, pos))))
    print("pos_weight %.1f (pos %d / cand %d)" % (pw, pos, tot), flush=True)

    with torch.no_grad():
        probe = encode_one(tok, [train[0]["seq"]], device, args.max_len)
        d = backbone(**probe).last_hidden_state.shape[-1]
    backbone, n_trainable = apply_strategy(backbone, args.strategy)
    head = PairHead(d).to(device)
    params = [p for p in head.parameters() if p.requires_grad] + \
        [p for p in backbone.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(params, lr=args.lr)
    pw_t = torch.tensor(pw, device=device)

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
                S[bi], y, reduction="none",
                pos_weight=pw_t)[m].mean()
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

    # ---- eval: pair-level F1, threshold tuned on val ----
    backbone.eval()
    head.eval()

    def collect_scores(recs):
        preds, golds, scores = [], [], []
        with torch.no_grad():
            for i in range(0, len(recs), args.batch_size * 2):
                b = recs[i:i + args.batch_size * 2]
                enc, S, tm, _ = run_batch(b, False)
                Ssm = torch.sigmoid(S)
                for bi, r in enumerate(b):
                    Lb = r["L"]
                    s = Ssm[bi, :Lb, :Lb].cpu().numpy()
                    scores.append(s)
                    golds.append(set(map(tuple, r.get("pairs", []))))
                    preds.append(None)  # filled after threshold chosen
        return scores, golds

    val_scores, val_golds = collect_scores(val)

    def f1_at(thr: float, scores, golds) -> float:
        tp = fp = fn = 0
        for s, g in zip(scores, golds):
            p = {(i, j) for i in range(s.shape[0])
                 for j in range(i + 1, s.shape[0]) if s[i, j] > thr}
            tp += len(p & g)
            fp += len(p - g)
            fn += len(g - p)
        prec = tp / max(1, tp + fp)
        rec = tp / max(1, tp + fn)
        return 2 * prec * rec / max(1e-9, prec + rec)

    best_thr, best_f1 = 0.5, -1.0
    for thr in (0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9):
        f = f1_at(thr, val_scores, val_golds)
        if f > best_f1:
            best_f1, best_thr = f, thr
    print("val threshold sweep: best thr=%.2f val F1=%.4f" %
          (best_thr, best_f1), flush=True)

    test_scores, test_golds = collect_scores(test)
    preds = [{(i, j) for i in range(s.shape[0])
              for j in range(i + 1, s.shape[0]) if s[i, j] > best_thr}
             for s in test_scores]
    m = pair_f1(preds, test_golds)
    m["threshold"] = best_thr
    m["val_f1"] = round(best_f1, 4)

    wall = time.time() - t0
    peak = torch.cuda.max_memory_allocated(args.device) / (1 << 20)
    result = {
        "run_id": rid, "model": args.model, "task": args.task,
        "strategy": args.strategy, "seed": args.seed, "split": args.split,
        "metric": "F1", "value": m["f1"], "precision": m["precision"],
        "recall": m["recall"], "threshold": m["threshold"],
        "val_f1": m["val_f1"], "pos_weight": round(pw, 1),
        "n_train": len(train), "n_test": len(test),
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
