"""m6A per-base traditional baselines: k-mer logistic regression + LGBM.

Per-position features: flanking k-mer one-hot (k=5 window) + position
features. Random arm = official BEACON split; family arm = cluster-pure
host-proxy split (make_family_split_mod).

Usage: python -m rnafteval.baselines_mod --split random
"""
from __future__ import annotations

import argparse
import json
import os
import random

import numpy as np

from .tasks import modification as mod_task

ROOT = "/mnt/cunyuliu/rna-ft-eval"
BEACON_RAW = os.path.join(ROOT, "data", "beacon_raw")


def load_split(split: str):
    if split == "family":
        import pyarrow.parquet as pq
        fam = os.path.join(ROOT, "data", "family_splits", "modification.parquet")
        t = pq.read_table(fam).to_pydict()
        by_side = {"train": [], "test": []}
        for seq, lab, sd in zip(t["seq"], t["labels"], t["split"]):
            if sd in by_side:
                by_side[sd].append(
                    {"seq": seq, "labels": [int(x) for x in str(lab).split()]})
        return by_side
    sp = mod_task.load_official_split()
    return {"train": sp["train"], "test": sp["test"]}


def position_features(seq: str, i: int, K: int = 5) -> list:
    """Flanking k-mer one-hot at position i + center nt id + rel position."""
    nt = {"A": 0, "C": 1, "G": 2, "U": 3}
    lo = max(0, i - K)
    hi = min(len(seq), i + K + 1)
    win = seq[lo:hi].replace("T", "U")
    # positional slot: offset of j within the full 2K+1 window
    x = [0.0] * (4 * (2 * K + 1))
    for j, ch in enumerate(win):
        idx = nt.get(ch, 4)
        if idx < 4:
            x[4 * j + idx] = 1.0
    return x + [i / max(1, len(seq)), float(i == len(seq) // 2)]


def build_xy(recs, rng, n_pos_cap=200000):
    X, y = [], []
    pos_idx = [(r, i) for r in recs for i, lab in enumerate(r["labels"]) if lab == 1]
    neg_idx = [(r, i) for r in recs for i, lab in enumerate(r["labels"]) if lab == 0]
    rng.shuffle(pos_idx)
    rng.shuffle(neg_idx)
    n_pos = min(len(pos_idx), n_pos_cap // 4)
    n_neg = min(len(neg_idx), 3 * n_pos)
    for r, i in pos_idx[:n_pos] + neg_idx[:n_neg]:
        X.append(position_features(r["seq"], i))
        y.append(r["labels"][i])
    return np.array(X, dtype=np.float32), np.array(y, dtype=np.int8)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="random", choices=["random", "family"])
    ap.add_argument("--n-train", type=int, default=2000,
                    help="number of train windows (per-base positions sampled)")
    args = ap.parse_args()

    parts = load_split(args.split)
    rng = random.Random(17)
    train = rng.sample(parts["train"], min(args.n_train, len(parts["train"])))
    test = parts["test"]

    Xtr, ytr = build_xy(train, rng)
    print("train pairs: pos=%d neg=%d" % (int(ytr.sum()), int((ytr == 0).sum())),
          flush=True)

    results = {}
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score
    clf = LogisticRegression(max_iter=2000, C=1.0, n_jobs=32)
    clf.fit(Xtr, ytr)

    import lightgbm as lgb
    m = lgb.LGBMClassifier(n_estimators=300, num_leaves=63, n_jobs=32,
                           verbose=-1)
    m.fit(Xtr, ytr)

    Xte, yte = build_xy(test, rng, n_pos_cap=200000)
    for name, mdl in (("kmer_logreg", clf), ("kmer_lgbm", m)):
        p = mdl.predict_proba(Xte)[:, 1]
        auc = float(roc_auc_score(yte, p))
        results[name] = {"auc": round(auc, 4)}
        print("%s AUC: %.4f" % (name, auc), flush=True)

    out = {"task": "modification", "split": args.split, "metric": "AUC",
           "results": results, "n_train_windows": len(train),
           "n_test_pairs": len(yte)}
    path = os.path.join(ROOT, "artifacts",
                        "baseline_modification_%s.json" % args.split)
    with open(path, "w") as fh:
        json.dump(out, fh, indent=2)
    print("saved", path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
