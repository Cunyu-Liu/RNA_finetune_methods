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
import json
import os
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


def split_train_validation(rows: list[dict], seed: int = 17,
                           val_fraction: float = 0.1) -> tuple[list[dict], list[dict]]:
    """Deterministically hold out validation rows from the training side only."""
    if len(rows) < 2:
        raise ValueError("at least two training rows are required for validation")
    if not 0.0 < val_fraction < 1.0:
        raise ValueError("val_fraction must be in (0, 1)")
    if any("cluster" in row for row in rows):
        if not all(row.get("cluster") is not None for row in rows):
            raise ValueError("family validation split requires cluster on every row")
        by_cluster = defaultdict(list)
        for i, row in enumerate(rows):
            by_cluster[str(row["cluster"])].append(i)
        clusters = sorted(by_cluster)
        random.Random(seed).shuffle(clusters)
        target = max(1, int(len(rows) * val_fraction))
        val_idx = set()
        for cluster in clusters:
            indices = by_cluster[cluster]
            if len(val_idx) < target and len(val_idx) + len(indices) < len(rows):
                val_idx.update(indices)
        if not val_idx or len(val_idx) == len(rows):
            raise ValueError("family validation split requires at least two clusters")
        train = [row for i, row in enumerate(rows) if i not in val_idx]
        val = [row for i, row in enumerate(rows) if i in val_idx]
        assert_no_overlap(train, val, unit="seq")
        return train, val
    indices = list(range(len(rows)))
    random.Random(seed).shuffle(indices)
    n_val = min(len(rows) - 1, max(1, int(len(rows) * val_fraction)))
    val_idx = set(indices[:n_val])
    train = [row for i, row in enumerate(rows) if i not in val_idx]
    val = [row for i, row in enumerate(rows) if i in val_idx]
    assert_no_overlap(train, val, unit="seq")
    return train, val


def assert_cluster_no_overlap(train: list[dict], eval_: list[dict]) -> None:
    train_clusters = {str(row["cluster"]) for row in train}
    overlap = train_clusters & {str(row["cluster"]) for row in eval_}
    assert not overlap, "FAMILY OVERLAP DETECTED: %s" % sorted(overlap)[:3]


def seeded_sample(rows: list[dict], n_train: int, seed: int) -> list[dict]:
    if n_train <= 0 or n_train >= len(rows):
        return rows
    return random.Random(seed).sample(rows, n_train)


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


def prepare_convergence_splits(train: list[dict], val: list[dict] | None,
                               test: list[dict], *, n_train: int = 0,
                               sample_seed: int = 17, holdout_seed: int = 17,
                               family: bool = False,
                               validation_source: str = "",
                               evidence_path: str = ""):
    """Build leak-free v2 splits without changing the legacy data path.

    Existing test rows have deduplication priority, then an existing validation
    split, then train. If validation is absent it is held out from train only.
    """
    input_rows = {"train": len(train), "val": len(val or []), "test": len(test)}
    evidence = {
        "protocol": "valplateau_v2",
        "validation_source": validation_source or (
            "train_holdout" if val is None else "provided_validation"),
        "input_rows": input_rows,
        "dedup_priority": ["test", "val", "train"],
        "removed_within_split": {"train": 0, "val": 0, "test": 0},
        "removed_cross_split": {"train": 0, "val": 0, "test": 0},
        "cross_split_examples": [],
        "family": family,
        "holdout_seed": holdout_seed,
    }

    def save(status="CHECKING", error=""):
        evidence["status"] = status
        if error:
            evidence["error"] = error
        if evidence_path:
            tmp = evidence_path + ".tmp"
            with open(tmp, "w") as fh:
                json.dump(evidence, fh, indent=2)
            os.replace(tmp, evidence_path)

    if family:
        missing = [side for side, rows in (("train", train), ("val", val or []),
                                          ("test", test))
                   if any(r.get("cluster") in (None, "") for r in rows)]
        if missing:
            message = "family validation requires cluster on every row: %s" % missing
            save("INVALID", message)
            raise ValueError(message)

    # Keep the test control fixed wherever possible: duplicates are removed from
    # validation/train rather than moved out of test into another side.
    sides = {"train": train, "test": test}
    if val is not None:
        sides["val"] = val
    seen = {}
    for side in ("test", "val", "train"):
        if side not in sides:
            continue
        local = set()
        kept = []
        for row in sides[side]:
            key = seq_hash(str(row.get("seq", row.get("sequence", ""))))
            if key in local:
                evidence["removed_within_split"][side] += 1
                continue
            local.add(key)
            if key in seen:
                evidence["removed_cross_split"][side] += 1
                if len(evidence["cross_split_examples"]) < 20:
                    evidence["cross_split_examples"].append({
                        "seq_hash": key, "kept": seen[key], "removed": side})
                continue
            seen[key] = side
            kept.append(row)
        sides[side] = kept
    train, test = sides["train"], sides["test"]
    val = sides.get("val")
    if val is None:
        train, val = split_train_validation(train, seed=holdout_seed)
    before_sample = len(train)
    train = seeded_sample(train, n_train, sample_seed)
    evidence["train_sampling"] = {
        "method": "seeded_sample", "n_train": n_train,
        "seed": sample_seed, "rows_before": before_sample,
        "rows_after": len(train),
    }
    evidence["output_rows"] = {
        "train": len(train), "val": len(val), "test": len(test)}
    save()
    try:
        if not train or not val or not test:
            raise ValueError("valplateau_v2 requires non-empty train/val/test")
        assert_no_overlap(train, val + test, unit="seq")
        assert_no_overlap(val, test, unit="seq")
        if family:
            assert_cluster_no_overlap(train, val + test)
            assert_cluster_no_overlap(val, test)
    except Exception as exc:
        save("INVALID", str(exc))
        raise
    save("OK")
    return train, val, test, evidence
