#!/bin/bash
# giga-650M full@1e-5 random 侧补缺（G4 守门 >=24G）：G1 队列 random 3 种子 9 次 attempt 全被 GPU1 他方 churn 挤爆 OOM（MAX ATTEMPTS 放弃）；
# 本队列换 GPU4，等 dualtrack G4 段（giga lora family）收尾释放后自动开跑；bs8 协议与 q_giga_full_bs8 对齐
R=/mnt/cunyuliu/rna-ft-eval
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/home/cunyuliu/llr_env/bin/python
GPU=4
LOG=$R/logs/q_giga_full_rand_g4.log
cd /home/cunyuliu/rna-ft-eval

$PY -c "import torch; assert torch.cuda.is_available()" || exit 2

for S in 17 29 43; do
  RID=ft_rinalmo650m_noncodingrnafamily_full_s${S}_random_lr1e-05
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
    if [ "$F" -ge 24 ]; then
      ATT=$((ATT+1))
      echo "=== attempt $ATT $RID GPU$GPU (free ${F}G) bs8 $(date +%T) ===" >> $LOG
      timeout 21600 $PY -m rnafteval.finetune_one --model RiNALMo-650M \
        --task noncoding-rna-family --strategy full --seed $S --split random \
        --device $GPU --lr 1e-5 --epochs 10 --batch-size 8 >> $LOG 2>&1
      RC=$?
      echo "--- exit $RC $(date +%T) ---" >> $LOG
      [ $RC -eq 0 ] && break
      $PY -c "
import fcntl,json
P=\"$R/ledger.jsonl\"
with open(P) as f: fcntl.flock(f,fcntl.LOCK_EX); rows=[l for l in f]
out=[l for l in rows if not (json.loads(l).get(\"run_id\")==\"$RID\" and json.loads(l).get(\"status\")==\"pending\")]
with open(P,\"w\") as f: fcntl.flock(f,fcntl.LOCK_EX); f.writelines(out)" >> $LOG 2>&1
    else
      echo "wait GPU$GPU free ${F}G < 24G $(date +%T) (dualtrack G4 段未收尾则正常等待)" >> $LOG
    fi
    sleep 300
  done
done
echo "GIGA-FULL-RAND G4 DONE $(date)" >> $LOG
