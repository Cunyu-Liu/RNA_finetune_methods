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
EXTERNAL = REPO / "scripts/mrl_external_nuc_tuning_default_14_jobs_20261112.json"
EXTERNAL_SELECTION = STATUS / "mrl_nuc_lr_selection_20261112.json"
EXTERNAL_TUNED = STATUS / "mrl_nuc_tuned_jobs_20261112.json"
MAIN_SELECTION = STATUS / "lr_validation_selection_20261111.json"
MAIN_TUNED = STATUS / "lr_tuned_jobs_20261111.json"
LORA_TUNING = REPO / "scripts/lr_lora_tuning_jobs_20261112.json"
LORA_SELECTION = STATUS / "lr_lora_validation_selection_20261112.json"
LORA_TUNED = STATUS / "lr_lora_tuned_jobs_20261112.json"
DORA = REPO / "scripts/dora_rank8_240_jobs_20261111.json"
PREDICTIONS = STATUS / "mrl_external_predictions_20261111"


def external_predictions_ready(log):
    from monitor_mrl_external_predictions import evaluation_path, is_valid

    jobs = load_jobs(EXTERNAL_TUNED)
    if len(jobs) != 6 or any(job.model != "NucleicBERT" for job in jobs):
        raise ValueError("external tuned registry must contain exactly six NucleicBERT jobs")
    missing = [job.rid for job in jobs
               if not is_valid(evaluation_path(PREDICTIONS, job.rid), job.rid)]
    log.write(json.dumps({"external_prediction_proof": "complete" if not missing else "pending",
                          "missing": missing}) + "\n")
    log.flush()
    return not missing


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
    state_dir = STATE / registry.stem
    previous_queue = (state_dir / "manifest.jsonl").exists() or (state_dir / "queue.log").exists()
    if done and previous_queue:
        raise RuntimeError(f"queue exited with incomplete cells: {registry}: {counts}")
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


def write_lora_tuning_registry():
    if LORA_TUNING.exists():
        return
    from expansion_jobs import lr_tuning_jobs
    jobs = lr_tuning_jobs(strategy="lora")
    assert len(jobs) == 320 and len({job["rid"] for job in jobs}) == 320
    LORA_TUNING.write_text(json.dumps(jobs, ensure_ascii=False, indent=2) + "\n")


E6_JOBS = REPO / "scripts/rinalmo_e6_checkpoint_jobs_20261112.json"
E6_STATE = STATUS / "rinalmo_e6_checkpoint_monitor_20261112/state.json"
E6_PID = STATE / "rinalmo_e6_checkpoint_monitor.pid"


def ensure_e6_queue(log):
    if E6_STATE.exists():
        state = json.loads(E6_STATE.read_text())
        if state.get("total") == 39 and state.get("completed") == 39:
            return True
    result = subprocess.run(["pgrep", "-af", "monitor_rinalmo_forgetting.py.*--jobs-json"],
                            text=True, capture_output=True)
    live = [line for line in result.stdout.splitlines() if line and "pgrep -af" not in line]
    if live:
        return False
    if E6_PID.exists():
        raise RuntimeError("RiNALMo forgetting monitor exited before 39 complete proofs")
    env = dict(os.environ, PYTHONPATH=".:scripts",
               RNAFT_ARTIFACT_ROOT="/teams/HoulabData_1788502323/liucunyu/rna-ft-eval/artifacts")
    with (STATE / "rinalmo_e6_checkpoint_monitor.log").open("a") as output:
        process = subprocess.Popen([
            sys.executable, "scripts/monitor_rinalmo_forgetting.py",
            "--jobs-json", str(E6_JOBS), "--state-dir", str(E6_STATE.parent),
            "--workers", "2", "--poll-s", "300",
        ], cwd=REPO, env=env, stdout=output, stderr=subprocess.STDOUT, start_new_session=True)
    E6_PID.write_text(json.dumps({"pid": process.pid, "jobs": str(E6_JOBS)})+"\n")
    log.write(json.dumps({"started": E6_JOBS.name, "pid": process.pid})+"\n")
    log.flush()
    return False


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
            "--expected-groups", "2",
        ], cwd=REPO, check=True, env=dict(
            os.environ, PYTHONPATH=".:scripts",
            RNAFT_ARTIFACT_ROOT="/teams/HoulabData_1788502323/liucunyu/rna-ft-eval/artifacts"))
    if not ensure_queue(EXTERNAL_TUNED, 2, log):
        return "external_tuned_running"
    if not external_predictions_ready(log):
        return "external_prediction_review"
    if not ensure_queue(MAIN_TUNED, 2, log):
        return "main_tuned_running"
    write_lora_tuning_registry()
    if not ensure_queue(LORA_TUNING, 2, log):
        return "lora_tuning_running"
    if not LORA_TUNED.exists():
        subprocess.run([
            sys.executable,
            "scripts/select_lr_validation.py",
            "--strategy", "lora",
            "--tuning-jobs", str(LORA_TUNING),
            "--selection-output", str(LORA_SELECTION),
            "--jobs-output", str(LORA_TUNED),
        ], cwd=REPO, check=True, env=dict(
            os.environ, PYTHONPATH=".:scripts",
            RNAFT_ARTIFACT_ROOT="/teams/HoulabData_1788502323/liucunyu/rna-ft-eval/artifacts"))
    if not ensure_queue(LORA_TUNED, 2, log):
        return "lora_tuned_running"
    write_dora_registry()
    if not ensure_queue(DORA, 2, log):
        return "dora_running"
    if not ensure_e6_queue(log):
        return "rinalmo_forgetting_running"
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
