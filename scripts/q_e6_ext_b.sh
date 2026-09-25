#!/bin/bash
# E6-EXT 并行侧翼 worker B —— 补 GPU0 空闲槽，逆序 + 每格原子锁
# 目的：多卡并行推进 E6-EXT 剩余 650M 格（谱线端点），不干扰主队列 q_e6_ext.sh
# 逆序（43->29->17）与主队列（17->29->43）错开，降低同格碰撞；cell_state 幂等兜底
R=/mnt/cunyuliu/rna-ft-eval
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/home/cunyuliu/llr_env/bin/python
LOG=$R/logs/q_e6_ext_b.log
LK=/tmp/e6ext_b_locks
mkdir -p $LK
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

run_e6() {
  MODEL=$1; STRAT=$2; S=$3; LR=$4; MING=$5; BS=$6; TO=$7
  RID=ft_$(echo $MODEL | tr -d '-' | tr 'A-Z' 'a-z')_e6forgetting_${STRAT}_s${S}_s0-heldout
  [ "$LR" != "3e-4" ] && RID=${RID}_lr$(python3 -c "print('%g' % $LR)")
  if ! mkdir "$LK/$RID" 2>/dev/null; then
    echo "skip-lock $RID $(date +%T)" >> $LOG; return 0
  fi
  ATT=0
  while [ $ATT -lt 4 ]; do
    D=$(cell_state $RID)
    if [ "$D" = "done" ] || [ "$D" = "fresh_pending" ]; then
      echo "skip $RID ($D) $(date +%T)" >> $LOG
      rmdir "$LK/$RID" 2>/dev/null; return 0
    fi
    G=$(pick_gpu $MING)
    if [ "$G" != "-1" ]; then
      ATT=$((ATT+1))
      SUF=""
      [ "$LR" != "3e-4" ] && SUF=$(python3 -c "print('_lr%g' % $LR)")
      echo "=== [extB] attempt $ATT $RID GPU$G bs$BS $(date +%T) ===" >> $LOG
      timeout $TO $PY -m rnafteval.e6_forget --model $MODEL \
        --strategy $STRAT --seed $S --lr $LR --device $G \
        --epochs 10 --batch-size $BS --n-holdout 2000 \
        --out-suffix "$SUF" >> $LOG 2>&1
      RC=$?
      echo "--- [extB] exit $RC $(date +%T) ---" >> $LOG
      if [ $RC -eq 0 ]; then rmdir "$LK/$RID" 2>/dev/null; return 0; fi
      $PY - <<PYEOF
import fcntl, json
P="/mnt/cunyuliu/rna-ft-eval/ledger.jsonl"
with open(P) as f:
    fcntl.flock(f, fcntl.LOCK_EX)
    rows=[l for l in f]
out=[l for l in rows if not (json.loads(l).get("run_id")=="$RID" and json.loads(l).get("status")=="pending")]
with open(P,"w") as f:
    fcntl.flock(f, fcntl.LOCK_EX)
    f.writelines(out)
PYEOF
    else
      echo "wait $RID (need ${MING}G) $(date +%T)" >> $LOG
    fi
    sleep 300
  done
  rmdir "$LK/$RID" 2>/dev/null
  return 1
}

echo "=== E6-EXT-B start $(date) ===" >> $LOG

for S in 43 29 17; do
  run_e6 RNA-Sc-650M lora $S 3e-4  20 32 21600
done
for S in 43 29 17; do
  run_e6 RNA-Sc-650M full $S 3e-05 24 8  30000
done
echo "E6-EXT-B DONE $(date)" >> $LOG