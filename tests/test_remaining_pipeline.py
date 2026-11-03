import json
from types import SimpleNamespace

import pytest

import remaining_pipeline as pipeline


def raw_job(rid, need=8):
    return {
        'task': 'degradation', 'model': 'RNA-FM', 'strategy': 'full',
        'split': 'random', 'seed': 17, 'lr': '3e-4', 'rank': 8,
        'n_train': 0, 'protocol': 'bestval_v1', 'rid': rid,
        'result_dir': f'/tmp/{rid}', 'module': 'rnafteval.finetune_regbase',
        'need_gb': need, 'args': ['--converge', '--lr', '3e-4'],
    }


def setup_stage(tmp_path, monkeypatch, jobs, accepted=()):
    monkeypatch.setattr(pipeline, 'STATUS', tmp_path)
    monkeypatch.setattr(pipeline, 'STATE_DIR', tmp_path / 'state')
    monkeypatch.setattr(pipeline, 'STATE_PATH', tmp_path / 'state.json')
    monkeypatch.setattr(pipeline, 'STAGES', {'core': ['jobs.json']})
    (tmp_path / 'jobs.json').write_text(json.dumps({'jobs': jobs}))
    rows = ['run_id,metric,value,best_val'] + [f'{rid},PCC,0.5,0.1' for rid in accepted]
    (tmp_path / 'bestval_ledger_export_20261101_v1.csv').write_text('\n'.join(rows) + '\n')


def test_registry_excludes_accepted_and_adds_margin(tmp_path, monkeypatch):
    setup_stage(tmp_path, monkeypatch, [raw_job('done'), raw_job('pending', 16)], ['done'])
    path, jobs = pipeline.build_stage_registry('core')
    assert [job.rid for job in jobs] == ['pending']
    assert jobs[0].need_gb == 17
    original = json.loads((tmp_path / 'jobs.json').read_text())['jobs']
    assert original[1]['need_gb'] == 16
    payload = json.loads(path.with_suffix('.meta.json').read_text())
    assert payload['safety_margin_gb'] == 1.0
    jobs_payload = json.loads(path.read_text())
    assert jobs_payload[0]['args'] == raw_job('pending', 16)['args']


def test_registry_rejects_duplicate_rids(tmp_path, monkeypatch):
    setup_stage(tmp_path, monkeypatch, [raw_job('same'), raw_job('same')])
    with pytest.raises(RuntimeError, match='duplicate RID'):
        pipeline.build_stage_registry('core')


def test_gate_rejects_incomplete_proof(tmp_path, monkeypatch):
    setup_stage(tmp_path, monkeypatch, [raw_job('pending')])
    _, jobs = pipeline.build_stage_registry('core')
    monkeypatch.setattr(pipeline, 'proof_state', lambda job: ('runnable', 'missing'))
    with pytest.raises(RuntimeError, match='core gate failed'):
        pipeline.verify_stage('core', jobs)


def test_gate_accepts_complete_proof(tmp_path, monkeypatch):
    setup_stage(tmp_path, monkeypatch, [raw_job('pending')])
    _, jobs = pipeline.build_stage_registry('core')
    monkeypatch.setattr(pipeline, 'proof_state', lambda job: ('complete', ''))
    pipeline.verify_stage('core', jobs)
    state = json.loads((tmp_path / 'state.json').read_text())
    assert state['stage'] == 'core_verified' and state['verified'] == 1


def test_pid_alive_rejects_zombie(monkeypatch):
    monkeypatch.setattr(pipeline.subprocess, 'run',
                        lambda *a, **k: SimpleNamespace(returncode=0, stdout='Z'))
    assert not pipeline.pid_alive(123)
    monkeypatch.setattr(pipeline.subprocess, 'run',
                        lambda *a, **k: SimpleNamespace(returncode=0, stdout='Sl'))
    assert pipeline.pid_alive(123)
