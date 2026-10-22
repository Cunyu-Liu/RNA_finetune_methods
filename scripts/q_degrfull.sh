#!/bin/bash
# q_degrfull: degradation (regbase) full lane — ERNIE / RNA-FM / NB full, 18 cells.
set -x
cd /home/cunyuliu/rna-ft-eval
export PYTHONPATH=/root/rnaft/pypath:/home/cunyuliu/rna-ft-eval:/home/cunyuliu/rna-sc
export HF_HOME=/root/hf_home
export HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/root/miniconda3/envs/llr_env/bin/python
LOG=/root/rnaft/logs/q_degrfull.log
mkdir -p /root/rnaft/logs
echo "=== q_degrfull start $(date -u +%FT%TZ) ===" >> $LOG

run_cell() {
  desc=$1; shift
  echo "=== $(date -u +%FT%TZ) $desc ===" >> $LOG
  timeout 14400 "$@" >> $LOG 2>&1
  echo "RC=$? $(date -u +%FT%TZ)" >> $LOG
}

for M in ERNIE-RNA RNA-FM; do
  for sp in random family; do
    for s in 17 29 43; do
      run_cell "degr $M full $sp s$s" $PY -m rnafteval.finetune_regbase --model $M --task degradation --strategy full --seed $s --split $sp --device 0 --epochs 10 --batch-size 16 --lr 1e-5
    done
  done
done
for sp in random family; do
  for s in 17 29 43; do
    run_cell "degr NB full $sp s$s" $PY -m rnafteval.finetune_regbase --model NucleicBERT --task degradation --strategy full --seed $s --split $sp --device 0 --epochs 10 --batch-size 8 --lr 1e-5
  done
done
echo "=== q_degrfull DONE $(date -u +%FT%TZ) ===" >> $LOG
