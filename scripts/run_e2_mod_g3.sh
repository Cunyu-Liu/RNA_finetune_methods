#!/bin/bash
# GPU3 整卡 (free ~16G): E2 第二任务维度 — RiNALMo m6A DoRA/IA3
# spec v1.4 E2 = 2 任务: ncRNA(per-seq) + m6A(per-base 粒度对照)
# 6 runs: {dora,ia3} × s{17,29,43} × random
# 口径 = 正式 m6A runs（epochs 3 / n-train 20000 / bs 32 / 默认 LR）
R=/mnt/cunyuliu/rna-ft-eval
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/home/cunyuliu/llr_env/bin/python
LOG=$R/logs/q_e2_mod_g3.log
cd /home/cunyuliu/rna-ft-eval
GPU=3

$PY -c "import torch; assert torch.cuda.is_available()" || exit 2
timeout 300 $PY -c "
import torch
free, _ = torch.cuda.mem_get_info($GPU)
assert free > 4e9, 'GPU$GPU free %.2fG < 4G' % (free/1e9)
print('GPU$GPU free %.2fG OK' % (free/1e9))" >> $LOG 2>&1 || exit 2

for strat in dora ia3; do
  for seed in 17 29 43; do
    echo "=== E2-MOD RiNALMo $strat s$seed random GPU$GPU $(date +%T) ===" >> $LOG
    timeout 21600 $PY -m rnafteval.finetune_base --model RiNALMo-micro \
      --task modification --strategy $strat --seed $seed --split random \
      --device $GPU --epochs 3 --n-train 20000 --batch-size 32 >> $LOG 2>&1
    echo "--- exit $? $(date +%T) ---" >> $LOG
  done
done
echo "E2 MOD (RiNALMo dora/ia3) GPU$GPU DONE $(date)" >> $LOG
