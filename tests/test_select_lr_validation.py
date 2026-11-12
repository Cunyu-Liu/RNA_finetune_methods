import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from select_lr_validation import load_invalid_candidates


def proof(rid='ft_test_default', **updates):
    value = {
        'run_id': rid,
        'nonfinite_reason': 'constant_prediction',
        'candidate_eligible': False,
        'cuda_available': True,
        'split_evidence_match': True,
        'plateau_status': 'CONVERGED',
        'n_test': 7600,
        'y_pred_std': 1e-9,
    }
    value.update(updates)
    return value


def write(tmp_path, value):
    path = tmp_path / 'proof.json'
    path.write_text(json.dumps(value))
    return path


def test_load_invalid_candidates_accepts_cuda_constant_proof(tmp_path):
    path = write(tmp_path, proof())
    documents = load_invalid_candidates([path])
    assert documents['ft_test_default']['candidate_eligible'] is False


def test_load_invalid_candidates_rejects_nonconstant_or_missing_cuda(tmp_path):
    with pytest.raises(ValueError, match='prediction is not constant'):
        load_invalid_candidates([write(tmp_path, proof(y_pred_std=0.1))])
    with pytest.raises(ValueError, match='CUDA or split proof'):
        load_invalid_candidates([write(tmp_path, proof(cuda_available=False))])


def test_lora_selection_uses_validation_and_preserves_strategy(tmp_path, monkeypatch):
    from types import SimpleNamespace
    import select_lr_validation as selector

    validation_loss = {'3e-4': 0.4, '1e-4': 0.1, '3e-5': 0.2, '1e-5': 0.3}
    tasks = (*selector.jobspec.TASK_MODULES, 'spliceai', 'degradation', 'ssi')
    jobs = []
    for task in tasks:
        for model in selector.jobspec.MODELS:
            for split in ('random', 'family'):
                for lr, best_val in validation_loss.items():
                    rid = f'ft_{task}_{model}_{split}_{lr}'
                    result = tmp_path / f'{rid}.json'
                    result.write_text(json.dumps({
                        'best_val': best_val, 'best_epoch': 2,
                        'value': 0.99 if lr == '3e-4' else 0.01,
                    }))
                    jobs.append(SimpleNamespace(
                        task=task, model=model, split=split, strategy='lora',
                        lr=lr, rid=rid, result_path=result))
    monkeypatch.setattr(selector.queue, 'load_jobs', lambda source: jobs)
    monkeypatch.setattr(selector.queue, 'proof_state', lambda job: ('complete', ''))
    selection = tmp_path / 'selection.json'
    formal = tmp_path / 'formal.json'
    source = tmp_path / 'tuning.json'
    source.write_text('[]')
    assert selector.main([
        '--strategy', 'lora', '--tuning-jobs', str(source),
        '--selection-output', str(selection), '--jobs-output', str(formal),
    ]) == 0
    document = json.loads(selection.read_text())
    assert document['test_metric_used'] is False
    assert len(document['rows']) == 80
    assert all(row['selected_lr'] == '1e-4' for row in document['rows'])
    assert {row['strategy'] for row in document['rows']} == {'lora'}
    formal_jobs = json.loads(formal.read_text())
    assert len(formal_jobs) == 240
    assert {job['strategy'] for job in formal_jobs} == {'lora'}
    assert {job['lr'] for job in formal_jobs} == {'1e-4'}
