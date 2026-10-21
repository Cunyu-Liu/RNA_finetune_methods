#!/bin/bash
# LANE 9: RNA-Sc-300M full finetune on 2 lighter new tasks (degradation/ssi) —
# full-FT arm for self-trained family in Q6 equivalence analysis. ~12G bs8.
set -x
cd /home/cunyuliu/rna-ft-eval
export PYTHONPATH=/root/rnaft/pypath:/home/cunyuliu/rna-ft-eval:/home/cunyuliu/rna-sc
export HF_HOME=/root/hf_home
export HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/root/miniconda3/envs/llr_env/bin/python
LOG=/root/rnaft/logs/q_rnascfull.log
echo "=== rnascfull start $(date -u +%FT%TZ) ===" > $LOG

sleep 120
for TASK in degradation:regbase ssi:regbase; do
  TN="${TASK%%:*}"; RN="${TASK##*:}"
  for SPLIT in random family; do
    for SEED in 17 29 43; do
      echo "--- $(date -u +%FT%TZ) RNA-Sc-300M $TN full s$SEED $SPLIT ---" >> $LOG
      timeout 14400 $PY -m rnafteval.finetune_$RN --model RNA-Sc-300M --task $TN --strategy full --seed $SEED --split $SPLIT --device 0 --epochs 10 --batch-size 8 --lr 3e-05 >> $LOG 2>&1
      echo "RC=$?" >> $LOG
    done
  done
done
echo "=== rnascfull ALL DONE $(date -u +%FT%TZ) ===" >> $LOG
