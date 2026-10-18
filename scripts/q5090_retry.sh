#!/bin/bash
# rerun the accelerate-failed cell: mega lora s43 family e3-3000 (will be picked up after current queue
# or run now in parallel? Single GPU — queue it as a follow-up script chained after q5090 finishes)
set -x
cd /home/cunyuliu/rna-ft-eval
export PYTHONPATH=/root/rnaft/pypath:/home/cunyuliu/rna-ft-eval:/home/cunyuliu/rna-sc
export HF_HOME=/root/hf_home
export HF_ENDPOINT=https://hf-mirror.com
PY=/root/miniconda3/envs/llr_env/bin/python
LOG=/root/rnaft/logs/q5090.log
# wait for q5090 to finish (marker) then rerun the failed cell
while ! grep -q "q5090 ALL DONE" $LOG 2>/dev/null; do sleep 300; done
echo "--- RETRY mega lora s43 family e3-3000 (accelerate was missing) $(date -u +%FT%TZ) ---" >> $LOG
timeout 21600 $PY -m rnafteval.finetune_one --model RiNALMo-mega --task noncoding-rna-family --strategy lora --seed 43 --split family --device 0 --lr 3e-4 --n-train 3000 --batch-size 16 --epochs 10 >> $LOG 2>&1
echo "RETRY_RC=$? $(date -u +%FT%TZ)" >> $LOG
