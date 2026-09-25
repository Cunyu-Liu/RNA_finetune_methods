#!/bin/bash
# m6A 650M 补格 sweeper（与主队列 q_m6a_ends.sh 互补）：
# - 反向序扫剩余格（full 优先——主队列 ATT 耗尽被放弃的格子由本队兜底）
# - fresh-pending(<=3h) 互斥：主队列在跑的格子跳过
# - 全卡位 pick_gpu（free,total 正确解包 + MIG 过滤）；门：lora/frozen 15G / full 18G
# - 3 轮全扫（每轮后重查 done 状态），幂等
R=/mnt/cunyuliu/rna-ft-eval
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/home/cunyuliu/llr_env/bin/python
LOG=$R/logs/q_m6a_sweep.log
cd /home/cunyuliu/rna-ft-eval

$PY -c "import torch; assert torch.cuda.is_available()" || exit 2

cell_state() {
  $PY - "$1" <<'PYEOF'
import json, sys, datetime
rid=sys.argv[1]; st="none"
for l in open("/mnt/cunyuliu/rna-ft-eval/ledger.jsonl"):
    r=json.loads(l)
    if r.get("run_id")==rid:
        if r.get("status")=="done": st="done"
        elif r.get("status")=="pending":
            t=datetime.datetime.fromisoformat(r["updated_utc"].replace("Z","+00:00"))
            age=(datetime.datetime.now(datetime.timezone.utc)-t).total_seconds()
            st="fresh_pending" if age<10800 else "stale_pending"
print(st)
PYEOF
}

pick_gpu() {
  $PY - $1 <<'PYEOF'
import sys, torch
need=int(sys.argv[1])
best=-1; best_free=0
for i in range(torch.cuda.device_count()):
    try:
        free, total = torch.cuda.mem_get_info(i)
    except Exception:
        continue
    if total < 20*2**30: continue
    if free>best_free: best_free=free; best=i
print(best if best_free>=need*1e9 else -1)
PYEOF
}

clean_pending() {
  $PY - <<PYEOF
import fcntl, json
P="/mnt/cunyuliu/rna-ft-eval/ledger.jsonl"
with open(P) as f:
    fcntl.flock(f, fcntl.LOCK_EX)
    rows=[l for l in f]
out=[l for l in rows if not (json.loads(l).get("run_id")=="$1" and json.loads(l).get("status")=="pending")]
with open(P,"w") as f:
    fcntl.flock(f, fcntl.LOCK_EX)
    f.writelines(out)
PYEOF
}

run_m6a() {
  STRAT=$1; SEED=$2; LRARG=$3; BS=$4; MING=$5
  RID=ft_rnasc650m_modification_${STRAT}_s${SEED}_random
  [ -n "$LRARG" ] && RID=${RID}_lr$(python3 -c "print('%g' % $LRARG)")
  ATT=0
  while [ $ATT -lt 2 ]; do
    D=$(cell_state $RID)
    if [ "$D" = "done" ] || [ "$D" = "fresh_pending" ]; then echo "sweep skip $RID ($D) $(date +%T)" >> $LOG; return 0; fi
    G=$(pick_gpu $MING)
    if [ "$G" != "-1" ]; then
      ATT=$((ATT+1))
      echo "=== sweep attempt $ATT $RID GPU$G bs$BS $(date +%T) ===" >> $LOG
      if [ -n "$LRARG" ]; then
        timeout 14400 $PY -m rnafteval.finetune_base --model RNA-Sc-650M \
          --strategy $STRAT --seed $SEED --split random \
          --device $G --lr $LRARG --epochs 3 --n-train 20000 --batch-size $BS >> $LOG 2>&1
      else
        timeout 14400 $PY -m rnafteval.finetune_base --model RNA-Sc-650M \
          --strategy $STRAT --seed $SEED --split random \
          --device $G --epochs 3 --n-train 20000 --batch-size $BS >> $LOG 2>&1
      fi
      RC=$?
      echo "--- sweep exit $RC $(date +%T) ---" >> $LOG
      [ $RC -eq 0 ] && return 0
      clean_pending $RID
    else
      echo "sweep wait $RID (need ${MING}G) $(date +%T)" >> $LOG
    fi
    sleep 240
  done
  return 1
}

echo "=== M6A-SWEEP start $(date) ===" >> $LOG
for PASS in 1 2 3; do
  echo "--- sweep pass $PASS $(date +%T) ---" >> $LOG
  run_m6a full 17 3e-05 8 18
  run_m6a full 29 3e-05 8 18
  run_m6a full 43 3e-05 8 18
  run_m6a lora 43 "" 32 15
  run_m6a lora 29 "" 32 15
  run_m6a frozen 43 "" 32 7
  run_m6a frozen 29 "" 32 7
  ND=$($PY -c "
import json
n=0
for l in open('$R/ledger.jsonl'):
    r=json.loads(l)
    if r.get('run_id','').startswith('ft_rnasc650m_modification') and r.get('status')=='done': n+=1
print(n)")
  echo "--- pass $PASS done-count $ND $(date +%T) ---" >> $LOG
  [ "$ND" -ge 9 ] && break
  sleep 120
done
echo "M6A-SWEEP DONE $(date)" >> $LOG
