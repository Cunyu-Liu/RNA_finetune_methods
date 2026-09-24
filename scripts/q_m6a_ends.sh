#!/bin/bash
# m6A 受控系等价线补格（1M + 650M 首尾闭合）：
#   Queue A（小）：RNA-Sc-1M frozen/lora/full@3e-5 × 3 种子，bs32，门 GPU0 >= 4G
#   Queue B（大）：RNA-Sc-650M frozen/lora bs32 + full@3e-5 bs8（OOM 教训）× 3 种子，
#                 全卡位 pick_gpu（total>=20G 过滤 MIG 切片）门 >= 24G
# 口径对齐 q_m6a_dualtrack.sh：finetune_base runner、epochs 3、n-train 20000
# 互斥：done 幂等 + fresh_pending(<=3h) 跳过；失败清 pending 重试(<=2)
R=/mnt/cunyuliu/rna-ft-eval
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/home/cunyuliu/llr_env/bin/python
LOG=$R/logs/q_m6a_ends.log
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
    free, total = torch.cuda.mem_get_info(i)
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
  MODEL=$1; STRAT=$2; SEED=$3; SP=$4; LRARG=$5; BS=$6; MING=$7
  MSLUG=$(echo $MODEL | tr -d "-")
  RID=ft_${MSLUG}_modification_${STRAT}_s${SEED}_${SP}
  [ -n "$LRARG" ] && RID=${RID}_lr$(python3 -c "print('%g' % $LRARG)")
  ATT=0
  while [ $ATT -lt 2 ]; do
    D=$(cell_state $RID)
    if [ "$D" = "done" ] || [ "$D" = "fresh_pending" ]; then echo "skip $RID ($D) $(date +%T)" >> $LOG; return 0; fi
    G=$(pick_gpu $MING)
    if [ "$G" != "-1" ]; then
      ATT=$((ATT+1))
      echo "=== attempt $ATT $RID GPU$G bs$BS $(date +%T) ===" >> $LOG
      if [ -n "$LRARG" ]; then
        timeout 14400 $PY -m rnafteval.finetune_base --model $MODEL \
          --strategy $STRAT --seed $SEED --split $SP \
          --device $G --lr $LRARG --epochs 3 --n-train 20000 --batch-size $BS >> $LOG 2>&1
      else
        timeout 14400 $PY -m rnafteval.finetune_base --model $MODEL \
          --strategy $STRAT --seed $SEED --split $SP \
          --device $G --epochs 3 --n-train 20000 --batch-size $BS >> $LOG 2>&1
      fi
      RC=$?
      echo "--- exit $RC $(date +%T) ---" >> $LOG
      [ $RC -eq 0 ] && return 0
      clean_pending $RID
    else
      echo "wait $RID (need ${MING}G) $(date +%T)" >> $LOG
    fi
    sleep 300
  done
  return 1
}

echo "=== M6A-ENDS start $(date) ===" >> $LOG

# Queue A: 1M（小，门 4G）
for S in 17 29 43; do
  run_m6a RNA-Sc-1M frozen $S random "" 32 4
  run_m6a RNA-Sc-1M lora   $S random "" 32 4
  run_m6a RNA-Sc-1M full   $S random 3e-05 32 4
done
echo "QUEUE-A (1M) DONE $(date)" >> $LOG

# Queue B: 650M（大，门 24G；full bs8）
for S in 17 29 43; do
  run_m6a RNA-Sc-650M frozen $S random "" 32 24
  run_m6a RNA-Sc-650M lora   $S random "" 32 24
  run_m6a RNA-Sc-650M full   $S random 3e-05 8 24
done
echo "M6A-ENDS DONE $(date)" >> $LOG
