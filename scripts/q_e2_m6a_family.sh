#!/bin/bash
# E2 PEFT 对称补全：m6A family 侧 {dora,ia3} —— 2 模型 x 2 方法 x 3 种子 = 12 runs
# <model> <gpu>
R=/mnt/cunyuliu/rna-ft-eval
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/home/cunyuliu/llr_env/bin/python
MODEL=$1
GPU=$2
TAG=$(echo $MODEL | tr -d "-")
LOG=$R/logs/q_e2_m6a_family_${TAG}_g${GPU}.log
cd /home/cunyuliu/rna-ft-eval

$PY -c "import torch; assert torch.cuda.is_available()" || exit 2
timeout 300 $PY -c "
import torch
free, _ = torch.cuda.mem_get_info($GPU)
assert free > 4e9, "free %.2fG" % (free/1e9)
print("GPU$GPU OK")" >> $LOG 2>&1 || exit 2

for strat in dora ia3; do
  for seed in 17 29 43; do
    D=$($PY -c "
import json
n=0
for l in open(\"$R/ledger.jsonl\"):
    r=json.loads(l)
    if r.get(\"model\")==\"$MODEL\" and r.get(\"task\")==\"modification\" and r.get(\"strategy\")==\"$strat\" and r.get(\"seed\")==$seed and r.get(\"split\")==\"family\" and r.get(\"status\")==\"done\": n=1
print(n)")
    [ "$D" = "1" ] && { echo "skip $strat s$seed (done)" >> $LOG; continue; }
    echo "=== E2-m6A-family $MODEL $strat s$seed GPU$GPU $(date +%T) ===" >> $LOG
    timeout 14400 $PY -m rnafteval.finetune_base --model $MODEL \
      --task modification --strategy $strat --seed $seed --split family \
      --device $GPU --epochs 3 --n-train 20000 --batch-size 32 >> $LOG 2>&1
    echo "--- exit $? $(date +%T) ---" >> $LOG
  done
done
echo "E2-M6A-FAMILY $MODEL DONE $(date)" >> $LOG
