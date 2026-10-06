#!/bin/bash
# 1006c: final-close monitor — when tunedmissing + ranksweep drain to 0 missing,
# trigger full exporter-chain refresh once (marker-guarded), then report.
R=/mnt/cunyuliu/rna-ft-eval
C=/home/cunyuliu/rna-ft-eval
PY=/home/cunyuliu/llr_env/bin/python
LOG=$R/logs/final_close_monitor.log
ts() { date "+%m-%d %H:%M:%S"; }
MISS_TM=$($PY $C/scripts/q_plan_need.py $C/scripts/p2_tunedmissing_plan.json 2>/dev/null | head -1)
MISS_RS=$($PY $C/scripts/q_plan_need.py $C/scripts/p2_ranksweep_1005_plan.json 2>/dev/null | head -1)
echo "[$(ts)] tm=$MISS_TM rs=$MISS_RS" >> $LOG
if [ -f $R/.refresh_final_1006c ]; then exit 0; fi
TM_OK=$(echo "$MISS_TM" | grep -c "missing=0")
RS_OK=$(echo "$MISS_RS" | grep -c "missing=0")
if [ "$TM_OK" = "1" ] && [ "$RS_OK" = "1" ]; then
  echo "[$(ts)] ALL DRAINED — launching full refresh chain" >> $LOG
  bash $C/scripts/q_refresh_final.sh >> $R/logs/refresh_final_1006c.log 2>&1
  echo "[$(ts)] refresh chain launched" >> $LOG
  touch $R/.refresh_final_1006c
fi
