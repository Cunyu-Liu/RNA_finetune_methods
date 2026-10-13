#!/bin/bash
# 1016: keepalive for mega E3 + bigtail plans (worker death -> re-dispatch)
# cron */10; created 2026-10-13 (quota-fixed rewrite)
R=/mnt/cunyuliu/rna-ft-eval
cd /home/cunyuliu/rna-ft-eval
PY=/home/cunyuliu/llr_env/bin/python
LOG=$R/logs/keepalive_1016.log

MISSING=$($PY /home/cunyuliu/rna-ft-eval/scripts/audit_1016.py)
MEGA=$(pgrep -fc "q_fill.py.*p2_1016_mega_e3_plan")
BIG=$(pgrep -fc "q_fill.py.*p2_1016_bigtail")
echo "$(date "+%m-%d %H:%M") 1016 missing=$MISSING mega_workers=$MEGA bigtail_workers=$BIG" >> $LOG
if [ "$MISSING" -gt 0 ]; then
  if [ "$MEGA" -lt 4 ]; then
    for s in $(seq 0 3); do
      if ! pgrep -f "q_fill.py $s 4 scripts/p2_1016_mega_e3" > /dev/null; then
        setsid nohup $PY scripts/q_fill.py $s 4 scripts/p2_1016_mega_e3_plan.json > /dev/null 2>&1 &
        echo "$(date "+%m-%d %H:%M") restarted mega s$s" >> $LOG
      fi
    done
  fi
  if [ "$BIG" -lt 4 ]; then
    for s in $(seq 0 3); do
      if ! pgrep -f "q_fill.py $s 4 scripts/p2_1016_bigtail" > /dev/null; then
        setsid nohup $PY scripts/q_fill.py $s 4 scripts/p2_1016_bigtail_plan.json > /dev/null 2>&1 &
        echo "$(date "+%m-%d %H:%M") restarted bigtail s$s" >> $LOG
      fi
    done
  fi
fi
