#!/bin/bash
# E6 official fixed-mask MLM correction; _mlm15fix keeps old runs/RIDs untouched.
R=/root/rna-ft-eval
PY=/root/miniconda3/envs/llr_env/bin/python
export PYTHONPATH=/root/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/root/hf_home HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
cd /home/cunyuliu/rna-ft-eval
LOG=$R/logs/q_e6_mlm15fix.log
DEV=${DEV:-0}
MODEL_FILE=${E6_MODEL_FILE:-/root/rnaft/e6_mlm15_models.active}
if [ -z "${MODELS:-}" ] && [ -f "$MODEL_FILE" ]; then
  MODELS=$(cat "$MODEL_FILE")
fi
if [ -n "${MODELS:-}" ]; then
  total=$(printf '%s\n' $MODELS | wc -l)
  total=$((total * 6))
else
  total=30
fi

proof() {
  local resdir=$1 model=$2 strat=$3 seed=$4
  $PY scripts/e6_mlm15_proof.py "$resdir" "$model" "$strat" "$seed" >/dev/null 2>&1
}

ok=0

E6_LANE_LOCK=/tmp/rnaft_e6mlm_lane.lock
exec 8>>"$E6_LANE_LOCK"
if ! flock -n 8; then
  echo "[mlm15fix] another lane instance holds the lock; exiting" >> "$LOG"
  exit 75
fi

wait_for_vram() {
  # E6 优先窗口：显存不足时等待（而非立刻 OOM）；每 5min 检查，最长 6h
  local need_mb=${1:-9000}
  local waited=0
  while true; do
    local free_mb
    free_mb=$(nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits | head -1)
    [ "$free_mb" -ge "$need_mb" ] && break
    if [ "$waited" -eq 0 ]; then
      echo "[mlm15fix] WAIT_VRAM need=${need_mb}MB free=${free_mb}MB $(date +%H:%M)" >> "$LOG"
    fi
    sleep 300
    waited=$((waited+300))
    [ "$waited" -ge 21600 ] && return 1
  done
  [ "$waited" -gt 0 ] && echo "[mlm15fix] VRAM_OK free=${free_mb}MB after ${waited}s" >> "$LOG"
  return 0
}

run_cell() {
  local model=$1 strat=$2 seed=$3 lr=$4 bs=$5
  if [ -n "${MODELS:-}" ] && [[ " $MODELS " != *" $model "* ]]; then
    return 0
  fi
  local resdir=$R/artifacts/e6/${model}_${strat}_s${seed}_mlm15fix_seedfix
  if proof "$resdir" "$model" "$strat" "$seed"; then
    echo "[mlm15fix] skip(done) $model $strat s$seed" >> $LOG
    ok=$((ok+1))
    return 0
  fi
  if [ -e "$resdir/result.json" ]; then
    echo "[mlm15fix] CONFLICT result exists without valid double proof: $model $strat s$seed" >> $LOG
    return 1
  fi
  local exclusive_last=0 exclusive_now
  while [ -e "${EXCLUSIVE_AIDO:-/root/rnaft/EXCLUSIVE_AIDO}" ]; do
    exclusive_now=$(date +%s)
    if [ "$exclusive_last" -eq 0 ] || [ $((exclusive_now-exclusive_last)) -ge "${EXCLUSIVE_WAIT_LOG_S:-900}" ]; then
      echo "[mlm15fix] WAIT EXCLUSIVE_AIDO $model $strat s$seed $(date -u +%FT%TZ)" >> "$LOG"
      exclusive_last=$exclusive_now
    fi
    sleep "${EXCLUSIVE_POLL_S:-15}"
  done
  if [ "$exclusive_last" -ne 0 ]; then
    if proof "$resdir" "$model" "$strat" "$seed"; then
      echo "[mlm15fix] skip(done-after-wait) $model $strat s$seed" >> "$LOG"
      ok=$((ok+1))
      return 0
    fi
    if [ -e "$resdir/result.json" ]; then
      echo "[mlm15fix] CONFLICT after wait: $model $strat s$seed" >> "$LOG"
      return 1
    fi
  fi
  local NEED=9500
  if [ "$strat" = "lora" ]; then NEED=8000; fi
  wait_for_vram $NEED || return 1
  echo "[mlm15fix] RUN $model $strat s$seed lr$lr bs$bs $(date +%H:%M)" >> $LOG
  $PY -m rnafteval.e6_forget --model "$model" --strategy "$strat" \
    --seed "$seed" --lr "$lr" --device "$DEV" --epochs 10 \
    --batch-size "$bs" --n-holdout 2000 --mask-rate 0.15 \
    --out-suffix "_mlm15fix_seedfix" >> $LOG 2>&1
  local rc=$?
  echo "[mlm15fix] exit $rc $model $strat s$seed $(date +%H:%M)" >> $LOG
  [ "$rc" -eq 0 ] || return "$rc"
  if ! proof "$resdir" "$model" "$strat" "$seed"; then
    echo "[mlm15fix] incomplete ledger/result double proof $model $strat s$seed" >> $LOG
    return 1
  fi
  ok=$((ok+1))
}

for seed in 17 29 43; do
  run_cell RiNALMo-micro lora $seed 3e-4 32
  run_cell RiNALMo-micro full $seed 1e-5 32
  run_cell RiNALMo-mega lora $seed 3e-4 16
  run_cell RiNALMo-mega full $seed 1e-5 16
  run_cell RiNALMo-650M lora $seed 3e-4 16
  run_cell RiNALMo-650M full $seed 1e-5 4
  run_cell ERNIE-RNA lora $seed 3e-4 32
  run_cell ERNIE-RNA full $seed 1e-5 32
  run_cell RNA-FM lora $seed 3e-4 32
  run_cell RNA-FM full $seed 1e-5 32
done
if [ "$ok" -eq "$total" ]; then
  echo "[mlm15fix] DONE cells=$ok/$total $(date)" >> $LOG
else
  echo "[mlm15fix] INCOMPLETE cells=$ok/$total $(date)" >> $LOG
  exit 1
fi
