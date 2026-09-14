#!/bin/bash
# per-base modification 任务队列 (GPU1)
R=/mnt/cunyuliu/rna-ft-eval
export HF_ENDPOINT=https://hf-mirror.com HF_HOME=/mnt/cunyuliu/hf_home
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/home/cunyuliu/llr_env/bin/python
cd /home/cunyuliu/rna-ft-eval
for strat in frozen head-only lora full; do
  for seed in 17 29 43; do
    echo "=== modification $strat s$seed $(date +%T) ===" >> $R/logs/q_mod.log
    timeout 14400 $PY -m rnafteval.finetune_base --model RNA-Sc-10M \
      --task modification --strategy $strat --seed $seed --split random \
      --device 1 --epochs 3 --n-train 20000 --batch-size 64 >> $R/logs/q_mod.log 2>&1
  done
done
echo "MOD QUEUE DONE $(date)" >> $R/logs/q_mod.log
