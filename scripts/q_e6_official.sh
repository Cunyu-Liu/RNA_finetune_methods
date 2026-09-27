#!/bin/bash
# Official-family E6 arms (2026-09-27): RiNALMo-mega + RiNALMo-650M × {lora, full@1e-5} × 3 seeds = 12 runs.
# Chained: waits until e6_v2 AND e6_v3 queues both exit, then runs serially on freed cards.
R=/mnt/cunyuliu/rna-ft-eval
PY=/home/cunyuliu/llr_env/bin/python
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
cd /home/cunyuliu/rna-ft-eval
LOG=$R/logs/q_e6_official.log
echo "=== e6off start-wait $(date) ===" >> $LOG

# wait for e6_v2 + e6_v3 to finish (their workers exit)
while true; do
  n=$(ps -eo args | grep -cE "[q]_e6_v2.sh|[q]_e6_v3.sh")
  if [ "$n" -eq 0 ]; then break; fi
  sleep 600
done
echo "=== e6off chains free $(date) ===" >> $LOG

run_cell () {
  local model=$1 strat=$2 seed=$3
  local lr=1e-05
  $PY -m rnafteval.e6_forget --model "$model" --strategy "$strat" \
      --seed "$seed" --lr "$lr" --device "$dev" >> $LOG 2>&1
  echo "[e6off] exit $? $model $strat s$seed $(date +%H:%M)" >> $LOG
}

pick_gpu () {
  nvidia-smi --query-gpu=index,memory.free --format=csv,noheader,nounits | \
  awk -F", " '{ if ($2+0 >= 14000 && $1 < 6) print $1 }' | head -1
}

for cell in "RiNALMo-mega lora 17" "RiNALMo-mega lora 29" "RiNALMo-mega lora 43" \
            "RiNALMo-mega full 17" "RiNALMo-mega full 29" "RiNALMo-mega full 43" \
            "RiNALMo-650M lora 17" "RiNALMo-650M lora 29" "RiNALMo-650M lora 43" \
            "RiNALMo-650M full 17" "RiNALMo-650M full 29" "RiNALMo-650M full 43"; do
  set -- $cell
  while true; do
    dev=$(pick_gpu)
    if [ -n "$dev" ]; then break; fi
    echo "[e6off] wait card for $cell $(date +%H:%M)" >> $LOG
    sleep 300
  done
  run_cell "$1" "$2" "$3"
done
echo "=== e6off DONE $(date) ===" >> $LOG
