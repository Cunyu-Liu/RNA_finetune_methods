#!/bin/bash
# FINAL refresh: fires once when the 3 pending-fill plans (tunedmissing/fullbig/gridbest)
# are all complete. Independent marker so the legacy .refresh_after_p1p2 run (Oct 2,
# before these plans existed) does not block the final re-export.
REPO=/home/cunyuliu/rna-ft-eval
R=/mnt/cunyuliu/rna-ft-eval
PY=/home/cunyuliu/llr_env/bin/python
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
MARK=$R/status/.refresh_final_1005
LOG=$R/status/refresh.log
[ -f "$MARK" ] && exit 0
allzero=1
for pl in p2_tunedmissing_plan p2_fullbig_formal_plan p2_gridbest_fill_plan p2_ss650_gridbest_plan; do
  n=$( $PY $REPO/scripts/q_plan_need.py $REPO/scripts/$pl.json 2>/dev/null | grep -oE "missing=[0-9]+" | head -1 | cut -d= -f2 )
  [ -z "$n" ] && n=1
  [ "$n" -ne 0 ] && allzero=0
done
nw=$(ps -ef | grep -E "[q]_fill\.py" | wc -l)
[ "$nw" -ne 0 ] && allzero=0
[ "$allzero" -ne 1 ] && exit 0
echo "===== $(date) FINAL REFRESH (3 fill plans drained) =====" >> $LOG
cd $REPO
for mod in export_c4 export_e2 export_e3 export_e6 export_randinit export_e6v2 export_e6v3 export_collapse export_e6_official export_resources export_resources_matrix export_splits export_leakage export_lr_grid; do
  echo "--- $mod ---" >> $LOG
  $PY -m rnafteval.$mod >> $LOG 2>&1 && echo "ok $mod" >> $LOG || echo "FAIL $mod" >> $LOG
done
echo "--- grid_audit ---" >> $LOG
$PY -m rnafteval.export_grid_audit --plan $REPO/scripts/p2_grid_fill_plan.json >> $LOG 2>&1 && echo "ok grid_audit" >> $LOG || echo "FAIL grid_audit" >> $LOG
echo "--- stats + decision_tree ---" >> $LOG
$PY -m rnafteval.stats >> $LOG 2>&1 && echo "ok stats" >> $LOG || echo "FAIL stats" >> $LOG
$PY -m rnafteval.decision_tree >> $LOG 2>&1 && echo "ok decision_tree" >> $LOG || echo "FAIL decision_tree" >> $LOG
echo "--- figures ---" >> $LOG
$PY -m rnafteval.figures --out $R/status/figs >> $LOG 2>&1 && echo "ok figures" >> $LOG || echo "FAIL figures" >> $LOG
$PY -m rnafteval.fig_resources >> $LOG 2>&1 && echo "ok fig_resources" >> $LOG || echo "FAIL fig_resources" >> $LOG
$PY -m rnafteval.fig_c5b >> $LOG 2>&1 && echo "ok fig_c5b" >> $LOG || echo "FAIL fig_c5b" >> $LOG
$PY -m rnafteval.fig_e6 >> $LOG 2>&1 && echo "ok fig_e6" >> $LOG || echo "FAIL fig_e6" >> $LOG
touch $MARK
echo "===== final refresh done $(date) =====" >> $LOG
