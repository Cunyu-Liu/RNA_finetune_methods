#!/bin/bash
# G6 (MIG 4.75G): 新模型 E1 种子补齐 s29/s43 (ncrna) — SpliceBERT/RNA-FM
# frozen+lora, ERNIE-RNA frozen (lora 需整卡, 见 MIG OOM 教训, 排未来整卡队列)
# family+random 双切分; 参数与 s17 首探一致 (epochs 10, bs 8)
R=/mnt/cunyuliu/rna-ft-eval
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/home/cunyuliu/llr_env/bin/python
LOG=$R/logs/q_newmodels_seeds_g6.log
cd /home/cunyuliu/rna-ft-eval
GPU=6

$PY -c "import torch; assert torch.cuda.is_available(), 'CUDA UNAVAILABLE'" || exit 2
timeout 300 $PY -c "
import torch
free, total = torch.cuda.mem_get_info($GPU)
assert free > 3e9, 'GPU$GPU free %.2fG < 3G' % (free/1e9)
print('GPU$GPU free %.2fG OK' % (free/1e9))" >> $LOG 2>&1 || exit 2

for job in "SpliceBERT frozen" "SpliceBERT lora" "ERNIE-RNA frozen" "RNA-FM frozen" "RNA-FM lora"; do
  set -- $job; model=$1; strat=$2
  for split in random family; do
    for seed in 29 43; do
      echo "=== $model $strat s$seed $split GPU$GPU $(date +%T) ===" >> $LOG
      timeout 14400 $PY -m rnafteval.finetune_one --model $model \
        --task noncoding-rna-family --strategy $strat --seed $seed --split $split \
        --device $GPU --epochs 10 --batch-size 8 >> $LOG 2>&1
      echo "--- exit $? $(date +%T) ---" >> $LOG
    done
  done
done
echo "NEWMODELS SEEDS GPU$GPU DONE $(date)" >> $LOG
