#!/bin/bash
# G5 整卡排空后(SSP s29 波+LR 网格): RiNALMo-micro SSP full x (random,family) s17
# E1 缺口: RiNALMo SSP 只有 frozen/lora, full 两 split 均缺 (MIG 装不下, 需整卡)
cd /home/cunyuliu/rna-ft-eval
PID=320118
while kill -0 $PID 2>/dev/null \
      && tr "\0" " " < /proc/$PID/cmdline 2>/dev/null | grep -q "run_ssp_wave_seeds"; do
  sleep 120
done
bash scripts/run_ssp_rinalmo_full.sh 5
