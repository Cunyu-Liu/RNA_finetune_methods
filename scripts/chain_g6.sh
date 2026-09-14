#!/bin/bash
cd /home/cunyuliu/rna-ft-eval
while kill -0 839182 2>/dev/null; do sleep 120; done
bash scripts/run_queue.sh scripts/queue_gpu6b.txt 6 q_family_b
