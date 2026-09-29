#!/bin/bash
# e6_official4（2026-09-29）：官方系遗忘谱线补位 + 协议一致性修正。
# 1) RiNALMo-650M {lora@3e-4, full@1e-5} × 3 种子（谱线大端，原队列 bs16 在竞卡下反复 OOM，从未落格）
# 2) RiNALMo-mega lora@3e-4 × 3 种子（协议修正：原 mega lora 跑的是 1e-5，与 micro/受控系 lora@3e-4 不一致；
#    以 _lr3e-04 后缀另存，不动既有 _s0-heldout 行——P4 决定是否切换口径）
# 工程：共享卡锁 + 抢锁后复核 + result.json done-skip + 3 轮重试 + expandable_segments
R=/mnt/cunyuliu/rna-ft-eval
PY=/home/cunyuliu/llr_env/bin/python
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
cd /home/cunyuliu/rna-ft-eval
LOG=$R/logs/q_e6_official4.log
CARD="$PY /home/cunyuliu/rna-ft-eval/scripts/rnaft_card.py"

$PY -c "import torch; assert torch.cuda.is_available(), 'CUDA NOT AVAILABLE'" || { echo "FATAL: CUDA unavailable (e6off4)" >> $LOG; exit 1; }
echo "=== e6off4 start $(date) ===" >> $LOG
# 行格式：model strategy seed lr bs need suffix
for cell in "RiNALMo-650M lora 17 3e-4 16 11 " \
            "RiNALMo-650M lora 29 3e-4 16 11 " \
            "RiNALMo-650M lora 43 3e-4 16 11 " \
            "RiNALMo-650M full 17 1e-5 4 16 " \
            "RiNALMo-650M full 29 1e-5 4 16 " \
            "RiNALMo-650M full 43 1e-5 4 16 " \
            "RiNALMo-mega lora 17 3e-4 16 11 _lr3e-04" \
            "RiNALMo-mega lora 29 3e-4 16 11 _lr3e-04" \
            "RiNALMo-mega lora 43 3e-4 16 11 _lr3e-04"; do
  set -- $cell
  M=$1; S=$2; SEED=$3; LR=$4; BS=$5; NEED=$6; SUF=$7
  resdir="$R/artifacts/e6/${M}_${S}_s${SEED}${SUF}"
  [ -f "$resdir/result.json" ] && { echo "[e6off4] skip(done) $M $S s$SEED$SUF" >> $LOG; continue; }
  ok=0
  for round in 1 2 3; do
    for att in $(seq 1 40); do
      GS=$($CARD pick $NEED)
      if [ -z "$GS" ]; then
        echo "[e6off4] wait card $M $S s$SEED$SUF r$round $(date +%H:%M)" >> $LOG; sleep 300; continue
      fi
      G=${GS%% *}; SL=${GS##* }
      if [ -f "$resdir/result.json" ]; then $CARD release "$G" "$SL"; ok=1; break; fi
      echo "[e6off4] RUN $M $S s$SEED lr$LR bs$BS GPU$G.$SL r$round $(date +%H:%M)" >> $LOG
      $PY -m rnafteval.e6_forget --model "$M" --strategy "$S" --seed "$SEED" \
          --lr "$LR" --device "$G" --batch-size "$BS" --out-suffix "$SUF" >> $LOG 2>&1
      rc=$?; $CARD release "$G" "$SL"
      echo "[e6off4] exit $rc $M $S s$SEED$SUF $(date +%H:%M)" >> $LOG
      if [ $rc -eq 0 ]; then ok=1; break; fi
    done
    [ $ok -eq 1 ] && break
  done
  [ $ok -eq 0 ] && echo "[e6off4] GAVEUP $M $S s$SEED$SUF" >> $LOG
done
echo "=== e6off4 DONE $(date) ===" >> $LOG