#!/bin/bash
# RNA-Sc full @ tuned LR 3e-5 (from grid2 s101) — formal 3 seeds x 2 splits
R=/mnt/cunyuliu/rna-ft-eval
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/home/cunyuliu/llr_env/bin/python
GPU=$1
LOG=$R/logs/q_rnasc_lrbest.log
cd /home/cunyuliu/rna-ft-eval
for job in "17 random" "29 random" "43 random" "17 family" "29 family" "43 family"; do
  set -- $job; seed=$1; split=$2
  echo "=== RNA-Sc full s$seed $split lr3e-5 GPU$GPU $(date +%T) ===" >> $LOG
  timeout 14400 $PY -m rnafteval.finetune_one --model RNA-Sc-10M \
    --task noncoding-rna-family --strategy full --seed $seed --split $split \
    --device $GPU --lr 3e-5 --epochs 10 --batch-size 16 >> $LOG 2>&1
done
echo "RNASC LRBEST DONE $(date)" >> $LOG
