"""MRL 翻译效率回归（BEACON MeanRibosomeLoading）—— per-seq 回归任务。

C4 per-seq 第二任务（与 ncRNA 互证）：76k 条 5'UTR（25nt）序列，
label = 平均核糖体负载（float 回归）。
官方切分 = 随机（random 臂直接用）；family 臂用 make_family_split 生成。
"""
from __future__ import annotations

import os

import pyarrow.parquet as pq


def load_mrl(data_dir: str) -> list[dict]:
    """合并三切分，供家族切分/去重使用。"""
    recs = []
    for split in ("train", "validation", "test"):
        path = os.path.join(data_dir, "%s.parquet" % split)
        if not os.path.exists(path):
            continue
        t = pq.read_table(path)
        d = t.to_pydict()
        for seq, lab in zip(d["seq"], d["label"]):
            recs.append({"seq": seq, "label": float(lab), "subset": split})
    return recs


def load_official_split(data_dir: str) -> dict[str, list[dict]]:
    out = {}
    for split in ("train", "validation", "test"):
        path = os.path.join(data_dir, "%s.parquet" % split)
        t = pq.read_table(path)
        d = t.to_pydict()
        out[split] = [{"seq": s, "label": float(l), "subset": split}
                      for s, l in zip(d["seq"], d["label"])]
    return out


if __name__ == "__main__":
    d = "/mnt/cunyuliu/rna-ft-eval/data/beacon_raw/mean-ribosome-loading/data"
    sp = load_official_split(d)
    for k, v in sp.items():
        print(k, len(v))
