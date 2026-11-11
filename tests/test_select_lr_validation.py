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
