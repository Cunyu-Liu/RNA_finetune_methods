#!/bin/bash
# 6 号审计后继：ncRNA lora family 剩余档（1M 已完成 3/3，30M/100M 跳过 done）→ 10M/30M/100M 若 done 缺则补
# 实际上 10M/30M/100M done 已齐，此链改为兜底重扫 + mega full family e33000 对照补充（已有）——
# 本队列改为： RiNALMo-micro head-only family 补 2 种子（s29/s43，缺口见 etc_audit ASYM head-only random=3 family=1）
R=/mnt/cunyuliu/rna-ft-eval
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/home/cunyuliu/llr_env/bin/python
GPU=$1
LOG=$R/logs/q_micro_headonly_fam_g${GPU}.log
cd /home/cunyuliu/rna-ft-eval

$PY -c "import torch; assert torch.cuda.is_available()" || exit 2
for seed in 29 43; do
  RID=ft_rinalmomicro_noncodingrnafamily_headonly_s${seed}_family
  D=$($PY -c "
import json
n=0
for l in open(\"$R/ledger.jsonl\"):
    r=json.loads(l)
    if r.get(\"run_id\")==\"$RID\" and r.get(\"status\")==\"done\": n=1
print(n)")
  [ "$D" = "1" ] && { echo "skip $RID" >> $LOG; continue; }
  echo "=== micro head-only family s$seed GPU$GPU $(date +%T) ===" >> $LOG
  timeout 7200 $PY -m rnafteval.finetune_one --model RiNALMo-micro \
    --task noncoding-rna-family --strategy head-only --seed $seed --split family \
    --device $GPU --epochs 10 >> $LOG 2>&1
  echo "--- exit $? $(date +%T) ---" >> $LOG
done
echo "MICRO-HEADONLY-FAM DONE $(date)" >> $LOG
