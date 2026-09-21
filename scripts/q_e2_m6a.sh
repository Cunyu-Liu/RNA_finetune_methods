#!/bin/bash
# E2-m6A 对称面板: <model> <gpu> —— m6A x {dora,ia3} x random x 3 种子
R=/mnt/cunyuliu/rna-ft-eval
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/home/cunyuliu/llr_env/bin/python
MODEL=$1
GPU=$2
TAG=$(echo $MODEL | tr -d "-")
LOG=$R/logs/q_e2_m6a_${TAG}_g${GPU}.log
cd /home/cunyuliu/rna-ft-eval

$PY -c "import torch; assert torch.cuda.is_available()" || exit 2
timeout 300 $PY -c "
import torch
free, _ = torch.cuda.mem_get_info($GPU)
assert free > 4e9, "free %.2fG" % (free/1e9)
print("GPU$GPU OK")" >> $LOG 2>&1 || exit 2

for strat in dora ia3; do
  for seed in 17 29 43; do
    echo "=== E2-m6A $MODEL $strat s$seed random GPU$GPU $(date +%T) ===" >> $LOG
    timeout 14400 $PY -m rnafteval.finetune_base --model $MODEL \
      --task modification --strategy $strat --seed $seed --split random \
      --device $GPU --epochs 3 --n-train 20000 --batch-size 32 >> $LOG 2>&1
    echo "--- exit $? $(date +%T) ---" >> $LOG
  done
done
echo "E2-M6A $MODEL DONE $(date)" >> $LOG
