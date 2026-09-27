#!/bin/bash
# e6_official v2: retry the 12 failed cells (OOM/contended cards last round).
# Now GPUs have room (2: 25GB free, 4: 12GB). Serial, high mem gate (18GB).
R=/mnt/cunyuliu/rna-ft-eval
PY=/home/cunyuliu/llr_env/bin/python
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
cd /home/cunyuliu/rna-ft-eval
LOG=$R/logs/q_e6_official2.log
echo "=== e6off2 start $(date) ===" >> $LOG

pick_gpu () {
  nvidia-smi --query-gpu=index,memory.free --format=csv,noheader,nounits | \
  awk -F", " '{ if ($2+0 >= 18000 && $1 < 6) print $1 }' | head -1
}

for cell in "RiNALMo-mega lora 17" "RiNALMo-mega lora 29" "RiNALMo-mega lora 43" \
            "RiNALMo-mega full 17" "RiNALMo-mega full 29" "RiNALMo-mega full 43" \
            "RiNALMo-650M lora 17" "RiNALMo-650M lora 29" "RiNALMo-650M lora 43" \
            "RiNALMo-650M full 17" "RiNALMo-650M full 29" "RiNALMo-650M full 43"; do
  set -- $cell
  # skip if result already exists
  resdir="$R/artifacts/e6/${1}_${2}_s${3}"
  if [ -f "$resdir/result.json" ]; then
    echo "[e6off2] skip(done) $cell" >> $LOG
    continue
  fi
  att=0
  while [ $att -lt 30 ]; do
    dev=$(pick_gpu)
    if [ -n "$dev" ]; then break; fi
    echo "[e6off2] wait card for $cell $(date +%H:%M)" >> $LOG
    sleep 300
  done
  $PY -m rnafteval.e6_forget --model "$1" --strategy "$2" \
      --seed "$3" --lr 1e-05 --device "$dev" >> $LOG 2>&1
  echo "[e6off2] exit $? $1 $2 s$3 $(date +%H:%M)" >> $LOG
done
echo "=== e6off2 DONE $(date) ===" >> $LOG
