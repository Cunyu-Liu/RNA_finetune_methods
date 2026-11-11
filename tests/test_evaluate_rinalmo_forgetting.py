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


def test_full_restore_only_exempts_known_non_mlm_pooler():
    from types import SimpleNamespace
    from evaluate_rinalmo_forgetting import restore_lm_backbone

    class FakeLM:
        def __init__(self, unexpected):
            self.unexpected = unexpected
        def load_state_dict(self, state, strict):
            assert strict is False
            return SimpleNamespace(missing_keys=[], unexpected_keys=self.unexpected)
        def state_dict(self):
            return {}

    allowed = ["pooler.dense.weight", "pooler.dense.bias"]
    assert restore_lm_backbone(FakeLM(allowed), {}, "full") == sorted(allowed)
    with pytest.raises(ValueError, match="encoder mismatch"):
        restore_lm_backbone(FakeLM(["encoder.unknown"]), {}, "full")


def test_lora_restore_maps_encoder_peft_to_maskedlm_peft():
    import torch
    from types import SimpleNamespace
    from evaluate_rinalmo_forgetting import restore_lm_backbone

    class FakePEFT:
        def __init__(self):
            self.target = {"base_model.model.model.encoder.weight": torch.tensor(1)}
            self.loaded = None
        def state_dict(self):
            return self.target
        def load_state_dict(self, state, strict):
            self.loaded = state
            return SimpleNamespace(missing_keys=["lm_head.decoder.weight"], unexpected_keys=[])

    model = FakePEFT()
    auxiliary = restore_lm_backbone(model, {
        "base_model.model.encoder.weight": torch.tensor(1),
        "base_model.model.pooler.dense.base_layer.weight": torch.tensor(2),
    }, "lora")
    assert list(model.loaded) == ["base_model.model.model.encoder.weight"]
    assert auxiliary == ["base_model.model.pooler.dense.base_layer.weight"]
