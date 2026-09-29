#!/bin/bash
# 新臂分析链定时刷新（0929）：6 导出器每 30 分钟重跑一次，status/*.md 始终反映最新落格。
# 用途：训练过程记录自动化（[PENDING] 标记自动翻转为实数）；P4 取表即用。
R=/mnt/cunyuliu/rna-ft-eval
PY=/home/cunyuliu/llr_env/bin/python
export PYTHONPATH=$R/pypath:/home/cunyuliu/rna-ft-eval
cd /home/cunyuliu/rna-ft-eval
LOG=$R/logs/refresh_new_arms.log
echo "=== refresh $(date) ===" >> $LOG
for m in export_randinit export_e6v2 export_e6v3 export_collapse export_e6_official; do
  $PY -m rnafteval.$m >> $LOG 2>&1
done
# grid audit 需要 plan（默认路径在 code 仓）
$PY -m rnafteval.export_grid_audit --plan /home/cunyuliu/rna-ft-eval/scripts/p2_grid_fill_plan.json >> $LOG 2>&1
echo "=== done $(date) ===" >> $LOG