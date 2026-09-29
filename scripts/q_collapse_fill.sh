#!/bin/bash
# collapse_tl 补位（2026-09-29）：10 格计划中 4 格未落（RiNALMo-micro / ERNIE-RNA × {lora,full} × s17 family）。
# 与 q_collapse_tl.sh 协议一致；新增：done 定向检查 + 共享卡锁 + 真 CUDA 断言。
R=/mnt/cunyuliu/rna-ft-eval
PY=/home/cunyuliu/llr_env/bin/python
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
cd /home/cunyuliu/rna-ft-eval
LOG=$R/logs/q_collapse_fill.log
CARD="$PY /home/cunyuliu/rna-ft-eval/scripts/rnaft_card.py"

is_done () {  # $1=modelkey $2=strat
  $PY - "$1" "$2" <<'PYEOF'
import json,sys
mk,strat=sys.argv[1:3]
rid="ft_%s_collapsetimeline_%s_s17_family_tl"%(mk,strat)
for l in open("/mnt/cunyuliu/rna-ft-eval/ledger.jsonl"):
    l=l.strip()
    if not l: continue
    try: r=json.loads(l)
    except Exception: continue
    if r.get("run_id")==rid and r.get("status")=="done": sys.exit(0)
sys.exit(1)
PYEOF
}

$PY -c "import torch; assert torch.cuda.is_available(), 'CUDA NOT AVAILABLE'" || { echo "FATAL: CUDA unavailable (collapse_fill)" >> $LOG; exit 1; }
echo "=== ctl_fill start $(date) ===" >> $LOG
for entry in "RiNALMo-micro rinalmomicro" "ERNIE-RNA ernierna"; do
  set -- $entry; M=$1; MK=$2
  for strat in lora full; do
    is_done "$MK" "$strat" && continue
    if [ "$strat" = "full" ]; then need=12; else need=8; fi
    ok=0
    for att in $(seq 1 40); do
      GS=$($CARD pick $need)
      if [ -z "$GS" ]; then
        echo "[ctl] wait card $M $strat $(date +%H:%M)" >> $LOG; sleep 240; continue
      fi
      G=${GS%% *}; SL=${GS##* }
      if is_done "$MK" "$strat"; then $CARD release "$G" "$SL"; ok=1; break; fi
      echo "[ctl] RUN $M $strat GPU$G.$SL $(date +%H:%M)" >> $LOG
      $PY -m rnafteval.collapse_timeline --model "$M" --strategy "$strat" \
          --seed 17 --device "$G" >> $LOG 2>&1
      rc=$?; $CARD release "$G" "$SL"
      echo "[ctl] exit $rc $M $strat $(date +%H:%M)" >> $LOG
      if [ $rc -eq 0 ]; then ok=1; break; fi
    done
    [ $ok -eq 0 ] && echo "[ctl] GAVEUP $M $strat" >> $LOG
  done
done
echo "=== ctl_fill DONE $(date) ===" >> $LOG