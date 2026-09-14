#!/bin/bash
# modification 补跑队列 (GPU2): full 3 种子 + frozen/headonly 29/43
R=/mnt/cunyuliu/rna-ft-eval
export HF_ENDPOINT=https://hf-mirror.com HF_HOME=/mnt/cunyuliu/hf_home
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/home/cunyuliu/llr_env/bin/python
cd /home/cunyuliu/rna-ft-eval
for job in "full 17" "full 29" "full 43" "frozen 29" "frozen 43" "head-only 17" "head-only 29" "head-only 43"; do
  set -- $job
  strat=$1; seed=$2
  echo "=== modification $strat s$seed GPU2 $(date +%T) ===" >> $R/logs/q_mod2.log
  timeout 14400 $PY -m rnafteval.finetune_base --model RNA-Sc-10M \
    --task modification --strategy $strat --seed $seed --split random \
    --device 2 --epochs 3 --n-train 20000 --batch-size 32 >> $R/logs/q_mod2.log 2>&1
done
echo "MOD2 QUEUE DONE $(date)" >> $R/logs/q_mod2.log
