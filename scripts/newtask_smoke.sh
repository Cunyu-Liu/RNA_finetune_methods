#!/bin/bash
# smoke + family-split generation for new tasks, chained AFTER q5090 finishes (GPU free then).
set -x
cd /home/cunyuliu/rna-ft-eval
export PYTHONPATH=/root/rnaft/pypath:/home/cunyuliu/rna-ft-eval:/home/cunyuliu/rna-sc
export HF_HOME=/root/hf_home
export HF_ENDPOINT=https://hf-mirror.com
PY=/root/miniconda3/envs/llr_env/bin/python
LOG=/root/rnaft/logs/newtask_smoke.log
echo "=== newtask smoke start $(date -u +%FT%TZ) ===" > $LOG

# 0. wait for q5090 done
while ! grep -q "q5090 ALL DONE" /root/rnaft/logs/q5090.log 2>/dev/null; do sleep 300; done
echo "q5090 done, GPU free $(date -u +%FT%TZ)" >> $LOG

# 1. family splits for degradation + ssi (mmseqs2 80/80, same protocol as make_family_split)
$PY - << 'EOF' >> $LOG 2>&1
# family split generation for new tasks: reuse make_family_split machinery with new task loaders
import os, subprocess, tempfile, random
import pyarrow as pa, pyarrow.parquet as pq
ROOT = "/root/rna-ft-eval"
MMSEQS = "/home/cunyuliu/mmseqs/bin/mmseqs"
from rnafteval.tasks import degradation as deg, ssi as ssi
from rnafteval.tasks.dedup import dedup

def fam_split(task_name, recs, out_path):
    recs = dedup(recs)
    tmp = tempfile.mkdtemp()
    fasta = os.path.join(tmp, "seqs.fasta")
    with open(fasta, "w") as fh:
        for i, r in enumerate(recs):
            fh.write(">%d\n%s\n" % (i, r["seq"].replace("U", "T")))
    subprocess.run([MMSEQS, "easy-cluster", fasta, os.path.join(tmp, "out"),
                    os.path.join(tmp, "tmp"), "--min-seq-id", "0.8", "-c", "0.8",
                    "--cov-mode", "0", "--threads", "8"], check=True, capture_output=True)
    cluster_of = [0] * len(recs)
    with open(os.path.join(tmp, "out_cluster.tsv")) as fh:
        for line in fh:
            rep, member = line.split()[:2]
            cluster_of[int(member)] = int(rep)
    # cluster-pure 80/10/10 (seed 17)
    clusters = sorted(set(cluster_of))
    random.Random(17).shuffle(clusters)
    n = len(clusters)
    side_of = {}
    for i, c in enumerate(clusters):
        side_of[c] = "train" if i < int(n*0.8) else ("val" if i < int(n*0.9) else "test")
    rows = {"seq": [], "labels": [], "cluster_id": [], "split": []}
    for r, c in zip(recs, cluster_of):
        rows["seq"].append(r["seq"])
        rows["labels"].append(list(map(float, r["labels"])))
        rows["cluster_id"].append(str(c))
        rows["split"].append(side_of[c])
    pq.write_table(pa.table(rows), out_path)
    from collections import Counter
    print(task_name, "clusters:", n, "split:", Counter(rows["split"]))

fam_split("degradation", deg.load_degradation(), os.path.join(ROOT, "data", "family_splits", "degradation.parquet"))
fam_split("ssi", ssi.load_ssi(), os.path.join(ROOT, "data", "family_splits", "ssi.parquet"))
print("FAMILY_SPLITS_DONE")
EOF
grep FAMILY_SPLITS_DONE $LOG || echo FAMSPLIT_FAILED

# 2. true-CUDA smoke: degradation frozen/lora + ssi frozen (small)
timeout 1200 $PY -m rnafteval.finetune_regbase --model RiNALMo-micro --task degradation --strategy frozen --seed 77 --split random --device 0 --epochs 1 --smoke >> $LOG 2>&1
echo "deg_frozen_RC=$?" >> $LOG
timeout 1200 $PY -m rnafteval.finetune_regbase --model RiNALMo-micro --task degradation --strategy lora --seed 77 --split random --device 0 --epochs 1 --smoke >> $LOG 2>&1
echo "deg_lora_RC=$?" >> $LOG
timeout 1200 $PY -m rnafteval.finetune_regbase --model RiNALMo-micro --task ssi --strategy frozen --seed 77 --split random --device 0 --epochs 1 --smoke >> $LOG 2>&1
echo "ssi_frozen_RC=$?" >> $LOG
timeout 1200 $PY -m rnafteval.finetune_regbase --model RiNALMo-micro --task ssi --strategy lora --seed 77 --split random --device 0 --epochs 1 --smoke >> $LOG 2>&1
echo "ssi_lora_RC=$?" >> $LOG
timeout 1200 $PY -m rnafteval.finetune_regbase --model RiNALMo-micro --task degradation --strategy frozen --seed 77 --split family --device 0 --epochs 1 --smoke >> $LOG 2>&1
echo "deg_fam_RC=$?" >> $LOG
echo "=== newtask smoke ALL DONE $(date -u +%FT%TZ) ===" >> $LOG
