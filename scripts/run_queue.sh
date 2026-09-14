#!/bin/bash
# 任务队列 runner: 读取任务列表文件, 逐个执行 finetune_one, 指定 GPU
# 用法: run_queue.sh <queue_file> <gpu_id> <logname>
# queue_file 每行: <model> <task> <strategy> <seed> <split> [batch_size]
QF=$1; GPU=$2; LOGNAME=$3
R=/mnt/cunyuliu/rna-ft-eval
export HF_ENDPOINT=https://hf-mirror.com HF_HOME=/mnt/cunyuliu/hf_home
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/home/cunyuliu/llr_env/bin/python
cd /home/cunyuliu/rna-ft-eval

while read -r model task strat seed split bs; do
  [ -z "$model" ] && continue
  echo "=== $model $task $strat s$seed $split bs=$bs GPU$GPU $(date +%T) ===" >> $R/logs/$LOGNAME.log
  timeout 14400 $PY -m rnafteval.finetune_one --model $model --task $task \
    --strategy $strat --seed $seed --split $split --device $GPU \
    --epochs 10 --batch-size ${bs:-16} >> $R/logs/$LOGNAME.log 2>&1
  echo "--- exit $? $(date +%T) ---" >> $R/logs/$LOGNAME.log
done < "$QF"
echo "QUEUE $LOGNAME DONE $(date)" >> $R/logs/$LOGNAME.log
