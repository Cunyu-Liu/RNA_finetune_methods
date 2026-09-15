#!/bin/bash
# GPU2 lrbest (PID 3601911) 结束后: SSP E1 补种子 s43 x random (3 runs)
# s29 全套由 dev5 的 chain_ssp29_g5 (G5, 触发更早) 承担 — 三 session 去重后分工:
#   G5=s29 random+family / G2=s43 random / G7=s43 family, 全 12 runs 恰好一次
# 纪律: kill -0 + /proc cmdline 双校验 (pgrep 壳文本污染已踩坑)
cd /home/cunyuliu/rna-ft-eval
PID=3601911
while kill -0 $PID 2>/dev/null \
      && tr '\0' ' ' < /proc/$PID/cmdline 2>/dev/null | grep -q "chain_g2_lrbest"; do
  sleep 120
done
bash scripts/run_ssp_seed.sh 2 43 random
