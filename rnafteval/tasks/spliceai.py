"""SpliceAI 剪接位点预测 — per-base 3 分类任务（BEACON SpliceAI）。

8 任务扩展新任务 #3（碱基级分类第 2 数据集，与 m6A 互证）。
数据：/root/rna-ft-eval/data/beacon_raw/spliceai/data/{train,validation,test}.parquet
  columns: sequence (100nt 窗口), labels (等长字符串 0/1/2; 1=acceptor, 2=donor)
官方切分 = 基因级（BEACON 原生）；random 臂 = 官方切分直接用（BEACON 切分即随机基因分配）；
family 臂 = make_family_split 对序列聚类后整簇归侧（协议与其他任务一致）。
"""
from __future__ import annotations

import os

import pyarrow.parquet as pq

BEACON_RAW = "/root/rna-ft-eval/data/beacon_raw"


def load_spliceai(data_dir: str | None = None) -> list[dict]:
    """合并三切分，供家族切分/去重使用。labels: str -> list[int]。"""
    d = data_dir or os.path.join(BEACON_RAW, "spliceai", "data")
    recs = []
    for split in ("train", "validation", "test"):
        path = os.path.join(d, "%s.parquet" % split)
        if not os.path.exists(path):
            continue
        t = pq.read_table(path)
        dd = t.to_pydict()
        for seq, lab in zip(dd["sequence"], dd["labels"]):
            recs.append({"seq": seq, "labels": [int(c) for c in lab],
                         "subset": split})
    return recs


def load_official_split(data_dir: str | None = None) -> dict[str, list[dict]]:
    d = data_dir or os.path.join(BEACON_RAW, "spliceai", "data")
    out = {}
    for split in ("train", "validation", "test"):
        path = os.path.join(d, "%s.parquet" % split)
        t = pq.read_table(path)
        dd = t.to_pydict()
        out[split] = [
            {"seq": s, "labels": [int(c) for c in lab], "subset": split}
            for s, lab in zip(dd["sequence"], dd["labels"])]
    return out


if __name__ == "__main__":
    sp = load_official_split()
    for k, v in sp.items():
        print(k, len(v))
    n_pos = sum(sum(1 for c in r["labels"] if c) for r in sp["train"][:2000])
    print("positive bases in first 2000 train rows:", n_pos)
