#!/bin/bash
# Auto-refresh product chain once P1 + all P2 plans have no missing cells.
# Idempotent: runs once, guarded by a marker. cron: every 20 min.
REPO=/home/cunyuliu/rna-ft-eval
R=/mnt/cunyuliu/rna-ft-eval
PY=/home/cunyuliu/llr_env/bin/python
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
MARK=$R/status/.refresh_after_p1p2
LOG=$R/status/refresh.log
[ -f "$MARK" ] && exit 0
need1=$( $PY $REPO/scripts/q_p1_need.py | head -1 | grep -oE "missing=[0-9]+" | cut -d= -f2 )
allzero=1
[ "${need1:-1}" -ne 0 ] && allzero=0
for pl in $REPO/scripts/p2_*.json; do
  [ -e "$pl" ] || continue
  n=$( $PY $REPO/scripts/q_plan_need.py "$pl" | grep -oE "missing=[0-9]+" | cut -d= -f2 )
  [ "${n:-1}" -ne 0 ] && allzero=0
done
# also require no fill workers alive (queues fully drained)
nw=$(ps -ef | grep -E "[q]_p1_fill.py|[q]_fill.py" | wc -l)
[ "$nw" -ne 0 ] && allzero=0
[ "$allzero" -ne 1 ] && exit 0
echo "===== $(date) ALL QUEUES DONE -> refresh product chain =====" >> $LOG
cd $REPO
for mod in export_c4 export_e2 export_e3 export_e6 export_resources export_resources_matrix export_splits export_leakage export_lr_grid stats; do
  echo "--- $mod ---" >> $LOG
  $PY -m rnafteval.$mod >> $LOG 2>&1 && echo "ok $mod" >> $LOG || echo "FAIL $mod" >> $LOG
done
echo "--- figures ---" >> $LOG
$PY -m rnafteval.figures --out $R/status/figs >> $LOG 2>&1 && echo "ok figures" >> $LOG || echo "FAIL figures" >> $LOG
$PY -m rnafteval.fig_resources >> $LOG 2>&1 && echo "ok fig_resources" >> $LOG || echo "FAIL fig_resources" >> $LOG
$PY -m rnafteval.fig_c5b >> $LOG 2>&1 && echo "ok fig_c5b" >> $LOG || echo "FAIL fig_c5b" >> $LOG
$PY -m rnafteval.fig_e6 >> $LOG 2>&1 && echo "ok fig_e6" >> $LOG || echo "FAIL fig_e6" >> $LOG
touch $MARK
echo "===== refresh done $(date) =====" >> $LOG
