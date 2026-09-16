#!/bin/bash
# G5 链: run_rinalmo_tuned2.sh (PID 830478) 排空后启动整卡轮询队列
# (ERNIE lora 种子补齐 + ERNIE/RNA-FM full 矩阵; kill -0 监听具体 PID, 禁 pgrep -f)
cd /home/cunyuliu/rna-ft-eval
PID=830478
while kill -0 $PID 2>/dev/null \
      && tr "\0" " " < /proc/$PID/cmdline 2>/dev/null | grep -q "run_rinalmo_tuned2"; do
  sleep 120
done
bash scripts/run_full_ef_any.sh
