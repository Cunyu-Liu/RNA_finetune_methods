#!/bin/bash
# micro dora family s17/s29 OOM 重试（G4 挤占所致，换卡+等显存+重试 x3）
R=/mnt/cunyuliu/rna-ft-eval
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/home/cunyuliu/llr_env/bin/python
GPU=$1
LOG=$R/logs/q_micro_dora_retry_g${GPU}.log
cd /home/cunyuliu/rna-ft-eval

$PY -c "import torch; assert torch.cuda.is_available()" || exit 2

for SEED in 17 29; do
  RID=ft_rinalmomicro_noncodingrnafamily_dora_s${SEED}_family
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
    if [ "$F" -ge 12 ]; then
      ATT=$((ATT+1))
      echo "=== attempt $ATT $RID GPU$GPU (free ${F}G) $(date +%T) ===" >> $LOG
      timeout 14400 $PY -m rnafteval.finetune_one --model RiNALMo-micro \
        --task noncoding-rna-family --strategy dora --seed $SEED --split family \
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
echo "MICRO-DORA-RETRY DONE $(date)" >> $LOG
