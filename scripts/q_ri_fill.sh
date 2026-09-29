#!/bin/bash
# random-init 控制臂补位（2026-09-29）：36 格计划中未落格 cell 定向重试。
# done 判定：ledger run_id = ft_<mk>_noncodingrnafamily_<strat>_s<seed>_<split>_ri 且 status=done。
# 协议与 q_random_init.sh 一致（默认 LR 3e-4；--random-init）；新增：共享卡锁 + 抢锁后复核 + 真 CUDA 断言。
R=/mnt/cunyuliu/rna-ft-eval
PY=/home/cunyuliu/llr_env/bin/python
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
cd /home/cunyuliu/rna-ft-eval
LOG=$R/logs/q_ri_fill.log
CARD="$PY /home/cunyuliu/rna-ft-eval/scripts/rnaft_card.py"

is_done () {  # $1=modelkey $2=strat $3=seed $4=split
  $PY - "$1" "$2" "$3" "$4" <<'PYEOF'
import json,sys
mk,strat,seed,split=sys.argv[1:5]
rid="ft_%s_noncodingrnafamily_%s_s%s_%s_ri"%(mk,strat,seed,split)
for l in open("/mnt/cunyuliu/rna-ft-eval/ledger.jsonl"):
    l=l.strip()
    if not l: continue
    try: r=json.loads(l)
    except Exception: continue
    if r.get("run_id")==rid and r.get("status")=="done": sys.exit(0)
sys.exit(1)
PYEOF
}

$PY -c "import torch; assert torch.cuda.is_available(), 'CUDA NOT AVAILABLE'" || { echo "FATAL: CUDA unavailable (ri_fill)" >> $LOG; exit 1; }
echo "=== ri_fill start $(date) ===" >> $LOG
for entry in "RiNALMo-micro rinalmomicro" "RNA-Sc-10M rnasc10m" "RNA-Sc-30M rnasc30m"; do
  set -- $entry; M=$1; MK=$2
  for strat in lora full; do
    if [ "$strat" = "full" ]; then need=10; else need=8; fi
    for split in random family; do
      for seed in 17 29 43; do
        is_done "$MK" "$strat" "$seed" "$split" && continue
        ok=0
        for att in $(seq 1 40); do
          GS=$($CARD pick $need)
          if [ -z "$GS" ]; then
            echo "[ri] wait card $M $strat s$seed $split $(date +%H:%M)" >> $LOG
            sleep 240; continue
          fi
          G=${GS%% *}; SL=${GS##* }
          if is_done "$MK" "$strat" "$seed" "$split"; then $CARD release "$G" "$SL"; ok=1; break; fi
          echo "[ri] RUN $M $strat s$seed $split GPU$G.$SL $(date +%H:%M)" >> $LOG
          $PY -m rnafteval.finetune_one --model "$M" --task noncoding-rna-family \
              --strategy "$strat" --seed "$seed" --split "$split" --device "$G" \
              --random-init >> $LOG 2>&1
          rc=$?; $CARD release "$G" "$SL"
          echo "[ri] exit $rc $M $strat s$seed $split $(date +%H:%M)" >> $LOG
          if [ $rc -eq 0 ]; then ok=1; break; fi
        done
        [ $ok -eq 0 ] && echo "[ri] GAVEUP $M $strat s$seed $split" >> $LOG
      done
    done
  done
done
echo "=== ri_fill DONE $(date) ===" >> $LOG