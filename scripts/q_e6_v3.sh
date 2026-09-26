#!/bin/bash
# E6-v3 cross-task retention queue (2026-09-27, user-required axis):
# 3 models × {lora, full@tuned} × 3 seeds = 18 runs. Each run = ncRNA finetune (10 ep)
# + 3 cross-task probes (m6A/MRL/SSP, probe head 2k/1ep) pre & post.
R=/mnt/cunyuliu/rna-ft-eval
PY=/home/cunyuliu/llr_env/bin/python
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
cd /home/cunyuliu/rna-ft-eval
LOG=$R/logs/q_e6_v3.log
echo "=== e6v3 start $(date) ===" >> $LOG

run_cell () {
  local model=$1 strat=$2 seed=$3 dev=$4
  $PY -m rnafteval.e6_retention --model "$model" --strategy "$strat" \
      --seed "$seed" --device "$dev" >> $LOG 2>&1
  echo "[e6v3] exit $? $model $strat s$seed $(date +%H:%M)" >> $LOG
}

pick_gpu () {
  nvidia-smi --query-gpu=index,memory.free --format=csv,noheader,nounits | \
  awk -F", " '{ if ($2+0 >= 11000 && $1 < 6) print $1 }' | head -1
}

for cell in "RNA-Sc-10M lora 17" "RNA-Sc-10M lora 29" "RNA-Sc-10M lora 43" \
            "RNA-Sc-10M full 17" "RNA-Sc-10M full 29" "RNA-Sc-10M full 43" \
            "RNA-Sc-30M lora 17" "RNA-Sc-30M lora 29" "RNA-Sc-30M lora 43" \
            "RNA-Sc-30M full 17" "RNA-Sc-30M full 29" "RNA-Sc-30M full 43" \
            "RiNALMo-micro lora 17" "RiNALMo-micro lora 29" "RiNALMo-micro lora 43" \
            "RiNALMo-micro full 17" "RiNALMo-micro full 29" "RiNALMo-micro full 43"; do
  set -- $cell
  while true; do
    G=$(pick_gpu)
    if [ -n "$G" ]; then break; fi
    echo "[e6v3] wait card for $cell $(date +%H:%M)" >> $LOG
    sleep 300
  done
  run_cell "$1" "$2" "$3" "$G"
done
echo "=== e6v3 DONE $(date) ===" >> $LOG
