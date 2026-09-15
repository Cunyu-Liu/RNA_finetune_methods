#!/bin/bash
# E2 PEFT 横评: RiNALMo-micro ncRNA random x {dora, ia3, head-only} x 3 seeds
# (lora/full 已有 formal 数据; prefix 依赖不兼容见 project_rules)
R=/mnt/cunyuliu/rna-ft-eval
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/home/cunyuliu/llr_env/bin/python
GPU=$1
LOG=$R/logs/q_e2_peft_g$GPU.log
cd /home/cunyuliu/rna-ft-eval
for job in "dora 17" "dora 29" "dora 43" "ia3 17" "ia3 29" "ia3 43" "head-only 17" "head-only 29" "head-only 43"; do
  set -- $job; strat=$1; seed=$2
  echo "=== RiNALMo $strat s$seed random GPU$GPU $(date +%T) ===" >> $LOG
  timeout 14400 $PY -m rnafteval.finetune_one --model RiNALMo-micro \
    --task noncoding-rna-family --strategy $strat --seed $seed --split random \
    --device $GPU --epochs 10 --batch-size 8 >> $LOG 2>&1
done
echo "E2 PEFT GPU$GPU DONE $(date)" >> $LOG
