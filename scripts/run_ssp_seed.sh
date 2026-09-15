#!/bin/bash
# SSP 单种子队列: run_ssp_seed.sh <GPU> <SEED> <SPLIT...>
# E1 口径: frozen/lora/full x 指定 split (head-only 属 E2, 不跑)
R=/mnt/cunyuliu/rna-ft-eval
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/home/cunyuliu/llr_env/bin/python
GPU=$1; SEED=$2; shift 2
SPLITS="$@"
[ -z "$SPLITS" ] && SPLITS="random family"
LOG=$R/logs/q_ssp_e1_g${GPU}.log
cd /home/cunyuliu/rna-ft-eval
for split in $SPLITS; do
  for strat in frozen lora full; do
    echo "=== ssp $strat s$SEED $split GPU$GPU $(date +%T) ===" >> $LOG
    timeout 21600 $PY -m rnafteval.finetune_ssp --model RNA-Sc-10M \
      --strategy $strat --seed $SEED --split $split \
      --device $GPU --epochs 3 --n-train 3000 --n-test 500 \
      --batch-size 4 >> $LOG 2>&1
  done
done
echo "SSP SEED$SEED GPU$GPU DONE $(date)" >> $LOG
