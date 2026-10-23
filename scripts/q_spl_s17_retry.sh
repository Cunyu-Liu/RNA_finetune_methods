#!/bin/bash
# q_spl_s17_retry: re-run spliceai 650M/mega lora s17 cells killed by 4h timeout (RC=124)
# 10h budget each. Sequential to limit memory pressure.
set -x
cd /home/cunyuliu/rna-ft-eval
export PYTHONPATH=/root/rnaft/pypath:/home/cunyuliu/rna-ft-eval:/home/cunyuliu/rna-sc
export HF_HOME=/root/hf_home
export HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/root/miniconda3/envs/llr_env/bin/python
LOG=/root/rnaft/logs/q_spl_s17_retry.log
echo "=== q_spl_s17_retry start $(date -u +%FT%TZ) ===" >> $LOG
run_cell() {
  desc=$1; shift
  echo "=== $(date -u +%FT%TZ) $desc ===" >> $LOG
  timeout 36000 "$@" >> $LOG 2>&1
  echo "RC=$? $(date -u +%FT%TZ)" >> $LOG
}
# mega first (in-flight s29 will finish on its own lane; these are s17 only)
run_cell "spl mega lora random s17 (10h)" $PY -m rnafteval.finetune_spl --model RiNALMo-mega --task spliceai --strategy lora --seed 17 --split random --device 0 --epochs 6 --batch-size 16 --lr 3e-4
run_cell "spl 650M lora random s17 (10h)" $PY -m rnafteval.finetune_spl --model RiNALMo-650M --task spliceai --strategy lora --seed 17 --split random --device 0 --epochs 6 --batch-size 16 --lr 3e-4
run_cell "spl mega lora family s17 (10h)" $PY -m rnafteval.finetune_spl --model RiNALMo-mega --task spliceai --strategy lora --seed 17 --split family --device 0 --epochs 6 --batch-size 16 --lr 3e-4
run_cell "spl 650M lora family s17 (10h)" $PY -m rnafteval.finetune_spl --model RiNALMo-650M --task spliceai --strategy lora --seed 17 --split family --device 0 --epochs 6 --batch-size 16 --lr 3e-4
echo "=== q_spl_s17_retry DONE $(date -u +%FT%TZ) ===" >> $LOG
