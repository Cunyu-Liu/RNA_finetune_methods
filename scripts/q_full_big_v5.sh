#!/bin/bash
# fullbig v5（1001）：1.6B full-FT 显存实测修正——AIDO bs2 实跑峰值 30.3G（AdamW fp32 态
# 1.6B×(2+2+4+4)bytes ≈ 19G + 激活/梯度 ≈ 30G），bs2+22G 门必然 OOM。
# v5：AIDO bs1 + 34G 门（近独占卡窗口）；RiboSpan full 实测 0.48@lr3e-5 已落，
# 其余格按网格选优。仍走共享卡锁 + done-skip + 3 轮重试。
R=/mnt/cunyuliu/rna-ft-eval
PY=/home/cunyuliu/llr_env/bin/python
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
cd /home/cunyuliu/rna-ft-eval
LOG=$R/logs/q_full_big_v5.log
CARD="$PY /home/cunyuliu/rna-ft-eval/scripts/rnaft_card.py"

run_cell () {  # $1=model $2=split $3=seed $4=lr $5=need $6=bs
  local M=$1 SPL=$2 SED=$3 LR=$4 NEED=$5 BS=$6
  local mkey=$(echo "$M" | tr -d '.-' | tr 'A-Z' 'a-z')
  local resdir="$R/artifacts/ft_${mkey}_noncodingrnafamily_full_s${SED}_${SPL}_lr${LR}"
  [ -f "$resdir/result.json" ] && { echo "[fb5] skip(done) $M s$SED $SPL lr$LR" >> $LOG; return 0; }
  local ok=0
  for round in 1 2 3; do
    for att in $(seq 1 40); do
      local GS=$($CARD pick $NEED)
      if [ -z "$GS" ]; then
        echo "[fb5] wait card $M s$SED $SPL lr$LR r$round $(date +%H:%M)" >> $LOG; sleep 300; continue
      fi
      local G=${GS%% *}; local SL=${GS##* }
      if [ -f "$resdir/result.json" ]; then $CARD release "$G" "$SL"; ok=1; break; fi
      echo "[fb5] RUN $M s$SED $SPL lr$LR bs$BS GPU$G.$SL r$round $(date +%H:%M)" >> $LOG
      $PY -m rnafteval.finetune_one --model "$M" --task noncoding-rna-family \
          --strategy full --seed "$SED" --split "$SPL" --device "$G" \
          --lr "$LR" --batch-size $BS --epochs 10 >> $LOG 2>&1
      local rc=$?; $CARD release "$G" "$SL"
      echo "[fb5] exit $rc $M s$SED $SPL lr$LR $(date +%H:%M)" >> $LOG
      if [ $rc -eq 0 ]; then ok=1; break; fi
    done
    [ $ok -eq 1 ] && break
  done
  [ $ok -eq 0 ] && echo "[fb5] GAVEUP $M s$SED $SPL lr$LR" >> $LOG
  return 0
}

$PY -c "import torch; assert torch.cuda.is_available(), 'CUDA NOT AVAILABLE'" || { echo "FATAL: CUDA unavailable (fb5)" >> $LOG; exit 1; }
echo "=== fullbig-v5 start $(date) ===" >> $LOG

# Stage 1: 网格补缺（AIDO 两档 / RiboSpan lr1e-05）——bs1 + 34G
for M in AIDO.RNA-1.6B RiboSpan-1K-40; do
  for LR in 1e-05 3e-05; do
    run_cell "$M" random 101 "$LR" 34 1
  done
done

# 读网格选优（无则保守 3e-5）
BESTFILE=/tmp/fullbig_v5_grid_choice.txt
$PY - <<'PYEOF' > $BESTFILE
import json
best={}
for l in open("/mnt/cunyuliu/rna-ft-eval/ledger.jsonl"):
    l=l.strip()
    if not l: continue
    try: r=json.loads(l)
    except Exception: continue
    if (r.get("seed")==101 and r.get("strategy")=="full" and r.get("status")=="done"
        and r.get("task")=="noncoding-rna-family" and r.get("split")=="random"
        and r.get("model") in ("AIDO.RNA-1.6B","RiboSpan-1K-40")
        and r.get("value") is not None and r.get("lr") is not None):
        m=r["model"]; lr=float(r["lr"]); v=r["value"]
        if m not in best or v>best[m][1]: best[m]=(lr,v)
for m,(lr,v) in best.items(): print(m, lr)
PYEOF
LRAIDO=$(grep "AIDO" $BESTFILE | awk '{print $2}'); LRAIDO=${LRAIDO:-3e-05}
LRRIBO=$(grep "RiboSpan" $BESTFILE | awk '{print $2}'); LRRIBO=${LRRIBO:-3e-05}
echo "[fb5] grid chose AIDO=$LRAIDO RiboSpan=$LRRIBO ($(cat $BESTFILE | tr '\n' ';'))" >> $LOG

# Stage 2: formal（AIDO bs1/34G；RiboSpan 网格已示 0.48@3e-5→full 用 bs1/34G 同样稳妥）
for M in AIDO.RNA-1.6B RiboSpan-1K-40; do
  if [ "$M" = "AIDO.RNA-1.6B" ]; then LR=$LRAIDO; else LR=$LRRIBO; fi
  for SPL in random family; do
    for SED in 17 29 43; do
      run_cell "$M" "$SPL" "$SED" "$LR" 34 1
    done
  done
done
echo "=== fullbig-v5 DONE $(date) ===" >> $LOG