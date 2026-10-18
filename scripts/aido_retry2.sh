#!/bin/bash
# AIDO 1.6B mrl full OOM retry v2: bs 2->1, CORRECT module finetune_mrl (v1 bug: used finetune_base
# which is modification-only -> trained on wrong data; killed after 75min, ledger cleaned)
set -x
cd /home/cunyuliu/rna-ft-eval
export PYTHONPATH=/root/rnaft/pypath:/home/cunyuliu/rna-ft-eval:/home/cunyuliu/rna-sc
export HF_HOME=/root/hf_home
export HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/root/miniconda3/envs/llr_env/bin/python
LOG=/root/rnaft/logs/aido_retry.log
echo "=== aido mrl full bs1 retry v2 (finetune_mrl) $(date -u +%FT%TZ) ===" > $LOG

timeout 14400 $PY -m rnafteval.finetune_mrl --model AIDO.RNA-1.6B --task mrl --strategy full --seed 43 --split random --device 0 --epochs 10 --batch-size 1 --lr 1e-05 >> $LOG 2>&1
echo "AIDO_RETRY_RC=$?" >> $LOG
echo "=== aido retry done $(date -u +%FT%TZ) ===" >> $LOG
