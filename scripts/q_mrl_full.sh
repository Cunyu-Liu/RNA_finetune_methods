#!/bin/bash
# MRL full 臂（A8 三任务扩展）: <model> <gpu>
# default x6 -> 判崩(random Pearson<0.45) -> s101 网格 {1e-5,3e-5} -> tuned x6
R=/mnt/cunyuliu/rna-ft-eval
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/home/cunyuliu/llr_env/bin/python
MODEL=$1
GPU=$2
TAG=$(echo $MODEL | tr -d "-")
LOG=$R/logs/q_mrl_full_${TAG}_g${GPU}.log
cd /home/cunyuliu/rna-ft-eval

$PY -c "import torch; assert torch.cuda.is_available()" || exit 2
timeout 300 $PY -c "
import torch
free, _ = torch.cuda.mem_get_info($GPU)
assert free > 4e9, "free %.2fG" % (free/1e9)
print("GPU$GPU OK")" >> $LOG 2>&1 || exit 2

for split in random family; do
  for seed in 17 29 43; do
    echo "=== $MODEL MRL full(default) s$seed $split GPU$GPU $(date +%T) ===" >> $LOG
    timeout 7200 $PY -m rnafteval.finetune_mrl --model $MODEL \
      --strategy full --seed $seed --split $split \
      --device $GPU --epochs 3 --n-train 20000 --batch-size 32 >> $LOG 2>&1
    echo "--- exit $? $(date +%T) ---" >> $LOG
  done
done

AVG=$($PY -c "
import json
vals = []
for l in open(\"$R/ledger.jsonl\"):
    r = json.loads(l)
    rid = r.get(\"run_id\",\"\")
    if (r.get(\"model\")==\"$MODEL\" and r.get(\"task\")==\"mrl\"
        and r.get(\"strategy\")==\"full\" and r.get(\"split\")==\"random\"
        and r.get(\"seed\") in (17,29,43) and r.get(\"status\")==\"done\"
        and \"_lr\" not in rid and \"_e3\" not in rid):
        if r.get(\"value\") is not None: vals.append(r[\"value\"])
print(\"%.4f\" % (sum(vals)/len(vals)) if vals else \"0\")")
echo "DEFAULT random AVG = $AVG" >> $LOG

OK=$($PY -c "print(1 if float(\"$AVG\") >= 0.45 else 0)")
if [ "$OK" = "1" ]; then
  echo "SURVIVOR — skip tuned arm (avg=$AVG)" >> $LOG
  echo "MRL-FULL $MODEL DONE (survivor) $(date)" >> $LOG
  exit 0
fi

for lr in 1e-5 3e-5; do
  echo "=== TUNING $MODEL MRL full s101 lr=$lr GPU$GPU $(date +%T) ===" >> $LOG
  timeout 7200 $PY -m rnafteval.finetune_mrl --model $MODEL \
    --strategy full --seed 101 --split random \
    --device $GPU --lr $lr --epochs 3 --n-train 20000 --batch-size 32 >> $LOG 2>&1
  echo "--- exit $? $(date +%T) ---" >> $LOG
done

BEST=$($PY -c "
import json
vals = {}
for l in open(\"$R/ledger.jsonl\"):
    r = json.loads(l)
    rid = r.get(\"run_id\",\"\")
    if (r.get(\"model\")==\"$MODEL\" and r.get(\"task\")==\"mrl\"
        and r.get(\"strategy\")==\"full\" and r.get(\"seed\")==101
        and r.get(\"split\")==\"random\" and r.get(\"status\")==\"done\" and \"_lr\" in rid):
        lr = rid.split(\"_lr\")[-1]
        v = r.get(\"value\")
        if v is not None and (lr not in vals or v > vals[lr]):
            vals[lr] = v
print(max(vals, key=vals.get) if vals else \"1e-5\")")
echo "BEST LR = $BEST" >> $LOG

for split in random family; do
  for seed in 17 29 43; do
    echo "=== FORMAL $MODEL MRL full s$seed $split lr=$BEST GPU$GPU $(date +%T) ===" >> $LOG
    timeout 7200 $PY -m rnafteval.finetune_mrl --model $MODEL \
      --strategy full --seed $seed --split $split \
      --device $GPU --lr $BEST --epochs 3 --n-train 20000 --batch-size 32 >> $LOG 2>&1
    echo "--- exit $? $(date +%T) ---" >> $LOG
  done
done
echo "MRL-FULL $MODEL DONE BEST=$BEST $(date)" >> $LOG
