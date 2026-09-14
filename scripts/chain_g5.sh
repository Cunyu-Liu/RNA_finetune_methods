#!/bin/bash
cd /home/cunyuliu/rna-ft-eval
while kill -0 1502028 2>/dev/null; do sleep 120; done
bash scripts/run_queue.sh scripts/queue_gpu5c.txt 5 q_rinalmo_full_g5
