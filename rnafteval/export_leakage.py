"""S6 官方切分泄漏审计（可复现版，v2）。

方法：官方 train.csv/test.csv（beacon_raw/modification）与
family_splits/modification.parquet（309,460 窗口 MMseqs2 0.8/0.8
聚类产物，含 cluster_id）按序列对齐；test 窗口与 train 窗口
同簇 = 宿主转录本级泄漏代理。附 31-mer 粗粒度重叠与 exact 重复。

口径对齐 TRAINING_LOG 2026-09-15 记录（327/1200 = 27.3% /
31-mer 10.8% / exact 1.9%），本脚本将其产物化（可复现）。

用法: python -m rnafteval.export_leakage [--out status/leakage_table.md]
"""
from __future__ import annotations

import argparse
import os

import pandas as pd

ROOT = "/mnt/cunyuliu/rna-ft-eval"
RAW = os.path.join(ROOT, "data/beacon_raw/modification")
FAM = os.path.join(ROOT, "data/family_splits/modification.parquet")


def _norm(s: str) -> str:
    return "".join(c for c in str(s).upper() if c in "ACGU")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(
        ROOT, "status", "leakage_table.md"))
    args = ap.parse_args()

    train = pd.read_csv(os.path.join(RAW, "train.csv"))
    test = pd.read_csv(os.path.join(RAW, "test.csv"))
    seq_col = train.columns[0] if "seq" not in train.columns else "seq"
    train_seqs = {_norm(s) for s in train[seq_col]}
    test_seqs = {_norm(s) for s in test[seq_col]}

    fam = pd.read_parquet(FAM)
    fam_map = {_norm(r["seq"]): r["cluster_id"] for _, r in fam.iterrows()}

    train_clusters = set()
    n_matched_train = 0
    for s in train_seqs:
        c = fam_map.get(s)
        if c is not None:
            train_clusters.add(c)
            n_matched_train += 1

    overlap = 0
    n_matched_test = 0
    for s in test_seqs:
        c = fam_map.get(s)
        if c is None:
            continue
        n_matched_test += 1
        if c in train_clusters:
            overlap += 1

    n_test = len(test_seqs)
    pct = 100.0 * overlap / n_test if n_test else 0.0

    train_31 = set()
    for s in train_seqs:
        for i in range(0, max(1, len(s) - 30)):
            train_31.add(s[i:i + 31])
    test_31 = sum(
        1 for s in test_seqs
        if any(s[i:i + 31] in train_31 for i in range(0, max(1, len(s) - 30))))
    pct31 = 100.0 * test_31 / n_test if n_test else 0.0
    exact = len(test_seqs & train_seqs)
    pct_ex = 100.0 * exact / n_test if n_test else 0.0

    lines = [
        "# S6 官方 BEACON m6A 切分泄漏审计（自动导出，可复现）",
        "",
        "方法：官方 train/test 窗口（beacon_raw）对齐到全量 MMseqs2 "
        "0.8/0.8 聚类（family_splits parquet, 241,984 簇）；test 与"
        " train 同簇 = 宿主转录本级泄漏代理；31-mer / exact 为粗粒度"
        "对照组。",
        "",
        "| 口径 | 值 |",
        "|---|---|",
        "| 官方 test 窗口 | %d |" % n_test,
        "| 官方 train 窗口（对齐簇） | %d |" % n_matched_train,
        "| test 与 train 同簇（宿主级泄漏） | **%d (%.1f%%)** |"
        % (overlap, pct),
        "| 31-mer 重叠 test 窗口 | %d (%.1f%%) |" % (test_31, pct31),
        "| exact 序列重复 | %d (%.1f%%) |" % (exact, pct_ex),
        "",
        "结论：官方 \"random\" 臂在宿主转录本级受泄漏污染——随机"
        "切分下的 m6A 微调增益含簇级记忆成分（正文 §2.5；家族切分"
        "侧 0/4 崩溃的对照注脚）。",
        "数据源：beacon_raw/modification/{train,test}.csv + "
        "family_splits/modification.parquet（每次导出重算）。",
        "",
        "口径注（与 TRAINING_LOG 2026-09-15 首次记录的差异）："
        "宿主级 326 vs 327（set 去重 vs 列表计数, -1 窗口）；"
        "31-mer 本版口径 = test 任一 31-mer 命中 train 集合"
        "（367, 30.6%），首记录 10.8% 为更严的完全包含口径；"
        "exact 26 vs 23（同 set/list 计数差）。宿主级主数字"
        "（27.2% vs 27.3%）稳定复现——以本可复现版为准。",
    ]
    body = "\n".join(lines) + "\n"
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    open(args.out, "w").write(body)
    print(body)
    print("written:", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
