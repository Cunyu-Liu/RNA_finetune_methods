import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from evaluate_rinalmo_forgetting import validate_source


def source(**updates):
    value = {"run_id": "ft_source", "model": "RiNALMo-micro", "task": "mrl",
             "split": "random", "seed": 17, "strategy": "full", "lr": 1e-5,
             "protocol": "bestval_v1", "smoke": False}
    value.update(updates)
    return value


def test_default_source_is_accepted():
    validate_source(source(), {"run_id": "ft_source", "status": "CONVERGED"})
    validate_source(source(strategy="lora", lr=3e-4),
                    {"run_id": "ft_source", "status": "CONVERGED"})


def test_tuned_full_source_cannot_be_mislabeled_as_default():
    with pytest.raises(ValueError, match="default LR"):
        validate_source(source(lr=3e-4), {"run_id": "ft_source", "status": "CONVERGED"})


def test_smoke_and_nonconverged_sources_are_rejected():
    with pytest.raises(ValueError, match="formal bestval"):
        validate_source(source(smoke=True), {"run_id": "ft_source", "status": "CONVERGED"})
    with pytest.raises(ValueError, match="convergence"):
        validate_source(source(), {"run_id": "ft_source", "status": "RUNNING"})
