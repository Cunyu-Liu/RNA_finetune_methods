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

CONT_LANE_LOCK=/tmp/rnaft_e6cont_lane.lock
exec 8>>"$CONT_LANE_LOCK"
if ! flock -n 8; then
  echo "[e6cont] another lane instance holds the lock; exiting" >> "$LOG"
  exit 75
fi
echo "[e6cont] start $(date) pid=$$" >> "$LOG"

wait_for_vram() {
  local need_mb=${1:-9000}
  local waited=0
  while true; do
    local free_mb
    free_mb=$(nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits | head -1)
    [ "$free_mb" -ge "$need_mb" ] && break
    if [ "$waited" -eq 0 ]; then
      echo "[e6cont] WAIT_VRAM need=${need_mb}MB free=${free_mb}MB $(date +%H:%M)" >> "$LOG"
    fi
    sleep 300
    waited=$((waited+300))
    [ "$waited" -ge 21600 ] && return 1
  done
  [ "$waited" -gt 0 ] && echo "[e6cont] VRAM_OK free=${free_mb}MB after ${waited}s" >> "$LOG"
  return 0
}

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
  wait_for_vram 9500 || return 1
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
