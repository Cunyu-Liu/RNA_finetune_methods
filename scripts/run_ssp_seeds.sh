#!/bin/bash
# SSP seeds 29/43: 3 strategies x 2 splits (E1 口径; head-only 不跑)
R=/mnt/cunyuliu/rna-ft-eval
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/home/cunyuliu/llr_env/bin/python
GPU=$1
LOG=$R/logs/q_ssp_seeds_g$GPU.log
cd /home/cunyuliu/rna-ft-eval
for seed in 29 43; do
  for job in "frozen random" "lora random" "full random" "frozen family" "lora family" "full family"; do
    set -- $job; strat=$1; split=$2
    echo "=== ssp $strat s$seed $split GPU$GPU $(date +%T) ===" >> $LOG
    timeout 21600 $PY -m rnafteval.finetune_ssp --model RNA-Sc-10M \
      --strategy $strat --seed $seed --split $split \
      --device $GPU --epochs 3 --n-train 3000 --n-test 500 \
      --batch-size 4 >> $LOG 2>&1
  done
done
echo "SSP SEEDS GPU$GPU DONE $(date)" >> $LOG
