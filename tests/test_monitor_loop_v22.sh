#!/bin/bash
# Local integration test: no training, GPU, ledger, network, or remote access.
set -eu

REPO=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
MONITOR=$REPO/scripts/monitor_loop_v22.sh
TMP_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/monitor-v22-test.XXXXXX")
ROOT=$TMP_ROOT/root
RNAFT=$TMP_ROOT/rnaft
STUB_BIN=$TMP_ROOT/bin
TEST_STARTS=$TMP_ROOT/lane.starts
TEST_LEGACY=$TMP_ROOT/legacy.started
TEST_MASTER=$TMP_ROOT/master.started
GPU_CALLS=$TMP_ROOT/gpu.calls
STALE_CALLS=$TMP_ROOT/stale.calls
PHASE_CALLS=$TMP_ROOT/phase.calls
CORRECTED_CALLS=$TMP_ROOT/corrected.calls
V2_PROOF_CALLS=$TMP_ROOT/v2-proof.calls
AIDO_CALLS=$TMP_ROOT/aido.calls
COMPLETION_STARTS=$TMP_ROOT/completion.starts
export TEST_STARTS TEST_LEGACY TEST_MASTER GPU_CALLS STALE_CALLS
export PHASE_CALLS CORRECTED_CALLS V2_PROOF_CALLS AIDO_CALLS COMPLETION_STARTS
TEST_PYTHON=$(command -v python3)
export TEST_PYTHON
mkdir -p "$ROOT/scripts" "$RNAFT/logs" "$STUB_BIN"

MONITOR_PIDS=()
cleanup() {
  rc=$?
  trap - EXIT
  for pid in ${MONITOR_PIDS[@]+"${MONITOR_PIDS[@]}"}; do
    kill "$pid" 2>/dev/null || true
    wait "$pid" 2>/dev/null || true
  done
  if [ -r "$TEST_STARTS" ]; then
    while IFS= read -r pid; do
      case "$pid" in ''|*[!0-9]*) ;; *) kill "$pid" 2>/dev/null || true ;; esac
    done < "$TEST_STARTS"
  fi
  rm -rf "$TMP_ROOT"
  exit "$rc"
}
trap cleanup EXIT

fail() {
  echo "FAIL: $*" >&2
  exit 1
}
assert_eq() {
  [ "$1" = "$2" ] || fail "$3 (expected=$1 actual=$2)"
}
start_count() {
  if [ -r "$TEST_STARTS" ]; then
    wc -l < "$TEST_STARTS" | tr -d ' '
  else
    echo 0
  fi
}
last_lane_pid() {
  tail -n 1 "$TEST_STARTS" | tr -d ' '
}
assert_alive() {
  kill -0 "$1" 2>/dev/null || fail "process $1 is not alive"
}

# util-linux flock is absent on the local Mac. This test-only shim exercises
# the same inherited-FD, nonblocking fcntl.flock semantics used by `flock -n FD`.
cat > "$STUB_BIN/flock" <<'EOF'
#!/usr/bin/env python3
import fcntl
import sys

if len(sys.argv) != 3 or sys.argv[1] not in ("-n", "--nonblock"):
    sys.exit(2)
try:
    fd = int(sys.argv[2])
    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
except (ValueError, OSError):
    sys.exit(1)
EOF
cat > "$STUB_BIN/setsid" <<'EOF'
#!/bin/sh
exec "$@"
EOF
cat > "$STUB_BIN/nvidia-smi" <<'EOF'
#!/bin/sh
echo call >> "$GPU_CALLS"
case "$*" in
  *memory.used*) echo 123 ;;
  *utilization.gpu*) echo 45 ;;
  *) exit 2 ;;
esac
EOF
cat > "$STUB_BIN/pgrep" <<'EOF'
#!/bin/sh
echo 0
exit 1
EOF
chmod +x "$STUB_BIN/flock" "$STUB_BIN/setsid" "$STUB_BIN/nvidia-smi" "$STUB_BIN/pgrep"

cat > "$TMP_ROOT/fake_python" <<'EOF'
#!/bin/sh
case "$1" in
  scripts/reset_stale_cron.py)
    echo call >> "$STALE_CALLS"
    echo stale-ok
    ;;
  scripts/e6_phase.py)
    echo call >> "$PHASE_CALLS"
    echo phase-ok
    ;;
  scripts/q_corrected_8task.py)
    [ "$2" = --verify-complete ] || exit 98
    echo call >> "$CORRECTED_CALLS"
    ;;
  scripts/exclusive_aido.py)
    [ "$2" = --verify-complete ] || exit 98
    echo call >> "$AIDO_CALLS"
    exit "${AIDO_VERIFY_RC:-0}"
    ;;
  scripts/e6_mlm15_proof.py)
    echo call >> "$V2_PROOF_CALLS"
    ;;
  *) exit 97 ;;
