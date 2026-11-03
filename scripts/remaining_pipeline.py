#!/usr/bin/env python3
"""Run remaining RNA-LM experiments in stage-gated, memory-bounded queues."""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import fcntl
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import traceback
from pathlib import Path

from expansion_queue import load_jobs, proof_state

STATUS = Path('/teams/HoulabData_1788502323/liucunyu/rna-ft-eval/status')
STATE_DIR = STATUS / 'remaining_pipeline_20261103'
STATE_PATH = STATUS / 'remaining_pipeline_20261103_state.json'
LOCK_PATH = STATUS / 'remaining_pipeline_20261103.lock'
STAGES = {
    'core': [
        'perbase_main_bestval_jobs_20261030.json',
        'complementary_jobs_20261027_pairalign_teams.json',
        'lr_tuning_jobs_20261030_small_first_20261102.json',
    ],
    'frozen': ['c5c_frozen_jobs_20261101.json'],
    'crispr': ['crispr_signal_jobs_20261101.json'],
    'rnasc': ['equivalence_rnasc_jobs_20261030.json'],
}
MARGIN_GB = 1.0


def utc_now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_state(stage, **fields):
    payload = {'stage': stage, 'updated_at': utc_now(), 'pid': os.getpid(), **fields}
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_PATH.with_suffix('.tmp')
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n')
    os.replace(tmp, STATE_PATH)
    print(json.dumps(payload, ensure_ascii=False), flush=True)


def latest_ledger():
    candidates = []
    for path in STATUS.glob('bestval_ledger_export_20261101_v*.csv'):
        match = re.fullmatch(r'bestval_ledger_export_20261101_v(\d+)\.csv', path.name)
        if match:
            candidates.append((int(match.group(1)), path))
    if not candidates:
        raise RuntimeError('no accepted best-val ledger found')
    return max(candidates)[1]


def accepted_run_ids():
    with latest_ledger().open(newline='') as handle:
        return {row['run_id'] for row in csv.DictReader(handle)}


def read_jobs(path):
    raw = json.loads(Path(path).read_text())
    return raw['jobs'] if isinstance(raw, dict) else raw


def build_stage_registry(stage):
    if stage not in STAGES:
        raise ValueError(f'unknown stage: {stage}')
    accepted = accepted_run_ids()
    selected = []
    for name in STAGES[stage]:
        for job in read_jobs(STATUS / name):
            if job['rid'] in accepted:
                continue
            derived = dict(job)
            derived['need_gb'] = float(job['need_gb']) + MARGIN_GB
            selected.append(derived)
    rids = [job['rid'] for job in selected]
    if len(rids) != len(set(rids)):
        raise RuntimeError(f'duplicate RID in {stage} registry')
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    output = STATE_DIR / f'{stage}_remaining.json'
    output.write_text(json.dumps(selected, ensure_ascii=False, indent=2) + '\n')
    metadata = {
        'pipeline_stage': stage,
        'sources': STAGES[stage],
        'base_ledger': latest_ledger().name,
        'safety_margin_gb': MARGIN_GB,
    }
    output.with_suffix('.meta.json').write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + '\n')
    jobs = load_jobs(output)
    return output, jobs


def pid_alive(pid):
    result = subprocess.run(['ps', '-p', str(pid), '-o', 'stat='], text=True,
                            capture_output=True)
    if result.returncode != 0:
        return False
    state = result.stdout.strip()
    return bool(state) and not state.startswith('Z')


def wait_for_parents(pids, poll_s, log_s=1800):
    pending = {int(pid) for pid in pids if pid_alive(pid)}
    if not pending:
        return
    write_state('waiting_existing', waiting_pids=sorted(pending),
                note='Existing parents own their runners; no kill or duplicate launch.')
    started = time.monotonic()
    last_log = started
    while pending:
        alive = {pid for pid in pending if pid_alive(pid)}
        now = time.monotonic()
        if alive != pending or now - last_log >= log_s:
            write_state('waiting_existing', waiting_pids=sorted(alive),
                        elapsed_seconds=int(now - started))
            last_log = now
        pending = alive
        if pending:
            time.sleep(poll_s)


def verify_stage(stage, jobs):
    incomplete = []
    for job in jobs:
        state, reason = proof_state(job)
        if state != 'complete':
            incomplete.append({'rid': job.rid, 'state': state, 'reason': reason})
    if incomplete:
        raise RuntimeError(f'{stage} gate failed: {incomplete[:20]}')
    write_state(f'{stage}_verified', verified=len(jobs),
                note='Every pending RID has complete result/plateau/checkpoint/CUDA proof.')


def run_stage(stage, workers, poll_s):
    registry, jobs = build_stage_registry(stage)
    if not jobs:
        write_state(f'{stage}_verified', verified=0, registry=str(registry))
        return
    write_state(f'{stage}_running', registry=str(registry), pending=len(jobs),
                registry_sha256=sha256(registry), workers=workers,
                safety_margin_gb=MARGIN_GB)
    command = [
        sys.executable, 'scripts/expansion_queue.py', '--jobs-json', str(registry),
        '--workers', str(workers), '--device', '0', '--state-dir', str(STATE_DIR),
        '--poll-s', str(poll_s),
    ]
    result = subprocess.run(command, cwd=Path(__file__).resolve().parents[1])
    if result.returncode != 0:
        raise RuntimeError(f'{stage} expansion queue exited {result.returncode}')
    verify_stage(stage, jobs)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wait-pids', default='')
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--workers', type=int, default=6)
    parser.add_argument('--wait-poll-s', type=int, default=120)
    parser.add_argument('--queue-poll-s', type=int, default=60)
    args = parser.parse_args(argv)
    if args.workers < 1:
        parser.error('--workers must be >= 1')
    wait_pids = [int(x) for x in args.wait_pids.split(',') if x.strip()]
    if args.prepare_only:
        summary = {}
        for stage in STAGES:
            path, jobs = build_stage_registry(stage)
            summary[stage] = {'pending': len(jobs), 'registry': str(path),
                              'sha256': sha256(path)}
        write_state('prepared', stages=summary,
                    note='Preparation only; no process was launched.')
        return 0
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with LOCK_PATH.open('w') as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print('another remaining pipeline is already active', file=sys.stderr)
            return 2
        try:
            wait_for_parents(wait_pids, args.wait_poll_s)
            for stage in STAGES:
                run_stage(stage, args.workers, args.queue_poll_s)
            write_state('complete', note='All registered remaining stages verified complete.')
            return 0
        except Exception as exc:
            write_state('blocked', error=str(exc), traceback=traceback.format_exc(),
                        note='No later stage will start after a failed gate.')
            return 1


if __name__ == '__main__':
    raise SystemExit(main())
