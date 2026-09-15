#!/bin/bash
# dev5: LR 网格 phase1 (PID 3043041) 结束后接 SSP seed29 波（E1 补种子）
# 注：photon 网格 phase2 由 1521671 之外的 2791607 (chain_lr2) 接续，不冲突
cd /home/cunyuliu/rna-ft-eval
while kill -0 3043041 2>/dev/null; do sleep 120; done
bash scripts/run_ssp_wave_seeds.sh 5 29
