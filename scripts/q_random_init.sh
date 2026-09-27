#!/bin/bash
# Random-init control arm (2026-09-28 user decision, NucleicBERT-style gap design):
# 3 models × {lora, full} × {random, family} × 3 seeds = 36 runs.
# Question answered (pre-registered): is the C4 collapse band a property of the
# PRETRAINED representation, or of BERT training dynamics? (random-init control)
R=/mnt/cunyuliu/rna-ft-eval
PY=/home/cunyuliu/llr_env/bin/python
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
cd /home/cunyuliu/rna-ft-eval
LOG=$R/logs/q_random_init.log
echo "=== ri start $(date) ===" >> $LOG

run_cell () {
  local model=$1 strat=$2 seed=$3 split=$4 dev=$5
  local lr=3e-4
  # random-init arm uses DEFAULT lr (3e-4) for both strategies — gap measured
  # against pretrained arm's default-lr rows (apples-to-apples on protocol)
  $PY -m rnafteval.finetune_one --model "$model" --task noncoding-rna-family \
      --strategy "$strat" --seed "$seed" --split "$split" --device "$dev" \
      --random-init >> $LOG 2>&1
  echo "[ri] exit $? $model $strat s$seed $split $(date +%H:%M)" >> $LOG
}

pick_gpu () {
  nvidia-smi --query-gpu=index,memory.free --format=csv,noheader,nounits | \
  awk -F", " '{ if ($2+0 >= 9000 && $1 < 6) print $1 }' | head -1
}

for model in RiNALMo-micro RNA-Sc-10M RNA-Sc-30M; do
  for strat in lora full; do
    for split in random family; do
      for seed in 17 29 43; do
        # skip if done (ledger run_id has _ri tag; result check)
        rid="ft_$(echo ${model} | tr -d '.-' | tr 'A-Z' 'a-z')_noncodingrnafamily_${strat/ -/}_s${seed}_${split}_ri"
        rid="ft_$(echo ${model} | tr -d '.' | tr 'A-Z' 'a-z' | tr '-' '')_noncodingrnafamily_${strat/only/only}_s${seed}_${split}_ri"
        # simpler: just attempt; claim() skips done automatically
        att=0
        while [ $att -lt 40 ]; do
          dev=$(pick_gpu)
          if [ -n "$dev" ]; then break; fi
          echo "[ri] wait card $model $strat s$seed $split $(date +%H:%M)" >> $LOG
          sleep 300
        done
        run_cell "$model" "$strat" "$seed" "$split" "$dev"
      done
    done
  done
done
echo "=== ri DONE $(date) ===" >> $LOG