esac
exit 0
EOF
chmod +x "$TMP_ROOT/fake_python"

cat > "$ROOT/scripts/q_test.sh" <<'EOF'
#!/bin/bash
echo "$$" >> "$TEST_STARTS"
exec "$TEST_PYTHON" -c 'import time; time.sleep(300)'
EOF
cat > "$ROOT/scripts/q_legacy.sh" <<'EOF'
#!/bin/bash
echo started >> "$TEST_LEGACY"
EOF
cat > "$ROOT/scripts/q_master.sh" <<'EOF'
#!/bin/bash
echo started >> "$TEST_MASTER"
EOF
echo q_test > "$ROOT/scripts/active_lanes.txt"
printf '%s\n' '{"status":"running"}' '{"status": "done"}' > "$RNAFT/ledger.jsonl"

ENV_BASE=(
  env
  "PATH=$STUB_BIN:$PATH"
  "MONITOR_V22_ROOT=$ROOT"
  "MONITOR_V22_RNAFT=$RNAFT"
  "MONITOR_V22_PY=$TMP_ROOT/fake_python"
  "MONITOR_V22_LOCK_DIR=$TMP_ROOT/locks"
  "MONITOR_V22_INTERVAL=1"
  "MONITOR_V22_E6_ARTIFACTS=$TMP_ROOT/e6"
  "E6_MODEL_FILE=$RNAFT/e6_mlm15_models.active"
)
ONCE_SEQ=0
run_once() {
  ONCE_SEQ=$((ONCE_SEQ + 1))
  if [ "$1" = absolute ]; then
    "${ENV_BASE[@]}" MONITOR_V22_ONCE=1 bash "$MONITOR" \
      > "$TMP_ROOT/once.$ONCE_SEQ.out" 2>&1
  else
    (cd "$REPO" && exec "${ENV_BASE[@]}" MONITOR_V22_ONCE=1 \
      bash scripts/monitor_loop_v22.sh) \
      > "$TMP_ROOT/once.$ONCE_SEQ.out" 2>&1
  fi
}
start_monitor() {
  i=$1
  if [ "$2" = absolute ]; then
    "${ENV_BASE[@]}" bash "$MONITOR" > "$TMP_ROOT/monitor.$i.out" 2>&1 &
  else
    (cd "$REPO" && exec "${ENV_BASE[@]}" bash scripts/monitor_loop_v22.sh) \
      > "$TMP_ROOT/monitor.$i.out" 2>&1 &
  fi
  MONITOR_PIDS[$i]=$!
}

# Four simultaneous launchers use both invocation forms. Exactly one monitor
# may own FD 9, and exactly one dummy executor may be created.
start_monitor 0 absolute
start_monitor 1 relative
start_monitor 2 absolute
start_monitor 3 relative
tries=0
while [ "$(start_count)" -lt 1 ]; do
  tries=$((tries + 1))
  [ "$tries" -lt 100 ] || fail "first lane did not start"
  sleep 0.1
done

winner=
tries=0
while :; do
  alive=0
  candidate=
  for pid in "${MONITOR_PIDS[@]}"; do
    state=$(ps -p "$pid" -o stat= 2>/dev/null || true)
    if kill -0 "$pid" 2>/dev/null && [[ "$state" != *Z* ]]; then
      alive=$((alive + 1))
      candidate=$pid
    fi
  done
  if [ "$alive" -eq 1 ]; then
    winner=$candidate
    break
  fi
  tries=$((tries + 1))
  [ "$tries" -lt 100 ] || fail "expected one live monitor, got $alive"
  sleep 0.1
done
for pid in "${MONITOR_PIDS[@]}"; do
  if [ "$pid" != "$winner" ]; then
    if wait "$pid"; then rc=0; else rc=$?; fi
    assert_eq 75 "$rc" "second monitor must reject the held monitor flock"
  fi
done
assert_eq 1 "$(start_count)" "concurrent launch created duplicate executors"
lane1=$(last_lane_pid)
assert_alive "$lane1"
grep -q 'START q_test launcher_pid=' "$RNAFT/logs/monitor_loop.log" || \
  fail "launcher PID was not logged"

# SIGKILL the monitor, not the lane. A relative-path one-cycle monitor must
# acquire the released monitor lock, observe the old launcher, and not respawn.
kill -9 "$winner"
wait "$winner" 2>/dev/null || true
run_once relative
assert_eq 1 "$(start_count)" "absolute/relative paths bypassed the lane lock"
assert_alive "$lane1"
grep -q 'OBSERVE q_test launcher_pid=' "$RNAFT/logs/monitor_loop.log" || \
  fail "next cycle did not observe the recorded launcher PID"

