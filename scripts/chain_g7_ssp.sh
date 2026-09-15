#!/bin/bash
# GPU7 queue_gpu7e (PID 1521671) 结束后: SSP E1 补种子 s43 x family (3 runs)
# s29 family 由 dev5 G5 链承担, 此处只补 s43 — 去重分工见 chain_g2_ssp 注释
cd /home/cunyuliu/rna-ft-eval
PID=1521671
while kill -0 $PID 2>/dev/null \
      && tr '\0' ' ' < /proc/$PID/cmdline 2>/dev/null | grep -q "run_queue"; do
  sleep 120
done
bash scripts/run_ssp_seed.sh 7 43 family
