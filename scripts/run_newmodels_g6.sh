#!/bin/bash
# 新模型首探 (GPU6 MIG 4.75G): frozen/lora x s17 random; 不排 full (MIG 显存)
R=/mnt/cunyuliu/rna-ft-eval
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/home/cunyuliu/llr_env/bin/python
LOG=$R/logs/q_newmodels2_g6.log
cd /home/cunyuliu/rna-ft-eval
for job in "ERNIE-RNA frozen" "ERNIE-RNA lora" "RNA-FM frozen" "RNA-FM lora" "SpliceBERT frozen" "SpliceBERT lora"; do
  set -- $job; model=$1; strat=$2
  echo "=== $model $strat s17 random GPU6 $(date +%T) ===" >> $LOG
  timeout 14400 $PY -m rnafteval.finetune_one --model $model \
    --task noncoding-rna-family --strategy $strat --seed 17 --split random \
    --device 6 --epochs 10 --batch-size 8 >> $LOG 2>&1
done
echo "NEWMODELS2 DONE $(date)" >> $LOG