# Historical DONE is not completion evidence. After actual executor SIGKILL,
# its inherited lock is released and a whitelisted replacement starts once.
echo '=== q_test DONE historical text ===' >> "$RNAFT/logs/q_test.log"
kill -9 "$lane1"
tries=0
while [ "$(start_count)" -lt 2 ]; do
  run_once absolute
  tries=$((tries + 1))
  [ "$tries" -lt 20 ] || fail "SIGKILL did not release the lane lifecycle lock"
  sleep 0.1
done
lane2=$(last_lane_pid)
[ "$lane2" != "$lane1" ] || fail "replacement reused the dead executor PID"
assert_alive "$lane2"
run_once relative
assert_eq 2 "$(start_count)" "live replacement was duplicated"

# Removal still stops an ordinary lane; q_master/legacy never revive.
echo '# no active lanes' > "$ROOT/scripts/active_lanes.txt"
kill -9 "$lane2"
sleep 0.1
run_once absolute
run_once relative
assert_eq 2 "$(start_count)" "removed lane was revived"
[ ! -e "$TEST_LEGACY" ] || fail "legacy lane was revived"
[ ! -e "$TEST_MASTER" ] || fail "q_master was revived"

grep -q 'GPU: 123MiB 45%' "$RNAFT/logs/monitor_loop.log" || fail "GPU snapshot stub missing"
grep -Eq 'ledger rows=[[:space:]]*2 done=1' "$RNAFT/logs/monitor_loop.log" || fail "ledger snapshot missing"
grep -q 'stale-ok' "$RNAFT/logs/monitor_loop.log" || fail "stale cleanup stub missing"
grep -q 'finetune_procs=0' "$RNAFT/logs/monitor_loop.log" || fail "process snapshot missing"

# Verified-complete AIDO/corrected/E6 lanes stay whitelisted but are not restarted.
# q_crisprfill has no completion gate and still starts despite historical DONE.
for lane in q_aido_exclusive q_corrected_8task q_e6_mlm15fix q_e6_v2_mlm15fix q_crisprfill; do
  cat > "$ROOT/scripts/$lane.sh" <<EOF
#!/bin/bash
echo $lane >> "$COMPLETION_STARTS"
EOF
done
printf '%s\n' q_aido_exclusive q_corrected_8task q_e6_mlm15fix q_e6_v2_mlm15fix q_crisprfill \
  > "$ROOT/scripts/active_lanes.txt"
echo COMPLETE > "$RNAFT/e6_mlm15_models.active"
echo '=== q_crisprfill DONE historical text ===' > "$RNAFT/logs/q_crisprfill.log"
run_once absolute
tries=0
while [ ! -s "$COMPLETION_STARTS" ]; do
  tries=$((tries + 1))
  [ "$tries" -lt 50 ] || fail "q_crisprfill did not retain normal launch behavior"
  sleep 0.1
done
assert_eq q_crisprfill "$(cat "$COMPLETION_STARTS")" \
  "a verified-complete lane was restarted"
assert_eq 1 "$(wc -l < "$CORRECTED_CALLS" | tr -d ' ')" \
  "corrected verify-complete was not called exactly once"
assert_eq 6 "$(wc -l < "$V2_PROOF_CALLS" | tr -d ' ')" \
  "E6-v2 completion did not check exactly six proofs"
assert_eq 1 "$(wc -l < "$AIDO_CALLS" | tr -d ' ')" \
  "AIDO verify-complete was not called exactly once"
[ -s "$PHASE_CALLS" ] || fail "E6 phase script was not called"
grep -q 'SKIP q_aido_exclusive (AIDO MRL s43' "$RNAFT/logs/monitor_loop.log" || \
  fail "AIDO completion skip was not logged"
grep -q 'SKIP q_corrected_8task (all 342' "$RNAFT/logs/monitor_loop.log" || \
  fail "corrected completion skip was not logged"
grep -q 'SKIP q_e6_mlm15fix (all 30' "$RNAFT/logs/monitor_loop.log" || \
  fail "E6 COMPLETE skip was not logged"
grep -q 'SKIP q_e6_v2_mlm15fix (all 6' "$RNAFT/logs/monitor_loop.log" || \
  fail "E6-v2 completion skip was not logged"

# AIDO without its double-proof/audit gate remains eligible for one retry.
: > "$COMPLETION_STARTS"
echo q_aido_exclusive > "$ROOT/scripts/active_lanes.txt"
export AIDO_VERIFY_RC=1
run_once absolute
tries=0
while [ ! -s "$COMPLETION_STARTS" ]; do
  tries=$((tries + 1))
  [ "$tries" -lt 50 ] || fail "incomplete AIDO lane was not retried"
  sleep 0.1
done
assert_eq q_aido_exclusive "$(cat "$COMPLETION_STARTS")" \
  "incomplete AIDO lane was incorrectly gated"
assert_eq 2 "$(wc -l < "$AIDO_CALLS" | tr -d ' ')" \
  "incomplete AIDO gate was not rechecked"

echo 'test_monitor_loop_v22: PASS (lifecycle locks, whitelist, verified-complete lane gates)'
