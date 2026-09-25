#!/bin/bash
# E6 谱线扩展：受控系 1M + 650M 两档补全（C6 尺度非单调性两端验证）
# 12 runs：1M/650M × {lora@3e-4, full@3e-05} × 3 种子
# 650M full 用 bs8 + 24G 门（历史：650M full-FT 需 bs8）；timeout 30000
# 其余同 q_e6.sh（幂等/互斥/pick_gpu 三陷阱防御/失败清 pending 重试）
R=/mnt/cunyuliu/rna-ft-eval
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/home/cunyuliu/llr_env/bin/python
LOG=$R/logs/q_e6.log
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
  ATT=0
  while [ $ATT -lt 4 ]; do
    D=$(cell_state $RID)
    if [ "$D" = "done" ] || [ "$D" = "fresh_pending" ]; then
      echo "skip $RID ($D) $(date +%T)" >> $LOG; return 0
    fi
    G=$(pick_gpu $MING)
    if [ "$G" != "-1" ]; then
      ATT=$((ATT+1))
      if [ "$LR" != "3e-4" ]; then
        SUF=$(python3 -c "print('_lr%g' % $LR)")
      else
        SUF=""
      fi
      echo "=== [ext] attempt $ATT $RID GPU$G bs$BS suffix='$SUF' $(date +%T) ===" >> $LOG
      timeout $TO $PY -m rnafteval.e6_forget --model $MODEL \
        --strategy $STRAT --seed $S --lr $LR --device $G \
        --epochs 10 --batch-size $BS --n-holdout 2000 \
        --out-suffix "$SUF" >> $LOG 2>&1
      RC=$?
      echo "--- [ext] exit $RC $(date +%T) ---" >> $LOG
      [ $RC -eq 0 ] && return 0
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
  return 1
}

echo "=== E6-EXT start $(date) ===" >> $LOG

for S in 17 29 43; do
  run_e6 RNA-Sc-1M   lora $S 3e-4  6 32 21600
  run_e6 RNA-Sc-1M   full $S 3e-05 6 32 21600
done
echo "E6-EXT-1M DONE $(date)" >> $LOG

for S in 17 29 43; do
  run_e6 RNA-Sc-650M lora $S 3e-4  20 32 21600
  run_e6 RNA-Sc-650M full $S 3e-05 24 8  30000
done
echo "E6-EXT DONE $(date)" >> $LOG
