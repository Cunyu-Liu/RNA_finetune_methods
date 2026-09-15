#!/bin/bash
# G5 chain_g5_rsspf (PID 1317267) 排空后: RiNALMo SSP full s29/s43 x 两切分
cd /home/cunyuliu/rna-ft-eval
PID=1317267
while kill -0 $PID 2>/dev/null \
      && tr "\0" " " < /proc/$PID/cmdline 2>/dev/null | grep -q "chain_g5_rsspf"; do
  sleep 120
done
bash scripts/run_ssp_rinalmo_full_seeds.sh 5
