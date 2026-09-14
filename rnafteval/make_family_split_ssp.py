"""SSP family-level split via MMseqs2 80-80 clustering.

Clusters the union (TR0+VL0+TS0) at 0.8/0.8, then whole-cluster 80/10/10.
Output:
  data/family_splits/secondary-structure.parquet  (id, seq, cluster_id, split)
  artifacts/ssp_family_ids.json                    (id -> cluster id str)
"""
from __future__ import annotations

import json
import os
import random
import subprocess
import tempfile

import pyarrow as pa
import pyarrow.parquet as pq

ROOT = "/mnt/cunyuliu/rna-ft-eval"
MMSEQS = "/home/cunyuliu/mmseqs/bin/mmseqs"
OUT_DIR = os.path.join(ROOT, "data", "family_splits")
FAM_IDS = os.path.join(ROOT, "artifacts", "ssp_family_ids.json")


def main() -> int:
    from rnafteval.tasks import ssp as ssp_task

    meta = ssp_task.load_metadata()
    recs = (ssp_task.load_split("TR0", meta) +
            ssp_task.load_split("VL0", meta) +
            ssp_task.load_split("TS0", meta))
    # dedup by id
    seen = set()
    uniq = []
    for r in recs:
        if r["id"] not in seen:
            seen.add(r["id"])
            uniq.append(r)
    recs = uniq
    print("union records: %d" % len(recs), flush=True)

    os.makedirs(OUT_DIR, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=os.path.join(ROOT, "data")) as tmp:
        fasta = os.path.join(tmp, "seqs.fasta")
        with open(fasta, "w") as fh:
            for i, r in enumerate(recs):
                fh.write(">%s\n%s\n" % (r["id"], r["seq"].replace("U", "T")))
        subprocess.run(
            [MMSEQS, "easy-cluster", fasta, os.path.join(tmp, "out"),
             os.path.join(tmp, "tmp"), "--min-seq-id", "0.8", "-c", "0.8",
             "--cov-mode", "0", "--threads", "16"],
            check=True, capture_output=True)
        cluster_of: dict[str, int] = {}
        n_clusters = 0
        seen_rep: dict[str, int] = {}
        with open(os.path.join(tmp, "out_cluster.tsv")) as fh:
            for line in fh:
                rep, member = line.split()[:2]
                if rep not in seen_rep:
                    seen_rep[rep] = n_clusters
                    n_clusters += 1
                cluster_of[member] = seen_rep[rep]
    print("clusters: %d" % n_clusters, flush=True)

    rng = random.Random(17)
    order = list(range(n_clusters))
    rng.shuffle(order)
    sizes = {}
    for r in recs:
        c = cluster_of[r["id"]]
        sizes[c] = sizes.get(c, 0) + 1
    n = len(recs)
    side = {}
    n_tr = n_va = 0
    for c in order:
        if n_tr < n * 0.8:
            side[c] = "train"
            n_tr += sizes[c]
        elif n_va < n * 0.1:
            side[c] = "val"
            n_va += sizes[c]
        else:
            side[c] = "test"

    tbl = pa.table({
        "id": [r["id"] for r in recs],
        "seq": [r["seq"] for r in recs],
        "cluster_id": ["c%d" % cluster_of[r["id"]] for r in recs],
        "split": [side[cluster_of[r["id"]]] for r in recs],
    })
    out = os.path.join(OUT_DIR, "secondary-structure.parquet")
    pq.write_table(tbl, out)
    with open(FAM_IDS, "w") as fh:
        json.dump({r["id"]: "c%d" % cluster_of[r["id"]] for r in recs}, fh)
    import collections
    cnt = collections.Counter(tbl.column("split").to_pylist())
    print("split sizes:", dict(cnt), "->", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
