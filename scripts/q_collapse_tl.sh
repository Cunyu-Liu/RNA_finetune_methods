#!/bin/bash
# C4 collapse timeline queue (2026-09-27): 5 models × {lora, full@default} × s17 = 10 runs.
# Evidence: per-epoch family test acc — when does the collapse happen?
R=/mnt/cunyuliu/rna-ft-eval
PY=/home/cunyuliu/llr_env/bin/python
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
cd /home/cunyuliu/rna-ft-eval
LOG=$R/logs/q_collapse_tl.log
echo "=== ctl start $(date) ===" >> $LOG

pick_gpu () {
  nvidia-smi --query-gpu=index,memory.free --format=csv,noheader,nounits | \
  awk -F", " '{ if ($2+0 >= 8000 && $1 < 6) print $1 }' | head -1
}

for cell in "RiNALMo-micro lora" "RiNALMo-micro full" \
            "ERNIE-RNA lora" "ERNIE-RNA full" \
            "SpliceBERT lora" "SpliceBERT full" \
            "RNA-Sc-10M lora" "RNA-Sc-10M full" \
            "RNA-Sc-30M lora" "RNA-Sc-30M full"; do
  set -- $cell
  while true; do
    G=$(pick_gpu)
    if [ -n "$G" ]; then break; fi
    echo "[ctl] wait card for $cell $(date +%H:%M)" >> $LOG
    sleep 300
  done
  $PY -m rnafteval.collapse_timeline --model "$1" --strategy "$2" \
      --seed 17 --device "$G" >> $LOG 2>&1
  echo "[ctl] exit $? $1 $2 $(date +%H:%M)" >> $LOG
done
echo "=== ctl DONE $(date) ===" >> $LOG
