#!/bin/bash
# SSP full-FT tuned 臂补全：ERNIE-RNA / RNA-FM / SpliceBERT x random+family x 3 种子（LR 1e-5，对齐 RiNALMo SSP tuned 协议）
# 口径对齐 q_ssp_generic.sh 正式 SSP run：epochs 3 / n-train 3000 / n-test 500 / batch-size 4
# <model> <gpu>；带 done 跳过
R=/mnt/cunyuliu/rna-ft-eval
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/home/cunyuliu/llr_env/bin/python
MODEL=$1
GPU=$2
TAG=$(echo $MODEL | tr -d "-")
LOG=$R/logs/q_ssp_fulltuned_${TAG}_g${GPU}.log
cd /home/cunyuliu/rna-ft-eval

$PY -c "import torch; assert torch.cuda.is_available()" || exit 2
timeout 300 $PY -c "
import torch
free, _ = torch.cuda.mem_get_info($GPU)
assert free > 2.5e9, 'free %.2fG' % (free/1e9)
print('GPU$GPU OK')" >> $LOG 2>&1 || exit 2

for split in random family; do
  for seed in 17 29 43; do
    MSLUG=$(echo $MODEL | tr -d "-")
    RID=ft_${MSLUG}_secondarystructure_full_s${seed}_${split}_lr1e-05
    D=$($PY -c "
import json
n=0
for l in open(\"$R/ledger.jsonl\"):
    r=json.loads(l)
    if r.get(\"run_id\")==\"$RID\" and r.get(\"status\")==\"done\": n=1
print(n)")
    [ "$D" = "1" ] && { echo "skip $RID (done)" >> $LOG; continue; }
    echo "=== SSP-fulltuned $MODEL $split s$seed GPU$GPU $(date +%T) ===" >> $LOG
    timeout 21600 $PY -m rnafteval.finetune_ssp --model $MODEL \
      --strategy full --seed $seed --split $split --device $GPU --lr 1e-5 \
      --epochs 3 --n-train 3000 --n-test 500 --batch-size 4 >> $LOG 2>&1
    echo "--- exit $? $(date +%T) ---" >> $LOG
  done
done
echo "SSP-FULLTUNED $MODEL DONE $(date)" >> $LOG
