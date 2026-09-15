#!/bin/bash
# 等 GPU6 lrbest 队列 (PID 3437317, run_rinalmo_lrbest.sh 6) 结束后:
# 新模型维度首探 ERNIE-RNA/RNA-FM/SpliceBERT x ncrna x frozen/lora x s17 random
# (GPU6 为 MIG 4.75G 切片, 只排 frozen/lora 防 OOM; full 待整卡恢复或换卡)
cd /home/cunyuliu/rna-ft-eval
PID=3437317
while kill -0 $PID 2>/dev/null \
      && tr '\0' ' ' < /proc/$PID/cmdline 2>/dev/null | grep -q "run_rinalmo_lrbest"; do
  sleep 120
done
bash scripts/run_queue.sh scripts/queue_gpu6f.txt 6 q_newmodels_g6
