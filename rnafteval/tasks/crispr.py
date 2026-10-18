"""CRISPR off-target — per-seq 二分类任务（BEACON CRISPROffTarget，GUIDE-seq 语义）。

8 任务扩展新任务 #4（序列级分类第 2 数据集，与 ncRNA 互证）。
数据：/root/rna-ft-eval/data/beacon_raw/crispr-off-target/data/{train,validation,test}.parquet
  columns: sgrna (23nt), target (23nt), label (double 0-1 cleavage fraction)
语义决定：
  - label > 0 = off-target 切割发生（正类，全数据 120/20319 = 0.59% 极不平衡——
    这正是 off-target 检测的真实难点，用 PR-AUC 做主指标（对不平衡鲁棒）+ ROC-AUC 副
  - 输入 = sgrna(23nt) + target(23nt) 拼接 46nt（文献常规：DeepOFF 等），模型自由学
    配对错配模式。不做复杂 pair-encoding（跨模型统一输入协议优先）。
切分协议：
  - random 臂 = 官方 train/test 直接用（官方切分即按 guide 分配，非家族泄漏）
  - family 臂 = mmseqs2 80/80 对 46nt 拼接序列聚类整簇归侧（与其他任务协议一致）
    （sgRNA 序列族内高度同源—— GUIDE-seq 同一 guide 的 off-target 位点天然成簇，
     family 切分比官方切分更严格，防"同 guide 近似位点跨侧"）
"""
from __future__ import annotations

import os

import pyarrow.parquet as pq

BEACON_RAW = "/root/rna-ft-eval/data/beacon_raw"


def _read(path: str) -> list[dict]:
    t = pq.read_table(path)
    d = t.to_pydict()
    out = []
    for sg, tg, lab in zip(d["sgrna"], d["target"], d["label"]):
        y = 1.0 if float(lab) > 0 else 0.0
        out.append({"seq": sg + tg, "label": y,
                    "sgrna": sg, "target": tg, "cleav": float(lab)})
    return out


def load_official_split(data_dir: str | None = None) -> dict[str, list[dict]]:
    d = data_dir or os.path.join(BEACON_RAW, "crispr-off-target", "data")
    return {"train": _read(os.path.join(d, "train.parquet")),
            "val": _read(os.path.join(d, "validation.parquet")),
            "test": _read(os.path.join(d, "test.parquet"))}


def load_crispr(data_dir: str | None = None) -> list[dict]:
    """合并三切分，供家族切分/去重使用。"""
    sp = load_official_split(data_dir)
    return sp["train"] + sp["val"] + sp["test"]


if __name__ == "__main__":
    sp = load_official_split()
    for k, v in sp.items():
        n_pos = sum(1 for r in v if r["label"] == 1.0)
        print(k, len(v), "pos:", n_pos, "rate: %.4f" % (n_pos / len(v)))
    print("total", sum(len(v) for v in sp.values()))
