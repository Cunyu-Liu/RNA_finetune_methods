#!/bin/bash
# ERNIE lora 重跑 GPU5 (整卡, 显式 attn 矩阵需整卡显存; bs=4 保守)
R=/mnt/cunyuliu/rna-ft-eval
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/home/cunyuliu/llr_env/bin/python
LOG=$R/logs/q_ernie_lora_g5.log
cd /home/cunyuliu/rna-ft-eval
echo "=== ERNIE-RNA lora s17 random GPU5 bs=4 $(date +%T) ===" >> $LOG
timeout 14400 $PY -m rnafteval.finetune_one --model ERNIE-RNA \
  --task noncoding-rna-family --strategy lora --seed 17 --split random \
  --device 5 --epochs 10 --batch-size 4 --max-len 256 >> $LOG 2>&1
echo "ERNIE LORA DONE $(date)" >> $LOG
