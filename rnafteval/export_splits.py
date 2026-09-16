"""S5 家族切分构建统计自动导出（三任务 parquet -> markdown 表）。

含簇数/切分尺寸/序列数/宿主代理说明（m6A: 同序列多窗口 =
宿主转录本代理设计）。附零重叠复算（A13 双层验证的产物化）。

用法: python -m rnafteval.export_splits [--out status/splits_table.md]
"""
from __future__ import annotations

import argparse
import os

import pandas as pd

ROOT = "/mnt/cunyuliu/rna-ft-eval"
TASKS = ["noncoding-rna-family", "secondary-structure", "modification"]
UNIT = {
    "noncoding-rna-family": "整条序列（家族簇整簇归一侧）",
    "secondary-structure": "整条序列（家族簇整簇归一侧）",
    "modification": "宿主转录本代理（同序列全部窗口整侧；位点→转录本→簇）",
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "status",
                                                  "splits_table.md"))
    args = ap.parse_args()
    lines = ["# S5 家族切分构建统计（自动导出，MMseqs2 0.8/0.8）", "",
             "| task | rows | unique seqs | clusters | train/val/test | "
             "切分单元（spec §3.4） | 零重叠复算 |",
             "|---|---|---|---|---|---|---|"]
    for task in TASKS:
        df = pd.read_parquet(
            os.path.join(ROOT, "data/family_splits/%s.parquet" % task))
        n_cl = df["cluster_id"].nunique()
        sizes = df.groupby("split").size()
        seqs = df["seq"].nunique()
        viol = int((df.groupby("cluster_id")["split"].nunique() > 1).sum())
        viol_seq = int((df.groupby("seq")["split"].nunique() > 1).sum())
        ok = "PASS（0 违规）" if viol == 0 and viol_seq == 0 else (
            "FAIL c=%d s=%d" % (viol, viol_seq))
        lines.append(
            "| %s | %d | %d | %d | %d/%d/%d | %s | %s |" % (
                task, len(df), seqs, n_cl, sizes.get("train", 0),
                sizes.get("val", 0), sizes.get("test", 0),
                UNIT[task], ok))
    lines += ["",
              "注：modification 的 rows > unique seqs 为宿主代理设计"
              "（同一转录本多窗口共享 cluster 归属；见 spec §3.4 表）。",
              "零重叠复算 = 每次导出时对 parquet 现场 groupby 复核"
              "（A13 独立验证的产物化，双层：构建期断言 + 导期复算）。"]
    body = "\n".join(lines) + "\n"
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    open(args.out, "w").write(body)
    print(body)
    print("written:", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
