#!/bin/bash
# 等 GPU2 lrbest 队列 (PID 3601911, 2026-09-15 14:16 实例) 结束后:
# SSP E1 补种子 s29/s43 x random (6 runs, 与 G7 family 半边并行)
# 纪律: kill -0 + /proc cmdline 双校验, 不用 pgrep -f (壳文本污染 13:35 已踩坑 x2)
cd /home/cunyuliu/rna-ft-eval
PID=3601911
while kill -0 $PID 2>/dev/null \
      && tr '\0' ' ' < /proc/$PID/cmdline 2>/dev/null | grep -q "chain_g2_lrbest"; do
  sleep 120
done
bash scripts/run_ssp_seed.sh 2 29 random
bash scripts/run_ssp_seed.sh 2 43 random
