#!/bin/bash
# G7 排空后: ① RNA-Sc SSP full s29 random (E1 随机列最后一格)
# ② RiNALMo SSP frozen/lora x s29/s43 x random/family (8 runs, MIG-safe)
R=/mnt/cunyuliu/rna-ft-eval
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/home/cunyuliu/llr_env/bin/python
GPU=$1
LOG=$R/logs/q_ssp_fill_g${GPU}.log
cd /home/cunyuliu/rna-ft-eval
echo "=== ssp RNA-Sc full s29 random GPU$GPU $(date +%T) ===" >> $LOG
timeout 21600 $PY -m rnafteval.finetune_ssp --model RNA-Sc-10M \
  --strategy full --seed 29 --split random \
  --device $GPU --epochs 3 --n-train 3000 --n-test 500 --batch-size 4 >> $LOG 2>&1
for seed in 29 43; do
  for split in random family; do
    for strat in frozen lora; do
      echo "=== ssp RiNALMo $strat s$seed $split GPU$GPU $(date +%T) ===" >> $LOG
      timeout 21600 $PY -m rnafteval.finetune_ssp --model RiNALMo-micro \
        --strategy $strat --seed $seed --split $split \
        --device $GPU --epochs 3 --n-train 3000 --n-test 500 --batch-size 4 >> $LOG 2>&1
    done
  done
done
echo "SSP FILL GPU$GPU DONE $(date)" >> $LOG
