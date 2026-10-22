#!/bin/bash
# q_splfull3: spliceai full-finetune lane — ERNIE / RNA-FM (12 cells, uncovered).
set -x
cd /home/cunyuliu/rna-ft-eval
export PYTHONPATH=/root/rnaft/pypath:/home/cunyuliu/rna-ft-eval:/home/cunyuliu/rna-sc
export HF_HOME=/root/hf_home
export HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/root/miniconda3/envs/llr_env/bin/python
LOG=/root/rnaft/logs/q_splfull3.log
mkdir -p /root/rnaft/logs
echo "=== q_splfull3 start $(date -u +%FT%TZ) ===" >> $LOG

run_cell() {
  desc=$1; shift
  echo "=== $(date -u +%FT%TZ) $desc ===" >> $LOG
  timeout 14400 "$@" >> $LOG 2>&1
  echo "RC=$? $(date -u +%FT%TZ)" >> $LOG
}

for sp in random family; do
  for s in 17 29 43; do
    run_cell "spl ERNIE full $sp s$s" $PY -m rnafteval.finetune_spl --model ERNIE-RNA --task spliceai --strategy full --seed $s --split $sp --device 0 --epochs 6 --batch-size 16 --lr 1e-5
  done
done
for sp in random family; do
  for s in 17 29 43; do
    run_cell "spl RNAFM full $sp s$s" $PY -m rnafteval.finetune_spl --model RNA-FM --task spliceai --strategy full --seed $s --split $sp --device 0 --epochs 6 --batch-size 16 --lr 1e-5
  done
done
echo "=== q_splfull3 DONE $(date -u +%FT%TZ) ===" >> $LOG
