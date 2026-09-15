#!/bin/bash
# RiNALMo full/lora @ tuned LR (1e-5, from A8 grid s101) — 3 formal seeds
R=/mnt/cunyuliu/rna-ft-eval
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/home/cunyuliu/llr_env/bin/python
GPU=$1
LOG=$R/logs/q_rinalmo_lrbest.log
cd /home/cunyuliu/rna-ft-eval
for job in "full 17 random" "full 29 random" "full 43 random" "full 17 family" "full 29 family" "full 43 family"; do
  set -- $job; strat=$1; seed=$2; split=$3
  echo "=== RiNALMo $strat s$seed $split lr1e-5 GPU$GPU $(date +%T) ===" >> $LOG
  timeout 14400 $PY -m rnafteval.finetune_one --model RiNALMo-micro \
    --task noncoding-rna-family --strategy $strat --seed $seed --split $split \
    --device $GPU --lr 1e-5 --epochs 10 --batch-size 8 >> $LOG 2>&1
done
echo "RINALMO LRBEST DONE $(date)" >> $LOG
