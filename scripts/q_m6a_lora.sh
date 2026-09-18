#!/bin/bash
# m6A lora 臂: <model> lora × s{17,29,43} × {random,family} = 6 runs
# 用法: q_m6a_lora.sh <model> <gpu>
R=/mnt/cunyuliu/rna-ft-eval
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/home/cunyuliu/llr_env/bin/python
MODEL=$1
TAG=$(echo $MODEL | tr -d "-")
LOG=$R/logs/q_m6a_lora_${TAG}_g$2.log
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
    echo "=== $MODEL m6A lora s$seed $split GPU$GPU $(date +%T) ===" >> $LOG
    timeout 21600 $PY -m rnafteval.finetune_base --model $MODEL \
      --task modification --strategy lora --seed $seed --split $split \
      --device $GPU --epochs 3 --n-train 20000 --batch-size 32 >> $LOG 2>&1
    echo "--- exit $? $(date +%T) ---" >> $LOG
  done
done
echo "M6A $MODEL LORA DONE $(date)" >> $LOG
