#!/bin/bash
# SSP E2 第三任务面板: RiNALMo SSP {dora,ia3} × s{17,29,43} = 6 runs
# 口径 = 正式 SSP runs（finetune_ssp: epochs 3 / n-train 3000 /
# n-test 500 / bs 4 / 默认 LR）
R=/mnt/cunyuliu/rna-ft-eval
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/home/cunyuliu/llr_env/bin/python
LOG=$R/logs/q_e2_ssp_g1.log
cd /home/cunyuliu/rna-ft-eval
GPU=$1

$PY -c "import torch; assert torch.cuda.is_available()" || exit 2
timeout 300 $PY -c "
import torch
free, _ = torch.cuda.mem_get_info($GPU)
assert free > 3e9, 'free %.2fG' % (free/1e9)
print('GPU$GPU OK')" >> $LOG 2>&1 || exit 2

for strat in dora ia3; do
  for seed in 17 29 43; do
    echo "=== E2-SSP $strat s$seed GPU$GPU $(date +%T) ===" >> $LOG
    timeout 21600 $PY -m rnafteval.finetune_ssp --model RiNALMo-micro \
      --strategy $strat --seed $seed --device $GPU \
      --epochs 3 --n-train 3000 --n-test 500 --batch-size 4 >> $LOG 2>&1
    echo "--- exit $? $(date +%T) ---" >> $LOG
  done
done
echo "E2 SSP DONE $(date)" >> $LOG
