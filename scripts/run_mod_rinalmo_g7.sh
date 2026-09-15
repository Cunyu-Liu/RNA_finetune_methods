#!/bin/bash
# G7 (MIG 4.75G): RiNALMo-micro modification E1 矩阵 frozen/lora x 3 seeds x 2 splits
# (E1 最大缺口: RiNALMo 在 modification 上 0 run) + E2 IA3 修复后重跑 x 3 seeds
# full 不上 MIG (需整卡, 排 G5 链)
R=/mnt/cunyuliu/rna-ft-eval
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/home/cunyuliu/llr_env/bin/python
LOG=$R/logs/q_mod_rinalmo_g7.log
cd /home/cunyuliu/rna-ft-eval
GPU=7

$PY -c "import torch; assert torch.cuda.is_available(), 'CUDA UNAVAILABLE'" || exit 2
timeout 300 $PY -c "
import torch
free, total = torch.cuda.mem_get_info($GPU)
assert free > 3e9, 'GPU$GPU free %.2fG < 3G' % (free/1e9)
print('GPU$GPU free %.2fG OK' % (free/1e9))" >> $LOG 2>&1 || exit 2

for strat in frozen lora; do
  for split in random family; do
    for seed in 17 29 43; do
      echo "=== modification RiNALMo $strat s$seed $split GPU$GPU $(date +%T) ===" >> $LOG
      timeout 14400 $PY -m rnafteval.finetune_base --model RiNALMo-micro \
        --task modification --strategy $strat --seed $seed --split $split \
        --device $GPU --epochs 3 --n-train 20000 --batch-size 32 >> $LOG 2>&1
      echo "--- exit $? $(date +%T) ---" >> $LOG
    done
  done
done

for seed in 17 29 43; do
  echo "=== RiNALMo ia3 s$seed random GPU$GPU post-fix-rerun $(date +%T) ===" >> $LOG
  timeout 14400 $PY -m rnafteval.finetune_one --model RiNALMo-micro \
    --task noncoding-rna-family --strategy ia3 --seed $seed --split random \
    --device $GPU --epochs 10 --batch-size 8 >> $LOG 2>&1
  echo "--- exit $? $(date +%T) ---" >> $LOG
done
echo "MOD RINALMO + IA3 RERUN GPU$GPU DONE $(date)" >> $LOG
