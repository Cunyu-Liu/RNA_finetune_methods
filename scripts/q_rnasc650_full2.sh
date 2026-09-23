#!/bin/bash
# RNA-Sc-650M full tuned 并行架构 v2（接管串行版 q_rnasc650_full.sh）
# 背景：串行 8 runs ~16h；GPU6 33G 空闲。设计：
#   A) GPU6 立即跑 s101 lr3e-5（与 GPU1 孤儿 lr1e-5 并行）→ 网格 ~2h 并行完成
#   B) 双格 done -> BEST LR -> formal 6 runs 双 worker 并行（前向/反向序 + fresh-pending 互斥）
# 互斥：fresh pending(<=3h) 视为他 worker 在跑则跳过；done 幂等跳过；失败清 pending 重试(<=2)
# 日志：追加写 q_rnasc650_full.log（与孤儿同日志，巡检兼容）
R=/mnt/cunyuliu/rna-ft-eval
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/home/cunyuliu/llr_env/bin/python
LOG=$R/logs/q_rnasc650_full.log
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
    free,_=torch.cuda.mem_get_info(i)
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

run_one() {
  RID=$1; S=$2; SP=$3; LR=$4; FORCE_GPU=$5
  ATT=0
  while [ $ATT -lt 2 ]; do
    D=$(cell_state $RID)
    if [ "$D" = "done" ]; then echo "skip $RID (done) $(date +%T)" >> $LOG; return 0; fi
    if [ "$D" = "fresh_pending" ]; then echo "skip $RID (other worker) $(date +%T)" >> $LOG; return 0; fi
    if [ -z "$FORCE_GPU" ]; then G=$(pick_gpu 24); else G=$FORCE_GPU; fi
    if [ "$G" != "-1" ]; then
      ATT=$((ATT+1))
      echo "=== attempt $ATT $RID GPU$G lr=$LR bs8 $(date +%T) ===" >> $LOG
      timeout 21600 $PY -m rnafteval.finetune_one --model RNA-Sc-650M \
        --task noncoding-rna-family --strategy full --seed $S --split $SP \
        --device $G --lr $LR --epochs 10 --batch-size 8 >> $LOG 2>&1
      RC=$?
      echo "--- exit $RC $(date +%T) ---" >> $LOG
      [ $RC -eq 0 ] && return 0
      clean_pending $RID
    else
      echo "wait GPU < 24G $(date +%T)" >> $LOG
    fi
    sleep 240
  done
  return 1
}

echo "=== RNASC650-FULL-v2 (parallel) start $(date) ===" >> $LOG

# 相位A：GPU6 立即跑 lr3e-5 网格格（GPU1 孤儿 lr1e-5 并行中）
run_one ft_rnasc650m_noncodingrnafamily_full_s101_random_lr3e-05 101 random 3e-5 6

# 等待孤儿 lr1e-5 落地（最长 3h 轮询）
W=0
while [ $W -lt 90 ]; do
  ST=$(cell_state ft_rnasc650m_noncodingrnafamily_full_s101_random_lr1e-05)
  [ "$ST" = "done" ] && break
  [ "$ST" = "stale_pending" ] && { echo "orphan lr1e-5 stale, re-run" >> $LOG; run_one ft_rnasc650m_noncodingrnafamily_full_s101_random_lr1e-05 101 random 1e-5 ""; break; }
  sleep 120; W=$((W+1))
done

BEST=$($PY -c "
import json
vals={}
for l in open('$R/ledger.jsonl'):
    r=json.loads(l)
    rid=r.get('run_id','')
    if (r.get('model')=='RNA-Sc-650M' and r.get('task')=='noncoding-rna-family'
        and r.get('strategy')=='full' and r.get('seed')==101 and r.get('split')=='random'
        and r.get('status')=='done' and '_lr' in rid):
        lr=rid.split('_lr')[-1]
        v=r.get('value')
        if v is not None and (lr not in vals or v>vals[lr]): vals[lr]=v
print(max(vals,key=vals.get) if vals else '3e-05')")
echo "BEST LR = $BEST $(date +%T)" >> $LOG

# 相位B：formal 6 runs 双 worker 并行（前向/反向序，60s 错峰）
worker_fwd() {
  sleep 60
  for SP in random family; do
    for S in 17 29 43; do
      run_one ft_rnasc650m_noncodingrnafamily_full_s${S}_${SP}_lr${BEST} $S $SP $BEST ""
    done
  done
  echo "WORKER-FWD DONE $(date +%T)" >> $LOG
}
worker_rev() {
  for SP in family random; do
    for S in 43 29 17; do
      run_one ft_rnasc650m_noncodingrnafamily_full_s${S}_${SP}_lr${BEST} $S $SP $BEST ""
    done
  done
  echo "WORKER-REV DONE $(date +%T)" >> $LOG
}
worker_fwd & P1=$!
worker_rev & P2=$!
wait $P1 $P2
echo "RNASC650-FULL-V2 DONE $(date)" >> $LOG
