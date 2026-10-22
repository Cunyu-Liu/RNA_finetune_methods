#!/bin/bash
# q_aidom6a: AIDO.RNA-1.6B modification (m6A) full lane — fills GPU heavily (bs2).
set -x
cd /home/cunyuliu/rna-ft-eval
export PYTHONPATH=/root/rnaft/pypath:/home/cunyuliu/rna-ft-eval:/home/cunyuliu/rna-sc
export HF_HOME=/root/hf_home
export HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/root/miniconda3/envs/llr_env/bin/python
LOG=/root/rnaft/logs/q_aidom6a.log
mkdir -p /root/rnaft/logs
echo "=== q_aidom6a start $(date -u +%FT%TZ) ===" >> $LOG

run_cell() {
  desc=$1; shift
  echo "=== $(date -u +%FT%TZ) $desc ===" >> $LOG
  timeout 28800 "$@" >> $LOG 2>&1
  echo "RC=$? $(date -u +%FT%TZ)" >> $LOG
}

for sp in random family; do
  for s in 17 29 43; do
    run_cell "aido m6a full $sp s$s" $PY -m rnafteval.finetune_base --model AIDO.RNA-1.6B --task modification --strategy full --seed $s --split $sp --device 0 --epochs 6 --batch-size 1 --lr 1e-5
  done
done
echo "=== q_aidom6a DONE $(date -u +%FT%TZ) ===" >> $LOG
