#!/bin/bash
# Big-model FULL-FT backfill (2026-09-28 user decision: 100M gate REMOVED).
# Cells: RiNALMo-mega, RiNALMo-650M, RNA-Sc-650M, AIDO.RNA-1.6B, RiboSpan-1K-40
#        × full @ tuned family LR × ncRNA random+family × 3 seeds = 60 runs.
# Tuned LR (family rule): RiNALMo 1e-5, RNA-Sc 3e-5, AIDO/RiboSpan 3e-5 (no
# family prior -> use conservative 3e-5 + bs 8).
# Memory gates: mega ~14G, 650M ~14G, 1.6B full ~24G (bf16? full-FT 1.6B ~24GB
# fp32 AdamW; use bs 4 if OOM).
R=/mnt/cunyuliu/rna-ft-eval
PY=/home/cunyuliu/llr_env/bin/python
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
cd /home/cunyuliu/rna-ft-eval
LOG=$R/logs/q_full_big.log
echo "=== fullbig start $(date) ===" >> $LOG

spec_lr () {
  case "$1" in
    RiNALMo-*) echo 1e-05 ;;
    RNA-Sc-*)  echo 3e-05 ;;
    *)         echo 3e-05 ;;
  esac
}
spec_need () {
  case "$1" in
    RiNALMo-mega|RNA-Sc-650M|RiNALMo-650M) echo 16 ;;
    *) echo 26 ;;
  esac
}
spec_bs () {
  case "$1" in
    AIDO.RNA-1.6B|RiboSpan-1K-40) echo 4 ;;
    *) echo 8 ;;
  esac
}

run_cell () {
  local model=$1 split=$2 seed=$3 dev=$4
  local lr=$(spec_lr "$model") need=$(spec_need "$model") bs=$(spec_bs "$model")
  if [ "$model" = "RiNALMo-mega" ]; then mod=rnafteval.finetune_one
  elif [ "$model" = "RiNALMo-650M" ]; then mod=rnafteval.finetune_one
  elif [ "$model" = "RNA-Sc-650M" ]; then mod=rnafteval.finetune_one
  else mod=rnafteval.finetune_one; fi
  $PY -m $mod --model "$model" --task noncoding-rna-family \
      --strategy full --seed "$seed" --split "$split" --device "$dev" \
      --lr "$lr" --batch-size "$bs" --epochs 10 >> $LOG 2>&1
  echo "[fullbig] exit $? $model s$seed $split $(date +%H:%M)" >> $LOG
}

pick_gpu () {
  local need=$1
  nvidia-smi --query-gpu=index,memory.free --format=csv,noheader,nounits | \
  awk -F", " -v n="$need" '{ if ($2+0 >= n*1024 && $1 < 6) print $1 }' | head -1
}

for model in RiNALMo-mega RiNALMo-650M RNA-Sc-650M AIDO.RNA-1.6B RiboSpan-1K-40; do
  need=$(spec_need "$model")
  for split in random family; do
    for seed in 17 29 43; do
      att=0
      while [ $att -lt 60 ]; do
        dev=$(pick_gpu $need)
        if [ -n "$dev" ]; then break; fi
        echo "[fullbig] wait card $model s$seed $split $(date +%H:%M)" >> $LOG
        sleep 600
      done
      run_cell "$model" "$split" "$seed" "$dev"
    done
  done
done
echo "=== fullbig DONE $(date) ===" >> $LOG
