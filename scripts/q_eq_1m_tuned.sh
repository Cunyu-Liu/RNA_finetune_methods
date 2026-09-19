#!/bin/bash
# 等价线 RNA-Sc-1M full tuned 臂: s101 LR 网格 -> 选优 -> formal 17/29/43 x {random,family}
R=/mnt/cunyuliu/rna-ft-eval
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/home/cunyuliu/llr_env/bin/python
GPU=$1
LOG=$R/logs/q_eq_1m_tuned_g$GPU.log
cd /home/cunyuliu/rna-ft-eval
MODEL=RNA-Sc-1M

$PY -c "import torch; assert torch.cuda.is_available()" || exit 2
timeout 300 $PY -c "
import torch
free, _ = torch.cuda.mem_get_info($GPU)
assert free > 3e9, "free %.2fG" % (free/1e9)
print("GPU$GPU OK")" >> $LOG 2>&1 || exit 2

for lr in 1e-5 3e-5 1e-4 3e-4; do
  echo "=== TUNING $MODEL full s101 lr=$lr GPU$GPU $(date +%T) ===" >> $LOG
  timeout 14400 $PY -m rnafteval.finetune_one --model $MODEL \
    --task noncoding-rna-family --strategy full --seed 101 --split random \
    --device $GPU --lr $lr --epochs 10 --batch-size 8 >> $LOG 2>&1
  echo "--- exit $? $(date +%T) ---" >> $LOG
done

BEST=$($PY -c "
import json
vals = {}
for l in open(\"$R/ledger.jsonl\"):
    r = json.loads(l)
    rid = r.get(\"run_id\",\"\")
    if (r.get(\"model\")==\"RNA-Sc-1M\" and r.get(\"task\")==\"noncoding-rna-family\"
        and r.get(\"strategy\")==\"full\" and r.get(\"seed\")==101
        and r.get(\"split\")==\"random\" and r.get(\"status\")==\"done\" and \"_lr\" in rid):
        lr = rid.split(\"_lr\")[-1]
        v = r.get(\"value\")
        if v is not None and (lr not in vals or v > vals[lr]):
            vals[lr] = v
best = max(vals, key=vals.get) if vals else \"3e-5\"
print(best)")
echo "BEST LR = $BEST" >> $LOG

for split in random family; do
  for seed in 17 29 43; do
    echo "=== FORMAL $MODEL full s$seed $split lr=$BEST GPU$GPU $(date +%T) ===" >> $LOG
    timeout 14400 $PY -m rnafteval.finetune_one --model $MODEL \
      --task noncoding-rna-family --strategy full --seed $seed --split $split \
      --device $GPU --lr $BEST --epochs 10 --batch-size 8 >> $LOG 2>&1
    echo "--- exit $? $(date +%T) ---" >> $LOG
  done
done
echo "EQ-1M-TUNED DONE BEST=$BEST $(date)" >> $LOG
