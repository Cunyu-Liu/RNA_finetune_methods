#!/bin/bash
# G7 链2: run_full3_g7.sh (PID 1923283) 排空后接 RiNALMo SSP tuned 补齐
# (kill -0 监听具体 PID + cmdline 校验, 禁 pgrep -f)
cd /home/cunyuliu/rna-ft-eval
PID=1923283
while kill -0 $PID 2>/dev/null \
      && tr "\0" " " < /proc/$PID/cmdline 2>/dev/null | grep -q "run_full3_g7"; do
  sleep 120
done
bash scripts/run_ssp_tuned5.sh
