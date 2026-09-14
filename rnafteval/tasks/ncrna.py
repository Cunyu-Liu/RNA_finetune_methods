"""ncRNA family classification (BEACON NoncodingRNAFamily) — per-seq, 13 classes.

Data: train 5670 / val 650 / test 2600, columns [sequence, label].
Official BEACON split is RANDOM (used as-is for the random-split arm);
our family-level split requires re-clustering (MMseqs2 80-80 within-task,
cross-referenced against the rna-sc family index — separate script).
"""
from __future__ import annotations

import os

import pyarrow.parquet as pq


def load_ncrna(data_dir: str) -> list[dict]:
    """Load BEACON noncoding-rna-family parquet files into records.

    Returns list of {seq, label, subset} dicts. Merges all three splits so
    callers can re-split (random arm re-derives; family arm uses cluster ids).
    """
    recs = []
    for split in ("train", "validation", "test"):
        path = os.path.join(data_dir, "%s.parquet" % split)
        if not os.path.exists(path):
            continue
        t = pq.read_table(path)
        d = t.to_pydict()
        for seq, lab in zip(d["sequence"], d["label"]):
            recs.append({"seq": seq, "label": int(lab), "subset": split})
    return recs


def load_official_split(data_dir: str) -> dict[str, list[dict]]:
    out = {}
    for split in ("train", "validation", "test"):
        path = os.path.join(data_dir, "%s.parquet" % split)
        t = pq.read_table(path)
        d = t.to_pydict()
        out[split] = [{"seq": s, "label": int(l), "subset": split}
                      for s, l in zip(d["sequence"], d["label"])]
    return out


if __name__ == "__main__":
    import sys
    d = sys.argv[1] if len(sys.argv) > 1 else \
        "/mnt/cunyuliu/rna-ft-eval/data/beacon_raw/noncoding-rna-family/data"
    recs = load_ncrna(d)
    print("records:", len(recs))
    sp = load_official_split(d)
    print({k: len(v) for k, v in sp.items()})
    print("sample:", recs[0]["seq"][:50], "label", recs[0]["label"])
