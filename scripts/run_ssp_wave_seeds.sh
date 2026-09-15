#!/bin/bash
# E1 SSP 补种子波：formal seed (29/43) x {frozen,lora,full} x {random,family}
# E1 主矩阵无 head-only（spec v1.2）。用法: run_ssp_wave_seeds.sh <gpu> <seed>
R=/mnt/cunyuliu/rna-ft-eval
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home
export HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/home/cunyuliu/llr_env/bin/python
GPU=$1
SEED=$2
LOG=$R/logs/ssp_seeds_s${SEED}_g${GPU}.log
cd /home/cunyuliu/rna-ft-eval

for split in random family; do
  for strat in frozen lora full; do
    echo "=== ssp $strat s$SEED $split GPU$GPU $(date +%T) ===" >> $LOG
    timeout 21600 $PY -m rnafteval.finetune_ssp --model RNA-Sc-10M \
      --strategy $strat --seed $SEED --split $split \
      --device $GPU --epochs 3 --n-train 3000 --n-test 500 \
      --batch-size 4 >> $LOG 2>&1
  done
done
echo "SSP SEEDS s$SEED GPU$GPU DONE $(date)" >> $LOG
