#!/bin/bash
# 第六波：剩余 ASYM 精确补齐
# 1) ncRNA 10M head-only random s29/s43（2 runs）
# 2) ncRNA RNA-Sc-10M dora/ia3 family（E2 对称，6 runs）
# 3) ncRNA micro dora/ia3 family（6 runs）
# <gpu1> <gpu2>；带 done 跳过
R=/mnt/cunyuliu/rna-ft-eval
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/home/cunyuliu/llr_env/bin/python
G1=$1
G2=$2
LOG=$R/logs/q_wave6_g${G1}_g${G2}.log
cd /home/cunyuliu/rna-ft-eval

$PY -c "import torch; assert torch.cuda.is_available()" || exit 2

skip_if_done() {
  RID=$1
  D=$($PY -c "
import json
n=0
for l in open(\"$R/ledger.jsonl\"):
    r=json.loads(l)
    if r.get(\"run_id\")==\"$RID\" and r.get(\"status\")==\"done\": n=1
print(n)")
  [ "$D" = "1" ]
}

for S in 29 43; do
  RID=ft_rnasc10m_noncodingrnafamily_headonly_s${S}_random
  skip_if_done $RID && { echo "skip $RID" >> $LOG; continue; }
  echo "=== 10M headonly random s$S GPU$G1 $(date +%T) ===" >> $LOG
  timeout 7200 $PY -m rnafteval.finetune_one --model RNA-Sc-10M \
    --task noncoding-rna-family --strategy head-only --seed $S --split random \
    --device $G1 --epochs 10 >> $LOG 2>&1
  echo "--- exit $? $(date +%T) ---" >> $LOG
done

for strat in dora ia3; do
  for S in 17 29 43; do
    RID=ft_rnasc10m_noncodingrnafamily_${strat}_s${S}_family
    skip_if_done $RID && { echo "skip $RID" >> $LOG; continue; }
    echo "=== 10M $strat family s$S GPU$G1 $(date +%T) ===" >> $LOG
    timeout 14400 $PY -m rnafteval.finetune_one --model RNA-Sc-10M \
      --task noncoding-rna-family --strategy $strat --seed $S --split family \
      --device $G1 --epochs 10 >> $LOG 2>&1
    echo "--- exit $? $(date +%T) ---" >> $LOG
  done
done
echo "WAVE6-G1 DONE $(date)" >> $LOG

for strat in dora ia3; do
  for S in 17 29 43; do
    RID=ft_rinalmomicro_noncodingrnafamily_${strat}_s${S}_family
    skip_if_done $RID && { echo "skip $RID" >> $LOG; continue; }
    echo "=== micro $strat family s$S GPU$G2 $(date +%T) ===" >> $LOG
    timeout 14400 $PY -m rnafteval.finetune_one --model RiNALMo-micro \
      --task noncoding-rna-family --strategy $strat --seed $S --split family \
      --device $G2 --epochs 10 >> $LOG 2>&1
    echo "--- exit $? $(date +%T) ---" >> $LOG
  done
done
echo "WAVE6-G2 DONE $(date)" >> $LOG
