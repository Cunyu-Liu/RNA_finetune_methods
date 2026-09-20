#!/bin/bash
# MRL per-seq 第二任务（C4 对齐）: 5 模型 x {frozen,lora} x {random,family} x 3 种子 = 60 runs
# 协议: epochs 3 / n-train 20000 / bs 32（对齐 m6A 口径）；指标 Pearson r
R=/mnt/cunyuliu/rna-ft-eval
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/home/cunyuliu/llr_env/bin/python
GPU=$1
LOG=$R/logs/q_mrl_c4_g${GPU}.log
cd /home/cunyuliu/rna-ft-eval

# 等 MRL 家族切分生成完成
while [ ! -f $R/data/family_splits/mrl.parquet ]; do
  echo "waiting for mrl family split $(date +%T)" >> $LOG
  sleep 60
done
echo "mrl family split ready $(date +%T)" >> $LOG

$PY -c "import torch; assert torch.cuda.is_available()" || exit 2
timeout 300 $PY -c "
import torch
free, _ = torch.cuda.mem_get_info($GPU)
assert free > 4e9, "free %.2fG" % (free/1e9)
print("GPU$GPU OK")" >> $LOG 2>&1 || exit 2

for M in RiNALMo-micro SpliceBERT ERNIE-RNA RNA-FM RNA-Sc-10M; do
  for strat in frozen lora; do
    for split in random family; do
      for seed in 17 29 43; do
        echo "=== MRL $M $strat s$seed $split GPU$GPU $(date +%T) ===" >> $LOG
        timeout 7200 $PY -m rnafteval.finetune_mrl --model $M \
          --strategy $strat --seed $seed --split $split \
          --device $GPU --epochs 3 --n-train 20000 --batch-size 32 >> $LOG 2>&1
        echo "--- exit $? $(date +%T) ---" >> $LOG
      done
    done
  done
done
echo "MRL-C4 DONE $(date)" >> $LOG
