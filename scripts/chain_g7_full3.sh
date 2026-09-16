#!/bin/bash
# G7 链: run_mod_rinalmo_g7.sh (PID 1376693) 排空后接 SpliceBERT full 矩阵
# (kill -0 监听具体 PID + cmdline 校验, 禁 pgrep -f)
cd /home/cunyuliu/rna-ft-eval
PID=1376693
while kill -0 $PID 2>/dev/null \
      && tr "\0" " " < /proc/$PID/cmdline 2>/dev/null | grep -q "run_mod_rinalmo_g7"; do
  sleep 120
done
bash scripts/run_full3_g7.sh
