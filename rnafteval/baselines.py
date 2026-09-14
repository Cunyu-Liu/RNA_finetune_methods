"""Traditional baselines: k-mer logistic regression + LightGBM (spec T1.3.7).

Same data / same split as the LM runs (B5: 预训练收益 = LM − 最强基线).
Usage: python -m rnafteval.baselines --task noncoding-rna-family --split random
"""
from __future__ import annotations

import argparse
import json
import os

import numpy as np

ROOT = "/mnt/cunyuliu/rna-ft-eval"
BEACON_RAW = os.path.join(ROOT, "data", "beacon_raw")

KMER_KS = (1, 2, 3, 4, 5, 6)


def kmer_features(seqs: list[str], k_list=KMER_KS) -> np.ndarray:
    """Sparse-friendly k-mer count via hashing (fixed dim)."""
    from collections import defaultdict
    dim = 4 ** max(k_list)
    X = np.zeros((len(seqs), len(k_list) * 4096), dtype=np.float32)
    for i, s in enumerate(seqs):
        s = s.upper().replace("U", "T")
        for j, k in enumerate(k_list):
            for p in range(len(s) - k + 1):
                km = s[p:p + k]
                # rolling hash into 4096 buckets per k
                h = 0
                for ch in km:
                    h = (h * 5 + ord(ch)) % 4096
                X[i, j * 4096 + h] += 1
    # L2 normalize per row
    norms = np.linalg.norm(X, axis=1, keepdims=True)
    norms[norms == 0] = 1
    return X / norms


def load_data(split: str):
    from .tasks import ncrna
    from .tasks.dedup import dedup
    from .splits import random_split
    recs = ncrna.load_ncrna(
        os.path.join(BEACON_RAW, "noncoding-rna-family", "data"))
    recs = dedup(recs)
    if split == "family":
        import pyarrow.parquet as pq
        t = pq.read_table(os.path.join(ROOT, "data", "family_splits",
                                       "noncoding-rna-family.parquet"))
        d = t.to_pydict()
        allr = [{"seq": s, "label": int(l)} for s, l in zip(d["seq"], d["label"])]
        parts = {k: [r for r, sp in zip(allr, d["split"]) if sp == k]
                 for k in ("train", "val", "test")}
    else:
        parts = random_split(recs, seed=17)
    return parts


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", default="noncoding-rna-family")
    ap.add_argument("--split", default="random")
    args = ap.parse_args()

    parts = load_data(args.split)
    Xtr = kmer_features([r["seq"] for r in parts["train"]])
    Xte = kmer_features([r["seq"] for r in parts["test"]])
    ytr = np.array([r["label"] for r in parts["train"]])
    yte = np.array([r["label"] for r in parts["test"]])
    print("features:", Xtr.shape, flush=True)

    results = {}

    from sklearn.linear_model import LogisticRegression
    clf = LogisticRegression(max_iter=2000, C=1.0, n_jobs=16)
    clf.fit(Xtr, ytr)
    results["kmer_logreg"] = float(clf.score(Xte, yte))
    print("kmer_logreg ACC:", results["kmer_logreg"], flush=True)

    import lightgbm as lgb
    m = lgb.LGBMClassifier(n_estimators=400, num_leaves=63, n_jobs=16,
                           verbose=-1)
    m.fit(Xtr, ytr)
    results["kmer_lgbm"] = float(m.score(Xte, yte))
    print("kmer_lgbm ACC:", results["kmer_lgbm"], flush=True)

    out = {
        "task": args.task, "split": args.split, "metric": "ACC",
        "results": results,
        "n_train": len(parts["train"]), "n_test": len(parts["test"]),
    }
    path = os.path.join(ROOT, "artifacts",
                        "baseline_%s_%s.json" % (args.task, args.split))
    with open(path, "w") as fh:
        json.dump(out, fh, indent=2)
    print("saved", path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
