#!/bin/bash
# LANE 10: NucleicBERT (tierB) on 4 new tasks — third-camp coverage for 8-task matrix.
# ~6G with bs8. Fills GPU toward ~22G total.
set -x
cd /home/cunyuliu/rna-ft-eval
export PYTHONPATH=/root/rnaft/pypath:/home/cunyuliu/rna-ft-eval:/home/cunyuliu/rna-sc
export HF_HOME=/root/hf_home
export HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/root/miniconda3/envs/llr_env/bin/python
LOG=/root/rnaft/logs/q_nblane.log
echo "=== nblane start $(date -u +%FT%TZ) ===" > $LOG

sleep 180
for TASK in degradation:regbase ssi:regbase spliceai:spl crispr-off-target:clf; do
  TN="${TASK%%:*}"; RN="${TASK##*:}"
  for SPLIT in random family; do
    for SEED in 17 29 43; do
      echo "--- $(date -u +%FT%TZ) NucleicBERT $TN lora s$SEED $SPLIT ---" >> $LOG
      timeout 14400 $PY -m rnafteval.finetune_$RN --model NucleicBERT --task $TN --strategy lora --seed $SEED --split $SPLIT --device 0 --epochs 10 --batch-size 8 >> $LOG 2>&1
      echo "RC=$?" >> $LOG
    done
  done
done
echo "=== nblane ALL DONE $(date -u +%FT%TZ) ===" >> $LOG
