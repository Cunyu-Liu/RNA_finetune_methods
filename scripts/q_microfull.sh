#!/bin/bash
# LANE 6: micro FULL finetune on 4 new tasks (equivalence-line Q6 data: full vs lora per task)
# ~1G per proc; fast cells.
set -x
cd /home/cunyuliu/rna-ft-eval
export PYTHONPATH=/root/rnaft/pypath:/home/cunyuliu/rna-ft-eval:/home/cunyuliu/rna-sc
export HF_HOME=/root/hf_home
export HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/root/miniconda3/envs/llr_env/bin/python
LOG=/root/rnaft/logs/q_microfull.log
echo "=== microfull start $(date -u +%FT%TZ) ===" > $LOG

for TASK in degradation:regbase ssi:regbase spliceai:spl crispr-off-target:clf; do
  TN="${TASK%%:*}"; RN="${TASK##*:}"
  for SPLIT in random family; do
    for SEED in 17 29 43; do
      echo "--- $(date -u +%FT%TZ) RiNALMo-micro $TN full s$SEED $SPLIT ---" >> $LOG
      timeout 7200 $PY -m rnafteval.finetune_$RN --model RiNALMo-micro --task $TN --strategy full --seed $SEED --split $SPLIT --device 0 --epochs 10 --batch-size 16 --lr 1e-05 >> $LOG 2>&1
      echo "RC=$?" >> $LOG
    done
  done
done
echo "=== microfull ALL DONE $(date -u +%FT%TZ) ===" >> $LOG
