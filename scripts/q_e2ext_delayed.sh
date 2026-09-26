#!/bin/bash
# E2-ext delayed launcher: wait until AIDO/RiboSpan queues (p2_*_plan) fully exit,
# then launch the hardened q_fill.py with the e2ext plan (24 runs, done-skip).
PY=/home/cunyuliu/llr_env/bin/python
cd /home/cunyuliu/rna-ft-eval
while true; do
  n=$(ps -eo args | grep "[q]_fill.py" | grep -c "p2_")
  if [ "$n" -eq 0 ]; then break; fi
  sleep 600
done
nohup setsid $PY scripts/q_fill.py 0 1 scripts/p2_e2ext_plan.json > /dev/null 2>&1 < /dev/null &
echo "launched e2ext at $(date)" >> /mnt/cunyuliu/rna-ft-eval/logs/q_e6_v2.log
