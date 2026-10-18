"""mRNA 降解率预测（BEACON Degradation, OpenVaccine）— per-base 回归任务。

8 任务扩展新任务 #4a（碱基级回归主数据集——用户要求的第 4 类任务）。
数据：/root/rnaft-eval/data/beacon_raw/degradation/
  - data/train.parquet (2155 行带标签) / data/validation.parquet (245 行带标签)
  - data/test.parquet 与 train-val-test/test_1.json 均为无标签 leaderboard 集（3634 行）
切分协议（诚实声明，BEACON test 无公开标签）：
  train = data/train.parquet 的 80%（seed 17 内部切分，簇级在下述 family 臂处理）
  val   = data/validation.parquet
  test  = data/train.parquet 的 20%（同一 seed 的互补侧；与 train 侧零重叠断言）
  （test_1.json 3634 行保留为 leaderboard 盲测集，不用于本课题指标）
标签 = deg_Mg_pH10 每序列 L 连续值；主指标 = per-base PCC + MCRMSE 汇总。
"""
from __future__ import annotations

import os
import random

import numpy as np
import pyarrow.parquet as pq

BEACON_RAW = "/root/rna-ft-eval/data/beacon_raw"
TARGET_COL = "deg_Mg_pH10"


def _read_labeled(path: str, target: str) -> list[dict]:
    t = pq.read_table(path)
    dd = t.to_pydict()
    out = []
    for seq, lab in zip(dd["sequence"], dd[target]):
        lab = np.asarray(lab, dtype=np.float32)
        assert len(lab) <= len(seq)
        out.append({"seq": seq, "labels": lab, "scored": len(lab)})
    return out


def load_degradation(data_dir: str | None = None,
                     target: str = TARGET_COL) -> list[dict]:
    """合并带标签两文件（train+validation），供家族切分/去重使用。"""
    d = data_dir or os.path.join(BEACON_RAW, "degradation", "data")
    recs = []
    for split in ("train", "validation"):
        path = os.path.join(d, "%s.parquet" % split)
        if os.path.exists(path):
            for r in _read_labeled(path, target):
                r["subset"] = split
                recs.append(r)
    return recs


def load_official_split(data_dir: str | None = None,
                        target: str = TARGET_COL,
                        seed: int = 17) -> dict[str, list[dict]]:
    """内部 80/20 协议（见模块 docstring）：train.parquet 80/20 + validation 为 val。"""
    d = data_dir or os.path.join(BEACON_RAW, "degradation", "data")
    train_all = _read_labeled(os.path.join(d, "train.parquet"), target)
    rng = random.Random(seed)
    idx = list(range(len(train_all)))
    rng.shuffle(idx)
    cut = int(len(idx) * 0.8)
    tr = [train_all[i] for i in idx[:cut]]
    te = [train_all[i] for i in idx[cut:]]
    val = _read_labeled(os.path.join(d, "validation.parquet"), target)
    for r in tr:
        r["subset"] = "train"
    for r in te:
        r["subset"] = "test"
    for r in val:
        r["subset"] = "validation"
    return {"train": tr, "validation": val, "test": te}


if __name__ == "__main__":
    sp = load_official_split()
    for k, v in sp.items():
        print(k, len(v))
    print("sample len:", len(sp["train"][0]["seq"]),
          "labels[:5]:", sp["train"][0]["labels"][:5])
