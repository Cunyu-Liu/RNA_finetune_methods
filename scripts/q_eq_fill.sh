#!/bin/bash
# 第五波：等价线受控系 1M 档补全（lora random 3 + frozen 双切分 6）+ 100M full tuned（双切分 6）
# 1M full 已有 _lr3e-05 tuned 版（ledger 双行重复无害）；100M full 一直缺——等价线受控系大端 full 参照
# <gpu>；带 done 跳过 + 失败清行重试 x2
R=/mnt/cunyuliu/rna-ft-eval
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/home/cunyuliu/llr_env/bin/python
GPU=$1
LOG=$R/logs/q_eq_fill_g${GPU}.log
cd /home/cunyuliu/rna-ft-eval

$PY -c "import torch; assert torch.cuda.is_available()" || exit 2

run_one() {
  MODEL=$1; STRAT=$2; SEED=$3; SP=$4; LRARG=$5; RIDX=$6
  MSLUG=$(echo $MODEL | tr -d "-")
  RID=ft_${MSLUG}_noncodingrnafamily_${STRAT}_s${SEED}_${SP}${RIDX}
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
free,_=torch.cuda.mem_get_info($GPU)
print(int(free/1e9))")
    if [ "$F" -ge 10 ]; then
      ATT=$((ATT+1))
      echo "=== attempt $ATT $RID GPU$GPU (free ${F}G) $(date +%T) ===" >> $LOG
      if [ "$LRARG" = "-" ]; then
        timeout 14400 $PY -m rnafteval.finetune_one --model $MODEL \
          --task noncoding-rna-family --strategy $STRAT --seed $SEED --split $SP \
          --device $GPU --epochs 10 >> $LOG 2>&1
      else
        timeout 14400 $PY -m rnafteval.finetune_one --model $MODEL \
          --task noncoding-rna-family --strategy $STRAT --seed $SEED --split $SP \
          --device $GPU --lr $LRARG --epochs 10 >> $LOG 2>&1
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

# 1M lora random（family 已齐）
for S in 17 29 43; do
  run_one RNA-Sc-1M lora $S random - ""
done
# 1M frozen 双切分
for SP in random family; do
  for S in 17 29 43; do
    run_one RNA-Sc-1M frozen $S $SP - ""
  done
done
# 100M full tuned 3e-5（对齐 30M/10M tuned 口径）双切
for SP in random family; do
  for S in 17 29 43; do
    run_one RNA-Sc-100M full $S $SP 3e-05 "_lr3e-05"
  done
done
echo "EQ-FILL DONE $(date)" >> $LOG
