#!/bin/bash
# G7 chain_g7_ssp (PID 3997155) 排空后: RNA-Sc full s29 random + RiNALMo SSP 种子波
cd /home/cunyuliu/rna-ft-eval
PID=3997155
while kill -0 $PID 2>/dev/null \
      && tr "\0" " " < /proc/$PID/cmdline 2>/dev/null | grep -q "chain_g7_ssp"; do
  sleep 120
done
bash scripts/run_ssp_fill_g7.sh 7
