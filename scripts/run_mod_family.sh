#!/bin/bash
# modification family-arm queue: 3 strategies x 3 seeds (spec E1: frozen/lora/full)
R=/mnt/cunyuliu/rna-ft-eval
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/home/cunyuliu/llr_env/bin/python
GPU=$1
LOG=$R/logs/q_mod_family.log
cd /home/cunyuliu/rna-ft-eval
for job in "frozen 17" "frozen 29" "frozen 43" "lora 17" "lora 29" "lora 43" "full 17" "full 29" "full 43"; do
  set -- $job; strat=$1; seed=$2
  echo "=== modification-family $strat s$seed GPU$GPU $(date +%T) ===" >> $LOG
  timeout 14400 $PY -m rnafteval.finetune_base --model RNA-Sc-10M \
    --task modification --strategy $strat --seed $seed --split family \
    --device $GPU --epochs 3 --n-train 20000 --batch-size 32 >> $LOG 2>&1
done
echo "MOD FAMILY QUEUE DONE $(date)" >> $LOG
