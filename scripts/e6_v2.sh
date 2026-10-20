#!/bin/bash
# E6 v2 rerun: 15 remaining cells (ERNIE lora/full x3, RNA-FM lora/full x3, NB full x3)
# Waits for all 4 parallel lanes to complete, then runs EXCLUSIVELY (no OOM contention).
set -x
cd /home/cunyuliu/rna-ft-eval
export PYTHONPATH=/root/rnaft/pypath:/home/cunyuliu/rna-ft-eval:/home/cunyuliu/rna-sc
export HF_HOME=/root/hf_home
export HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/root/miniconda3/envs/llr_env/bin/python
LOG=/root/rnaft/logs/e6_v2.log
echo "=== e6 v2 wait start $(date -u +%FT%TZ) ===" > $LOG

# wait for all four lanes to finish
while true; do
  b=$(grep -c 'ALL DONE' /root/rnaft/logs/q_biglane.log 2>/dev/null || echo 0)
  m=$(grep -c 'ALL DONE' /root/rnaft/logs/q_megalane.log 2>/dev/null || echo 0)
  o=$(grep -c 'ALL DONE' /root/rnaft/logs/q_officiallane.log 2>/dev/null || echo 0)
  f=$(grep -c 'ALL DONE' /root/rnaft/logs/q_fulllane.log 2>/dev/null || echo 0)
  if [ "$b" -ge 1 ] && [ "$m" -ge 1 ] && [ "$o" -ge 1 ] && [ "$f" -ge 1 ]; then
    break
  fi
  sleep 600
done
echo "all lanes done - starting E6 v2 exclusive $(date -u +%FT%TZ)" >> $LOG

run() {
  model=$1; strat=$2; seed=$3; lr=$4; bs=$5
  echo "=== $(date -u +%FT%TZ) e6v2 $model $strat s$seed lr=$lr bs=$bs ===" >> $LOG
  timeout 14400 $PY -m rnafteval.e6_forget --model $model --strategy $strat --seed $seed --lr $lr --device 0 --epochs 10 --batch-size $bs >> $LOG 2>&1
  echo "RC=$? $(date -u +%FT%TZ)" >> $LOG
}

# ERNIE-RNA: lora@3e-4 bs32; full@1e-5 bs32
for s in 17 29 43; do run ERNIE-RNA lora $s 3e-4 32; done
for s in 17 29 43; do run ERNIE-RNA full $s 1e-5 32; done
# RNA-FM: lora@3e-4 bs32; full@1e-5 bs32
for s in 17 29 43; do run RNA-FM lora $s 3e-4 32; done
for s in 17 29 43; do run RNA-FM full $s 1e-5 32; done
# NucleicBERT full only (lora already done)
for s in 17 29 43; do run NucleicBERT full $s 1e-5 8; done
echo "ALL_E6_V2_DONE $(date -u +%FT%TZ)" >> $LOG
