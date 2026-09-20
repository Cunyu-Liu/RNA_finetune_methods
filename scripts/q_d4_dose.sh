#!/bin/bash
# A8-D4 预训练深度剂量实验: RNA-Sc-10M 同配方, 只变预训练进度 ck{1,5,10,15,20}
# ncRNA + m6A x full@3e-4 默认 x s17 random —— 早期崩/晚期幸存 => 预训练深度因果
R=/mnt/cunyuliu/rna-ft-eval
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/home/cunyuliu/llr_env/bin/python
GPU=$1
LOG=$R/logs/q_d4_dose_g${GPU}.log
cd /home/cunyuliu/rna-ft-eval

$PY -c "import torch; assert torch.cuda.is_available()" || exit 2
timeout 300 $PY -c "
import torch
free, _ = torch.cuda.mem_get_info($GPU)
assert free > 5e9, "free %.2fG" % (free/1e9)
print("GPU$GPU OK")" >> $LOG 2>&1 || exit 2

for ck in 1 5 10 15; do
  M=RNA-Sc-10M-ck$ck
  echo "=== D4 $M ncRNA full(default) s17 random GPU$GPU $(date +%T) ===" >> $LOG
  timeout 14400 $PY -m rnafteval.finetune_one --model $M \
    --task noncoding-rna-family --strategy full --seed 17 --split random \
    --device $GPU --epochs 10 --batch-size 8 >> $LOG 2>&1
  echo "--- exit $? $(date +%T) ---" >> $LOG
  echo "=== D4 $M m6A full(default) s17 random GPU$GPU $(date +%T) ===" >> $LOG
  timeout 14400 $PY -m rnafteval.finetune_base --model $M \
    --task modification --strategy full --seed 17 --split random \
    --device $GPU --epochs 3 --n-train 20000 --batch-size 32 >> $LOG 2>&1
  echo "--- exit $? $(date +%T) ---" >> $LOG
done
echo "D4-DOSE DONE $(date)" >> $LOG
