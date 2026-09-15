#!/bin/bash
cd /home/cunyuliu/rna-ft-eval
while pgrep -f "run_lr_grid.sh 5" > /dev/null; do sleep 120; done
bash scripts/run_lr_grid2.sh 5
