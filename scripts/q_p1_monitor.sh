#!/bin/bash
# P1 gap-fill monitor (cron, every 20 min): progress + GPU + real-CUDA scan + auto-refill.
REPO=/home/cunyuliu/rna-ft-eval
R=/mnt/cunyuliu/rna-ft-eval
PY=/home/cunyuliu/llr_env/bin/python
OUT=$R/status/p1_monitor.log
mkdir -p $R/status
{
  echo "===== $(date) P1 monitor ====="
  echo "-- GPU --"; nvidia-smi --query-gpu=index,memory.free,memory.used,utilization.gpu --format=csv,noheader
  echo "-- progress --"; $PY $REPO/scripts/q_p1_need.py
  n=$(ps -ef | grep "q_p1_fill.py" | grep -v grep | wc -l); echo "workers_alive=$n"
  echo "-- real-CUDA scan (empty = clean) --"
  grep -lEi "cpu fallback|cuda not available|cuda unavailable|no cuda-capable" $R/logs/q_p1_fill_s*.log 2>/dev/null
} >> $OUT 2>&1
need=$( $PY $REPO/scripts/q_p1_need.py | head -1 | grep -oE "missing=[0-9]+" | cut -d= -f2 )
n=$(ps -ef | grep "q_p1_fill.py" | grep -v grep | wc -l)
if [ "${need:-0}" -gt 0 ] && [ "$n" -eq 0 ]; then
  echo "$(date) AUTO-REFILL: need=$need workers=0 -> relaunch 6 shards" >> $OUT
  mkdir -p /tmp/p1_locks
  cd $REPO
  for s in 0 1 2 3 4 5; do
    setsid nohup $PY $REPO/scripts/q_p1_fill.py $s 6 >> $R/logs/q_p1_fill_s${s}.log 2>&1 &
  done
fi
