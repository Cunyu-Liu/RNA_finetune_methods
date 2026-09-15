#!/bin/bash
# G5 (整卡 40G): ERNIE-RNA lora s17 family 重跑 (MIG OOM 教训: 显式 attn 矩阵需整卡)
#   + RiNALMo-micro modification full x 3 seeds x 2 splits (E1 缺口, full 需整卡)
GPU=${1:-5}
R=/mnt/cunyuliu/rna-ft-eval
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/home/cunyuliu/llr_env/bin/python
LOG=$R/logs/q_ernmod_g$GPU.log
cd /home/cunyuliu/rna-ft-eval

$PY -c "import torch; assert torch.cuda.is_available(), 'CUDA UNAVAILABLE'" || exit 2

echo "=== ERNIE-RNA lora s17 family GPU$GPU bs=8 $(date +%T) ===" >> $LOG
timeout 14400 $PY -m rnafteval.finetune_one --model ERNIE-RNA \
  --task noncoding-rna-family --strategy lora --seed 17 --split family \
  --device $GPU --epochs 10 --batch-size 8 >> $LOG 2>&1
echo "--- ernie exit $? $(date +%T) ---" >> $LOG

for split in random family; do
  for seed in 17 29 43; do
    echo "=== modification RiNALMo full s$seed $split GPU$GPU $(date +%T) ===" >> $LOG
    timeout 21600 $PY -m rnafteval.finetune_base --model RiNALMo-micro \
      --task modification --strategy full --seed $seed --split $split \
      --device $GPU --epochs 3 --n-train 20000 --batch-size 32 >> $LOG 2>&1
    echo "--- exit $? $(date +%T) ---" >> $LOG
  done
done
echo "ERNIE + MOD FULL GPU$GPU DONE $(date)" >> $LOG
