#!/bin/bash
# G6 链: run_newmodels_seeds_g6.sh (PID 3098539) 排空后接 SpliceBERT full
# family 侧 (GPU 参数化; ledger claim 与 G7 队列自动错峰不重复)
# (kill -0 监听具体 PID, 禁 pgrep -f)
cd /home/cunyuliu/rna-ft-eval
PID=3098539
while kill -0 $PID 2>/dev/null \
      && tr "\0" " " < /proc/$PID/cmdline 2>/dev/null | grep -q "run_newmodels_seeds_g6"; do
  sleep 120
done
bash scripts/run_full3_g7.sh 6
