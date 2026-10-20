#!/bin/bash
# LANE 7: 650M FULL finetune on 3 lighter new tasks (degradation/ssi/crispr; spliceai
# too slow for 650M full 10ep on 32G — leave to q_diag rerun lane). ~12G with bs8.
set -x
cd /home/cunyuliu/rna-ft-eval
export PYTHONPATH=/root/rnaft/pypath:/home/cunyuliu/rna-ft-eval:/home/cunyuliu/rna-sc
export HF_HOME=/root/hf_home
export HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/root/miniconda3/envs/llr_env/bin/python
LOG=/root/rnaft/logs/q_650full.log
echo "=== 650full start $(date -u +%FT%TZ) ===" > $LOG

sleep 60
for TASK in degradation:regbase ssi:regbase crispr-off-target:clf; do
  TN="${TASK%%:*}"; RN="${TASK##*:}"
  for SPLIT in random family; do
    for SEED in 17 29 43; do
      echo "--- $(date -u +%FT%TZ) RiNALMo-650M $TN full s$SEED $SPLIT ---" >> $LOG
      timeout 14400 $PY -m rnafteval.finetune_$RN --model RiNALMo-650M --task $TN --strategy full --seed $SEED --split $SPLIT --device 0 --epochs 10 --batch-size 8 --lr 1e-05 >> $LOG 2>&1
      echo "RC=$?" >> $LOG
    done
  done
done
echo "=== 650full ALL DONE $(date -u +%FT%TZ) ===" >> $LOG
