#!/bin/bash
# m6A 模型扩展首探: <model> frozen × s{17,29,43} × {random,family} = 6 runs
# C4 per-base 崩溃矩阵从 0/4 扩到 0/8（ERNIE/RNA-FM 入场）
# 口径 = RiNALMo m6A 正式 runs（epochs 3 / n-train 20000 / bs 32）
R=/mnt/cunyuliu/rna-ft-eval
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/home/cunyuliu/llr_env/bin/python
MODEL=$1
TAG=$(echo $MODEL | tr -d "-")
LOG=$R/logs/q_m6a_${TAG}_g$2.log
cd /home/cunyuliu/rna-ft-eval
GPU=$2

$PY -c "import torch; assert torch.cuda.is_available()" || exit 2
timeout 300 $PY -c "
import torch
free, _ = torch.cuda.mem_get_info($GPU)
assert free > 4e9, 'free %.2fG' % (free/1e9)
print('GPU$GPU OK')" >> $LOG 2>&1 || exit 2

for split in random family; do
  for seed in 17 29 43; do
    echo "=== $MODEL m6A frozen s$seed $split GPU$GPU $(date +%T) ===" >> $LOG
    timeout 21600 $PY -m rnafteval.finetune_base --model $MODEL \
      --task modification --strategy frozen --seed $seed --split $split \
      --device $GPU --epochs 3 --n-train 20000 --batch-size 32 >> $LOG 2>&1
    echo "--- exit $? $(date +%T) ---" >> $LOG
  done
done
echo "M6A $MODEL FROZEN DONE $(date)" >> $LOG
