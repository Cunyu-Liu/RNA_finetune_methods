#!/bin/bash
# 第四波：MRL 30M/100M full tuned（1e-5）x 双切分 x 3 种子 = 12 runs
# <gpu>；带 done 跳过 + 失败清行重试 x2
R=/mnt/cunyuliu/rna-ft-eval
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/home/cunyuliu/llr_env/bin/python
GPU=$1
LOG=$R/logs/q_mrl_fulltuned_g${GPU}.log
cd /home/cunyuliu/rna-ft-eval

$PY -c "import torch; assert torch.cuda.is_available()" || exit 2

for MODEL in RNA-Sc-30M RNA-Sc-100M; do
  MSLUG=$(echo $MODEL | tr -d "-")
  for SP in random family; do
    for SEED in 17 29 43; do
      RID=ft_${MSLUG}_mrl_full_s${SEED}_${SP}_lr1e-05
      ATT=0
      while [ $ATT -lt 2 ]; do
        D=$($PY -c "
import json
n=0
for l in open(\"$R/ledger.jsonl\"):
    r=json.loads(l)
    if r.get(\"run_id\")==\"$RID\" and r.get(\"status\")==\"done\": n=1
print(n)")
        [ "$D" = "1" ] && { echo "skip $RID (done)" >> $LOG; break; }
        F=$($PY -c "
import torch
free,_=torch.cuda.mem_get_info($GPU)
print(int(free/1e9))")
        if [ "$F" -ge 8 ]; then
          ATT=$((ATT+1))
          echo "=== attempt $ATT $RID GPU$GPU (free ${F}G) $(date +%T) ===" >> $LOG
          timeout 10800 $PY -m rnafteval.finetune_mrl --model $MODEL \
            --strategy full --seed $SEED --split $SP --device $GPU \
            --lr 1e-5 --epochs 3 --batch-size 32 >> $LOG 2>&1
          RC=$?
          echo "--- exit $RC $(date +%T) ---" >> $LOG
          [ $RC -eq 0 ] && break
          $PY -c "
import fcntl,json
P=\"$R/ledger.jsonl\"
with open(P) as f: fcntl.flock(f,fcntl.LOCK_EX); rows=[l for l in f]
out=[l for l in rows if not (json.loads(l).get(\"run_id\")==\"$RID\" and json.loads(l).get(\"status\")==\"pending\")]
with open(P,\"w\") as f: fcntl.flock(f,fcntl.LOCK_EX); f.writelines(out)
print(\"cleaned\")" >> $LOG 2>&1
        fi
        sleep 300
      done
    done
  done
done
echo "MRL-FULLTUNED DONE $(date)" >> $LOG
