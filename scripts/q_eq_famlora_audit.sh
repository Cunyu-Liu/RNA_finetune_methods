#!/bin/bash
# 崩溃带修订数据补全：ncRNA family 侧 lora，1M/10M/30M/100M 各 3 种子
# 目的：确认"148M LoRA 击穿崩溃带"是否为孤点——四档全谱重测（带 done 跳过 + 失败清行重试 x2）
# <gpu>
R=/mnt/cunyuliu/rna-ft-eval
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/home/cunyuliu/llr_env/bin/python
GPU=$1
LOG=$R/logs/q_eq_famlora_audit_g${GPU}.log
cd /home/cunyuliu/rna-ft-eval

$PY -c "import torch; assert torch.cuda.is_available()" || exit 2

for MODEL in RNA-Sc-1M RNA-Sc-10M RNA-Sc-30M RNA-Sc-100M; do
  MSLUG=$(echo $MODEL | tr -d "-")
  for seed in 17 29 43; do
    RID=ft_${MSLUG}_noncodingrnafamily_lora_s${seed}_family
    ATT=0
    while [ $ATT -lt 3 ]; do
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
      if [ "$F" -ge 10 ]; then
        ATT=$((ATT+1))
        echo "=== attempt $ATT $RID GPU$GPU (free ${F}G) $(date +%T) ===" >> $LOG
        timeout 14400 $PY -m rnafteval.finetune_one --model $MODEL \
          --task noncoding-rna-family --strategy lora --seed $seed --split family \
          --device $GPU --epochs 10 >> $LOG 2>&1
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
echo "FAMILY-LORA AUDIT DONE $(date)" >> $LOG
