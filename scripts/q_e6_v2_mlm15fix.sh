#!/bin/bash
# Sequence-level 12-label modification with independent validation/best-val.
# Legacy per-base and fixed-epoch RIDs remain read-only historical evidence.
R=${R:-/root/rna-ft-eval}
REPO=${REPO:-/home/cunyuliu/rna-ft-eval}
PY=${PY:-/root/miniconda3/envs/llr_env/bin/python}
export PYTHONPATH=/root/rna-ft-eval/pypath:$REPO${PYTHONPATH:+:$PYTHONPATH}
export HF_HOME=/root/hf_home HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
cd "$REPO" || exit 1
LOG=${LOG:-$R/logs/q_e6_v2_mlm15fix.log}
mkdir -p "$(dirname "$LOG")" || exit 1
DEV=${DEV:-0}
TIMEOUT_S=${E6_V2_TIMEOUT_S:-21600}
SUFFIX=_mlm15fix_seedfix_seqmlfix_bestval_v1
EXTRA=_taskm6a_s0_mlm15fix_seedfix_seqmlfix_bestval_v1

proof() {
  local resdir=$1 model=$2 strat=$3 seed=$4
  "$PY" scripts/e6_mlm15_proof.py "$resdir" "$model" "$strat" "$seed" \
    --ledger-task e6-forgetting --extra "$EXTRA" \
    --result-task modification --protocol-prefix E6-v2-fixed-mask-mlm \
    >/dev/null 2>&1
}

ok=0
run_cell() {
  local model=$1 strat=$2 seed=$3 lr=$4
  local resdir=$R/artifacts/e6/${model}_${strat}_task-m6a_s${seed}${SUFFIX}
  if proof "$resdir" "$model" "$strat" "$seed"; then
    echo "[e6v2-mlm15fix] skip(done) $model $strat s$seed" >> "$LOG"
    ok=$((ok+1))
    return 0
  fi
  if [ -e "$resdir/result.json" ]; then
    echo "[e6v2-mlm15fix] CONFLICT result exists without valid double proof: $model $strat s$seed" >> "$LOG"
    return 1
  fi
  local exclusive_last=0 exclusive_now
  while [ -e "${EXCLUSIVE_AIDO:-/root/rnaft/EXCLUSIVE_AIDO}" ]; do
    exclusive_now=$(date +%s)
    if [ "$exclusive_last" -eq 0 ] || [ $((exclusive_now-exclusive_last)) -ge "${EXCLUSIVE_WAIT_LOG_S:-900}" ]; then
      echo "[e6v2-mlm15fix] WAIT EXCLUSIVE_AIDO $model $strat s$seed $(date -u +%FT%TZ)" >> "$LOG"
      exclusive_last=$exclusive_now
    fi
    sleep "${EXCLUSIVE_POLL_S:-15}"
  done
  if [ "$exclusive_last" -ne 0 ]; then
    if proof "$resdir" "$model" "$strat" "$seed"; then
      echo "[e6v2-mlm15fix] skip(done-after-wait) $model $strat s$seed" >> "$LOG"
      ok=$((ok+1))
      return 0
    fi
    if [ -e "$resdir/result.json" ]; then
      echo "[e6v2-mlm15fix] CONFLICT after wait: $model $strat s$seed" >> "$LOG"
      return 1
    fi
  fi
  echo "[e6v2-mlm15fix] RUN $model $strat s$seed lr$lr bs32 $(date +%H:%M)" >> "$LOG"
  timeout "$TIMEOUT_S" "$PY" -m rnafteval.e6_forget_task \
    --model "$model" --task modification --strategy "$strat" \
    --seed "$seed" --lr "$lr" --device "$DEV" \
    --converge --convergence-mode bestval \
    --batch-size 32 --n-holdout 2000 --mask-rate 0.15 \
    --out-suffix "$SUFFIX" >> "$LOG" 2>&1
  local rc=$?
  echo "[e6v2-mlm15fix] exit $rc $model $strat s$seed $(date +%H:%M)" >> "$LOG"
  [ "$rc" -eq 0 ] || return "$rc"
  if ! proof "$resdir" "$model" "$strat" "$seed"; then
    echo "[e6v2-mlm15fix] incomplete ledger/result double proof $model $strat s$seed" >> "$LOG"
    return 1
  fi
  ok=$((ok+1))
}

for seed in 17 29 43; do
  run_cell RiNALMo-micro lora "$seed" 3e-4
  run_cell RiNALMo-micro full "$seed" 1e-5
done
if [ "$ok" -eq 6 ]; then
  echo "[e6v2-mlm15fix] DONE cells=$ok/6 $(date)" >> "$LOG"
  exit 0
else
  echo "[e6v2-mlm15fix] INCOMPLETE cells=$ok/6 $(date)" >> "$LOG"
  exit 1
fi
