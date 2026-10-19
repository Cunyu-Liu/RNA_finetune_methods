#!/bin/bash
# PARALLEL lane: big models (RiNALMo-650M + RiNALMo-mega) on 4 new tasks
# Fills GPU memory alongside m8_repair (micro lane).
# 650M lora ~17G + micro ~2G < 32G. Runs bs16.
# Serves PPT Q2 (3 models x 6 tasks mechanism vis) + Q1 (8-task coverage).
set -x
cd /home/cunyuliu/rna-ft-eval
export PYTHONPATH=/root/rnaft/pypath:/home/cunyuliu/rna-ft-eval:/home/cunyuliu/rna-sc
export HF_HOME=/root/hf_home
export HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/root/miniconda3/envs/llr_env/bin/python
LOG=/root/rnaft/logs/q_biglane.log
echo "=== biglane start $(date -u +%FT%TZ) ===" > $LOG

# 650M: 4 new tasks x lora x random x 3 seeds (12 cells, ~17G each w/ bs16)
for TASK in degradation:regbase ssi:regbase spliceai:spl crispr-off-target:clf; do
  TN="${TASK%%:*}"; RN="${TASK##*:}"
  for SEED in 17 29 43; do
    echo "--- $(date -u +%FT%TZ) RiNALMo-650M $TN lora s$SEED random ---" >> $LOG
    timeout 14400 $PY -m rnafteval.finetune_$RN --model RiNALMo-650M --task $TN --strategy lora --seed $SEED --split random --device 0 --epochs 10 --batch-size 16 >> $LOG 2>&1
    echo "RC=$?" >> $LOG
  done
done
echo "=== biglane 650M random lane done $(date -u +%FT%TZ) ===" >> $LOG

# 650M: 4 new tasks x lora x family x 3 seeds (12 cells)
for TASK in degradation:regbase ssi:regbase spliceai:spl crispr-off-target:clf; do
  TN="${TASK%%:*}"; RN="${TASK##*:}"
  for SEED in 17 29 43; do
    echo "--- $(date -u +%FT%TZ) RiNALMo-650M $TN lora s$SEED family ---" >> $LOG
    timeout 14400 $PY -m rnafteval.finetune_$RN --model RiNALMo-650M --task $TN --strategy lora --seed $SEED --split family --device 0 --epochs 10 --batch-size 16 >> $LOG 2>&1
    echo "RC=$?" >> $LOG
  done
done
echo "=== biglane 650M family lane done $(date -u +%FT%TZ) ===" >> $LOG

# mega: 4 new tasks x lora x (random+family) x 3 seeds (24 cells, bs16 ~8G)
for TASK in degradation:regbase ssi:regbase spliceai:spl crispr-off-target:clf; do
  TN="${TASK%%:*}"; RN="${TASK##*:}"
  for SPLIT in random family; do
    for SEED in 17 29 43; do
      echo "--- $(date -u +%FT%TZ) RiNALMo-mega $TN lora s$SEED $SPLIT ---" >> $LOG
      timeout 14400 $PY -m rnafteval.finetune_$RN --model RiNALMo-mega --task $TN --strategy lora --seed $SEED --split $SPLIT --device 0 --epochs 10 --batch-size 16 >> $LOG 2>&1
      echo "RC=$?" >> $LOG
    done
  done
done
echo "=== biglane ALL DONE $(date -u +%FT%TZ) ===" >> $LOG
