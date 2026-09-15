#!/bin/bash
# dev6: lrbest-g6 (PID 3437317) 结束后接 SSP seed43 波（E1 补种子）
cd /home/cunyuliu/rna-ft-eval
while kill -0 3437317 2>/dev/null; do sleep 120; done
bash scripts/run_ssp_wave_seeds.sh 6 43
