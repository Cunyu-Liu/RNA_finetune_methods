#!/bin/bash
# SSP wave3: leak-fixed runner (independent VL0/cluster-val calibration).
# Usage: run_ssp_wave3.sh <gpu>  — per-GPU sequential queue, setsid-detached
R=/mnt/cunyuliu/rna-ft-eval
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home
export HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/home/cunyuliu/llr_env/bin/python
GPU=$1
LOG=$R/logs/ssp_wave3_g$GPU.log
cd /home/cunyuliu/rna-ft-eval

run_one() {
  strat=$1; seed=$2; split=$3
  echo "=== ssp $strat s$seed $split GPU$GPU $(date +%T) ===" >> $LOG
  timeout 21600 $PY -m rnafteval.finetune_ssp --model RNA-Sc-10M \
    --strategy $strat --seed $seed --split $split \
    --device $GPU --epochs 3 --n-train 3000 --n-test 500 \
    --batch-size 4 >> $LOG 2>&1
}

case $GPU in
  5) run_one frozen 17 random; run_one head-only 17 random ;;
  6) run_one lora 17 random; run_one full 17 random ;;
  7) run_one frozen 17 family; run_one head-only 17 family; run_one lora 17 family; run_one full 17 family ;;
esac
echo "SSP WAVE3 GPU$GPU DONE $(date)" >> $LOG
