"""BEACON modification: sequence-level multi-label classification.

Data: 101-nt sequence plus 12 space-separated binary modification-type targets.
The label vector is not a per-base target grid. m6A is label index 7; its AUC
is the primary metric and the 12-label mean AUC is auxiliary.
"""
from __future__ import annotations

import os

import pyarrow.parquet as pq

BEACON_RAW = "/root/rna-ft-eval/data/beacon_raw"


def load_modification(data_dir: str | None = None) -> list[dict]:
    d = data_dir or os.path.join(BEACON_RAW, "modification", "data")
    recs = []
    for split in ("train", "validation", "test"):
        path = os.path.join(d, "%s.parquet" % split)
        if not os.path.exists(path):
            continue
        t = pq.read_table(path)
        dd = t.to_pydict()
        for seq, lab in zip(dd["sequence"], dd["label"]):
            labs = [int(x) for x in str(lab).split()]
            recs.append({"seq": seq, "labels": labs, "subset": split})
    return recs


def load_official_split(data_dir: str | None = None) -> dict[str, list[dict]]:
    d = data_dir or os.path.join(BEACON_RAW, "modification", "data")
    out = {}
    for split in ("train", "validation", "test"):
        path = os.path.join(d, "%s.parquet" % split)
        if not os.path.exists(path):
            continue
        t = pq.read_table(path)
        dd = t.to_pydict()
        out[split] = [{"seq": s, "labels": [int(x) for x in str(l).split()],
                       "subset": split}
                      for s, l in zip(dd["sequence"], dd["label"])]
    return out


if __name__ == "__main__":
    sp = load_official_split()
    print({k: len(v) for k, v in sp.items()})
    r = sp["train"][0]
    print("seq len:", len(r["seq"]), "labels:", len(r["labels"]),
          "pos frac:", sum(r["labels"]) / len(r["labels"]))
