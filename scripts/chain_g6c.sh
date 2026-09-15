#!/bin/bash
cd /home/cunyuliu/rna-ft-eval
while kill -0 2040999 2>/dev/null; do sleep 120; done
bash scripts/run_queue.sh scripts/queue_gpu6c.txt 6 q_rnasc_seeds_g6
