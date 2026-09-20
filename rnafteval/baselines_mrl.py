"""MRL 传统基线：k-mer Ridge + LightGBM 回归（B5 同数据同切分口径）。

用法: python -m rnafteval.baselines_mrl --split random
产物: status/baseline_mrl_<split>.json（Pearson r / MSE）
"""
from __future__ import annotations

import argparse
import json
import os
import random

import numpy as np

from .baselines import kmer_features

ROOT = "/mnt/cunyuliu/rna-ft-eval"


def load_mrl_parts(split: str):
    from .tasks import mrl as mrl_task
    from .tasks.dedup import dedup
    if split == "family":
        import pyarrow.parquet as pq
        t = pq.read_table(os.path.join(ROOT, "data", "family_splits",
                                       "mrl.parquet")).to_pydict()
        parts = {k: [{"seq": s, "label": float(l)}
                     for s, l, sp in zip(t["seq"], t["label"], t["split"])
                     if sp == k]
                 for k in ("train", "val", "test")}
    else:
        sp = mrl_task.load_official_split(
            os.path.join(ROOT, "data", "beacon_raw",
                        "mean-ribosome-loading", "data"))
        parts = {"train": sp["train"], "val": sp["validation"],
                 "test": sp["test"]}
    # LM 协议对齐: train 子采样 20000 (rng 17)
    rng = random.Random(17)
    parts["train"] = rng.sample(parts["train"],
                                min(20000, len(parts["train"])))
    return parts


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="random", choices=["random", "family"])
    args = ap.parse_args()

    parts = load_mrl_parts(args.split)
    Xtr = kmer_features([r["seq"] for r in parts["train"]])
    ytr = np.array([r["label"] for r in parts["train"]])
    Xte = kmer_features([r["seq"] for r in parts["test"]])
    yte = np.array([r["label"] for r in parts["test"]])

    results = {}
    from sklearn.linear_model import Ridge
    from sklearn.metrics import mean_squared_error
    for alpha in (1.0, 10.0, 100.0):
        m = Ridge(alpha=alpha).fit(Xtr, ytr)
        p = m.predict(Xte)
        results["ridge_a%g" % alpha] = {
            "pearson_r": float(np.corrcoef(yte, p)[0, 1]),
            "mse": float(mean_squared_error(yte, p))}
    try:
        import lightgbm as lgb
        m = lgb.LGBMRegressor(n_estimators=500, n_jobs=32, verbose=-1)
        m.fit(Xtr, ytr)
        p = m.predict(Xte)
        results["lgbm"] = {
            "pearson_r": float(np.corrcoef(yte, p)[0, 1]),
            "mse": float(mean_squared_error(yte, p))}
    except Exception as e:
        results["lgbm_error"] = str(e)

    best = max(results.items(), key=lambda kv: kv[1].get("pearson_r", -9)
               if isinstance(kv[1], dict) else -9)
    out = {"task": "mrl", "split": args.split, "metric": "PEARSON_R",
           "best": best[0], "best_value": best[1]["pearson_r"],
           "all": results,
           "results": {k: {"pearson_r": v["pearson_r"], "mse": v["mse"]}
                       for k, v in results.items() if isinstance(v, dict)}}
    os.makedirs(os.path.join(ROOT, "artifacts"), exist_ok=True)
    path = os.path.join(ROOT, "artifacts", "baseline_mrl_%s.json" % args.split)
    with open(path, "w") as f:
        json.dump(out, f, indent=1)
    p2 = os.path.join(ROOT, "status", "baseline_mrl_%s.json" % args.split)
    with open(p2, "w") as f:
        json.dump(out, f, indent=1)
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
