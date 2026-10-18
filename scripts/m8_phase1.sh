#!/bin/bash
# 8-task matrix phase 1: family splits for spliceai/crispr + smoke all new runners + first batch of full runs
# runs AFTER aido_retry finishes (GPU free). Chain: wait aido -> famsplit -> smoke -> batch A (micro model, all 8 tasks, frozen+lora, random+family)
set -x
cd /home/cunyuliu/rna-ft-eval
export PYTHONPATH=/root/rnaft/pypath:/home/cunyuliu/rna-ft-eval:/home/cunyuliu/rna-sc
export HF_HOME=/root/hf_home
export HF_ENDPOINT=https://hf-mirror.com
PY=/root/miniconda3/envs/llr_env/bin/python
LOG=/root/rnaft/logs/m8_phase1.log
echo "=== m8 phase1 start $(date -u +%FT%TZ) ===" > $LOG

# 0. wait for aido_retry done
while ! grep -q "aido retry done" /root/rnaft/logs/aido_retry.log 2>/dev/null; do sleep 120; done
echo "aido done, GPU free $(date -u +%FT%TZ)" >> $LOG

# 1. family splits for spliceai + crispr (mmseqs2 80/80, cluster-pure 80/10/10)
$PY - << 'EOF' >> $LOG 2>&1
import os, subprocess, tempfile, random
import pyarrow as pa, pyarrow.parquet as pq
ROOT = "/root/rna-ft-eval"
MMSEQS = "/home/cunyuliu/mmseqs/bin/mmseqs"
from rnafteval.tasks import spliceai as spl, crispr as crp
from rnafteval.tasks.dedup import dedup

def fam_split(task_name, recs, out_path, label_field="labels", label_fn=None):
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
    clusters = sorted(set(cluster_of))
    random.Random(17).shuffle(clusters)
    n = len(clusters)
    side_of = {}
    for i, c in enumerate(clusters):
        side_of[c] = "train" if i < int(n*0.8) else ("val" if i < int(n*0.9) else "test")
    rows = {"seq": [], label_field: [], "cluster_id": [], "split": []}
    for r, c in zip(recs, cluster_of):
        rows["seq"].append(r["seq"])
        rows[label_field].append(label_fn(r) if label_fn else r["labels"])
        rows["cluster_id"].append(str(c))
        rows["split"].append(side_of[c])
    # rename key if needed (parquet column name must match runner reads)
    final = {k: v for k, v in rows.items()}
    if label_field != "labels":
        final["labels"] = final.pop(label_field)
    pq.write_table(pa.table(final), out_path)
    from collections import Counter
    print(task_name, "clusters:", n, "split:", Counter(rows["split"]))

# spliceai: labels already list[int]
fam_split("spliceai", spl.load_spliceai(),
          os.path.join(ROOT, "data", "family_splits", "spliceai.parquet"))
# crispr: binary label int (from float)
fam_split("crispr-off-target", crp.load_crispr(),
          os.path.join(ROOT, "data", "family_splits", "crispr-off-target.parquet"),
          label_field="labels", label_fn=lambda r: [int(r["label"])])
print("FAMILY_SPLITS_M8_DONE")
EOF
grep FAMILY_SPLITS_M8_DONE $LOG || { echo "FAMSPLIT_FAILED" >> $LOG; exit 1; }

# 2. smoke: all 6 new-runner cells (crispr frozen/lora r+f, spliceai frozen/lora r)
timeout 1200 $PY -m rnafteval.finetune_clf --model RiNALMo-micro --task crispr-off-target --strategy frozen --seed 77 --split random --device 0 --epochs 1 --smoke >> $LOG 2>&1
echo "crispr_frozen_RC=$?" >> $LOG
timeout 1200 $PY -m rnafteval.finetune_clf --model RiNALMo-micro --task crispr-off-target --strategy lora --seed 77 --split random --device 0 --epochs 1 --smoke >> $LOG 2>&1
echo "crispr_lora_RC=$?" >> $LOG
timeout 1200 $PY -m rnafteval.finetune_clf --model RiNALMo-micro --task crispr-off-target --strategy frozen --seed 77 --split family --device 0 --epochs 1 --smoke >> $LOG 2>&1
echo "crispr_fam_RC=$?" >> $LOG
timeout 1200 $PY -m rnafteval.finetune_spl --model RiNALMo-micro --task spliceai --strategy frozen --seed 77 --split random --device 0 --epochs 1 --smoke >> $LOG 2>&1
echo "spl_frozen_RC=$?" >> $LOG
timeout 1200 $PY -m rnafteval.finetune_spl --model RiNALMo-micro --task spliceai --strategy lora --seed 77 --split random --device 0 --epochs 1 --smoke >> $LOG 2>&1
echo "spl_lora_RC=$?" >> $LOG
timeout 1200 $PY -m rnafteval.finetune_spl --model RiNALMo-micro --task spliceai --strategy frozen --seed 77 --split family --device 0 --epochs 1 --smoke >> $LOG 2>&1
echo "spl_fam_RC=$?" >> $LOG

# 3. batch A: micro model x 8 tasks x (frozen+lora) x (random+family) x 3 seeds — full runs
# note: ncRNA/m6A/MRL cells already exist in ledger from prior queues; new tasks only:
#   crispr (clf), spliceai (spl), degradation (regbase), ssi (regbase)
for TASK in crispr-off-target:clf spliceai:spl degradation:regbase ssi:regbase; do
  TN="${TASK%%:*}"; RN="${TASK##*:}"
  for STRAT in frozen lora; do
    for SPLIT in random family; do
      for SEED in 17 29 43; do
        echo "--- $(date -u +%FT%TZ) RiNALMo-micro $TN $STRAT s$SEED $SPLIT ---" >> $LOG
        timeout 7200 $PY -m rnafteval.finetune_$RN --model RiNALMo-micro --task $TN --strategy $STRAT --seed $SEED --split $SPLIT --device 0 --epochs 10 >> $LOG 2>&1
        echo "RC=$?" >> $LOG
      done
    done
  done
done
echo "=== m8 phase1 ALL DONE $(date -u +%FT%TZ) ===" >> $LOG
