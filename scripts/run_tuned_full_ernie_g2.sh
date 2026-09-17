#!/bin/bash
# GPU2 整卡 (free 13.6G): ERNIE full tuned-LR 补跑
# 背景: 默认 3e-4 全崩 (6/6, ln-13 平原 epoch 0 即卡死)
# 86M 模型显式配对 attn — 需整卡 (与 lora 同理); 峰值预算 ~7G < 13.6G
# 协议 (B1): s101 tuning (1e-5 vs 3e-5) → formal 17/29/43 × 2 切分
R=/mnt/cunyuliu/rna-ft-eval
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/home/cunyuliu/llr_env/bin/python
LOG=$R/logs/q_tuned_full_ernie_g2.log
cd /home/cunyuliu/rna-ft-eval
GPU=2

$PY -c "import torch; assert torch.cuda.is_available()" || exit 2
timeout 300 $PY -c "
import torch
free, _ = torch.cuda.mem_get_info($GPU)
assert free > 10e9, 'GPU$GPU free %.2fG < 10G' % (free/1e9)
print('GPU$GPU free %.2fG OK' % (free/1e9))" >> $LOG 2>&1 || exit 2

for lr in 1e-5 3e-5; do
  echo "=== TUNING ERNIE full s101 lr=$lr GPU$GPU $(date +%T) ===" >> $LOG
  timeout 21600 $PY -m rnafteval.finetune_one --model ERNIE-RNA \
    --task noncoding-rna-family --strategy full --seed 101 --split random \
    --device $GPU --lr $lr --epochs 10 --batch-size 8 >> $LOG 2>&1
  echo "--- exit $? $(date +%T) ---" >> $LOG
done

BEST=$($PY -c "
import json
vals = {}
for l in open('$R/ledger.jsonl'):
    r = json.loads(l)
    rid = r.get('run_id','')
    if rid == 'ft_ernierna_noncodingrnafamily_full_s101_random_lr1e-05' and r.get('status')=='done':
        vals['1e-5'] = r.get('value') or 0
    if rid == 'ft_ernierna_noncodingrnafamily_full_s101_random_lr3e-05' and r.get('status')=='done':
        vals['3e-5'] = r.get('value') or 0
print(max(vals, key=vals.get) if vals else '1e-5')
")
echo "TUNING WINNER lr=$BEST $(date +%T)" >> $LOG

for split in random family; do
  for seed in 17 29 43; do
    echo "=== FORMAL ERNIE full s$seed $split lr=$BEST GPU$GPU $(date +%T) ===" >> $LOG
    timeout 21600 $PY -m rnafteval.finetune_one --model ERNIE-RNA \
      --task noncoding-rna-family --strategy full --seed $seed --split $split \
      --device $GPU --lr $BEST --epochs 10 --batch-size 8 >> $LOG 2>&1
    echo "--- exit $? $(date +%T) ---" >> $LOG
  done
done
echo "TUNED FULL ERNIE GPU$GPU DONE lr=$BEST $(date)" >> $LOG
