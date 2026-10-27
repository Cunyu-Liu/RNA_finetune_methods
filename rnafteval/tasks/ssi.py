"""结构得分插补（BEACON Structural Score Imputation）— per-base 回归任务。

8 任务扩展新任务 #4b（碱基级回归第 2 数据集，与 degradation 互证——spec R1"每类 ≥2 数据集"）。
数据：/root/rna-ft-eval/data/beacon_raw/structural-score-imputation/data/
  columns: sequence (100nt), struct (预测分布 per-base float), struct_true (真值 per-base float)
标签 = struct_true（每位置 0-1 连续结构得分）。
random 臂 = 官方切分；family 臂 = mmseqs 聚类整簇归侧。
"""
from __future__ import annotations

import os

import numpy as np
import pyarrow.parquet as pq

from rnafteval.splits import seq_hash, split_train_validation

BEACON_RAW = "/root/rna-ft-eval/data/beacon_raw"
TARGET_COL = "struct_true"
RANDOM_GROUPING = "sequence_hash_keep_same_sequence_records_together"


def load_ssi(data_dir: str | None = None,
             target: str = TARGET_COL) -> list[dict]:
    d = data_dir or os.path.join(BEACON_RAW,
                                 "structural-score-imputation", "data")
    recs = []
    for split in ("train", "validation", "test"):
        path = os.path.join(d, "%s.parquet" % split)
        if not os.path.exists(path):
            continue
        t = pq.read_table(path)
        dd = t.to_pydict()
        for seq, lab in zip(dd["sequence"], dd[target]):
            lab = np.asarray([float(x) for x in str(lab).split()],
                             dtype=np.float32)
            assert len(lab) == len(seq), "label/seq len mismatch: %d vs %d" % (
                len(lab), len(seq))
            recs.append({"seq": seq, "labels": lab, "subset": split})
    return recs


def load_official_split(data_dir: str | None = None,
                        target: str = TARGET_COL) -> dict[str, list[dict]]:
    d = data_dir or os.path.join(BEACON_RAW,
                                 "structural-score-imputation", "data")
    out = {}
    for split in ("train", "validation", "test"):
        path = os.path.join(d, "%s.parquet" % split)
        t = pq.read_table(path)
        dd = t.to_pydict()
        out[split] = [
            {"seq": s,
             "labels": np.asarray([float(x) for x in str(l).split()],
                                  dtype=np.float32),
             "subset": split}
            for s, l in zip(dd["sequence"], dd[target])]
    return out


def split_train_validation_by_sequence(rows: list[dict], seed: int = 17):
    """Keep same-sequence records with distinct labels on one validation side."""
    grouped = [dict(row, cluster=seq_hash(row["seq"])) for row in rows]
    return split_train_validation(grouped, seed=seed)


def same_sequence_record_counts(rows: list[dict]) -> int:
    return len(rows) - len({seq_hash(row["seq"]) for row in rows})


if __name__ == "__main__":
    sp = load_official_split()
    for k, v in sp.items():
        print(k, len(v))
    print("sample len:", len(sp["train"][0]["seq"]),
          "labels[:5]:", sp["train"][0]["labels"][:5])
