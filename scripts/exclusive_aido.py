#!/usr/bin/env python3
"""Run the AIDO MRL s43 cell in a cooperative, exclusive GPU window."""
from __future__ import annotations

import argparse
import contextlib
import fcntl
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from rnafteval import ledger

MODEL = "AIDO.RNA-1.6B"
TASK = "mrl"
STRATEGY = "full"
SEED = 43
SPLIT = "random"
LR = 1e-5
EPOCHS = 3
RUN_ID = ledger.run_id(MODEL, TASK, STRATEGY, SEED, SPLIT,
                       extra="_lr%g" % LR)
ARTIFACTS_ROOT = Path("/root/rna-ft-eval/artifacts")
FLAG = Path("/root/rnaft/EXCLUSIVE_AIDO")
LOCK_PATH = Path("/tmp/rnaft_aido_exclusive.lock")
AUDIT_SCRIPT = REPO_ROOT / "scripts" / "audit_1016.py"
TIMEOUT_S = 12 * 60 * 60
POLL_S = 15
DRAIN_STABLE_S = 30
WAIT_LOG_S = 300
GPU_SAFE_MIB = 512
DEVICE = 0
PROCESS_RE = re.compile(
    r"(?:^|\s)-m\s+rnafteval\.(?:finetune[\w.]*|e6_forget(?:_task)?)(?:\s|$)")


class AlreadyRunning(Exception):
    pass


def result_path():
    return ARTIFACTS_ROOT / RUN_ID / "result.json"


def training_command():
    return [
        sys.executable, "-m", "rnafteval.finetune_mrl",
        "--model", MODEL, "--task", TASK, "--strategy", STRATEGY,
        "--seed", str(SEED), "--split", SPLIT, "--device", str(DEVICE),
        "--epochs", str(EPOCHS), "--batch-size", "1", "--lr", "1e-05",
    ]


def protocol_error(payload):
    if not isinstance(payload, dict):
        return "JSON is not an object"
    expected = {
        "run_id": RUN_ID, "model": MODEL, "task": TASK,
        "strategy": STRATEGY, "seed": SEED, "split": SPLIT,
        "lr": LR, "epochs": EPOCHS,
    }
    errors = ["%s mismatch" % key for key, value in expected.items()
              if payload.get(key) != value]
    if payload.get("metric") != "PEARSON_R":
        errors.append("metric mismatch")
    value = payload.get("value")
    try:
        finite = (not isinstance(value, bool)
                  and isinstance(value, (int, float)) and math.isfinite(value))
    except (TypeError, ValueError, OverflowError):
        finite = False
    if not finite:
        errors.append("PEARSON_R is not finite numeric")
    return "; ".join(errors)


def proof_state():
    """complete = runner ledger/result double proof; never repairs evidence."""
    row = ledger.by_run_id(RUN_ID)
    ledger_done = bool(row and row.get("status") == "done")
    if ledger_done:
        error = protocol_error(row)
        if error:
            return "conflict", "ledger " + error
    path = result_path()
    if not path.exists():
        if ledger_done:
            return "conflict", "ledger done but result.json is missing"
        return "runnable", ""
    try:
        with path.open() as fh:
            payload = json.load(fh)
    except (OSError, ValueError) as exc:
        return "conflict", "invalid result.json: %s" % exc
    error = protocol_error(payload)
    if error:
        return "conflict", "result " + error
    if not ledger_done:
        return "conflict", "valid result.json but ledger is not done"
    return "complete", ""


def audit_status():
    try:
        proc = subprocess.run(
            [sys.executable, str(AUDIT_SCRIPT)], cwd=str(REPO_ROOT),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            check=False)
    except OSError as exc:
        return False, "audit launch failed: %s" % exc
    output = proc.stdout.strip()
    if proc.returncode == 0 and output == "0":
        return True, ""
    return False, "audit_1016 rc=%s output=%r stderr=%r" % (
        proc.returncode, output, proc.stderr.strip())


def verify_complete():
    state, reason = proof_state()
    if state != "complete":
        print("AIDO_VERIFY_INCOMPLETE %s" % reason, file=sys.stderr)
        return 1
    ok, reason = audit_status()
    if not ok:
        print("AIDO_VERIFY_INCOMPLETE %s" % reason, file=sys.stderr)
        return 1
    print("AIDO_VERIFY_COMPLETE run_id=%s audit=0" % RUN_ID)
    return 0


