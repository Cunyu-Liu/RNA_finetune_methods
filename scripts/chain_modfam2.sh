#!/bin/bash
cd /home/cunyuliu/rna-ft-eval
while pgrep -f "run_queue.sh scripts/queue_fill_e1_g2.txt" > /dev/null; do sleep 120; done
bash scripts/run_mod_family2.sh
