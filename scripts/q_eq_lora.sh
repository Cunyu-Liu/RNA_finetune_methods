#!/bin/bash
# 等价线 LoRA 臂: <model> <gpu> — ncRNA × lora × {random,family} × s{17,29,43}
# 协议对齐 E2: epochs 10 / bs 8 / 默认 LR 3e-4
R=/mnt/cunyuliu/rna-ft-eval
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/home/cunyuliu/llr_env/bin/python
MODEL=$1
GPU=$2
TAG=$(echo $MODEL | tr -d "-")
LOG=$R/logs/q_eq_lora_${TAG}_g${GPU}.log
cd /home/cunyuliu/rna-ft-eval

$PY -c "import torch; assert torch.cuda.is_available()" || exit 2
timeout 300 $PY -c "
import torch
free, _ = torch.cuda.mem_get_info($GPU)
assert free > 4e9, "free %.2fG" % (free/1e9)
print("GPU$GPU OK")" >> $LOG 2>&1 || exit 2

for split in random family; do
  for seed in 17 29 43; do
    echo "=== $MODEL ncRNA lora s$seed $split GPU$GPU $(date +%T) ===" >> $LOG
    timeout 21600 $PY -m rnafteval.finetune_one --model $MODEL \
      --task noncoding-rna-family --strategy lora --seed $seed --split $split \
      --device $GPU --epochs 10 --batch-size 8 >> $LOG 2>&1
    echo "--- exit $? $(date +%T) ---" >> $LOG
  done
done
echo "EQ-LORA $MODEL DONE $(date)" >> $LOG
