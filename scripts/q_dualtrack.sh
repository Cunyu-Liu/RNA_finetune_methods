#!/bin/bash
# 双轨验证波（用户指令 2026-09-22）：官方系 RiNALMo 三档等价线 + 第二任务（m6A）双系等价线补全
# A) giga-650M full tuned 1e-5 x 双切分 x 3 种子（官方系 3x3 网格最后一格）
# B) m6A 官方系：micro full@1e-5 + mega full@1e-5 + mega lora + giga lora（双切分 x3 种子）
# C) m6A 受控系：RNA-Sc 10M/30M/100M {full@3e-5, lora}（双切分 x3 种子）
# 口径：n-train 20000 / epochs 3 / batch 32（对齐既有 m6A 正式 run）
# <gpu_a> <gpu_b>；带 done 跳过 + 失败清行重试 x2 + 等显存（20G for 650M full）
R=/mnt/cunyuliu/rna-ft-eval
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/home/cunyuliu/llr_env/bin/python
GA=$1
GB=$2
LOG=$R/logs/q_dualtrack_g${GA}_g${GB}.log
cd /home/cunyuliu/rna-ft-eval

$PY -c "import torch; assert torch.cuda.is_available()" || exit 2

run_one() {
  MODEL=$1; TASK=$2; STRAT=$3; SEED=$4; SP=$5; GP=$6; LRARG=$7; MING=$8
  MSLUG=$(echo $MODEL | tr -d "-")
  TSLUG=$TASK
  RID=ft_${MSLUG}_${TSLUG}_${STRAT}_s${SEED}_${SP}${LRARG:+_lr$(echo $LRARG | sed 's/0\.0*/e-/;s/e-0*/e-/')}
  # 简化：直接构造 _lr 标签（finetune_one/base 会用 %g 格式）
  RID=ft_${MSLUG}_${TSLUG}_${STRAT}_s${SEED}_${SP}
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
    [ "$D" = "1" ] && { echo "skip $RID (done)" >> $LOG; return 0; }
    F=$($PY -c "
import torch
free,_=torch.cuda.mem_get_info($GP)
print(int(free/1e9))")
    if [ "$F" -ge "$MING" ]; then
      ATT=$((ATT+1))
      echo "=== attempt $ATT $RID GPU$GP (free ${F}G) $(date +%T) ===" >> $LOG
      if [ "$TASK" = "noncoding-rna-family" ]; then
        if [ -n "$LRARG" ]; then
          timeout 21600 $PY -m rnafteval.finetune_one --model $MODEL \
            --task $TASK --strategy $STRAT --seed $SEED --split $SP \
            --device $GP --lr $LRARG --epochs 10 >> $LOG 2>&1
        else
          timeout 21600 $PY -m rnafteval.finetune_one --model $MODEL \
            --task $TASK --strategy $STRAT --seed $SEED --split $SP \
            --device $GP --epochs 10 >> $LOG 2>&1
        fi
      else
        if [ -n "$LRARG" ]; then
          timeout 14400 $PY -m rnafteval.finetune_base --model $MODEL \
            --task $TASK --strategy $STRAT --seed $SEED --split $SP \
            --device $GP --lr $LRARG --epochs 3 --n-train 20000 --batch-size 32 >> $LOG 2>&1
        else
          timeout 14400 $PY -m rnafteval.finetune_base --model $MODEL \
            --task $TASK --strategy $STRAT --seed $SEED --split $SP \
            --device $GP --epochs 3 --n-train 20000 --batch-size 32 >> $LOG 2>&1
        fi
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
    fi
    sleep 300
  done
  echo "MAX ATTEMPTS $RID" >> $LOG
}

# ============ GA：giga-650M full tuned（ncRNA 官方系最后一格）============
for SP in random family; do
  for S in 17 29 43; do
    run_one RiNALMo-650M noncoding-rna-family full $S $SP $GA 1e-05 20
  done
done
echo "DUALTRACK-A DONE $(date)" >> $LOG

# ============ GB：m6A 双系等价线（官方 + 受控） ============
# B1 官方系：micro/mega full@1e-5 + mega/giga lora
for SP in random family; do
  for S in 17 29 43; do
    run_one RiNALMo-micro modification full $S $SP $GB 1e-05 6
  done
done
for SP in random family; do
  for S in 17 29 43; do
    run_one RiNALMo-mega modification full $S $SP $GB 1e-05 8
  done
done
for SP in random family; do
  for S in 17 29 43; do
    run_one RiNALMo-mega modification lora $S $SP $GB "" 8
  done
done
for SP in random family; do
  for S in 17 29 43; do
    run_one RiNALMo-650M modification lora $S $SP $GB "" 12
  done
done
echo "DUALTRACK-B-OFFICIAL DONE $(date)" >> $LOG
# B2 受控系：RNA-Sc 10M/30M/100M {full@3e-5, lora}
for M in RNA-Sc-10M RNA-Sc-30M RNA-Sc-100M; do
  for SP in random family; do
    for S in 17 29 43; do
      run_one $M modification full $S $SP $GB 3e-05 6
    done
  done
done
for M in RNA-Sc-10M RNA-Sc-30M RNA-Sc-100M; do
  for SP in random family; do
    for S in 17 29 43; do
      run_one $M modification lora $S $SP $GB "" 6
    done
  done
done
echo "DUALTRACK-B-CONTROLLED DONE $(date)" >> $LOG
echo "DUALTRACK DONE $(date)" >> $LOG
