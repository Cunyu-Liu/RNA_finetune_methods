#!/bin/bash
# tuned-LR 补跑: RiNALMo m6A full @1e-5 (默认 3e-4 崩到 0.30) 3 seeds x 2 splits
# + SSP full 复核 @1e-5 s17 (默认 0.006 崩)
R=/mnt/cunyuliu/rna-ft-eval
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/home/cunyuliu/llr_env/bin/python
GPU=$1
LOG=$R/logs/q_rinalmo_tuned2.log
cd /home/cunyuliu/rna-ft-eval
for job in "17 random" "29 random" "43 random" "17 family" "29 family" "43 family"; do
  set -- $job; seed=$1; split=$2
  echo "=== RiNALMo m6A full s$seed $split lr1e-5 GPU$GPU $(date +%T) ===" >> $LOG
  timeout 14400 $PY -m rnafteval.finetune_base --model RiNALMo-micro \
    --task modification --strategy full --seed $seed --split $split \
    --device $GPU --lr 1e-5 --epochs 3 --n-train 20000 --batch-size 32 >> $LOG 2>&1
done
echo "=== RiNALMo SSP full s17 random lr1e-5 复核 $(date +%T) ===" >> $LOG
timeout 21600 $PY -m rnafteval.finetune_ssp --model RiNALMo-micro \
  --strategy full --seed 17 --split random --device $GPU \
  --lr 1e-5 --epochs 3 --n-train 3000 --n-test 500 --batch-size 4 >> $LOG 2>&1
echo "RINALMO TUNED2 DONE $(date)" >> $LOG
