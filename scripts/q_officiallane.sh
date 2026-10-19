#!/bin/bash
# FOURTH lane: small official models (ERNIE-RNA 86M + RNA-FM 96M) on new tasks
# Fills remaining GPU memory (~5G) + collects 8-task coverage for official models.
set -x
cd /home/cunyuliu/rna-ft-eval
export PYTHONPATH=/root/rnaft/pypath:/home/cunyuliu/rna-ft-eval:/home/cunyuliu/rna-sc
export HF_HOME=/root/hf_home
export HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/root/miniconda3/envs/llr_env/bin/python
LOG=/root/rnaft/logs/q_officiallane.log
echo "=== officiallane start $(date -u +%FT%TZ) ===" > $LOG

for MODEL in ERNIE-RNA RNA-FM; do
  for TASK in degradation:regbase ssi:regbase spliceai:spl crispr-off-target:clf; do
    TN="${TASK%%:*}"; RN="${TASK##*:}"
    for SPLIT in random family; do
      for SEED in 17 29 43; do
        echo "--- $(date -u +%FT%TZ) $MODEL $TN lora s$SEED $SPLIT ---" >> $LOG
        timeout 14400 $PY -m rnafteval.finetune_$RN --model $MODEL --task $TN --strategy lora --seed $SEED --split $SPLIT --device 0 --epochs 10 --batch-size 16 >> $LOG 2>&1
        echo "RC=$?" >> $LOG
      done
    done
  done
done
echo "=== officiallane ALL DONE $(date -u +%FT%TZ) ===" >> $LOG
