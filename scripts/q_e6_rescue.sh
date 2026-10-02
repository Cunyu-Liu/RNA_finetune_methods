#!/bin/bash
# e6 650M lora s17 救援（20min cron）：GAVEUP 死格兜底
R=/mnt/cunyuliu/rna-ft-eval
PY=/home/cunyuliu/llr_env/bin/python
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
cd /home/cunyuliu/rna-ft-eval
LOG=$R/logs/q_patch_dead_cells.log
CARD="$PY /home/cunyuliu/rna-ft-eval/scripts/rnaft_card.py"

res1=$R/artifacts/e6/RiNALMo-650M_lora_s17/result.json
[ -f "$res1" ] && exit 0
pgrep -f "e6_forget.*seed 17" > /dev/null && exit 0
echo "[e6rescue] relaunch $(date +%H:%M)" >> $LOG
for att in $(seq 1 200); do
  GS=$($CARD pick 11)
  [ -z "$GS" ] && { sleep 300; continue; }
  G=${GS%% *}; SL=${GS##* }
  [ -f "$res1" ] && { $CARD release $G $SL; exit 0; }
  pgrep -f "e6_forget.*seed 17" > /dev/null && { $CARD release $G $SL; exit 0; }
  echo "[e6rescue] RUN GPU$G.$SL $(date +%H:%M)" >> $LOG
  setsid nohup $PY -m rnafteval.e6_forget --model RiNALMo-650M --strategy lora \
      --seed 17 --lr 3e-4 --device $G --batch-size 16 >> $LOG 2>&1 < /dev/null &
  sleep 60
  $CARD release $G $SL
  exit 0
done
