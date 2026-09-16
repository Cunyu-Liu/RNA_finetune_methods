#!/bin/bash
# E3 小数据首轴 (GPU7 MIG): RiNALMo ncRNA family × {10,100,1000,full}
# × {frozen,lora,full} × 3 种子 = 36 runs (1 已冒烟)
# C3 预览: 标注量-策略翻转点。簇级子集 (e3_subsampler, T3.1.1)。
# full 档 = 全量 train (6859); 小档 LR 与全量矩阵一致 (协议不变量)
R=/mnt/cunyuliu/rna-ft-eval
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/home/cunyuliu/llr_env/bin/python
LOG=$R/logs/q_e3_axis_g7.log
cd /home/cunyuliu/rna-ft-eval
GPU=7

$PY -c "import torch; assert torch.cuda.is_available(), 'CUDA UNAVAILABLE'" || exit 2
timeout 300 $PY -c "
import torch
free, total = torch.cuda.mem_get_info($GPU)
assert free > 2e9, 'GPU$GPU free %.2fG < 2G' % (free/1e9)
print('GPU$GPU free %.2fG OK' % (free/1e9))" >> $LOG 2>&1 || exit 2

for n in 10 100 1000 0; do
  for strat in frozen lora full; do
    for seed in 17 29 43; do
      echo "=== E3 n=$n $strat s$seed GPU$GPU $(date +%T) ===" >> $LOG
      timeout 14400 $PY -m rnafteval.finetune_one --model RiNALMo-micro \
        --task noncoding-rna-family --strategy $strat --seed $seed \
        --split family --device $GPU --epochs 10 --batch-size 8 \
        --n-train $n >> $LOG 2>&1
      echo "--- exit $? $(date +%T) ---" >> $LOG
    done
  done
done
echo "E3 AXIS GPU$GPU DONE $(date)" >> $LOG
