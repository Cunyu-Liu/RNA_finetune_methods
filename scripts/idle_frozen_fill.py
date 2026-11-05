#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import torch

from expansion_queue import load_jobs, proof_state

STATUS = Path('/teams/HoulabData_1788502323/liucunyu/rna-ft-eval/status')
ARTIFACTS = Path('/teams/HoulabData_1788502323/liucunyu/rna-ft-eval/artifacts')
SOURCE = STATUS / 'c5c_frozen_jobs_20261101.json'
STATE_DIR = STATUS / 'remaining_pipeline_20261103'
REGISTRY = STATUS / 'queue_actions/idle_frozen_fill_current.json'
STATE_PATH = STATUS / 'idle_frozen_fill_20261104_state.json'
LOCK_PATH = STATUS / 'idle_frozen_fill_20261104.lock'
LOG_PATH = STATUS / 'idle_frozen_fill_20261104.log'


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def write_state(stage, **fields):
    value = {'stage': stage, 'updated_at': utc_now(), **fields}
    tmp = STATE_PATH.with_suffix('.json.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    tmp.replace(STATE_PATH)
    print(json.dumps(value, ensure_ascii=False), flush=True)


def memory_allows(free_gb, need_gb=9.0, core_window_gb=19.0):
    return need_gb <= free_gb < core_window_gb


def large_gpu_processes(threshold_mb=12000):
    output = subprocess.check_output([
        'nvidia-smi', '--query-compute-apps=pid,used_memory',
        '--format=csv,noheader,nounits',
    ], text=True)
    processes = []
    for line in output.splitlines():
        pid, memory = line.rsplit(',', 1)
        used_mb = int(memory.strip())
        if used_mb >= threshold_mb:
            processes.append({'pid': int(pid), 'used_mb': used_mb})
    return processes


def next_runnable(jobs, proof=proof_state):
    for job in jobs:
        if job.model != 'RiNALMo-micro' or '_dense_' in job.rid:
            continue
        state, reason = proof(job)
        if state == 'runnable':
            return job
        if state != 'complete':
            raise RuntimeError(f'{job.rid}: {state}: {reason}')
    return None


def child_env():
    return dict(os.environ, RNAFT_ARTIFACT_ROOT=str(ARTIFACTS))


def prepare_registry(job):
    raw = json.loads(SOURCE.read_text())
    matches = [dict(item) for item in raw if item['rid'] == job.rid]
    assert len(matches) == 1
    matches[0]['need_gb'] = job.need_gb + 1.0
    REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    tmp = REGISTRY.with_suffix('.json.tmp')
    tmp.write_text(json.dumps(matches, ensure_ascii=False, indent=2) + '\n')
    tmp.replace(REGISTRY)
    checked = load_jobs(REGISTRY)
    assert len(checked) == 1 and checked[0].rid == job.rid
    return checked[0]


def run_cell(job, poll_s):
    registered = prepare_registry(job)
    command = [sys.executable, 'scripts/expansion_queue.py', '--jobs-json', str(REGISTRY),
               '--workers', '1', '--device', '0', '--state-dir', str(STATE_DIR),
               '--poll-s', str(poll_s)]
    write_state('launching', rid=job.rid, need_gb=registered.need_gb,
                registry_sha256=hashlib.sha256(REGISTRY.read_bytes()).hexdigest())
    with LOG_PATH.open('a') as log:
        completed = subprocess.run(command, cwd=Path(__file__).resolve().parents[1],
                                   stdout=log, stderr=subprocess.STDOUT, env=child_env())
    state, reason = proof_state(registered)
    if completed.returncode != 0 or state != 'complete':
        write_state('blocked', rid=job.rid, returncode=completed.returncode,
                    proof_state=state, reason=reason)
        return False
    write_state('cell_complete', rid=job.rid, proof_state=state)
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--once', action='store_true')
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--poll-s', type=float, default=60.0)
    parser.add_argument('--core-window-gb', type=float, default=19.0)
    args = parser.parse_args()
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOCK_PATH.open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            write_state('blocked', reason='another idle Frozen monitor holds the lock')
            return 2
        jobs = load_jobs(SOURCE)
        candidate = next_runnable(jobs)
        if candidate is None:
            write_state('complete')
            return 0
        if args.prepare_only:
            write_state('prepared', rid=candidate.rid,
                        candidates=sum(j.model == 'RiNALMo-micro' and '_dense_' not in j.rid for j in jobs))
            return 0
        while True:
            free_gb = torch.cuda.mem_get_info(0)[0] / 1024 ** 3
            candidate = next_runnable(jobs)
            if candidate is None:
                write_state('complete')
                return 0
            need_gb = candidate.need_gb + 1.0
            if not memory_allows(free_gb, need_gb, args.core_window_gb):
                write_state('waiting_core_window' if free_gb >= args.core_window_gb else 'waiting_memory',
                            free_gb=free_gb, need_gb=need_gb, core_window_gb=args.core_window_gb)
            elif large_gpu_processes():
                write_state('waiting_core_process', free_gb=free_gb,
                            large_processes=large_gpu_processes())
            elif not run_cell(candidate, args.poll_s):
                return 1
            if args.once:
                return 0
            time.sleep(args.poll_s)


if __name__ == '__main__':
    raise SystemExit(main())
