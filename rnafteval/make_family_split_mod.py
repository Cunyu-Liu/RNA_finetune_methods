"""Modification (per-base m6A) family-level split via MMseqs2 80-80.

Split unit per spec §3.4: host transcript — all sites of one transcript stay
on one side. BEACON windows carry no transcript ID; overlapping 101-nt
windows from one transcript cluster together at 0.8/0.8, which implements
the host-purity rule as the closest available proxy.

Output: data/family_splits/modification.parquet (seq, cluster_id, split)
"""
from __future__ import annotations

import os
import random
import subprocess
import tempfile

import pyarrow as pa
import pyarrow.parquet as pq

from rnafteval.tasks import modification as mod_task

ROOT = "/mnt/cunyuliu/rna-ft-eval"
MMSEQS = "/home/cunyuliu/mmseqs/bin/mmseqs"
OUT = os.path.join(ROOT, "data", "family_splits", "modification.parquet")


def main() -> int:
    sp = mod_task.load_official_split()
    recs = sp["train"] + sp["validation"] + sp["test"]
    print("union windows: %d" % len(recs), flush=True)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with tempfile.TemporaryDirectory(dir=os.path.join(ROOT, "data")) as tmp:
        fasta = os.path.join(tmp, "seqs.fasta")
        with open(fasta, "w") as fh:
            for i, r in enumerate(recs):
                fh.write(">%d\n%s\n" % (i, r["seq"]))
        subprocess.run(
            [MMSEQS, "easy-cluster", fasta, os.path.join(tmp, "out"),
             os.path.join(tmp, "tmp"), "--min-seq-id", "0.8", "-c", "0.8",
             "--cov-mode", "0", "--threads", "16"],
            check=True, capture_output=True)
        cluster_of: dict[int, int] = {}
        n_clusters = 0
        seen_rep: dict[str, int] = {}
        with open(os.path.join(tmp, "out_cluster.tsv")) as fh:
            for line in fh:
                rep, member = line.split()[:2]
                if rep not in seen_rep:
                    seen_rep[rep] = n_clusters
                    n_clusters += 1
                cluster_of[int(member)] = seen_rep[rep]
    print("clusters: %d" % n_clusters, flush=True)

    rng = random.Random(17)
    order = list(range(n_clusters))
    rng.shuffle(order)
    sizes = {}
    for r_idx in range(len(recs)):
        c = cluster_of[r_idx]
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

    # host purity assertion: one cluster -> one side (by construction);
    # verify no duplicate window sequence straddles sides
    seq_side = {}
    for r_idx, r in enumerate(recs):
        s = side[cluster_of[r_idx]]
        if r["seq"] in seq_side:
            assert seq_side[r["seq"]] == s, "duplicate seq straddles sides"
        seq_side[r["seq"]] = s

    import collections
    cnt = collections.Counter(side[cluster_of[i]] for i in range(len(recs)))
    tbl = pa.table({
        "seq": [r["seq"] for r in recs],
        "labels": [" ".join(str(x) for x in r["labels"]) for r in recs],
        "cluster_id": ["c%d" % cluster_of[i] for i in range(len(recs))],
        "split": [side[cluster_of[i]] for i in range(len(recs))],
    })
    pq.write_table(tbl, OUT)
    print("split sizes:", dict(cnt), "->", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
