#!/bin/bash
set -x
cd /home/cunyuliu/rna-ft-eval
export PYTHONPATH=/root/rnaft/pypath:/home/cunyuliu/rna-ft-eval:/home/cunyuliu/rna-sc
export HF_HOME=/root/hf_home
export HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/root/miniconda3/envs/llr_env/bin/python
LOG=/root/rnaft/logs/q_crisprfill.log
echo "=== q_crisprfill start $(date -u +%FT%TZ) ===" >> $LOG
run_cell() {
  desc=$1; shift
  echo "=== $(date -u +%FT%TZ) $desc ===" >> $LOG
  timeout 14400 "$@" >> $LOG 2>&1
  echo "RC=$? $(date -u +%FT%TZ)" >> $LOG
}
# frozen for 6 models
for M in ERNIE-RNA RNA-FM NucleicBERT RNA-Sc-300M RiNALMo-mega RiNALMo-650M; do
  for sp in random family; do
    for s in 17 29 43; do
      run_cell "crispr $M frozen $sp s$s" $PY -m rnafteval.finetune_clf --model $M --task crispr-off-target --strategy frozen --seed $s --split $sp --device 0 --epochs 10 --batch-size 8 --lr 3e-4
    done
  done
done
# full for 4 small models
for M in ERNIE-RNA RNA-FM NucleicBERT RNA-Sc-300M; do
  for sp in random family; do
    for s in 17 29 43; do
      run_cell "crispr $M full $sp s$s" $PY -m rnafteval.finetune_clf --model $M --task crispr-off-target --strategy full --seed $s --split $sp --device 0 --epochs 10 --batch-size 8 --lr 1e-5
    done
  done
done
echo "=== q_crisprfill DONE $(date -u +%FT%TZ) ===" >> $LOG
