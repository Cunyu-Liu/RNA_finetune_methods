#!/bin/bash
# A8 LR grid phase 2: RNA-Sc-10M (当前默认 3e-4)
R=/mnt/cunyuliu/rna-ft-eval
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/home/cunyuliu/llr_env/bin/python
GPU=$1
LOG=$R/logs/q_lr_grid2.log
cd /home/cunyuliu/rna-ft-eval
for lr in 1e-5 3e-5 1e-4 3e-4; do
  for job in "RNA-Sc-10M full" "RNA-Sc-10M lora"; do
    set -- $job; model=$1; strat=$2
    echo "=== LR $lr $model $strat s101 GPU$GPU $(date +%T) ===" >> $LOG
    timeout 7200 $PY -m rnafteval.finetune_one --model $model \
      --task noncoding-rna-family --strategy $strat --seed 101 --split random \
      --device $GPU --lr $lr --epochs 10 --batch-size 16 >> $LOG 2>&1
  done
done
echo "LR GRID2 DONE $(date)" >> $LOG
