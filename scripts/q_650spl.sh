#!/bin/bash
# LANE 11: 650M spliceai full (slow big cell, ~15G bs8) — completes 650M full
# 4-task coverage for Q2/Q6.
set -x
cd /home/cunyuliu/rna-ft-eval
export PYTHONPATH=/root/rnaft/pypath:/home/cunyuliu/rna-ft-eval:/home/cunyuliu/rna-sc
export HF_HOME=/root/hf_home
export HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/root/miniconda3/envs/llr_env/bin/python
LOG=/root/rnaft/logs/q_650spl.log
echo "=== 650spliceai start $(date -u +%FT%TZ) ===" > $LOG

for SPLIT in random family; do
  for SEED in 17 29 43; do
    echo "--- $(date -u +%FT%TZ) RiNALMo-650M spliceai full s$SEED $SPLIT ---" >> $LOG
    timeout 28800 $PY -m rnafteval.finetune_spl --model RiNALMo-650M --task spliceai --strategy full --seed $SEED --split $SPLIT --device 0 --epochs 10 --batch-size 8 --lr 1e-05 >> $LOG 2>&1
    echo "RC=$?" >> $LOG
  done
done
echo "=== 650spliceai ALL DONE $(date -u +%FT%TZ) ===" >> $LOG
