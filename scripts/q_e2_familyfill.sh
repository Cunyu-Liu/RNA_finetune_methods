#!/bin/bash
# 第五波：m6A head-only family 侧（RNA-Sc-10M，E2 对称）+ MRL E2 family 侧（dora/ia3 x micro+10M）
# <gpu1>（m6A）——MRL family 侧另卡；带 done 跳过
R=/mnt/cunyuliu/rna-ft-eval
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/home/cunyuliu/llr_env/bin/python
G1=$1
G2=$2
LOG=$R/logs/q_e2_familyfill_g${G1}_g${G2}.log
cd /home/cunyuliu/rna-ft-eval

$PY -c "import torch; assert torch.cuda.is_available()" || exit 2

# G1: m6A head-only family (RNA-Sc-10M x3)
for S in 17 29 43; do
  RID=ft_rnasc10m_modification_headonly_s${S}_family
  D=$($PY -c "
import json
n=0
for l in open(\"$R/ledger.jsonl\"):
    r=json.loads(l)
    if r.get(\"run_id\")==\"$RID\" and r.get(\"status\")==\"done\": n=1
print(n)")
  [ "$D" = "1" ] && { echo "skip $RID" >> $LOG; continue; }
  echo "=== m6A headonly family RNA-Sc-10M s$S GPU$G1 $(date +%T) ===" >> $LOG
  timeout 14400 $PY -m rnafteval.finetune_base --model RNA-Sc-10M \
    --task modification --strategy head-only --seed $S --split family \
    --device $G1 --epochs 3 --n-train 20000 --batch-size 32 >> $LOG 2>&1
  echo "--- exit $? $(date +%T) ---" >> $LOG
done
echo "M6A-HEADONLY-FAMILY DONE $(date)" >> $LOG

# G2: MRL E2 family 侧 dora/ia3（micro + 10M）
for M in RiNALMo-micro RNA-Sc-10M; do
  MSLUG=$(echo $M | tr -d "-")
  for strat in dora ia3; do
    for S in 17 29 43; do
      RID=ft_${MSLUG}_mrl_${strat}_s${S}_family
      D=$($PY -c "
import json
n=0
for l in open(\"$R/ledger.jsonl\"):
    r=json.loads(l)
    if r.get(\"run_id\")==\"$RID\" and r.get(\"status\")==\"done\": n=1
print(n)")
      [ "$D" = "1" ] && { echo "skip $RID" >> $LOG; continue; }
      echo "=== MRL E2 $M $strat family s$S GPU$G2 $(date +%T) ===" >> $LOG
      timeout 7200 $PY -m rnafteval.finetune_mrl --model $M \
        --strategy $strat --seed $S --split family \
        --device $G2 --epochs 3 --n-train 20000 --batch-size 32 >> $LOG 2>&1
      echo "--- exit $? $(date +%T) ---" >> $LOG
    done
  done
done
echo "MRL-E2-FAMILY DONE $(date)" >> $LOG
