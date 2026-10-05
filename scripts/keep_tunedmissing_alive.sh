#!/bin/bash
# Keep P2 fill workers alive ONLY while their plan still has missing cells.
# Covers tunedmissing (6 shards) + fullbig/gridbest (single-shard restart).
# When missing=0 workers exit and this script does nothing, so q_refresh_when_done
# (which requires zero live fill workers) can trigger unimpeded.
cd /home/cunyuliu/rna-ft-eval
PY=/home/cunyuliu/llr_env/bin/python
for plan in p2_tunedmissing_plan p2_fullbig_formal_plan p2_gridbest_fill_plan; do
  MISS=$($PY scripts/q_plan_need.py scripts/$plan.json 2>/dev/null | grep -oE "missing=[0-9]+" | head -1 | cut -d= -f2)
  [ -z "$MISS" ] && MISS=1
  [ "$MISS" -eq 0 ] && continue
  for s in 0 1 2 3 4 5; do
    if ! ps -ef | grep -E "[q]_fill\.py $s 6 .*$plan" | grep -qv grep; then
      setsid nohup $PY scripts/q_fill.py $s 6 scripts/$plan.json </dev/null >>/dev/null 2>&1 &
      echo "[$(date)] restarted $plan s$s (missing=$MISS)" >> /mnt/cunyuliu/rna-ft-eval/logs/keepalive.log
    fi
  done
done
