#!/bin/bash
# LANE 8: RNA-Sc-300M (self-trained) on 4 new tasks — 8-task matrix coverage
# for the self-trained family + fills GPU. ~6G with bs16.
set -x
cd /home/cunyuliu/rna-ft-eval
export PYTHONPATH=/root/rnaft/pypath:/home/cunyuliu/rna-ft-eval:/home/cunyuliu/rna-sc
export HF_HOME=/root/hf_home
export HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/root/miniconda3/envs/llr_env/bin/python
LOG=/root/rnaft/logs/q_rnasc.log
echo "=== rnasc lane start $(date -u +%FT%TZ) ===" > $LOG

for TASK in degradation:regbase ssi:regbase spliceai:spl crispr-off-target:clf; do
  TN="${TASK%%:*}"; RN="${TASK##*:}"
  for SPLIT in random family; do
    for SEED in 17 29 43; do
      echo "--- $(date -u +%FT%TZ) RNA-Sc-300M $TN lora s$SEED $SPLIT ---" >> $LOG
      timeout 14400 $PY -m rnafteval.finetune_$RN --model RNA-Sc-300M --task $TN --strategy lora --seed $SEED --split $SPLIT --device 0 --epochs 10 --batch-size 16 >> $LOG 2>&1
      echo "RC=$?" >> $LOG
    done
  done
done
echo "=== rnasc lane ALL DONE $(date -u +%FT%TZ) ===" >> $LOG
