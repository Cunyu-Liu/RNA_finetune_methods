#!/bin/bash
# G7 (MIG 4.75G): SpliceBERT E1 full 矩阵补齐 x 3 seeds x 2 splits (ncrna)
# 显存依据: 同模型 lora 峰值 1013MB -> full ~1.5G, MIG 可容纳
R=/mnt/cunyuliu/rna-ft-eval
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/home/cunyuliu/llr_env/bin/python
LOG=$R/logs/q_full3_g7.log
cd /home/cunyuliu/rna-ft-eval
GPU=${1:-7}

$PY -c "import torch; assert torch.cuda.is_available(), 'CUDA UNAVAILABLE'" || exit 2

ok=0
for i in $(seq 1 10); do
  if timeout 300 $PY -c "
import torch
free, total = torch.cuda.mem_get_info($GPU)
assert free > 2e9, 'GPU$GPU free %.2fG < 2G' % (free/1e9)
print('GPU$GPU free %.2fG OK' % (free/1e9))" >> $LOG 2>&1; then
    ok=1; break
  fi
  echo "memcheck retry $i (60s) $(date +%T)" >> $LOG
  sleep 60
done
[ $ok -eq 1 ] || { echo "G7 MEMCHECK FAILED exit 2 $(date)" >> $LOG; exit 2; }

for split in random family; do
  for seed in 17 29 43; do
    echo "=== SpliceBERT full s$seed $split GPU$GPU $(date +%T) ===" >> $LOG
    timeout 14400 $PY -m rnafteval.finetune_one --model SpliceBERT \
      --task noncoding-rna-family --strategy full --seed $seed --split $split \
      --device $GPU --epochs 10 --batch-size 8 >> $LOG 2>&1
    echo "--- exit $? $(date +%T) ---" >> $LOG
  done
done
echo "SPLICEBERT FULL GPU$GPU DONE $(date)" >> $LOG
