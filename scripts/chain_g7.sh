#!/bin/bash
cd /home/cunyuliu/rna-ft-eval
while kill -0 1238673 2>/dev/null; do sleep 120; done
bash scripts/run_queue.sh scripts/queue_gpu7e.txt 7 q_rinalmo_seeds_g7
