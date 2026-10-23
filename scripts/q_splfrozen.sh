#!/bin/bash
# q_splfrozen: spliceai micro/ERNIE frozen cells (cheap, fills GPU while big lanes run)
set -x
cd /home/cunyuliu/rna-ft-eval
export PYTHONPATH=/root/rnaft/pypath:/home/cunyuliu/rna-ft-eval:/home/cunyuliu/rna-sc
export HF_HOME=/root/hf_home
export HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/root/miniconda3/envs/llr_env/bin/python
LOG=/root/rnaft/logs/q_splfrozen.log
echo "=== q_splfrozen start $(date -u +%FT%TZ) ===" >> $LOG
run_cell() {
  desc=$1; shift
  echo "=== $(date -u +%FT%TZ) $desc ===" >> $LOG
  timeout 14400 "$@" >> $LOG 2>&1
  echo "RC=$? $(date -u +%FT%TZ)" >> $LOG
}
for sp in random family; do
  for s in 17 29 43; do
    run_cell "spl micro frozen $sp s$s" $PY -m rnafteval.finetune_spl --model RiNALMo-micro --task spliceai --strategy frozen --seed $s --split $sp --device 0 --epochs 6 --batch-size 16 --lr 3e-4
  done
done
for sp in random family; do
  for s in 17 29 43; do
    run_cell "spl ERNIE frozen $sp s$s" $PY -m rnafteval.finetune_spl --model ERNIE-RNA --task spliceai --strategy frozen --seed $s --split $sp --device 0 --epochs 6 --batch-size 16 --lr 3e-4
  done
done
echo "=== q_splfrozen DONE $(date -u +%FT%TZ) ===" >> $LOG
