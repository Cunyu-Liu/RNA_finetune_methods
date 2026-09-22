#!/bin/bash
# m6A 双系等价线（q_dualtrack B 部分独立版）：
# 官方系 micro/mega full@1e-5 + mega/giga lora；受控系 10M/30M/100M {full@3e-5, lora}
# <gpu_b>（主）<gpu_c>（辅助——受控系小模型）；带 done 跳过 + 失败清行重试 x2
R=/mnt/cunyuliu/rna-ft-eval
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/home/cunyuliu/llr_env/bin/python
GB=$1
GC=$2
LOG=$R/logs/q_m6a_dualtrack_g${GB}_g${GC}.log
cd /home/cunyuliu/rna-ft-eval

$PY -c "import torch; assert torch.cuda.is_available()" || exit 2

run_m6a() {
  MODEL=$1; STRAT=$2; SEED=$3; SP=$4; GP=$5; LRARG=$6; MING=$7
  MSLUG=$(echo $MODEL | tr -d "-")
  RID=ft_${MSLUG}_modification_${STRAT}_s${SEED}_${SP}
  [ -n "$LRARG" ] && RID=${RID}_lr$(python3 -c "print('%g' % $LRARG)")
  ATT=0
  while [ $ATT -lt 2 ]; do
    D=$($PY -c "
import json
n=0
for l in open(\"$R/ledger.jsonl\"):
    r=json.loads(l)
    if r.get(\"run_id\")==\"$RID\" and r.get(\"status\")==\"done\": n=1
print(n)")
    [ "$D" = "1" ] && { echo "skip $RID" >> $LOG; return 0; }
    F=$($PY -c "
import torch
free,_=torch.cuda.mem_get_info($GP)
print(int(free/1e9))")
    if [ "$F" -ge "$MING" ]; then
      ATT=$((ATT+1))
      echo "=== attempt $ATT $RID GPU$GP (free ${F}G) $(date +%T) ===" >> $LOG
      if [ -n "$LRARG" ]; then
        timeout 14400 $PY -m rnafteval.finetune_base --model $MODEL \
          --strategy $STRAT --seed $SEED --split $SP \
          --device $GP --lr $LRARG --epochs 3 --n-train 20000 --batch-size 32 >> $LOG 2>&1
      else
        timeout 14400 $PY -m rnafteval.finetune_base --model $MODEL \
          --strategy $STRAT --seed $SEED --split $SP \
          --device $GP --epochs 3 --n-train 20000 --batch-size 32 >> $LOG 2>&1
      fi
      RC=$?
      echo "--- exit $RC $(date +%T) ---" >> $LOG
      [ $RC -eq 0 ] && return 0
      $PY -c "
import fcntl,json
P=\"$R/ledger.jsonl\"
with open(P) as f: fcntl.flock(f,fcntl.LOCK_EX); rows=[l for l in f]
out=[l for l in rows if not (json.loads(l).get(\"run_id\")==\"$RID\" and json.loads(l).get(\"status\")==\"pending\")]
with open(P,\"w\") as f: fcntl.flock(f,fcntl.LOCK_EX); f.writelines(out)" >> $LOG 2>&1
    else
      echo "wait $RID GPU$GP free ${F}G < ${MING}G $(date +%T)" >> $LOG
    fi
    sleep 300
  done
  echo "MAX ATTEMPTS $RID" >> $LOG
}

# ---- GB：官方系（大模型优先夜间）----
for SP in random family; do
  for S in 17 29 43; do
    run_m6a RiNALMo-micro full $S $SP $GB 1e-05 6
  done
done
echo "M6A-OFFICIAL-MICRO DONE $(date)" >> $LOG
for SP in random family; do
  for S in 17 29 43; do
    run_m6a RiNALMo-mega full $S $SP $GB 1e-05 8
  done
done
echo "M6A-OFFICIAL-MEGA-FULL DONE $(date)" >> $LOG
for SP in random family; do
  for S in 17 29 43; do
    run_m6a RiNALMo-mega lora $S $SP $GB "" 8
  done
done
echo "M6A-OFFICIAL-MEGA-LORA DONE $(date)" >> $LOG
for SP in random family; do
  for S in 17 29 43; do
    run_m6a RiNALMo-650M lora $S $SP $GB "" 12
  done
done
echo "M6A-OFFICIAL-GIGA-LORA DONE $(date)" >> $LOG

# ---- GC：受控系 ----
for M in RNA-Sc-10M RNA-Sc-30M RNA-Sc-100M; do
  for SP in random family; do
    for S in 17 29 43; do
      run_m6a $M full $S $SP $GC 3e-05 6
    done
  done
done
echo "M6A-CONTROLLED-FULL DONE $(date)" >> $LOG
for M in RNA-Sc-10M RNA-Sc-30M RNA-Sc-100M; do
  for SP in random family; do
    for S in 17 29 43; do
      run_m6a $M lora $S $SP $GC "" 6
    done
  done
done
echo "M6A-CONTROLLED-LORA DONE $(date)" >> $LOG
echo "M6A-DUALTRACK DONE $(date)" >> $LOG
