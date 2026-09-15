#!/bin/bash
# G5 链: run_ssp_rinalmo_full_seeds.sh (PID 630606) 排空后接 ERNIE lora family
# + RiNALMo modification full 矩阵 (kill -0 监听具体 PID, 禁 pgrep -f)
cd /home/cunyuliu/rna-ft-eval
PID=630606
while kill -0 $PID 2>/dev/null \
      && tr "\0" " " < /proc/$PID/cmdline 2>/dev/null | grep -q "run_ssp_rinalmo_full_seeds"; do
  sleep 120
done
bash scripts/run_g5_ernie_mod.sh 5
