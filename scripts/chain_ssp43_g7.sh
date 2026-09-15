#!/bin/bash
# dev7: q_rinalmo_seeds_g7 队列 (PID 1521671) 结束后接 SSP seed43 波（E1 补种子）
cd /home/cunyuliu/rna-ft-eval
while kill -0 1521671 2>/dev/null; do sleep 120; done
bash scripts/run_ssp_wave_seeds.sh 7 43
