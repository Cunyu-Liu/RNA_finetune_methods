#!/usr/bin/env python3
"""Generate nested whole-cluster subsets for dense E3/C5c comparisons."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import random

import pandas as pd

ROOT = Path("/root/rna-ft-eval")
DEFAULT_SOURCE = ROOT / "data/family_splits/noncoding-rna-family.parquet"
DEFAULT_OUT = ROOT / "data/e3_subsets"
LEVELS = (10, 100, 1000, 1500, 2000, 2500, 3000)
SEEDS = (17, 29, 43, 101)


def sha256_text(value):
    return hashlib.sha256(value.encode()).hexdigest()


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def nested_cluster_subsets(frame, levels=LEVELS, seeds=SEEDS):
    if not {"split", "cluster_id"} <= set(frame.columns):
        raise ValueError("family table requires split and cluster_id")
    if len(set(levels)) != len(levels) or any(
            isinstance(n, bool) or not isinstance(n, int) or n <= 0 for n in levels):
        raise ValueError("levels must be distinct positive integers")
    train = frame.loc[frame["split"] == "train"].reset_index(drop=True)
    if train.empty or train["cluster_id"].isna().any():
        raise ValueError("training rows and cluster assignments must be nonempty")
    groups = {}
    for index, cluster in enumerate(train["cluster_id"]):
        groups.setdefault(cluster, []).append(index)
    output = {}
    for seed in seeds:
        clusters = sorted(groups, key=str)
        random.Random(seed).shuffle(clusters)
        for level in levels:
            picked, rows = [], []
            for cluster in clusters:
                if len(rows) >= level:
                    break
                picked.append(cluster)
                rows.extend(groups[cluster])
            rows = sorted(rows)
            expected = sorted(index for cluster in picked for index in groups[cluster])
            assert rows == expected
            output[(seed, level)] = {
                "seed": seed, "requested_n_train": level, "rows": rows,
                "n_rows": len(rows), "n_clusters": len(picked),
                "cluster_ids": [str(cluster) for cluster in picked],
                "whole_clusters": True,
                "saturated": len(rows) == len(train),
            }
    for seed in seeds:
        ordered = sorted(levels)
        for smaller, larger in zip(ordered, ordered[1:]):
            assert set(output[(seed, smaller)]["rows"]) <= \
                set(output[(seed, larger)]["rows"])
    return output, len(train)


def write_subset(out_dir, source_sha, seed, level, subset):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = "ncrna_%d_s%d_dense" % (level, seed)
    text = "".join("%d\n" % index for index in subset["rows"])
    metadata = {key: value for key, value in subset.items() if key != "rows"}
    metadata.update({
        "row_indices_sha256": sha256_text(text),
        "cluster_ids_sha256": sha256_text(
            json.dumps(subset["cluster_ids"], separators=(",", ":"))),
        "source_parquet_sha256": source_sha,
        "sampling": "seeded_cluster_order_then_whole_cluster_nested",
    })
    for suffix, content in ((".txt", text),
                            (".json", json.dumps(metadata, indent=2) + "\n")):
        path = out_dir / (stem + suffix)
        if path.exists() and path.read_text() != content:
            raise FileExistsError("refusing to overwrite different subset: %s" % path)
        temporary = path.with_name(path.name + ".tmp")
        temporary.write_text(content)
        os.replace(temporary, path)
    return metadata


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default=str(DEFAULT_SOURCE))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT))
    parser.add_argument("--levels", default=",".join(map(str, LEVELS)))
    parser.add_argument("--seeds", default=",".join(map(str, SEEDS)))
    args = parser.parse_args(argv)
    levels = [int(value) for value in args.levels.split(",")]
    seeds = [int(value) for value in args.seeds.split(",")]
    source_sha = sha256_file(args.source)
    frame = pd.read_parquet(args.source, columns=["split", "cluster_id"])
    subsets, n_train = nested_cluster_subsets(frame, levels, seeds)
    manifest = []
    for (seed, level), subset in subsets.items():
        metadata = write_subset(args.out_dir, source_sha, seed, level, subset)
        metadata["nested_within_seed"] = True
        manifest.append(metadata)
    manifest_path = Path(args.out_dir) / "dense_manifest.json"
    payload = {"source": args.source, "source_sha256": source_sha,
               "n_train_rows": n_train, "levels": levels, "seeds": seeds,
               "subsets": manifest}
    temporary = manifest_path.with_name(manifest_path.name + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n")
    os.replace(temporary, manifest_path)
    print(json.dumps({"subsets": len(manifest), "n_train_rows": n_train,
                      "manifest": str(manifest_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
