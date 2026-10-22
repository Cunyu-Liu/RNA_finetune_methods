#!/bin/bash
# q_crisprfam: crispr-off-target family-split lane — 27 cells (all pending in ledger).
# Models × strategy × seeds 17/29/43, family split. Runs alongside spliceai lanes.
set -x
cd /home/cunyuliu/rna-ft-eval
export PYTHONPATH=/root/rnaft/pypath:/home/cunyuliu/rna-ft-eval:/home/cunyuliu/rna-sc
export HF_HOME=/root/hf_home
export HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/root/miniconda3/envs/llr_env/bin/python
LOG=/root/rnaft/logs/q_crisprfam.log
mkdir -p /root/rnaft/logs
echo "=== q_crisprfam start $(date -u +%FT%TZ) ===" >> $LOG

run_cell() {
  desc=$1; shift
  echo "=== $(date -u +%FT%TZ) $desc ===" >> $LOG
  timeout 14400 "$@" >> $LOG 2>&1
  echo "RC=$? $(date -u +%FT%TZ)" >> $LOG
}

# micro (fastest first): frozen / full / lora
for s in 17 29 43; do
  run_cell "crispr micro frozen family s$s" $PY -m rnafteval.finetune_clf --model RiNALMo-micro --task crispr-off-target --strategy frozen --seed $s --split family --device 0 --epochs 10 --batch-size 32 --lr 1e-3
done
for s in 17 29 43; do
  run_cell "crispr micro full family s$s" $PY -m rnafteval.finetune_clf --model RiNALMo-micro --task crispr-off-target --strategy full --seed $s --split family --device 0 --epochs 10 --batch-size 32 --lr 1e-5
done
for s in 17 29 43; do
  run_cell "crispr micro lora family s$s" $PY -m rnafteval.finetune_clf --model RiNALMo-micro --task crispr-off-target --strategy lora --seed $s --split family --device 0 --epochs 10 --batch-size 32 --lr 3e-4
done
# ERNIE / RNA-FM lora
for s in 17 29 43; do
  run_cell "crispr ERNIE lora family s$s" $PY -m rnafteval.finetune_clf --model ERNIE-RNA --task crispr-off-target --strategy lora --seed $s --split family --device 0 --epochs 10 --batch-size 32 --lr 3e-4
done
for s in 17 29 43; do
  run_cell "crispr RNAFM lora family s$s" $PY -m rnafteval.finetune_clf --model RNA-FM --task crispr-off-target --strategy lora --seed $s --split family --device 0 --epochs 10 --batch-size 32 --lr 3e-4
done
# 650M lora / full
for s in 17 29 43; do
  run_cell "crispr 650M lora family s$s" $PY -m rnafteval.finetune_clf --model RiNALMo-650M --task crispr-off-target --strategy lora --seed $s --split family --device 0 --epochs 10 --batch-size 16 --lr 3e-4
done
for s in 17 29 43; do
  run_cell "crispr 650M full family s$s" $PY -m rnafteval.finetune_clf --model RiNALMo-650M --task crispr-off-target --strategy full --seed $s --split family --device 0 --epochs 10 --batch-size 16 --lr 1e-5
done
# mega lora / full (bs8)
for s in 17 29 43; do
  run_cell "crispr mega lora family s$s" $PY -m rnafteval.finetune_clf --model RiNALMo-mega --task crispr-off-target --strategy lora --seed $s --split family --device 0 --epochs 10 --batch-size 8 --lr 3e-4
done
for s in 17 29 43; do
  run_cell "crispr mega full family s$s" $PY -m rnafteval.finetune_clf --model RiNALMo-mega --task crispr-off-target --strategy full --seed $s --split family --device 0 --epochs 10 --batch-size 8 --lr 1e-5
done
echo "=== q_crisprfam DONE $(date -u +%FT%TZ) ===" >> $LOG
