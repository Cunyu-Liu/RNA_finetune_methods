#!/bin/bash
# E6-v2 补位（2026-10-03）：0927 q_e6_v2.sh 单轮循环中 3 格 OOM 竞卡失败后未落地
# （ledger 一直 pending、artifacts 无 result.json，0927 文档「18/18」不实）。
# 缺口：RiNALMo-micro lora s17 / RNA-Sc-30M lora s29 / RNA-Sc-30M lora s43。
# 协议与 q_e6_v2.sh 完全一致（m6A 起点、lora@3e-04）；共享卡锁 + 真 CUDA 断言 + 多轮重试。
R=/mnt/cunyuliu/rna-ft-eval
PY=/home/cunyuliu/llr_env/bin/python
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
cd /home/cunyuliu/rna-ft-eval
LOG=$R/logs/q_e6_v2_fill.log
CARD="$PY /home/cunyuliu/rna-ft-eval/scripts/rnaft_card.py"

$PY -c "import torch; assert torch.cuda.is_available(), 'CUDA NOT AVAILABLE'" || { echo "FATAL: CUDA unavailable (e6v2_fill)" >> $LOG; exit 1; }
echo "=== e6v2_fill start $(date) ===" >> $LOG

declare -a CELLS=("RiNALMo-micro 17" "RNA-Sc-30M 29" "RNA-Sc-30M 43")
for cell in "${CELLS[@]}"; do
  set -- $cell
  M=$1; SEED=$2; S=lora; LR=3e-04; NEED=12
  resdir="$R/artifacts/e6/${M}_${S}_task-m6a_s${SEED}"
  if [ -f "$resdir/result.json" ]; then echo "[e6v2f] skip(done) $M $S s$SEED" >> $LOG; continue; fi
  ok=0
  for round in 1 2 3 4; do
    for att in $(seq 1 40); do
      GS=$($CARD pick $NEED)
      if [ -z "$GS" ]; then
        echo "[e6v2f] wait card $M $S s$SEED r$round $(date +%H:%M)" >> $LOG; sleep 300; continue
      fi
      G=${GS%% *}; SL=${GS##* }
      if [ -f "$resdir/result.json" ]; then $CARD release "$G" "$SL"; ok=1; break; fi
      echo "[e6v2f] RUN $M $S s$SEED GPU$G.$SL r$round $(date +%H:%M)" >> $LOG
      $PY -m rnafteval.e6_forget_task --model "$M" --task modification \
          --strategy "$S" --seed "$SEED" --lr "$LR" --device "$G" >> $LOG 2>&1
      rc=$?; $CARD release "$G" "$SL"
      echo "[e6v2f] exit $rc $M $S s$SEED $(date +%H:%M)" >> $LOG
      if [ $rc -eq 0 ] && [ -f "$resdir/result.json" ]; then ok=1; break; fi
    done
    [ $ok -eq 1 ] && break
  done
  [ $ok -eq 0 ] && echo "[e6v2f] GAVEUP $M $S s$SEED" >> $LOG
done
echo "=== e6v2_fill DONE $(date) ===" >> $LOG
