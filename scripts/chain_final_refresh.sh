#!/bin/bash
# 守护链: 四队列 (G5 full_ef 2015376 / G7 full3 1923283 / G6 seeds 3098539 /
# SSP tuned5 待启动, 由 chain_g7_ssptuned 2192474 接续) 全部排空后,
# 自动刷新 C4/E2/stats/figures 终版产物 (kill -0 监听, 禁 pgrep -f)
cd /home/cunyuliu/rna-ft-eval
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
PY=/home/cunyuliu/llr_env/bin/python
LOG=/mnt/cunyuliu/rna-ft-eval/logs/chain_final_refresh.log

wait_pid() {
  local pid=$1 name=$2
  while kill -0 $pid 2>/dev/null; do
    sleep 300
  done
  echo "$name (PID $pid) drained $(date +%T)" >> $LOG
}

wait_pid 2015376 "G5 full_ef_any"
wait_pid 1923283 "G7 full3"
wait_pid 3098539 "G6 newmodels_seeds"
wait_pid 2192474 "chain_g7_ssptuned"

echo "ALL QUEUES DRAINED $(date) — refreshing artifacts" >> $LOG
$PY -m rnafteval.export_c4 --out /mnt/cunyuliu/rna-ft-eval/status/c4_table.md >> $LOG 2>&1
$PY -m rnafteval.export_e2 >> $LOG 2>&1
$PY -m rnafteval.stats >> $LOG 2>&1
$PY -m rnafteval.figures --out /mnt/cunyuliu/rna-ft-eval/status/figs >> $LOG 2>&1
$PY -m rnafteval.export_resources >> $LOG 2>&1
$PY -m rnafteval.export_lr_grid >> $LOG 2>&1
$PY -m rnafteval.export_splits >> $LOG 2>&1
$PY -m rnafteval.export_leakage >> $LOG 2>&1
echo "FINAL REFRESH DONE $(date)" >> $LOG
