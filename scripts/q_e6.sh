#!/bin/bash
# E6 灾难性遗忘正式矩阵（v1 协议：pre/post S0 heldout NLL + 重排噪声带）
# 设计：受控系 10M/30M/100M × {lora, full@tuned-lr} × 3 种子 = 18 runs
#       + RiNALMo-micro {lora, full@1e-5} × 3 种子 = 6 runs（官方系对照）
# 门：10M/30M/micro 6G；100M 10G；全卡位 pick_gpu（MIG 过滤+try/except，
#     三陷阱全修）；幂等 done-skip；失败清 pending 重试（<=2）
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
  MODEL=$1; STRAT=$2; S=$3; LR=$4; MING=$5; BS=$6
  RID=ft_$(echo $MODEL | tr -d '-' | tr 'A-Z' 'a-z')_e6forgetting_${STRAT}_s${S}_s0-heldout
  [ "$LR" != "3e-4" ] && RID=${RID}_lr$(python3 -c "print('%g' % $LR)")
  ATT=0
  while [ $ATT -lt 2 ]; do
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
      echo "=== attempt $ATT $RID GPU$G bs$BS suffix='$SUF' $(date +%T) ===" >> $LOG
      timeout 21600 $PY -m rnafteval.e6_forget --model $MODEL \
        --strategy $STRAT --seed $S --lr $LR --device $G \
        --epochs 10 --batch-size $BS --n-holdout 2000 \
        --out-suffix "$SUF" >> $LOG 2>&1
      RC=$?
      echo "--- exit $RC $(date +%T) ---" >> $LOG
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

echo "=== E6-MATRIX start $(date) ===" >> $LOG

# 受控系（tuned LR 口径与 ncRNA 一致：受控 3e-5，micro 官方 1e-5）
for S in 17 29 43; do
  run_e6 RNA-Sc-10M  lora $S 3e-4 6 32
  run_e6 RNA-Sc-10M  full $S 3e-05 6 32
  run_e6 RNA-Sc-30M  lora $S 3e-4 6 32
  run_e6 RNA-Sc-30M  full $S 3e-05 6 32
  run_e6 RNA-Sc-100M lora $S 3e-4 10 32
  run_e6 RNA-Sc-100M full $S 3e-05 10 32
done
echo "E6-CONTROLLED DONE $(date)" >> $LOG

# 官方系对照（micro）
for S in 17 29 43; do
  run_e6 RiNALMo-micro lora $S 3e-4 6 32
  run_e6 RiNALMo-micro full $S 1e-05 6 32
done
echo "E6-MATRIX DONE $(date)" >> $LOG