def training_processes():
    proc = subprocess.run(["ps", "-eo", "pid=,args="],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError("ps failed rc=%s: %s" % (
            proc.returncode, proc.stderr.strip()))
    matches = []
    for line in proc.stdout.splitlines():
        if not PROCESS_RE.search(line):
            continue
        fields = line.strip().split(None, 1)
        if fields and fields[0].isdigit() and int(fields[0]) != os.getpid():
            matches.append(int(fields[0]))
    return sorted(set(matches))


def gpu_state():
    common = ["-i", str(DEVICE), "--format=csv,noheader,nounits"]
    memory = subprocess.run(
        ["nvidia-smi", *common, "--query-gpu=memory.used"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
    apps = subprocess.run(
        ["nvidia-smi", *common, "--query-compute-apps=pid"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
    if memory.returncode != 0 or apps.returncode != 0:
        raise RuntimeError("nvidia-smi failed memory_rc=%s apps_rc=%s" % (
            memory.returncode, apps.returncode))
    try:
        used = int(memory.stdout.strip().splitlines()[0])
    except (IndexError, ValueError) as exc:
        raise RuntimeError("invalid nvidia-smi memory output: %r" %
                           memory.stdout) from exc
    compute_pids = [line.strip() for line in apps.stdout.splitlines()
                    if line.strip()]
    return used, compute_pids


def drain_status():
    processes = training_processes()
    used, compute_pids = gpu_state()
    # Idle dispatcher parents may retain a small CUDA context while waiting.
    # They do not block AIDO; only live training and total memory matter.
    safe = not processes and used <= GPU_SAFE_MIB
    detail = "finetune_e6_pids=%s gpu_used_mib=%d compute_pids=%s" % (
        processes, used, compute_pids)
    return safe, detail


def wait_for_drain():
    safe_since = None
    next_log = 0.0
    while True:
        safe, detail = drain_status()
        now = time.monotonic()
        if safe:
            if safe_since is None:
                safe_since = now
            if now - safe_since >= DRAIN_STABLE_S:
                print("AIDO_DRAIN_COMPLETE " + detail, flush=True)
                return
        else:
            safe_since = None
        if now >= next_log:
            print("AIDO_WAIT_DRAIN " + detail, flush=True)
            next_log = now + WAIT_LOG_S
        time.sleep(POLL_S)


def set_flag():
    FLAG.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(FLAG.parent),
                                    prefix=FLAG.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as fh:
            json.dump({"pid": os.getpid(), "run_id": RUN_ID}, fh)
        os.replace(tmp_name, FLAG)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
        raise


def clear_flag():
    try:
        FLAG.unlink()
    except FileNotFoundError:
        pass


@contextlib.contextmanager
def lifecycle_lock():
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOCK_PATH.open("a+") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise AlreadyRunning from exc
        try:
            yield
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def run_exclusive():
    flagged = False
    try:
        # The lifecycle lock makes replacing a flag left by a dead owner safe.
        set_flag()
        flagged = True
        state, reason = proof_state()
        if state == "conflict":
            print("AIDO_CONFLICT " + reason, file=sys.stderr, flush=True)
            return 1
        if state != "complete":
            wait_for_drain()
            # A pre-existing child may have completed this exact cell while draining.
            state, reason = proof_state()
            if state == "conflict":
                print("AIDO_CONFLICT " + reason, file=sys.stderr, flush=True)
                return 1
        if state == "complete":
            ok, reason = audit_status()
            if not ok:
                print("AIDO_AUDIT_FAILED " + reason, file=sys.stderr, flush=True)
                return 1
            print("AIDO_ALREADY_COMPLETE run_id=%s audit=0" % RUN_ID, flush=True)
            return 0

        print("AIDO_RUN run_id=%s timeout_s=%d" % (RUN_ID, TIMEOUT_S), flush=True)
        try:
            proc = subprocess.run(training_command(), cwd=str(REPO_ROOT),
                                  timeout=TIMEOUT_S, check=False)
            rc = proc.returncode
        except subprocess.TimeoutExpired:
            print("AIDO_TIMEOUT timeout_s=%d" % TIMEOUT_S,
                  file=sys.stderr, flush=True)
            return 1
        except OSError as exc:
            print("AIDO_LAUNCH_FAILED %s" % exc, file=sys.stderr, flush=True)
            return 1
        if rc != 0:
            print("AIDO_RUN_FAILED rc=%s" % rc, file=sys.stderr, flush=True)
            return 1
        state, reason = proof_state()
        if state != "complete":
            print("AIDO_PROOF_FAILED " + (reason or "rc=0 without double proof"),
                  file=sys.stderr, flush=True)
            return 1
        ok, reason = audit_status()
        if not ok:
            print("AIDO_AUDIT_FAILED " + reason, file=sys.stderr, flush=True)
            return 1
        print("AIDO_DONE run_id=%s audit=0" % RUN_ID, flush=True)
        return 0
    finally:
        if flagged:
            clear_flag()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-complete", action="store_true",
                        help="read-only double-proof plus audit_1016=0 gate")
    args = parser.parse_args(argv)
    if args.verify_complete:
        return verify_complete()
    try:
        with lifecycle_lock():
            return run_exclusive()
    except AlreadyRunning:
        print("AIDO_DUPLICATE lock=%s" % LOCK_PATH, file=sys.stderr)
        return 75
    except Exception as exc:
        print("AIDO_ERROR %s: %s" % (type(exc).__name__, exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
