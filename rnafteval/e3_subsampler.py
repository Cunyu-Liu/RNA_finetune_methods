"""T3.1.1 簇级分层降采样器（E3 小数据 regime）。

随机抽簇 → 整簇纳入（机理篇 Q3 决议），生成 {10, 100, 1000} 档
标注子集（簇中位数 1 → 档位近似精确）。10000 档由全量 train
（6859）直接代表——ncRNA train 不足 10k，档 4 定义为全量。

产物: data/e3_subsets/ncrna_<n>_<seed>.txt（train 序列 ID 行表,
与 parquet 行号对应——runner 用行号切片）。

用法: python -m rnafteval.e3_subsampler
"""
from __future__ import annotations

import os
import random

import pandas as pd

ROOT = "/mnt/cunyuliu/rna-ft-eval"
SRC = os.path.join(ROOT, "data/family_splits/noncoding-rna-family.parquet")
OUT = os.path.join(ROOT, "data/e3_subsets")
LEVELS = [10, 100, 1000]
SEEDS = [17, 29, 43]


def main() -> int:
    os.makedirs(OUT, exist_ok=True)
    df = pd.read_parquet(SRC)
    train = df[df["split"] == "train"].reset_index(drop=True)
    by_cluster = {}
    for idx, row in train.iterrows():
        by_cluster.setdefault(row["cluster_id"], []).append(idx)
    clusters = sorted(by_cluster)

    for sd in SEEDS:
        rng = random.Random(sd)
        for n in LEVELS:
            cl = list(clusters)
            rng.shuffle(cl)
            picked, rows = [], []
            for c in cl:
                picked.append(c)
                rows.extend(by_cluster[c])
                if len(rows) >= n:
                    break
            rows = sorted(set(rows))[:n] if n <= 1000 else rows
            path = os.path.join(OUT, "ncrna_%d_s%d.txt" % (n, sd))
            with open(path, "w") as f:
                for r in sorted(rows):
                    f.write("%d\n" % r)
            print("%s: %d rows (%d clusters)" % (path, len(rows),
                                                 len(picked)))
    full_path = os.path.join(OUT, "ncrna_full.txt")
    if not os.path.exists(full_path):
        with open(full_path, "w") as f:
            for r in range(len(train)):
                f.write("%d\n" % r)
        print("%s: %d rows (full train)" % (full_path, len(train)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
