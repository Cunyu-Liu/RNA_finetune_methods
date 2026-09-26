#!/bin/bash
# P1/P2 gap-fill monitor (cron 20min): progress + GPU + real-CUDA scan + auto-refill.
REPO=/home/cunyuliu/rna-ft-eval
R=/mnt/cunyuliu/rna-ft-eval
PY=/home/cunyuliu/llr_env/bin/python
OUT=$R/status/p1_monitor.log
mkdir -p $R/status
{
  echo "===== $(date) fill monitor ====="
  echo "-- GPU --"; nvidia-smi --query-gpu=index,memory.free,memory.used,utilization.gpu --format=csv,noheader
  echo "-- P1 --"; $PY $REPO/scripts/q_p1_need.py | head -1
  echo "-- P2 plans --"
  for pl in $REPO/scripts/p2_*.json; do
    [ -e "$pl" ] || continue
    echo "  $(basename $pl): $($PY $REPO/scripts/q_plan_need.py $pl)"
  done
  echo "workers P1=$(ps -ef|grep q_p1_fill.py|grep -v grep|wc -l) P2=$(ps -ef|grep q_fill.py|grep -v grep|wc -l)"
  echo "-- real-CUDA scan (empty = clean) --"
  grep -lEi "cpu fallback|cuda not available|cuda unavailable|no cuda-capable" $R/logs/q_p1_fill_s*.log $R/logs/q_fill_*.log 2>/dev/null
} >> $OUT 2>&1
need1=$( $PY $REPO/scripts/q_p1_need.py | head -1 | grep -oE "missing=[0-9]+" | cut -d= -f2 )
n1=$(ps -ef | grep "q_p1_fill.py" | grep -v grep | wc -l)
if [ "${need1:-0}" -gt 0 ] && [ "$n1" -eq 0 ]; then
  echo "$(date) AUTO-REFILL P1: need=$need1" >> $OUT
  mkdir -p /tmp/p1_locks; cd $REPO
  for s in 0 1 2 3 4 5; do setsid nohup $PY $REPO/scripts/q_p1_fill.py $s 6 >> $R/logs/q_p1_fill_s${s}.log 2>&1 & done
fi
for pl in $REPO/scripts/p2_*.json; do
  [ -e "$pl" ] || continue
  tag=$(basename $pl .json)
  needp=$( $PY $REPO/scripts/q_plan_need.py $pl | grep -oE "missing=[0-9]+" | cut -d= -f2 )
  np=$(ps -ef | grep "q_fill.py" | grep -v grep | grep -c "$tag")
  if [ "${needp:-0}" -gt 0 ] && [ "$np" -eq 0 ]; then
    echo "$(date) AUTO-REFILL $tag: need=$needp" >> $OUT
    lk=$($PY -c "import json;print(json.load(open("$pl"))[\"lockdir\"])"); mkdir -p $lk; cd $REPO
    for s in 0 1 2; do setsid nohup $PY $REPO/scripts/q_fill.py $s 3 $pl >> $R/logs/q_fill_${tag}_s${s}.log 2>&1 & done
  fi
done
