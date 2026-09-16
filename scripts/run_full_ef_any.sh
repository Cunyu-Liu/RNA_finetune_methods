#!/bin/bash
# 整卡轮询队列: 每 10min 扫 GPU0-5, 首个 free>=10G 的卡承接
# ERNIE lora s29/s43 补齐 + ERNIE/RNA-FM full 矩阵 (4+6+6=16 runs, ncrna)
# 依据: ERNIE 显式 attn 需整卡 (lora 峰值 4659MB 超 MIG); RNA-FM lora 峰值
# 3632MB -> full 超 MIG; GPU5 当前他人 ~38G 占用, 等未来空闲卡 ("未来空闲卡
# 随时征用" 落实为轮询). 最长等 72h.
R=/mnt/cunyuliu/rna-ft-eval
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/home/cunyuliu/llr_env/bin/python
LOG=$R/logs/q_full_ef_any.log
cd /home/cunyuliu/rna-ft-eval

$PY -c "import torch; assert torch.cuda.is_available(), 'CUDA UNAVAILABLE'" || exit 2

GPU=""
attempt=0
while [ $attempt -lt 432 ]; do
  attempt=$((attempt+1))
  GPU=$($PY -c "
import torch
for i in range(6):
    try:
        free, total = torch.cuda.mem_get_info(i)
    except Exception:
        continue
    if free > 10e9:
        print(i)
        break
")
  [ -n "$GPU" ] && break
  if [ $((attempt % 6)) -eq 1 ]; then
    echo "scan #$attempt: 无整卡 free>=10G, 10min 后重试 $(date +%T)" >> $LOG
  fi
  sleep 600
done
if [ -z "$GPU" ]; then
  echo "GIVEUP: 72h 无整卡空闲 $(date)" >> $LOG
  exit 3
fi
echo "CLAIM GPU$GPU (scan #$attempt) $(date)" >> $LOG
timeout 300 $PY -c "
import torch
free, total = torch.cuda.mem_get_info($GPU)
print('GPU$GPU free %.2fG at claim' % (free/1e9))" >> $LOG 2>&1

for split in random family; do
  for seed in 29 43; do
    echo "=== ERNIE-RNA lora s$seed $split GPU$GPU $(date +%T) ===" >> $LOG
    timeout 21600 $PY -m rnafteval.finetune_one --model ERNIE-RNA \
      --task noncoding-rna-family --strategy lora --seed $seed --split $split \
      --device $GPU --epochs 10 --batch-size 8 >> $LOG 2>&1
    echo "--- exit $? $(date +%T) ---" >> $LOG
  done
done

for model in ERNIE-RNA RNA-FM; do
  for split in random family; do
    for seed in 17 29 43; do
      echo "=== $model full s$seed $split GPU$GPU $(date +%T) ===" >> $LOG
      timeout 21600 $PY -m rnafteval.finetune_one --model $model \
        --task noncoding-rna-family --strategy full --seed $seed --split $split \
        --device $GPU --epochs 10 --batch-size 8 >> $LOG 2>&1
      echo "--- exit $? $(date +%T) ---" >> $LOG
    done
  done
done
echo "ERNIE+RNAFM FULL-ARM QUEUE GPU$GPU DONE $(date)" >> $LOG
