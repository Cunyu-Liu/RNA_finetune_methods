#!/bin/bash
# E6-v2 task-origin forgetting queue (2026-09-27): fill the differential-forgetting gap.
# Cells: 3 models (10M/30M/micro) × {ncRNA-start (exists in v1 for 10M/30M; micro exists),
#        m6A-start} × {lora, full@tuned} × 3 seeds. We only need to RUN m6A-start cells:
#        v1 already covers ncRNA-start for these models.
# m6A-start cells: 3 models × 2 strategies × 3 seeds = 18 runs (~1-3h each on 1 GPU).
# GPU: use idle MIG? No — needs 10-24GB. Run on GPU5/2/4 when free <3GB? Use free-slot detection.
R=/mnt/cunyuliu/rna-ft-eval
PY=/home/cunyuliu/llr_env/bin/python
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
cd /home/cunyuliu/rna-ft-eval
LOG=$R/logs/q_e6_v2.log
echo "=== e6v2 start $(date) ===" >> $LOG

run_cell () {
  local model=$1 strat=$2 seed=$3 dev=$4
  local lr
  if [ "$strat" = "full" ]; then
    if [ "$model" = "RiNALMo-micro" ]; then lr=1e-05; else lr=3e-05; fi
  else lr=3e-04; fi
  $PY -m rnafteval.e6_forget_task --model "$model" --task modification \
      --strategy "$strat" --seed "$seed" --lr "$lr" --device "$dev" \
      >> $LOG 2>&1
  echo "[e6v2] exit $? $model $strat s$seed $(date +%H:%M)" >> $LOG
}

# pick GPUs with >=12GB free (full@30M needs ~13GB; lora ~10GB)
pick_gpu () {
  nvidia-smi --query-gpu=index,memory.free --format=csv,noheader,nounits | \
  awk -F", " '{ if ($2+0 >= 12000 && $1 < 6) print $1 }' | head -1
}

# Wait for AIDO/RiboSpan queue to drain enough that a card has room; poll.
for cell in "RNA-Sc-10M lora 17" "RNA-Sc-10M lora 29" "RNA-Sc-10M lora 43" \
            "RNA-Sc-10M full 17" "RNA-Sc-10M full 29" "RNA-Sc-10M full 43" \
            "RiNALMo-micro lora 17" "RiNALMo-micro lora 29" "RiNALMo-micro lora 43" \
            "RiNALMo-micro full 17" "RiNALMo-micro full 29" "RiNALMo-micro full 43" \
            "RNA-Sc-30M lora 17" "RNA-Sc-30M lora 29" "RNA-Sc-30M lora 43" \
            "RNA-Sc-30M full 17" "RNA-Sc-30M full 29" "RNA-Sc-30M full 43"; do
  set -- $cell
  while true; do
    G=$(pick_gpu)
    if [ -n "$G" ]; then break; fi
    echo "[e6v2] wait card for $cell $(date +%H:%M)" >> $LOG
    sleep 300
  done
  run_cell "$1" "$2" "$3" "$G"
done
echo "=== e6v2 DONE $(date) ===" >> $LOG
