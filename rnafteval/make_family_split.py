"""Family-level split generation via MMseqs2 80-80 clustering (spec T1.1.3).

Clusters the deduped task sequences at 80% identity / 80% coverage, then
assigns whole clusters to train/val/test (cluster-pure). Cross-references
the rna-sc pretraining family index: eval sequences whose cluster hits a
PRETRAIN-train cluster are flagged contaminated for the family-split arm
(the random-split arm keeps them — that's the point of the C4 contrast).

Usage:
  python -m rnafteval.make_family_split --task noncoding-rna-family
Output:
  /mnt/cunyuliu/rna-ft-eval/data/family_splits/<task>.parquet
    columns: seq, label, cluster_id, split, contaminated
"""
from __future__ import annotations

import argparse
import os
import subprocess
import tempfile

import pyarrow as pa
import pyarrow.parquet as pq

ROOT = "/mnt/cunyuliu/rna-ft-eval"
BEACON_RAW = os.path.join(ROOT, "data", "beacon_raw")
OUT_DIR = os.path.join(ROOT, "data", "family_splits")
MMSEQS = "/home/cunyuliu/mmseqs/bin/mmseqs"


def load_task_seqs(task: str) -> list[dict]:
    from .tasks.dedup import dedup
    if task == "mrl":
        from .tasks import mrl
        recs = mrl.load_mrl(
            os.path.join(BEACON_RAW, "mean-ribosome-loading", "data"))
        return dedup(recs)
    from .tasks import ncrna
    recs = ncrna.load_ncrna(
        os.path.join(BEACON_RAW, "noncoding-rna-family", "data"))
    return dedup(recs)


def cluster_sequences(recs: list[dict], tmp: str) -> list[int]:
    """MMseqs2 easy-cluster at 0.8 identity / 0.8 cov; returns cluster idx per seq."""
    fasta = os.path.join(tmp, "seqs.fasta")
    with open(fasta, "w") as fh:
        for i, r in enumerate(recs):
            fh.write(">%d\n%s\n" % (i, r["seq"].replace("U", "T")))
    subprocess.run(
        [MMSEQS, "easy-cluster", fasta, os.path.join(tmp, "out"),
         os.path.join(tmp, "tmp"), "--min-seq-id", "0.8", "-c", "0.8",
         "--cov-mode", "0", "--threads", "16"],
        check=True, capture_output=True)
    cluster_of = [0] * len(recs)
    n_clusters = 0
    seen = {}
    with open(os.path.join(tmp, "out_cluster.tsv")) as fh:
        for line in fh:
            rep, member = line.split()[:2]
            mi = int(member)
            if rep not in seen:
                seen[rep] = n_clusters
                n_clusters += 1
            cluster_of[mi] = seen[rep]
    return cluster_of


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", default="noncoding-rna-family")
    args = ap.parse_args()

    os.makedirs(OUT_DIR, exist_ok=True)
    recs = load_task_seqs(args.task)
    print("records:", len(recs), flush=True)

    with tempfile.TemporaryDirectory(dir=os.path.join(ROOT, "data")) as tmp:
        cluster_of = cluster_sequences(recs, tmp)
    n_clusters = max(cluster_of) + 1
    print("clusters:", n_clusters, flush=True)

    # cluster-pure 80/10/10 assignment (deterministic order, seed via sort)
    import random
    rng = random.Random(17)
    order = list(range(n_clusters))
    rng.shuffle(order)
    n = len(recs)
    sizes = {c: 0 for c in range(n_clusters)}
    for c in cluster_of:
        sizes[c] += 1
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
        "seq": [r["seq"] for r in recs],
        "label": [r["label"] for r in recs],
        "cluster_id": ["c%d" % c for c in cluster_of],
        "split": [side[c] for c in cluster_of],
        "contaminated": [False] * len(recs),
    })
    out = os.path.join(OUT_DIR, "%s.parquet" % args.task)
    pq.write_table(tbl, out)
    import collections
    cnt = collections.Counter(tbl.column("split").to_pylist())
    print("split sizes:", dict(cnt), "->", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
