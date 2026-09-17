#!/bin/bash
# RiNALMo ncrna full family @1e-5 tuned 臂补齐（3 runs）
# QA 审计发现: random 侧 tuned 三种子存在（0.939/0.935/0.941）,
# family 侧 tuned 缺失——5 模型中唯一未知 tuned family 行为的洞
# （其余 4 模型 tuned family 均崩 0.06-0.10; 本臂回答 RiNALMo 是否同样）
# 口径 = random 侧真 tuned 行（epochs 10 / bs 8 / lr 1e-5 / 全量 6859）
R=/mnt/cunyuliu/rna-ft-eval
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/home/cunyuliu/llr_env/bin/python
LOG=$R/logs/q_tuned_fam_rinalmo.log
cd /home/cunyuliu/rna-ft-eval
GPU=$1

$PY -c "import torch; assert torch.cuda.is_available()" || exit 2
timeout 300 $PY -c "
import torch
free, _ = torch.cuda.mem_get_info($GPU)
assert free > 2.5e9, 'GPU$GPU free %.2fG < 2.5G' % (free/1e9)
print('GPU$GPU free %.2fG OK' % (free/1e9))" >> $LOG 2>&1 || exit 2

for seed in 17 29 43; do
  echo "=== RiNALMo full family s$seed lr1e-5 GPU$GPU $(date +%T) ===" >> $LOG
  timeout 14400 $PY -m rnafteval.finetune_one --model RiNALMo-micro \
    --task noncoding-rna-family --strategy full --seed $seed --split family \
    --device $GPU --lr 1e-5 --epochs 10 --batch-size 8 >> $LOG 2>&1
  echo "--- exit $? $(date +%T) ---" >> $LOG
done
echo "RINALMO TUNED FAMILY DONE $(date)" >> $LOG
