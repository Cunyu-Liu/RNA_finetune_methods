#!/bin/bash
# monitor_loop v2.2: whitelist-only respawn with kernel-owned lifecycle locks.
# active_lanes.txt is the sole automatic launch/respawn control. DONE text is
# deliberately ignored: a whitelisted lane restarts after ANY exit; remove it
# to prevent another launch. Removing a lane never kills a live process.
# There is no q_master heartbeat or respawn of non-whitelisted legacy lanes/plans.
ROOT=${MONITOR_V22_ROOT:-/home/cunyuliu/rna-ft-eval}
RNAFT=${MONITOR_V22_RNAFT:-/root/rnaft}
PY=${MONITOR_V22_PY:-/root/miniconda3/envs/llr_env/bin/python}
INTERVAL=${MONITOR_V22_INTERVAL:-900}
ONCE=${MONITOR_V22_ONCE:-0}
LOCK_DIR=${MONITOR_V22_LOCK_DIR:-/tmp/rnaft_monitor_v22}
ACTIVE=$ROOT/scripts/active_lanes.txt
LEDGER=$RNAFT/ledger.jsonl
LOG=$RNAFT/logs/monitor_loop.log
STATE_DIR=$RNAFT/monitor_v22
MONITOR_LOCK=$LOCK_DIR/monitor.lock

export PYTHONPATH=/root/rnaft/pypath:/home/cunyuliu/rna-ft-eval:/home/cunyuliu/rna-sc
export HF_HOME=/root/hf_home
export HF_ENDPOINT=https://hf-mirror.com

command -v flock >/dev/null 2>&1 || {
  echo "monitor v2.2 requires flock" >&2
  exit 127
}
[ -r "$ACTIVE" ] || {
  echo "monitor v2.2 cannot read $ACTIVE" >&2
  exit 1
}
cd "$ROOT" || exit 1
mkdir -p "$LOCK_DIR" "$STATE_DIR" "$RNAFT/logs" || exit 1

# FD 9 belongs only to the monitor. The cycle subshell and sleep close it so
# lane processes or an orphaned sleep cannot keep a dead monitor locked in.
exec 9>>"$MONITOR_LOCK" || exit 1
if ! flock -n 9; then
  echo "monitor v2.2 already running (lock=$MONITOR_LOCK)" >&2
  exit 75
fi

observe_launcher() {
  local lane=$1 pid_file pid observation
  pid_file=$STATE_DIR/$lane.launcher.pid
  [ -r "$pid_file" ] || return 0
  IFS= read -r pid < "$pid_file"
  case "$pid" in
    ''|*[!0-9]*) echo "OBSERVE $lane invalid launcher pid file"; return 0 ;;
  esac
  observation=$(ps -p "$pid" -o pid= -o stat= -o args= 2>/dev/null)
  if [ -n "$observation" ]; then
    echo "OBSERVE $lane launcher_pid=$pid $observation"
  else
    echo "OBSERVE $lane launcher_pid=$pid exited"
  fi
  # Observation is informational only; never kill or spawn from ps/pgrep text.
}

while true; do
  (
    echo "=== monitor v2.2 $(date '+%F %T') ==="
    used=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1)
    util=$(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits | head -1)
    echo "GPU: ${used}MiB ${util}%"
    rows=$(wc -l < "$LEDGER" 2>/dev/null)
    done=$(grep -c '"status": "done"' "$LEDGER" 2>/dev/null)
    echo "ledger rows=${rows:-0} done=${done:-0}"

    # Default 900-second cycle retains the 15-minute stale cleanup cadence.
    "$PY" scripts/reset_stale_cron.py 2>&1 | head -2

    while IFS= read -r L || [ -n "$L" ]; do
      case "$L" in
        ''|'#'*) continue ;;
        *[!A-Za-z0-9_-]*) echo "SKIP invalid active lane name: $L"; continue ;;
      esac
      SCRIPT=$ROOT/scripts/$L.sh
      LANE_LOCK=$LOCK_DIR/lane_$L.lock
      PID_FILE=$STATE_DIR/$L.launcher.pid
      observe_launcher "$L"
      [ -f "$SCRIPT" ] || {
        echo "SKIP $L (missing $SCRIPT)"
        continue
      }

      # Lock first, then recheck mutable launch conditions while holding it.
      exec 8>>"$LANE_LOCK" || continue
      if ! flock -n 8; then
        echo "SKIP $L (lifecycle flock held)"
        exec 8>&-
        continue
      fi
      if ! grep -F -x -- "$L" "$ACTIVE" >/dev/null 2>&1; then
        echo "SKIP $L (removed from active whitelist)"
        exec 8>&-
        continue
      fi
      if [ ! -f "$SCRIPT" ]; then
        echo "SKIP $L (script removed before launch)"
        exec 8>&-
        continue
      fi

      # The launcher inherits locked FD 8 and execs the real lane bash, which
      # keeps it for life. This monitor closes its copy immediately: no TTL.
      setsid nohup bash "$SCRIPT" >> /dev/null 2>&1 < /dev/null &
      launcher_pid=$!
      printf '%s\n' "$launcher_pid" > "$PID_FILE"
      exec 8>&-
      echo "START $L launcher_pid=$launcher_pid lifecycle_lock=$LANE_LOCK"
    done < "$ACTIVE"

    nfin=$(pgrep -fc "rnafteval.finetune" 2>/dev/null || true)
    nfin=${nfin:-0}
    echo "finetune_procs=$nfin"
    if [ "$used" -lt 20000 ]; then
      echo "WARN: GPU under-used (${used}MiB, ${nfin} procs)"
    fi
  ) 9>&- >> "$LOG" 2>&1

  [ "$ONCE" = 1 ] && break
  sleep "$INTERVAL" 9>&-
done
