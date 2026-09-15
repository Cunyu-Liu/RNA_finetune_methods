#!/bin/bash
# 等 mod_family2 (PID 由 pgrep 指向真实进程) 结束后跑 lrbest random 三种子
cd /home/cunyuliu/rna-ft-eval
while pgrep -x -f "bash scripts/run_mod_family2.sh" >/dev/null 2>&1 || pgrep -x -f "bash scripts/run_mod_family2.sh " >/dev/null 2>&1; do sleep 120; done
R=/mnt/cunyuliu/rna-ft-eval
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/home/cunyuliu/llr_env/bin/python
LOG=$R/logs/q_lrbest_g2.log
for job in "17 random" "29 random" "43 random"; do
  set -- $job; seed=$1; split=$2
  echo "=== RiNALMo full s$seed $split lr1e-5 GPU2 $(date +%T) ===" >> $LOG
  timeout 14400 $PY -m rnafteval.finetune_one --model RiNALMo-micro \
    --task noncoding-rna-family --strategy full --seed $seed --split $split \
    --device 2 --lr 1e-5 --epochs 10 --batch-size 8 >> $LOG 2>&1
done
echo "LRBEST G2 DONE $(date)" >> $LOG
