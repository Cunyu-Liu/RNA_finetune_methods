"""SSP traditional baselines: local pairing rules + LGBM pair classifier.

Baselines for secondary structure (B5 收益口径: LM − 最强基线):
  1. bracket_prior: canonical Watson-Crick/GU pair prior, no learning
     (predict all (i,j) with complementary nt as pairs — precision/recall
     floor; deliberately naive, the "no-context" reference)
  2. kmer_lgbm_pair: per-pair LightGBM with local features
     (nt_i, nt_j, |i-j|, local windows, sequence base composition)

Same TR0/TS0 (random arm) or family split as the LM runs.

Usage:
  python -m rnafteval.baselines_ssp --split random [--n-train 2000]
"""
from __future__ import annotations

import argparse
import json
import os
import random

import numpy as np

from .tasks import ssp as ssp_task

ROOT = "/mnt/cunyuliu/rna-ft-eval"

COMP = {"A": "U", "U": "A", "G": "C", "C": "G"}
CANON = {("A", "U"), ("U", "A"), ("G", "C"), ("C", "G"),
         ("G", "U"), ("U", "G")}


def bracket_prior_preds(rec: dict) -> set:
    """Naive complementary-pair baseline (predict ALL complementary pairs)."""
    seq = rec["seq"]
    L = rec["L"]
    out = set()
    for i in range(L):
        for j in range(i + 1, L):
            if (seq[i], seq[j]) in CANON:
                out.add((i, j))
    return out


def pair_local_features(seq: str, i: int, j: int) -> list:
    nt_id = {"A": 0, "C": 1, "G": 2, "U": 3}
    x = [nt_id.get(seq[i], 4), nt_id.get(seq[j], 4),
         abs(i - j), i, j, len(seq)]
    # local composition windows (i, j)
    for center, w in ((i, 0), (j, 0)):
        lo, hi = max(0, center - 3), min(len(seq), center + 4)
        win = seq[lo:hi]
        for c in "ACGU":
            x.append(win.count(c))
    return x


def sample_pairs(recs: list[dict], rng: random.Random,
                 neg_ratio: int = 3) -> tuple[np.ndarray, np.ndarray]:
    X, y = [], []
    for r in recs:
        pairs = set(map(tuple, r.get("pairs", [])))
        L = r["L"]
        seq = r["seq"]
        pos = list(pairs)
        # negatives: non-paired (i, j) with i<j, restricted to same span
        # distribution as positives (span-matched negatives avoid the
        # trivially-easy far-apart negatives)
        neg = []
        if pos:
            for _ in range(len(pos) * neg_ratio):
                pi = rng.choice(pos)
                span = abs(pi[1] - pi[0])
                i = rng.randrange(0, max(1, L - span - 1))
                j = i + span
                if i < j < L and (i, j) not in pairs:
                    neg.append((i, j))
        else:
            for _ in range(4 * neg_ratio):
                i = rng.randrange(0, L)
                j = rng.randrange(0, L)
                if i < j and (i, j) not in pairs:
                    neg.append((i, j))
        for p in pos:
            X.append(pair_local_features(seq, *p))
            y.append(1)
        for p in neg:
            X.append(pair_local_features(seq, *p))
            y.append(0)
    return np.array(X, dtype=np.float32), np.array(y, dtype=np.int8)


def pair_f1(preds: list[set], golds: list[set]) -> dict:
    tp = fp = fn = 0
    for p, g in zip(preds, golds):
        tp += len(p & g)
        fp += len(p - g)
        fn += len(g - p)
    prec = tp / max(1, tp + fp)
    rec = tp / max(1, tp + fn)
    f1 = 2 * prec * rec / max(1e-9, prec + rec)
    return {"precision": round(prec, 4), "recall": round(rec, 4),
            "f1": round(f1, 4)}


def lgbm_predict(rec: dict, model, rng: random.Random) -> set:
    seq, L = rec["seq"], rec["L"]
    X = []
    ij = []
    for i in range(L):
        for j in range(i + 1, L):
            X.append(pair_local_features(seq, i, j))
            ij.append((i, j))
    if not ij:
        return set()
    P = model.predict_proba(np.array(X, dtype=np.float32))[:, 1]
    return {p for p, s in zip(ij, P) if s > 0.5}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="random", choices=["random", "family"])
    ap.add_argument("--n-train", type=int, default=1500)
    ap.add_argument("--n-test", type=int, default=300)
    ap.add_argument("--max-len", type=int, default=192)
    args = ap.parse_args()

    rng = random.Random(17)
    meta = ssp_task.load_metadata()
    if not meta:
        print(json.dumps({"event": "SSP_META_MISSING"}))
        return 3
    if args.split == "random":
        train = ssp_task.load_split("TR0", meta, max_len=args.max_len)
        test = ssp_task.load_split("TS0", meta, max_len=args.max_len)
    else:
        # family arm: precomputed MMseqs2 cluster split (make_family_split_ssp)
        fam_parquet = os.path.join(
            ROOT, "data", "family_splits", "secondary-structure.parquet")
        if not os.path.exists(fam_parquet):
            print(json.dumps({"event": "SSP_FAMILY_SPLIT_MISSING"}))
            return 3
        import pyarrow.parquet as pq
        tbl = pq.read_table(fam_parquet).to_pydict()
        side_of = dict(zip(tbl["id"], tbl["split"]))
        union = []
        for split_name in ("TR0", "VL0", "TS0"):
            union += ssp_task.load_split(split_name, meta,
                                         max_len=args.max_len)
        seen = set()
        uniq = [r for r in union if not (r["id"] in seen or seen.add(r["id"]))]
        train = [r for r in uniq if side_of.get(r["id"]) == "train"]
        test = [r for r in uniq if side_of.get(r["id"]) == "test"]

    train = rng.sample(train, min(args.n_train, len(train)))
    test = rng.sample(test, min(args.n_test, len(test)))

    results = {}

    # --- baseline 1: bracket prior ---
    preds = [bracket_prior_preds(r) for r in test]
    golds = [set(map(tuple, r.get("pairs", []))) for r in test]
    results["bracket_prior"] = pair_f1(preds, golds)
    print("bracket_prior:", results["bracket_prior"], flush=True)

    # --- baseline 2: kmer/lgbm pair classifier ---
    Xtr, ytr = sample_pairs(train, rng)
    print("pair features:", Xtr.shape, "pos_rate=%.4f" %
          (ytr.mean() if len(ytr) else 0), flush=True)
    import lightgbm as lgb
    m = lgb.LGBMClassifier(n_estimators=300, num_leaves=63, n_jobs=32,
                           verbose=-1)
    m.fit(Xtr, ytr)
    preds = [lgbm_predict(r, m, rng) for r in test]
    results["kmer_lgbm_pair"] = pair_f1(preds, golds)
    print("kmer_lgbm_pair:", results["kmer_lgbm_pair"], flush=True)

    out = {"task": "secondary-structure", "split": args.split,
           "metric": "F1", "results": results,
           "n_train": len(train), "n_test": len(test),
           "max_len": args.max_len}
    path = os.path.join(ROOT, "artifacts",
                        "baseline_secondary-structure_%s.json" % args.split)
    with open(path, "w") as fh:
        json.dump(out, fh, indent=2)
    print("saved", path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
