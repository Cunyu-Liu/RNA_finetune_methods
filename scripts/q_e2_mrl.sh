#!/bin/bash
# E2-MRL 面板: RiNALMo/RNA-Sc MRL x {dora,ia3} x random x 3 seeds = 12 runs
R=/mnt/cunyuliu/rna-ft-eval
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/home/cunyuliu/llr_env/bin/python
GPU=$1
LOG=$R/logs/q_e2_mrl_g${GPU}.log
cd /home/cunyuliu/rna-ft-eval

$PY -c "import torch; assert torch.cuda.is_available()" || exit 2
timeout 300 $PY -c "
import torch
free, _ = torch.cuda.mem_get_info($GPU)
assert free > 4e9, "free %.2fG" % (free/1e9)
print("GPU$GPU OK")" >> $LOG 2>&1 || exit 2

for M in RiNALMo-micro RNA-Sc-10M; do
  for strat in dora ia3; do
    for seed in 17 29 43; do
      echo "=== E2-MRL $M $strat s$seed random GPU$GPU $(date +%T) ===" >> $LOG
      timeout 7200 $PY -m rnafteval.finetune_mrl --model $M \
        --strategy $strat --seed $seed --split random \
        --device $GPU --epochs 3 --n-train 20000 --batch-size 32 >> $LOG 2>&1
      echo "--- exit $? $(date +%T) ---" >> $LOG
    done
  done
done
echo "E2-MRL DONE $(date)" >> $LOG
