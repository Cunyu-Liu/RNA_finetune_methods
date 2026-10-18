#!/bin/bash
# Stage 4th in chain: AIDO mrl full s43 retry with extended timeout (12h) after E6 official done
set -x
cd /home/cunyuliu/rna-ft-eval
export PYTHONPATH=/root/rnaft/pypath:/home/cunyuliu/rna-ft-eval:/home/cunyuliu/rna-sc
export HF_HOME=/root/hf_home
export HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/root/miniconda3/envs/llr_env/bin/python
LOG=/root/rnaft/logs/aido_retry3.log
echo "=== aido mrl full bs1 retry v3 (12h timeout) $(date -u +%FT%TZ) ===" > $LOG

while ! grep -q 'ALL_E6_OFFICIAL_DONE' /root/rnaft/logs/e6_official_5090.log 2>/dev/null; do sleep 600; done
echo "E6 done, starting aido v3 $(date -u +%FT%TZ)" >> $LOG

timeout 43200 $PY -m rnafteval.finetune_mrl --model AIDO.RNA-1.6B --task mrl --strategy full --seed 43 --split random --device 0 --epochs 10 --batch-size 1 --lr 1e-05 >> $LOG 2>&1
echo "AIDO_RETRY3_RC=$?" >> $LOG
echo "=== aido retry v3 done $(date -u +%FT%TZ) ===" >> $LOG
