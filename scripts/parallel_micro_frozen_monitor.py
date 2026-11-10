#!/usr/bin/env python3
"""Keep measured-small micro Frozen cells parallel during non-micro core work."""
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

import expansion_queue as q

STATUS = Path('/teams/HoulabData_1788502323/liucunyu/rna-ft-eval/status')
SOURCE = STATUS / 'c5c_frozen_jobs_20261101.json'
STATE_DIR = STATUS / 'remaining_pipeline_20261103'
STATE_PATH = STATUS / 'parallel_micro_frozen_monitor_state.json'
LOCK_PATH = STATUS / 'parallel_micro_frozen_monitor.lock'


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def write_state(stage, **fields):
    value = {'stage': stage, 'updated_at': utc_now(), 'pid': os.getpid(), **fields}
    tmp = STATE_PATH.with_suffix('.json.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    tmp.replace(STATE_PATH)
    print(json.dumps(value, ensure_ascii=False), flush=True)


def core_training_processes():
    output = subprocess.check_output(['ps', '-eo', 'pid,args'], text=True)
    processes = []
    for line in output.splitlines():
        pid, command = line.strip().split(None, 1)
        if '-m rnafteval.' not in command:
            continue
        if '--strategy frozen' in command and '--model RiNALMo-micro' in command:
            continue
        processes.append({'pid': int(pid), 'command': command})
    return processes


def select_jobs(workers=14):
    raw = json.loads(SOURCE.read_text())
    by_rid = {item['rid']: item for item in raw}
    jobs = []
    for job in q.load_jobs(SOURCE):
        if job.model != 'RiNALMo-micro' or '_dense_' in job.rid:
            continue
        state, reason = q.proof_state(job)
        if state in ('complete', 'running'):
            continue
        if state != 'runnable':
            raise RuntimeError(f'{job.rid}: {state}: {reason}')
        item = dict(by_rid[job.rid])
        item['need_gb'] = 1.5 if job.task == 'noncoding-rna-family' else 0.75
        jobs.append((job, item))
        if len(jobs) == workers:
            break
    result = []
    for job, item in jobs:
        job.need_gb = item['need_gb']
        result.append((job, item))
    return result


def write_registry(items, label):
    path = STATUS / f'queue_actions/parallel_micro_frozen_{label}.json'
    path.write_text(json.dumps([item for _, item in items], ensure_ascii=False, indent=2) + '\n')
    checked = q.load_jobs(path)
    assert [job.rid for job in checked] == [job.rid for job, _ in items]
    return path


def wait_attached(pid, poll_s):
    while Path(f'/proc/{pid}').exists():
        write_state('attached_batch_running', attached_pid=pid,
                    core_processes=core_training_processes())
        time.sleep(poll_s)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workers', type=int, default=14)
    parser.add_argument('--poll-s', type=float, default=60)
    parser.add_argument('--attach-pid', type=int)
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--once', action='store_true')
    args = parser.parse_args()
    if args.workers < 1 or args.poll_s <= 0:
        parser.error('workers must be positive and poll-s must be > 0')
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOCK_PATH.open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            write_state('blocked', reason='another parallel micro Frozen monitor holds the lock')
            return 2
        if args.prepare_only:
            items = select_jobs(args.workers)
            path = write_registry(items, 'next_prepared')
            write_state('prepared', registry=str(path), rids=[job.rid for job, _ in items],
                        registry_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
            return 0
        if args.attach_pid:
            wait_attached(args.attach_pid, args.poll_s)
            attached = q.load_jobs(STATUS / 'queue_actions/parallel_micro_frozen_jobs_20261110.json')
            if q.verify_jobs(attached):
                write_state('blocked', reason='attached batch has incomplete proof')
                return 1
        while True:
            core = core_training_processes()
            if not core:
                write_state('waiting_core_process')
                if args.once:
                    return 0
                time.sleep(args.poll_s)
                continue
            items = select_jobs(args.workers)
            if not items:
                write_state('complete')
                return 0
            label = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S')
            path = write_registry(items, label)
            write_state('batch_running', registry=str(path),
                        registry_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                        rids=[job.rid for job, _ in items], core_processes=core)
            jobs = [job for job, _ in items]
            rc = q.dispatch(jobs, workers=args.workers, state_dir=STATE_DIR,
                            poll_s=15, allow_same_model=True)
            if rc or q.verify_jobs(jobs):
                write_state('blocked', registry=str(path), returncode=rc,
                            reason='batch failed or proof incomplete')
                return 1
            write_state('batch_complete', registry=str(path), completed=len(jobs))
            if args.once:
                return 0
            time.sleep(args.poll_s)


if __name__ == '__main__':
    raise SystemExit(main())
