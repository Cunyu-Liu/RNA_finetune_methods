#!/bin/bash
# GPU5 整卡 (free 13.8G): E3 第二模型轴 — RNA-Sc-10M 受控对照
# C3 翻转点的模型间对照: 与 RiNALMo 首轴同构
#   n ∈ {10,100,1000,full=6859} × {frozen,lora,full} × 3 种子 = 36 runs
# 子集 = e3_subsampler 已生成 (ncrna_<n>_s<seed>.txt 通用不分模型)
# 协议不变量: epochs 10 / bs 8 与首轴一致 (可比性)
R=/mnt/cunyuliu/rna-ft-eval
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/home/cunyuliu/llr_env/bin/python
LOG=$R/logs/q_e3_axis_rnasc_g5.log
cd /home/cunyuliu/rna-ft-eval
GPU=5

$PY -c "import torch; assert torch.cuda.is_available()" || exit 2
timeout 300 $PY -c "
import torch
free, _ = torch.cuda.mem_get_info($GPU)
assert free > 4e9, 'GPU$GPU free %.2fG < 4G' % (free/1e9)
print('GPU$GPU free %.2fG OK' % (free/1e9))" >> $LOG 2>&1 || exit 2

for n in 10 100 1000 0; do
  for strat in frozen lora full; do
    for seed in 17 29 43; do
      echo "=== E3-RNASC n=$n $strat s$seed GPU$GPU $(date +%T) ===" >> $LOG
      timeout 7200 $PY -m rnafteval.finetune_one --model RNA-Sc-10M \
        --task noncoding-rna-family --strategy $strat --seed $seed \
        --split family --device $GPU --epochs 10 --batch-size 8 \
        --n-train $n >> $LOG 2>&1
      echo "--- exit $? $(date +%T) ---" >> $LOG
    done
  done
done
echo "E3 AXIS RNA-SC GPU$GPU DONE $(date)" >> $LOG
