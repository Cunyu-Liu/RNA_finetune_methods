#!/bin/bash
# 第二轮守护链: 等全部在跑队列排空后终刷十产物
# 监听 PID 写死（派发时查实填入, 全程 kill -0, 禁 pgrep -f）:
#   G1 tuned-splice 1876363 / G2 tuned-ernie 1892631 /
#   G5 E3-RNA-Sc 1905764 / G6 newmodels 3098539 /
#   G7 e3-tuned-full E3TUNED_PID（由派发方回填）
cd /home/cunyuliu/rna-ft-eval
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
PY=/home/cunyuliu/llr_env/bin/python
LOG=/mnt/cunyuliu/rna-ft-eval/logs/chain_final_refresh2.log
E3TUNED_PID=1976066

wait_pid() {
  local pid=$1 name=$2
  while kill -0 $pid 2>/dev/null; do
    sleep 300
  done
  echo "$name (PID $pid) drained $(date +%T)" >> $LOG
}

wait_pid 1876363 "G1 tuned-splice"
wait_pid 1892631 "G2 tuned-ernie"
wait_pid 1905764 "G5 E3-rnasc"
wait_pid 3098539 "G6 newmodels"
wait_pid $E3TUNED_PID "G7 e3-tuned-full"

echo "ALL ROUND-2 QUEUES DRAINED $(date) — final refresh" >> $LOG
$PY -m rnafteval.export_c4 --out /mnt/cunyuliu/rna-ft-eval/status/c4_table.md >> $LOG 2>&1
$PY -m rnafteval.export_e2 >> $LOG 2>&1
$PY -m rnafteval.stats >> $LOG 2>&1
$PY -m rnafteval.figures --out /mnt/cunyuliu/rna-ft-eval/status/figs >> $LOG 2>&1
$PY -m rnafteval.export_resources >> $LOG 2>&1
$PY -m rnafteval.export_lr_grid >> $LOG 2>&1
$PY -m rnafteval.export_splits >> $LOG 2>&1
$PY -m rnafteval.export_leakage >> $LOG 2>&1
$PY -m rnafteval.export_e3 >> $LOG 2>&1
$PY -m rnafteval.fig_e3 >> $LOG 2>&1
echo "ROUND-2 FINAL REFRESH DONE (10 artifacts) $(date)" >> $LOG
