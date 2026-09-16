#!/bin/bash
# G7: RiNALMo SSP full tuned 补齐 5 runs (s29/43 random + s17/29/43 family)
# 依据: s17 random tuned=0.1758 vs 默认 3e-4 崩 0.006 (29x); 峰值 1057MB MIG 可跑
# 参数与 tuned2 复核一致 (lr 1e-5, epochs 3, n-train 3000, n-test 500, bs 4)
R=/mnt/cunyuliu/rna-ft-eval
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/home/cunyuliu/llr_env/bin/python
LOG=$R/logs/q_ssp_tuned5.log
cd /home/cunyuliu/rna-ft-eval
GPU=7

$PY -c "import torch; assert torch.cuda.is_available(), 'CUDA UNAVAILABLE'" || exit 2
timeout 300 $PY -c "
import torch
free, total = torch.cuda.mem_get_info($GPU)
assert free > 2e9, 'GPU$GPU free %.2fG < 2G' % (free/1e9)
print('GPU$GPU free %.2fG OK' % (free/1e9))" >> $LOG 2>&1 || exit 2

for job in "29 random" "43 random" "17 family" "29 family" "43 family"; do
  set -- $job; seed=$1; split=$2
  echo "=== RiNALMo SSP full s$seed $split lr1e-5 GPU$GPU $(date +%T) ===" >> $LOG
  timeout 21600 $PY -m rnafteval.finetune_ssp --model RiNALMo-micro \
    --strategy full --seed $seed --split $split --device $GPU \
    --lr 1e-5 --epochs 3 --n-train 3000 --n-test 500 --batch-size 4 >> $LOG 2>&1
  echo "--- exit $? $(date +%T) ---" >> $LOG
done
echo "SSP TUNED5 GPU$GPU DONE $(date)" >> $LOG
