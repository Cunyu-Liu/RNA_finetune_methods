#!/bin/bash
# crispr lr ablation for 650M collapse diagnosis + spliceai timeout reruns
# runs after all lanes + e6_v2 complete (exclusive window)
set -x
cd /home/cunyuliu/rna-ft-eval
export PYTHONPATH=/root/rnaft/pypath:/home/cunyuliu/rna-ft-eval:/home/cunyuliu/rna-sc
export HF_HOME=/root/hf_home
export HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/root/miniconda3/envs/llr_env/bin/python
LOG=/root/rnaft/logs/q_diag.log
echo "=== q_diag wait start $(date -u +%FT%TZ) ===" > $LOG

while ! grep -q 'ALL_E6_V2_DONE' /root/rnaft/logs/e6_v2.log 2>/dev/null; do sleep 600; done
echo "E6 v2 done, starting diag $(date -u +%FT%TZ)" >> $LOG

# 1. 650M crispr lora lr=1e-4 (collapse diagnosis: default 3e-4 too aggressive)
for s in 17 29 43; do
  echo "--- $(date -u +%FT%TZ) RiNALMo-650M crispr lora s$s lr1e-4 ---" >> $LOG
  timeout 7200 $PY -m rnafteval.finetune_clf --model RiNALMo-650M --task crispr-off-target --strategy lora --seed $s --split random --device 0 --epochs 10 --batch-size 16 --lr 1e-4 >> $LOG 2>&1
  echo "RC=$?" >> $LOG
done

# 2. spliceai timeout reruns: 24h timeout for family big cells (650M/mega/ERNIE full set)
for SPEC in "RiNALMo-650M:lora" "RiNALMo-mega:lora" "RiNALMo-mega:full" "ERNIE-RNA:lora"; do
  M="${SPEC%%:*}"; ST="${SPEC##*:}"
  BS=16; [ "$ST" = "full" ] && BS=8
  LR=""; [ "$ST" = "full" ] && LR="1e-05"
  echo "--- $(date -u +%FT%TZ) spliceai rerun $M $ST family ---" >> $LOG
  for s in 17 29 43; do
    timeout 28800 $PY -m rnafteval.finetune_spl --model $M --task spliceai --strategy $ST --seed $s --split family --device 0 --epochs 10 --batch-size $BS ${LR:+--lr $LR} >> $LOG 2>&1
    echo "RC=$?" >> $LOG
  done
done
echo "=== q_diag ALL DONE $(date -u +%FT%TZ) ===" >> $LOG
