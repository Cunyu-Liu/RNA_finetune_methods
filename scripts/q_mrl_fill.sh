#!/bin/bash
# MRL frozen/full 补臂（C4 表A 三任务全臂版）：RNA-Sc-30M/100M + RiNALMo-650M/mega
# frozen: 全 16；full: tuned 1e-5（对齐 A8 tuned 协议）x 双切分 x 3 种子
# <gpu1> <gpu2>；带 done 跳过 + 失败清行重试 x2
R=/mnt/cunyuliu/rna-ft-eval
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/home/cunyuliu/llr_env/bin/python
G1=$1
G2=$2
LOG=$R/logs/q_mrl_fill_g${G1}_g${G2}.log
cd /home/cunyuliu/rna-ft-eval

$PY -c "import torch; assert torch.cuda.is_available()" || exit 2

run_one() {
  MODEL=$1; STRAT=$2; SEED=$3; SP=$4; GP=$5; LRARG=$6; RIDX=$7
  MSLUG=$(echo $MODEL | tr -d "-")
  RID=ft_${MSLUG}_mrl_${STRAT}_s${SEED}_${SP}${RIDX}
  ATT=0
  while [ $ATT -lt 2 ]; do
    D=$($PY -c "
import json
n=0
for l in open(\"$R/ledger.jsonl\"):
    r=json.loads(l)
    if r.get(\"run_id\")==\"$RID\" and r.get(\"status\")==\"done\": n=1
print(n)")
    [ "$D" = "1" ] && { echo "skip $RID (done)" >> $LOG; return 0; }
    F=$($PY -c "
import torch
free,_=torch.cuda.mem_get_info($GP)
print(int(free/1e9))")
    if [ "$F" -ge 8 ]; then
      ATT=$((ATT+1))
      echo "=== attempt $ATT $RID GPU$GP (free ${F}G) $(date +%T) ===" >> $LOG
      if [ "$LRARG" = "-" ]; then
        timeout 10800 $PY -m rnafteval.finetune_mrl --model $MODEL \
          --strategy $STRAT --seed $SEED --split $SP --device $GP \
          --epochs 3 --batch-size 32 >> $LOG 2>&1
      else
        timeout 10800 $PY -m rnafteval.finetune_mrl --model $MODEL \
          --strategy $STRAT --seed $SEED --split $SP --device $GP \
          --lr $LRARG --epochs 3 --batch-size 32 >> $LOG 2>&1
      fi
      RC=$?
      echo "--- exit $RC $(date +%T) ---" >> $LOG
      [ $RC -eq 0 ] && return 0
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
  echo "MAX ATTEMPTS $RID" >> $LOG
}

# G1: frozen 全 4 模型（快）
for M in RNA-Sc-30M RNA-Sc-100M RiNALMo-650M RiNALMo-mega; do
  for S in 17 29 43; do
    for SP in random family; do
      run_one $M frozen $S $SP $G1 - ""
    done
  done
done
echo "MRL-FROZEN DONE $(date)" >> $LOG

# G2: full tuned 1e-5（30M/100M ≤100M 档；650M/mega full 违反 B7 分层纪律不做）
for M in RNA-Sc-30M RNA-Sc-100M; do
  for S in 17 29 43; do
    for SP in random family; do
      run_one $M full $S $SP $G2 1e-5 "_lr1e-05"
    done
  done
done
echo "MRL-FILL DONE $(date)" >> $LOG
