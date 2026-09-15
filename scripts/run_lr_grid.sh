#!/bin/bash
# A8 LR grid (tuning seed=101, spec E1 优化器协议):
# RiNALMo-micro full FT 在 lr=3e-4 崩溃 (ACC 0.07) -> 网格搜 {1e-5, 3e-5, 1e-4, 3e-4}
R=/mnt/cunyuliu/rna-ft-eval
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/home/cunyuliu/llr_env/bin/python
GPU=$1
LOG=$R/logs/q_lr_grid.log
cd /home/cunyuliu/rna-ft-eval
for lr in 1e-5 3e-5 1e-4 3e-4; do
  for job in "RiNALMo-micro full" "RiNALMo-micro lora"; do
    set -- $job; model=$1; strat=$2
    echo "=== LR $lr $model $strat s101 GPU$GPU $(date +%T) ===" >> $LOG
    timeout 7200 $PY -m rnafteval.finetune_one --model $model \
      --task noncoding-rna-family --strategy $strat --seed 101 --split random \
      --device $GPU --lr $lr --epochs 10 --batch-size 8 >> $LOG 2>&1
  done
done
echo "LR GRID DONE $(date)" >> $LOG
