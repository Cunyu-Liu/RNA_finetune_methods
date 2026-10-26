#!/bin/bash
# valplateau_v1 continuation: E6 micro cells whose fixed-epoch runs ended
# still-improving (12-21%/ep tail drop). Independent _e6cont RID suffix;
# only counts when valplateau.py says the extended curve is at plateau.
R=${R:-/root/rna-ft-eval}
REPO=${REPO:-/home/cunyuliu/rna-ft-eval}
PY=${PY:-/root/miniconda3/envs/llr_env/bin/python}
export PYTHONPATH=/root/rnaft/pypath:$REPO${PYTHONPATH:+:$PYTHONPATH}
export HF_HOME=/root/hf_home HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
cd "$REPO" || exit 1
LOG=${LOG:-$R/logs/q_e6_continuation.log}
mkdir -p "$(dirname "$LOG")"
DEV=${DEV:-0}
MAX_ROUNDS=${MAX_ROUNDS:-3}
EXTRA_EP=${EXTRA_EP:-10}

echo "[e6cont] start $(date)" >> "$LOG"

run_cell() {
  local model=$1 strat=$2 seed=$3 lr=$4
  local base=$R/artifacts/e6/${model}_${strat}_s${seed}_mlm15fix_seedfix
  local cont=$R/artifacts/e6/${model}_${strat}_s${seed}_e6cont
  # completion check: continuation result exists AND plateau flat
  if [ -f "$cont/result.json" ] && $PY scripts/valplateau.py \
      --e6-root "$cont" >/dev/null 2>&1; then
    echo "[e6cont] skip(done) $model $strat s$seed" >> "$LOG"
    return 0
  fi
  local EP=$EXTRA_EP
  local INIT=
  if [ -f "$base/ckpt.pt" ]; then
    INIT="--init-ckpt $base/ckpt.pt"
  else
    EP=$((EXTRA_EP * 3))
    echo "[e6cont] no base ckpt -> full rerun epochs=$EP $model $strat s$seed" >> "$LOG"
  fi
  echo "[e6cont] RUN $model $strat s$seed (epochs=$EP) $(date +%H:%M)" >> "$LOG"
  timeout 86400 "$PY" -m rnafteval.e6_forget \
    --model "$model" --strategy "$strat" --seed "$seed" --lr "$lr" \
    --device "$DEV" --epochs $EP --batch-size 32 \
    --n-holdout 2000 --mask-rate 0.15 $INIT --save-ckpt \
    --out-suffix "_e6cont" >> "$LOG" 2>&1
  local rc=$?
  echo "[e6cont] exit $rc $model $strat s$seed $(date +%H:%M)" >> "$LOG"
  return $rc
}

for seed in 17 29 43; do
  run_cell RiNALMo-micro lora "$seed" 3e-4
  run_cell RiNALMo-micro full "$seed" 1e-5
done
echo "[e6cont] cycle complete $(date)" >> "$LOG"
