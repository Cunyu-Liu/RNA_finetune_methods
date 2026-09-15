#!/bin/bash
# RiNALMo SSP: frozen/lora x random/family, seed 17 (MIG-safe: lora-only + frozen)
R=/mnt/cunyuliu/rna-ft-eval
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/home/cunyuliu/llr_env/bin/python
GPU=$1
LOG=$R/logs/q_ssp_rinalmo_g$GPU.log
cd /home/cunyuliu/rna-ft-eval
for job in "frozen 17 random" "lora 17 random" "frozen 17 family" "lora 17 family"; do
  set -- $job; strat=$1; seed=$2; split=$3
  echo "=== ssp RiNALMo $strat s$seed $split GPU$GPU $(date +%T) ===" >> $LOG
  timeout 21600 $PY -m rnafteval.finetune_ssp --model RiNALMo-micro \
    --strategy $strat --seed $seed --split $split \
    --device $GPU --epochs 3 --n-train 3000 --n-test 500 \
    --batch-size 4 >> $LOG 2>&1
done
echo "SSP RINALMO GPU$GPU DONE $(date)" >> $LOG
