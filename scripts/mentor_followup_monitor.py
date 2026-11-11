#!/usr/bin/env python3
import argparse
import collections
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from expansion_jobs import peft_rank_jobs
from expansion_queue import load_jobs, proof_state

REPO = Path(__file__).resolve().parents[1]
STATUS = Path("/teams/HoulabData_1788502323/liucunyu/rna-ft-eval/status")
STATE = STATUS / "mentor_followup_20261111"
P0 = REPO / "scripts/main_remaining_650m_18_jobs_20261111.json"
EXTERNAL = REPO / "scripts/mrl_external_tuning_default_28_jobs_20261111.json"
EXTERNAL_SELECTION = STATUS / "mrl_external_lr_selection_20261111.json"
EXTERNAL_TUNED = STATUS / "mrl_external_tuned_jobs_20261111.json"
MAIN_SELECTION = STATUS / "lr_validation_selection_20261111.json"
MAIN_TUNED = STATUS / "lr_tuned_jobs_20261111.json"
DORA = REPO / "scripts/dora_rank8_240_jobs_20261111.json"


def jobs_status(path):
    counts = collections.Counter()
    for job in load_jobs(path):
        state, reason = proof_state(job)
        counts[state] += 1
        if state == "conflict":
            raise RuntimeError(f"proof conflict: {job.rid}: {reason}")
    return counts


def live_queue(registry):
    result = subprocess.run(["pgrep", "-af", f"expansion_queue.py.*{registry.name}"], text=True, capture_output=True)
    lines = [line for line in result.stdout.splitlines() if line and "pgrep -af" not in line]
    return lines


def ensure_queue(registry, workers, log):
    counts = jobs_status(registry)
    if counts.get("conflict"):
        raise RuntimeError(str(counts))
    running = live_queue(registry)
    done = counts.get("complete", 0)
    total = sum(counts.values())
    log.write(json.dumps({"registry": registry.name, "counts": counts, "queue_processes": running}) + "\n")
    log.flush()
    if done == total:
        return True
    if running:
        return False
    if done:
        raise RuntimeError(f"queue exited with incomplete cells: {registry}: {counts}")
    state_dir = STATE / registry.stem
    state_dir.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env.update({
        "PYTHONPATH": ".:scripts",
        "RNAFT_ARTIFACT_ROOT": "/teams/HoulabData_1788502323/liucunyu/rna-ft-eval/artifacts",
        "HF_HOME": "/root/hf_home",
    })
    with (state_dir / "queue.log").open("a") as queue_log:
        process = subprocess.Popen([
            sys.executable,
            "scripts/expansion_queue.py", "--jobs-json", str(registry),
            "--workers", str(workers), "--state-dir", str(state_dir),
        ], cwd=REPO, env=env, stdout=queue_log, stderr=subprocess.STDOUT, start_new_session=True)
    log.write(json.dumps({"started": registry.name, "pid": process.pid}) + "\n")
    log.flush()
    return False


def write_dora_registry():
    if DORA.exists():
        return
    jobs = [job for job in peft_rank_jobs() if job["strategy"] == "dora"]
    assert len(jobs) == 240
    DORA.write_text(json.dumps(jobs, ensure_ascii=False, indent=2) + "\n")


def run_once(log):
    if not ensure_queue(P0, 2, log):
        return "p0_running"
    if not ensure_queue(EXTERNAL, 2, log):
        return "external_tuning_default_running"
    if not EXTERNAL_TUNED.exists():
        subprocess.run([
            sys.executable,
            "scripts/select_mrl_external_lr.py",
            "--tuning-default-jobs", str(EXTERNAL),
            "--selection-output", str(EXTERNAL_SELECTION),
            "--jobs-output", str(EXTERNAL_TUNED),
        ], cwd=REPO, check=True, env=dict(os.environ, PYTHONPATH=".:scripts"))
    if not ensure_queue(EXTERNAL_TUNED, 2, log):
        return "external_tuned_running"
    if not ensure_queue(MAIN_TUNED, 2, log):
        return "main_tuned_running"
    write_dora_registry()
    if not ensure_queue(DORA, 2, log):
        return "dora_running"
    return "complete"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--poll-s", type=int, default=120)
    args = parser.parse_args()
    STATE.mkdir(parents=True, exist_ok=True)
    with (STATE / "monitor.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with (STATE / "monitor.log").open("a") as log:
            while True:
                stage = run_once(log)
                (STATE / "state.json").write_text(json.dumps({"stage": stage, "updated_at": time.time()}) + "\n")
                if args.once or stage == "complete":
                    print(stage)
                    break
                time.sleep(args.poll_s)


if __name__ == "__main__":
    main()
