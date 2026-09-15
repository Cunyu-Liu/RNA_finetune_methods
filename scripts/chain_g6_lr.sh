#!/bin/bash
cd /home/cunyuliu/rna-ft-eval
while pgrep -f "run_ssp_wave3.sh 6" > /dev/null; do sleep 180; done
bash scripts/run_rinalmo_lrbest.sh 6
