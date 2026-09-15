#!/bin/bash
# G5: RiNALMo SSP full s29/s43 x random/family (整卡, E1 full 列收尾)
R=/mnt/cunyuliu/rna-ft-eval
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/home/cunyuliu/llr_env/bin/python
GPU=$1
LOG=$R/logs/q_ssp_rinalmo_full_seeds_g$GPU.log
cd /home/cunyuliu/rna-ft-eval
for seed in 29 43; do
  for split in random family; do
    echo "=== ssp RiNALMo full s$seed $split GPU$GPU $(date +%T) ===" >> $LOG
    timeout 21600 $PY -m rnafteval.finetune_ssp --model RiNALMo-micro \
      --strategy full --seed $seed --split $split \
      --device $GPU --epochs 3 --n-train 3000 --n-test 500 --batch-size 4 >> $LOG 2>&1
  done
done
echo "SSP RINALMO FULL SEEDS GPU$GPU DONE $(date)" >> $LOG
