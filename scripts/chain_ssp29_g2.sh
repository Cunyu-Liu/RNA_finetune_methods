#!/bin/bash
# dev2: lrbest-g2 (PID 3601911) 结束后接 SSP seed29 波（E1 补种子）
cd /home/cunyuliu/rna-ft-eval
while kill -0 3601911 2>/dev/null; do sleep 120; done
bash scripts/run_ssp_wave_seeds.sh 2 29
