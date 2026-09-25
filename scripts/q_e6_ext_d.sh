#!/bin/bash
# E6-EXT 650M full-FT 专用并行 worker（单种子）—— 每实例只负责一个种子，
# 多实例 + pick_gpu 取「空闲最多」的卡 → 自然分散到不同卡，最大化并行占满显存。
# 用户指令：只要有显存就立即提交、禁止过严 gate、每卡显存占满。
# ledger 实测 650M full peak 13247-14044MB → 本 worker 门 14GiB；
# pick_gpu 仍保留 total<20GiB 过滤以排除 MIG 1g.5gb 小切片（torch 实测仅 4.75GiB）。
# 同格互斥（确定性，不靠竞态）：与 q_e6_ext_c.sh **共用** 锁目录
#   /tmp/e6ext_c_locks（每格一个 mkdir 原子锁），确保同一 full 格在任何时刻
#   最多只有一个 worker 真正启动；外加 ledger fresh_pending 兜底。
# 本 worker 一实例一种子 → 三实例可把 3 个 650M full 格在 3 张空卡上并行跑满。
# 用法: q_e6_ext_d.sh <seed>
set -u
SEED="${1:?usage: q_e6_ext_d.sh <seed>}"
R=/mnt/cunyuliu/rna-ft-eval
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/home/cunyuliu/llr_env/bin/python
LOG=$R/logs/q_e6_ext_d_s${SEED}.log
LK=/tmp/e6ext_c_locks
mkdir -p $LK
cd /home/cunyuliu/rna-ft-eval

$PY -c "import torch; assert torch.cuda.is_available()" || exit 2

MODEL=RNA-Sc-650M; STRAT=full; LR=3e-05; MING=14; BS=8; TO=30000
RID=ft_rnasc650m_e6forgetting_full_s${SEED}_s0-heldout_lr3e-05

cell_state() {
  $PY - "$RID" <<'PYEOF'
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
  $PY - $MING <<'PYEOF'
import sys, torch
need=int(sys.argv[1]); best=-1; bf=0
for i in range(torch.cuda.device_count()):
    try:
        free, total = torch.cuda.mem_get_info(i)
    except Exception:
        continue
    if total < 20*2**30: continue
    if free>bf: bf=free; best=i
print(best if bf>=need*1e9 else -1)
PYEOF
}

clear_pending() {
  $PY - "$RID" <<'PYEOF'
import fcntl, json, sys
rid=sys.argv[1]; P="/mnt/cunyuliu/rna-ft-eval/ledger.jsonl"
with open(P) as f:
    fcntl.flock(f, fcntl.LOCK_EX)
    rows=[l for l in f]
out=[l for l in rows if not (json.loads(l).get("run_id")==rid and json.loads(l).get("status")=="pending")]
with open(P,"w") as f:
    fcntl.flock(f, fcntl.LOCK_EX)
    f.writelines(out)
PYEOF
}

if ! mkdir "$LK/$RID" 2>/dev/null; then
  echo "skip-lock $RID $(date +%T)" >> $LOG; exit 0
fi
echo "=== E6-EXT-D s$SEED start $(date) ===" >> $LOG

A=0
while [ $A -lt 400 ]; do
  D=$(cell_state)
  if [ "$D" = "done" ]; then
    echo "done $RID $(date +%T)" >> $LOG
    rmdir "$LK/$RID" 2>/dev/null; exit 0
  fi
  if [ "$D" = "fresh_pending" ]; then
    echo "wait $RID (fresh_pending by peer) $(date +%T)" >> $LOG
  else
    G=$(pick_gpu)
    if [ "$G" != "-1" ]; then
      A=$((A+1))
      echo "=== [extD] attempt $A $RID GPU$G bs$BS need${MING}G $(date +%T) ===" >> $LOG
      timeout $TO $PY -m rnafteval.e6_forget --model $MODEL \
        --strategy $STRAT --seed $SEED --lr $LR --device $G \
        --epochs 10 --batch-size $BS --n-holdout 2000 \
        --out-suffix "_lr3e-05" >> $LOG 2>&1
      RC=$?
      echo "--- [extD] exit $RC $(date +%T) ---" >> $LOG
      if [ $RC -eq 0 ]; then rmdir "$LK/$RID" 2>/dev/null; exit 0; fi
      clear_pending
    else
      echo "wait $RID (need ${MING}G) $(date +%T)" >> $LOG
    fi
  fi
  $PY -c "import time; time.sleep(240)"
done
rmdir "$LK/$RID" 2>/dev/null
echo "giveup $RID after $A attempts $(date +%T)" >> $LOG
exit 1