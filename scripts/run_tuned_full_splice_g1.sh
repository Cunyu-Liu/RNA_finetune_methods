#!/bin/bash
# GPU1 整卡 (free 13.7G): SpliceBERT full tuned-LR 补跑
# 背景: 默认 3e-4 全崩 (6/6, ln-13 平原) — C1/C4 图 full 列需 tuned 协议臂
# 协议 (B1): s101 tuning 选 LR (1e-5 vs 3e-5) → formal 17/29/43 × 2 切分
R=/mnt/cunyuliu/rna-ft-eval
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/home/cunyuliu/llr_env/bin/python
LOG=$R/logs/q_tuned_full_splice_g1.log
cd /home/cunyuliu/rna-ft-eval
GPU=1

$PY -c "import torch; assert torch.cuda.is_available()" || exit 2
timeout 300 $PY -c "
import torch
free, _ = torch.cuda.mem_get_info($GPU)
assert free > 10e9, 'GPU$GPU free %.2fG < 10G' % (free/1e9)
print('GPU$GPU free %.2fG OK' % (free/1e9))" >> $LOG 2>&1 || exit 2

# --- 阶段 1: tuning s101 双档 ---
for lr in 1e-5 3e-5; do
  echo "=== TUNING SpliceBERT full s101 lr=$lr GPU$GPU $(date +%T) ===" >> $LOG
  timeout 14400 $PY -m rnafteval.finetune_one --model SpliceBERT \
    --task noncoding-rna-family --strategy full --seed 101 --split random \
    --device $GPU --lr $lr --epochs 10 --batch-size 8 >> $LOG 2>&1
  echo "--- exit $? $(date +%T) ---" >> $LOG
done

# --- 阶段 2: 选优 (ledger 读值) ---
BEST=$($PY -c "
import json
vals = {}
for l in open('$R/ledger.jsonl'):
    r = json.loads(l)
    rid = r.get('run_id','')
    if rid == 'ft_splicebert_noncodingrnafamily_full_s101_random_lr1e-05' and r.get('status')=='done':
        vals['1e-5'] = r.get('value') or 0
    if rid == 'ft_splicebert_noncodingrnafamily_full_s101_random_lr3e-05' and r.get('status')=='done':
        vals['3e-5'] = r.get('value') or 0
print(max(vals, key=vals.get) if vals else '3e-5')
")
echo "TUNING WINNER lr=$BEST $(date +%T)" >> $LOG

# --- 阶段 3: formal 3 种子 × 2 切分 ---
for split in random family; do
  for seed in 17 29 43; do
    echo "=== FORMAL SpliceBERT full s$seed $split lr=$BEST GPU$GPU $(date +%T) ===" >> $LOG
    timeout 14400 $PY -m rnafteval.finetune_one --model SpliceBERT \
      --task noncoding-rna-family --strategy full --seed $seed --split $split \
      --device $GPU --lr $BEST --epochs 10 --batch-size 8 >> $LOG 2>&1
    echo "--- exit $? $(date +%T) ---" >> $LOG
  done
done
echo "TUNED FULL SPLICEBERT GPU$GPU DONE lr=$BEST $(date)" >> $LOG
