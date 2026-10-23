#!/bin/bash
set -x
cd /home/cunyuliu/rna-ft-eval
export PYTHONPATH=/root/rnaft/pypath:/home/cunyuliu/rna-ft-eval:/home/cunyuliu/rna-sc
export HF_HOME=/root/hf_home
export HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/root/miniconda3/envs/llr_env/bin/python
LOG=/root/rnaft/logs/q_spl650.log
echo "=== q_spl650 start $(date -u +%FT%TZ) ===" >> $LOG
run_cell() {
  desc=$1; shift
  echo "=== $(date -u +%FT%TZ) $desc ===" >> $LOG
  timeout 14400 "$@" >> $LOG 2>&1
  echo "RC=$? $(date -u +%FT%TZ)" >> $LOG
}
for s in 17 29 43; do
  run_cell "spl 650M lora random s$s" $PY -m rnafteval.finetune_spl --model RiNALMo-650M --task spliceai --strategy lora --seed $s --split random --device 0 --epochs 6 --batch-size 16 --lr 3e-4
done
for s in 17 29 43; do
  run_cell "spl 650M lora family s$s" $PY -m rnafteval.finetune_spl --model RiNALMo-650M --task spliceai --strategy lora --seed $s --split family --device 0 --epochs 6 --batch-size 16 --lr 3e-4
done
echo "=== q_spl650 DONE $(date -u +%FT%TZ) ===" >> $LOG
