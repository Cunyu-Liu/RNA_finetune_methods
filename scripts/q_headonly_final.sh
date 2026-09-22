#!/bin/bash
# 第七波b：head-only 全任务对称收官（E2 六臂完备性——head-only 是 E2 横评成员）
# m6A/MRL: micro+10M head-only x 双切分 x3 = 12+12 runs; SSP: micro 双切 x3 + 10M s29/s43 补 = 8+4 runs
# <gpu1> <gpu2> <gpu3>；带 done 跳过 + 失败清行重试 x2
R=/mnt/cunyuliu/rna-ft-eval
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/home/cunyuliu/llr_env/bin/python
G1=$1; G2=$2; G3=$3
LOG=$R/logs/q_headonly_final_g${G1}_g${G2}_g${G3}.log
cd /home/cunyuliu/rna-ft-eval

$PY -c "import torch; assert torch.cuda.is_available()" || exit 2

run_m6a() {
  MODEL=$1; GP=$2
  MSLUG=$(echo $MODEL | tr -d "-")
  for SP in random family; do
    for S in 17 29 43; do
      RID=ft_${MSLUG}_modification_headonly_s${S}_${SP}
      ATT=0
      while [ $ATT -lt 2 ]; do
        D=$($PY -c "
import json
n=0
for l in open(\"$R/ledger.jsonl\"):
    r=json.loads(l)
    if r.get(\"run_id\")==\"$RID\" and r.get(\"status\")==\"done\": n=1
print(n)")
        [ "$D" = "1" ] && { echo "skip $RID" >> $LOG; break; }
        F=$($PY -c "
import torch
free,_=torch.cuda.mem_get_info($GP)
print(int(free/1e9))")
        if [ "$F" -ge 4 ]; then
          ATT=$((ATT+1))
          echo "=== m6A headonly $MODEL $SP s$S GPU$GP $(date +%T) ===" >> $LOG
          timeout 14400 $PY -m rnafteval.finetune_base --model $MODEL \
            --task modification --strategy head-only --seed $S --split $SP \
            --device $GP --epochs 3 --n-train 20000 --batch-size 32 >> $LOG 2>&1
          RC=$?
          echo "--- exit $RC $(date +%T) ---" >> $LOG
          [ $RC -eq 0 ] && break
          $PY -c "
import fcntl,json
P=\"$R/ledger.jsonl\"
with open(P) as f: fcntl.flock(f,fcntl.LOCK_EX); rows=[l for l in f]
out=[l for l in rows if not (json.loads(l).get(\"run_id\")==\"$RID\" and json.loads(l).get(\"status\")==\"pending\")]
with open(P,\"w\") as f: fcntl.flock(f,fcntl.LOCK_EX); f.writelines(out)" >> $LOG 2>&1
        fi
        sleep 300
      done
    done
  done
}

run_mrl() {
  MODEL=$1; GP=$2
  MSLUG=$(echo $MODEL | tr -d "-")
  for SP in random family; do
    for S in 17 29 43; do
      RID=ft_${MSLUG}_mrl_headonly_s${S}_${SP}
      ATT=0
      while [ $ATT -lt 2 ]; do
        D=$($PY -c "
import json
n=0
for l in open(\"$R/ledger.jsonl\"):
    r=json.loads(l)
    if r.get(\"run_id\")==\"$RID\" and r.get(\"status\")==\"done\": n=1
print(n)")
        [ "$D" = "1" ] && { echo "skip $RID" >> $LOG; break; }
        F=$($PY -c "
import torch
free,_=torch.cuda.mem_get_info($GP)
print(int(free/1e9))")
        if [ "$F" -ge 4 ]; then
          ATT=$((ATT+1))
          echo "=== MRL headonly $MODEL $SP s$S GPU$GP $(date +%T) ===" >> $LOG
          timeout 7200 $PY -m rnafteval.finetune_mrl --model $MODEL \
            --strategy head-only --seed $S --split $SP \
            --device $GP --epochs 3 --n-train 20000 --batch-size 32 >> $LOG 2>&1
          RC=$?
          echo "--- exit $RC $(date +%T) ---" >> $LOG
          [ $RC -eq 0 ] && break
          $PY -c "
import fcntl,json
P=\"$R/ledger.jsonl\"
with open(P) as f: fcntl.flock(f,fcntl.LOCK_EX); rows=[l for l in f]
out=[l for l in rows if not (json.loads(l).get(\"run_id\")==\"$RID\" and json.loads(l).get(\"status\")==\"pending\")]
with open(P,\"w\") as f: fcntl.flock(f,fcntl.LOCK_EX); f.writelines(out)" >> $LOG 2>&1
        fi
        sleep 300
      done
    done
  done
}

run_ssp() {
  MODEL=$1; SEEDS=$2; GP=$3
  MSLUG=$(echo $MODEL | tr -d "-")
  for SP in random family; do
    for S in $SEEDS; do
      RID=ft_${MSLUG}_secondarystructure_headonly_s${S}_${SP}
      ATT=0
      while [ $ATT -lt 2 ]; do
        D=$($PY -c "
import json
n=0
for l in open(\"$R/ledger.jsonl\"):
    r=json.loads(l)
    if r.get(\"run_id\")==\"$RID\" and r.get(\"status\")==\"done\": n=1
print(n)")
        [ "$D" = "1" ] && { echo "skip $RID" >> $LOG; break; }
        F=$($PY -c "
import torch
free,_=torch.cuda.mem_get_info($GP)
print(int(free/1e9))")
        if [ "$F" -ge 4 ]; then
          ATT=$((ATT+1))
          echo "=== SSP headonly $MODEL $SP s$S GPU$GP $(date +%T) ===" >> $LOG
          timeout 21600 $PY -m rnafteval.finetune_ssp --model $MODEL \
            --strategy head-only --seed $S --split $SP --device $GP \
            --epochs 3 --n-train 3000 --n-test 500 --batch-size 4 >> $LOG 2>&1
          RC=$?
          echo "--- exit $RC $(date +%T) ---" >> $LOG
          [ $RC -eq 0 ] && break
          $PY -c "
import fcntl,json
P=\"$R/ledger.jsonl\"
with open(P) as f: fcntl.flock(f,fcntl.LOCK_EX); rows=[l for l in f]
out=[l for l in rows if not (json.loads(l).get(\"run_id\")==\"$RID\" and json.loads(l).get(\"status\")==\"pending\")]
with open(P,\"w\") as f: fcntl.flock(f,fcntl.LOCK_EX); f.writelines(out)" >> $LOG 2>&1
        fi
        sleep 300
      done
    done
  done
}

# 三卡并行：G1 m6A、G2 MRL、G3 SSP
run_m6a RiNALMo-micro $G1
run_m6a RNA-Sc-10M $G1
echo "HEADONLY-M6A DONE $(date)" >> $LOG
run_mrl RiNALMo-micro $G2
run_mrl RNA-Sc-10M $G2
echo "HEADONLY-MRL DONE $(date)" >> $LOG
run_ssp RiNALMo-micro "17 29 43" $G3
run_ssp RNA-Sc-10M "29 43" $G3
echo "HEADONLY-SSP DONE $(date)" >> $LOG
echo "HEADONLY-FINAL DONE $(date)" >> $LOG
