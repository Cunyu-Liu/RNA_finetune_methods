#!/bin/bash
# e6-v3 跨任务保持度补位（2026-09-29）：18 格计划中 1 格未落（RiNALMo-micro lora s43）。
# 协议与 q_e6_v3.sh 一致（probe-style retention；ncRNA 微调前后 m6A/MRL/SSP probe）；共享卡锁 + 真 CUDA 断言。
R=/mnt/cunyuliu/rna-ft-eval
PY=/home/cunyuliu/llr_env/bin/python
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
cd /home/cunyuliu/rna-ft-eval
LOG=$R/logs/q_e6ret_fill.log
CARD="$PY /home/cunyuliu/rna-ft-eval/scripts/rnaft_card.py"

M=RiNALMo-micro; S=lora; SEED=43; NEED=10
resdir="$R/artifacts/e6ret/${M}_${S}_s${SEED}"
$PY -c "import torch; assert torch.cuda.is_available(), 'CUDA NOT AVAILABLE'" || { echo "FATAL: CUDA unavailable (e6ret_fill)" >> $LOG; exit 1; }
echo "=== e6ret_fill start $(date) ===" >> $LOG
[ -f "$resdir/result.json" ] && { echo "[e6ret] skip(done) $M $S s$SEED" >> $LOG; exit 0; }
ok=0
for round in 1 2 3; do
  for att in $(seq 1 40); do
    GS=$($CARD pick $NEED)
    if [ -z "$GS" ]; then
      echo "[e6ret] wait card $M $S s$SEED r$round $(date +%H:%M)" >> $LOG; sleep 300; continue
    fi
    G=${GS%% *}; SL=${GS##* }
    if [ -f "$resdir/result.json" ]; then $CARD release "$G" "$SL"; ok=1; break; fi
    echo "[e6ret] RUN $M $S s$SEED GPU$G.$SL r$round $(date +%H:%M)" >> $LOG
    $PY -m rnafteval.e6_retention --model "$M" --strategy "$S" --seed "$SEED" --device "$G" >> $LOG 2>&1
    rc=$?; $CARD release "$G" "$SL"
    echo "[e6ret] exit $rc $M $S s$SEED $(date +%H:%M)" >> $LOG
    if [ $rc -eq 0 ]; then ok=1; break; fi
  done
  [ $ok -eq 1 ] && break
done
[ $ok -eq 0 ] && echo "[e6ret] GAVEUP $M $S s$SEED" >> $LOG
echo "=== e6ret_fill DONE $(date) ===" >> $LOG