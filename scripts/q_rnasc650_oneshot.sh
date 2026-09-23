#!/bin/bash
# RNA-Sc-650M formal 单发补格：q_rnasc650_oneshot.sh <seed> <split>
# 用途：填 GPU0/1 空闲窗口，与 v3 双 worker 的 fresh-pending(<=3h) 互斥共处（g2 同款模式）
R=/mnt/cunyuliu/rna-ft-eval
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/home/cunyuliu/llr_env/bin/python
S=$1; SP=$2
RID=ft_rnasc650m_noncodingrnafamily_full_s${S}_${SP}_lr3e-05
LOG=$R/logs/q_rnasc650_full.log
cd /home/cunyuliu/rna-ft-eval

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
  $PY <<'PYEOF'
import torch
best=-1; best_free=0
for i in range(torch.cuda.device_count()):
    total,_=torch.cuda.mem_get_info(i)
    if total < 20*2**30: continue
    free,_=torch.cuda.mem_get_info(i)
    if free>best_free: best_free=free; best=i
print(best if best_free>=26*1e9 else -1)
PYEOF
}

ATT=0
while [ $ATT -lt 2 ]; do
  D=$(cell_state)
  if [ "$D" = "done" ] || [ "$D" = "fresh_pending" ]; then echo "oneshot s${S}_${SP}: skip ($D) $(date +%T)" >> $LOG; exit 0; fi
  G=$(pick_gpu)
  if [ "$G" != "-1" ]; then
    ATT=$((ATT+1))
    echo "=== oneshot attempt $ATT $RID GPU$G lr=3e-5 bs8 $(date +%T) ===" >> $LOG
    timeout 21600 $PY -m rnafteval.finetune_one --model RNA-Sc-650M \
      --task noncoding-rna-family --strategy full --seed $S --split $SP \
      --device $G --lr 3e-5 --epochs 10 --batch-size 8 >> $LOG 2>&1
    RC=$?
    echo "--- oneshot exit $RC $(date +%T) ---" >> $LOG
    [ $RC -eq 0 ] && exit 0
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
    echo "oneshot s${S}_${SP}: wait GPU $(date +%T)" >> $LOG
  fi
  sleep 300
done
exit 1
