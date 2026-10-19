#!/bin/bash
# FIFTH lane: mega FULL finetune on new tasks (PPT Q2 needs full-FT pre/post too)
# bs8 ~12G; total across lanes ~29G/32G near-full occupancy.
set -x
cd /home/cunyuliu/rna-ft-eval
export PYTHONPATH=/root/rnaft/pypath:/home/cunyuliu/rna-ft-eval:/home/cunyuliu/rna-sc
export HF_HOME=/root/hf_home
export HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/root/miniconda3/envs/llr_env/bin/python
LOG=/root/rnaft/logs/q_fulllane.log
echo "=== fulllane start $(date -u +%FT%TZ) ===" > $LOG

# 1. wait a bit for other lanes to settle (avoid simultaneous cold-start OOM)
sleep 120

for TASK in degradation:regbase ssi:regbase spliceai:spl crispr-off-target:clf; do
  TN="${TASK%%:*}"; RN="${TASK##*:}"
  for SPLIT in random family; do
    for SEED in 17 29 43; do
      echo "--- $(date -u +%FT%TZ) RiNALMo-mega $TN full s$SEED $SPLIT ---" >> $LOG
      timeout 14400 $PY -m rnafteval.finetune_$RN --model RiNALMo-mega --task $TN --strategy full --seed $SEED --split $SPLIT --device 0 --epochs 10 --batch-size 8 --lr 1e-05 >> $LOG 2>&1
      echo "RC=$?" >> $LOG
    done
  done
done
echo "=== fulllane ALL DONE $(date -u +%FT%TZ) ===" >> $LOG
