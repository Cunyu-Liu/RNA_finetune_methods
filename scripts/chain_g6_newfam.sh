#!/bin/bash
# G6 MIG 排空后: 新模型 family 切分首探 (frozen/lora x s17)
# (MIG 4.75G 不排 full; 已有 random 首探 run 在跑)
cd /home/cunyuliu/rna-ft-eval
PID=850663
while kill -0 $PID 2>/dev/null \
      && tr "\0" " " < /proc/$PID/cmdline 2>/dev/null | grep -q "run_newmodels"; do
  sleep 120
done
bash scripts/run_queue.sh scripts/queue_gpu6g.txt 6 q_newfam_g6
