#!/bin/bash
# SSP wave2 (patrol 2026-09-15 08:20): 重启被 SIGHUP 杀死的 lora s17 random /
# frozen s17 family，并补齐 s17 策略行。nohup+setsid 防 SIGHUP 复发。
R=/mnt/cunyuliu/rna-ft-eval
export HF_ENDPOINT=https://hf-mirror.com HF_HOME=/mnt/cunyuliu/hf_home
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/home/cunyuliu/llr_env/bin/python
cd /home/cunyuliu/rna-ft-eval
run_ssp () {
  strat=$1; seed=$2; split=$3; dev=$4
  echo "=== ssp $strat s$seed $split GPU$dev start $(date +%T) ===" >> $R/logs/ssp_wave2.log
  timeout 14400 $PY -m rnafteval.finetune_ssp --model RNA-Sc-10M \
    --strategy $strat --seed $seed --split $split --device $dev --epochs 3 \
    >> $R/logs/ssp_wave2.log 2>&1
  echo "--- ssp $strat s$seed $split exit $? $(date +%T) ---" >> $R/logs/ssp_wave2.log
}
if [ "$1" = g6 ]; then
  run_ssp frozen 17 family 6
  run_ssp head-only 17 family 6
elif [ "$1" = g7 ]; then
  run_ssp lora 17 random 7
  run_ssp full 17 random 7
fi
echo "SSP_WAVE2_$1 DONE $(date)" >> $R/logs/ssp_wave2.log
