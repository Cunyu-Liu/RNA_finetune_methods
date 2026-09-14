"""Random + family-level split generation with zero-overlap assertions.

Family split (spec §3.4): the split-unit (whole sequence / host transcript /
host gene) maps through the global family table (cluster_id_8080) so that one
family never spans train/eval sides. For eval datasets we cluster the dataset
itself (MMseqs2 80-80 within-task, cross-referenced against pretraining-family
table when available) — implemented in split scripts; this module asserts.

Zero-overlap assertion (TokBench lesson): raises if any eval unit (sequence or
host id) also appears in the finetune set.
"""
from __future__ import annotations

import hashlib
import random
from collections import defaultdict


def seq_hash(seq: str) -> str:
    canonical = seq.strip().upper().replace("U", "T")
    return hashlib.sha1(canonical.encode()).hexdigest()[:16]


def random_split(records: list[dict], seed: int = 17,
                 frac: tuple[float, float, float] = (0.8, 0.1, 0.1)) -> dict:
    rng = random.Random(seed)
    idx = list(range(len(records)))
    rng.shuffle(idx)
    n = len(records)
    n_tr = int(n * frac[0])
    n_va = int(n * frac[1])
    return {
        "train": [records[i] for i in idx[:n_tr]],
        "val": [records[i] for i in idx[n_tr:n_tr + n_va]],
        "test": [records[i] for i in idx[n_tr + n_va:]],
    }


def family_split(records: list[dict], family_key: str = "family_id",
                 seed: int = 17,
                 frac: tuple[float, float, float] = (0.8, 0.1, 0.1)) -> dict:
    """Cluster-pure split: all records sharing family_key stay on one side."""
    by_fam: dict[str, list[int]] = defaultdict(list)
    for i, r in enumerate(records):
        by_fam[str(r.get(family_key, seq_hash(str(r.get("seq", "")))))].append(i)
    fams = sorted(by_fam.keys())
    rng = random.Random(seed)
    rng.shuffle(fams)
    n = len(records)
    side = {}
    n_tr = n_va = 0
    for f in fams:
        size = len(by_fam[f])
        if n_tr < n * frac[0]:
            side[f] = "train"
            n_tr += size
        elif n_va < n * frac[1]:
            side[f] = "val"
            n_va += size
        else:
            side[f] = "test"
    out = {"train": [], "val": [], "test": []}
    for f, idxs in by_fam.items():
        for i in idxs:
            out[side[f]].append(records[i])
    # cluster-purity assertion
    fam_sides: dict[str, set[str]] = defaultdict(set)
    for split, rows in out.items():
        for r in rows:
            fam_sides[str(r.get(family_key, seq_hash(str(r.get("seq", "")))))].add(split)
    for f, sides in fam_sides.items():
        assert len(sides) == 1, "family %s spans splits: %s" % (f, sides)
    return out


def assert_no_overlap(train: list[dict], eval_: list[dict],
                      unit: str = "seq", host_field: str = "") -> None:
    """Zero-overlap assertion (B1). unit: 'seq' | 'host'."""
    def key(r):
        if unit == "host":
            return str(r[host_field])
        return seq_hash(str(r.get("seq", r.get("sequence", ""))))
    tr_keys = {key(r) for r in train}
    for r in eval_:
        k = key(r)
        assert k not in tr_keys, "OVERLAP DETECTED: %s in both train and eval" % k[:12]
