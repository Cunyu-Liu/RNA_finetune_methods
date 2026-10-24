#!/bin/bash
set -x
cd /home/cunyuliu/rna-ft-eval
export PYTHONPATH=/root/rnaft/pypath:/home/cunyuliu/rna-ft-eval:/home/cunyuliu/rna-sc
export HF_HOME=/root/hf_home
export HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/root/miniconda3/envs/llr_env/bin/python
LOG=/root/rnaft/logs/q_splfill4.log
echo "=== q_splfill4 start $(date -u +%FT%TZ) ===" >> $LOG
run_cell() {
  desc=$1; shift
  echo "=== $(date -u +%FT%TZ) $desc ===" >> $LOG
  timeout 21600 "$@" >> $LOG 2>&1
  echo "RC=$? $(date -u +%FT%TZ)" >> $LOG
}
for s in 17 29; do
  run_cell "spl micro lora random s$s" $PY -m rnafteval.finetune_spl --model RiNALMo-micro --task spliceai --strategy lora --seed $s --split random --device 0 --epochs 6 --batch-size 16 --lr 3e-4
done
for s in 17 29; do
  run_cell "spl ERNIE full random s$s" $PY -m rnafteval.finetune_spl --model ERNIE-RNA --task spliceai --strategy full --seed $s --split random --device 0 --epochs 6 --batch-size 16 --lr 1e-5
done
for sp in random family; do
  for s in 17 29 43; do
    run_cell "spl Sc-300M lora $sp s$s" $PY -m rnafteval.finetune_spl --model RNA-Sc-300M --task spliceai --strategy lora --seed $s --split $sp --device 0 --epochs 6 --batch-size 16 --lr 3e-4
  done
done
echo "=== q_splfill4 DONE $(date -u +%FT%TZ) ===" >> $LOG
