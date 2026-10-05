#!/bin/bash
cd /home/cunyuliu/rna-ft-eval
PY=/home/cunyuliu/llr_env/bin/python
MISS=$($PY scripts/q_plan_need.py scripts/p2_gapfill_1005_plan.json 2>/dev/null | grep -oE "missing=[0-9]+" | head -1 | cut -d= -f2)
[ -z "$MISS" ] && MISS=1
[ "$MISS" -eq 0 ] && exit 0
for s in 0 1 2 3; do
  if ! ps -ef | grep -E "[q]_fill\.py $s 4 .*gapfill" | grep -qv grep; then
    setsid nohup $PY scripts/q_fill.py $s 4 scripts/p2_gapfill_1005_plan.json </dev/null >>/dev/null 2>&1 &
    echo "[$(date)] restarted gapfill s$s (missing=$MISS)" >> /mnt/cunyuliu/rna-ft-eval/logs/keepalive.log
  fi
done
