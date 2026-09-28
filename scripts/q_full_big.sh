#!/bin/bash
R=/mnt/cunyuliu/rna-ft-eval
PY=/home/cunyuliu/llr_env/bin/python
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
cd /home/cunyuliu/rna-ft-eval
LOG=$R/logs/q_full_big.log
echo "=== fullbig-v2 stage1 start $(date) ===" >> $LOG

pick_gpu () {
  local need=$1
  nvidia-smi --query-gpu=index,memory.free --format=csv,noheader,nounits | \
  awk -F", " -v n="$need" '{ if ($2+0 >= n*1024 && $1 < 6) print $1 }' | head -1
}

for model in AIDO.RNA-1.6B RiboSpan-1K-40; do
  for lr in 1e-05 3e-05; do
    att=0
    while [ $att -lt 60 ]; do
      dev=$(pick_gpu 28)
      if [ -n "$dev" ]; then break; fi
      sleep 600
    done
    $PY -m rnafteval.finetune_one --model "$model" --task noncoding-rna-family \
        --strategy full --seed 101 --split random --device "$dev" \
        --lr "$lr" --batch-size 2 --epochs 10 >> $LOG 2>&1
    echo "[fullbig1] exit $? $model s101 lr$lr $(date +%H:%M)" >> $LOG
  done
done

BESTFILE=/tmp/fullbig_grid_choice.txt
$PY - <<'PYEOF' > $BESTFILE
import json
rows=[json.loads(l) for l in open("/mnt/cunyuliu/rna-ft-eval/ledger.jsonl")]
best={}
for r in rows:
    if (r.get("seed")==101 and r.get("strategy")=="full" and r.get("status")=="done"
       and r.get("task")=="noncoding-rna-family" and r.get("split")=="random"
       and r.get("model") in ("AIDO.RNA-1.6B","RiboSpan-1K-40")
       and r.get("value") is not None and r.get("lr") is not None):
        m=r["model"]; lr=float(r["lr"]); v=r["value"]
        if m not in best or v>best[m][1]:
            best[m]=(lr,v)
for m,(lr,v) in best.items():
    print(m, lr)
PYEOF
LRAIDO=$(grep "AIDO" $BESTFILE | awk '{print $2}')
LRRIBO=$(grep "RiboSpan" $BESTFILE | awk '{print $2}')
LRAIDO=${LRAIDO:-3e-05}
LRRIBO=${LRRIBO:-3e-05}
echo "[fullbig] grid chose AIDO=$LRAIDO RiboSpan=$LRRIBO" >> $LOG

spec_lr () {
  case "$1" in
    RiNALMo-mega) echo 1e-05 ;;
    RiNALMo-650M) echo 1e-05 ;;
    RNA-Sc-650M) echo 3e-05 ;;
    AIDO.RNA-1.6B) echo $LRAIDO ;;
    RiboSpan-1K-40) echo $LRRIBO ;;
  esac
}
spec_bs () { case "$1" in AIDO*|RiboSpan*) echo 4;; *) echo 8;; esac; }
spec_need () { case "$1" in AIDO*|RiboSpan*) echo 26;; *) echo 16;; esac; }

for model in RiNALMo-mega RiNALMo-650M RNA-Sc-650M AIDO.RNA-1.6B RiboSpan-1K-40; do
  need=$(spec_need "$model"); bs=$(spec_bs "$model"); lr=$(spec_lr "$model")
  for split in random family; do
    for seed in 17 29 43; do
      att=0
      while [ $att -lt 60 ]; do
        dev=$(pick_gpu $need)
        if [ -n "$dev" ]; then break; fi
        echo "[fullbig] wait card $model s$seed $split $(date +%H:%M)" >> $LOG
        sleep 600
      done
      $PY -m rnafteval.finetune_one --model "$model" --task noncoding-rna-family \
          --strategy full --seed "$seed" --split "$split" --device "$dev" \
          --lr "$lr" --batch-size "$bs" --epochs 10 >> $LOG 2>&1
      echo "[fullbig] exit $? $model s$seed $split lr=$lr $(date +%H:%M)" >> $LOG
    done
  done
done
echo "=== fullbig DONE $(date) ===" >> $LOG
