#!/bin/bash
# m6A 双轨受控系 full@3e-5 轨并行加速（G5 逆序）：10M/30M/100M full x 双切分 x 3 seed = 18 runs
# 与主队列 q_m6a_dualtrack G3 段（full 优先）零碰撞：双端 done 跳过（bash 小写 RID + python 模块内建 skip）
R=/mnt/cunyuliu/rna-ft-eval
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/home/cunyuliu/llr_env/bin/python
GPU=5
LOG=$R/logs/q_m6a_ctrl_full_g5.log
cd /home/cunyuliu/rna-ft-eval

$PY -c "import torch; assert torch.cuda.is_available()" || exit 2

run_full() {
  MODEL=$1; SEED=$2; SP=$3
  MSLUG=$(echo $MODEL | tr -d "-")
  RID=ft_${MSLUG}_modification_full_s${SEED}_${SP}_lr3e-05
  RIDL=$(echo $RID | tr 'A-Z' 'a-z')
  ATT=0
  while [ $ATT -lt 2 ]; do
    D=$($PY -c "
import json
n=0
for l in open('$R/ledger.jsonl'):
    r=json.loads(l)
    if r.get('run_id')=='$RIDL' and r.get('status')=='done': n=1
print(n)")
    [ "$D" = "1" ] && { echo "skip $RIDL (done)" >> $LOG; return 0; }
    F=$($PY -c "
import torch
free,_=torch.cuda.mem_get_info($GPU)
print(int(free/1e9))")
    if [ "$F" -ge 8 ]; then
      ATT=$((ATT+1))
      echo "=== attempt $ATT $RIDL GPU$GPU (free ${F}G) $(date +%T) ===" >> $LOG
      timeout 14400 $PY -m rnafteval.finetune_base --model $MODEL \
        --strategy full --seed $SEED --split $SP \
        --device $GPU --lr 3e-05 --epochs 3 --n-train 20000 --batch-size 32 >> $LOG 2>&1
      RC=$?
      echo "--- exit $RC $(date +%T) ---" >> $LOG
      [ $RC -eq 0 ] && return 0
      $PY -c "
import fcntl,json
P='$R/ledger.jsonl'
with open(P) as f: fcntl.flock(f,fcntl.LOCK_EX); rows=[l for l in f]
out=[l for l in rows if not (json.loads(l).get('run_id')=='$RIDL' and json.loads(l).get('status')=='pending')]
with open(P,'w') as f: fcntl.flock(f,fcntl.LOCK_EX); f.writelines(out)
print('cleaned')" >> $LOG 2>&1
    else
      echo "wait $RIDL GPU$GPU free ${F}G < 8G $(date +%T)" >> $LOG
    fi
    sleep 300
  done
  echo "MAX ATTEMPTS $RIDL" >> $LOG
}

for M in RNA-Sc-100M RNA-Sc-30M RNA-Sc-10M; do
  for SP in random family; do
    for S in 43 29 17; do
      run_full $M $S $SP
    done
  done
done
echo "M6A-CTRL-FULL G5 DONE $(date)" >> $LOG
