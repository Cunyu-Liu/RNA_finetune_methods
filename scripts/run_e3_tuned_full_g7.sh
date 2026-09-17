#!/bin/bash
# GPU7 MIG: E3 tuned-full 补跑 — RiNALMo full @1e-5 × n ∈ {10,100,1000} × 3 种子
# 背景: E3 首轴 full 列小档为默认 LR 崩溃值 (A8) — C3 干净曲线需要 tuned 臂
# run_id = _e3<n>_lr1e-05 双标签 (不与现有行冲突)
R=/mnt/cunyuliu/rna-ft-eval
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/home/cunyuliu/llr_env/bin/python
LOG=$R/logs/q_e3_tuned_full_g7.log
cd /home/cunyuliu/rna-ft-eval
GPU=7

$PY -c "import torch; assert torch.cuda.is_available()" || exit 2
timeout 300 $PY -c "
import torch
free, _ = torch.cuda.mem_get_info($GPU)
assert free > 2e9, 'GPU$GPU free %.2fG < 2G' % (free/1e9)
print('GPU$GPU free %.2fG OK' % (free/1e9))" >> $LOG 2>&1 || exit 2

for n in 10 100 1000; do
  for seed in 17 29 43; do
    echo "=== E3-TUNED n=$n full s$seed lr1e-5 GPU$GPU $(date +%T) ===" >> $LOG
    timeout 14400 $PY -m rnafteval.finetune_one --model RiNALMo-micro \
      --task noncoding-rna-family --strategy full --seed $seed \
      --split family --device $GPU --lr 1e-5 --epochs 10 --batch-size 8 \
      --n-train $n >> $LOG 2>&1
    echo "--- exit $? $(date +%T) ---" >> $LOG
  done
done
echo "E3 TUNED FULL GPU$GPU DONE $(date)" >> $LOG
