#!/bin/bash
# AIDO v4: mrl full s43 — final chain position (after e6_v2)
set -x
cd /home/cunyuliu/rna-ft-eval
export PYTHONPATH=/root/rnaft/pypath:/home/cunyuliu/rna-ft-eval:/home/cunyuliu/rna-sc
export HF_HOME=/root/hf_home
export HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/root/miniconda3/envs/llr_env/bin/python
LOG=/root/rnaft/logs/aido_retry4.log
echo "=== aido v4 wait start $(date -u +%FT%TZ) ===" > $LOG

while ! grep -q 'ALL_E6_V2_DONE' /root/rnaft/logs/e6_v2.log 2>/dev/null; do sleep 600; done
echo "E6 v2 done, starting aido v4 $(date -u +%FT%TZ)" >> $LOG

timeout 43200 $PY -m rnafteval.finetune_mrl --model AIDO.RNA-1.6B --task mrl --strategy full --seed 43 --split random --device 0 --epochs 10 --batch-size 1 --lr 1e-05 >> $LOG 2>&1
echo "AIDO_RETRY4_RC=$?" >> $LOG
echo "=== aido v4 done $(date -u +%FT%TZ) ===" >> $LOG
