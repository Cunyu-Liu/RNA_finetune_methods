import json
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pytest
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import mechanism_mrl as mech
from rnafteval import valplateau as vp
from rnafteval.strategies import make_head


def test_manifest_is_order_independent_and_preserves_continuous_labels():
    rows = [{"seq": "ACGU", "label": 1.25},
            {"seq": "AAAA", "label": -0.5},
            {"seq": "GGGG", "label": 3.0}]
    first, manifest = mech.make_manifest(rows, "random", 17, 2)
    second, reversed_manifest = mech.make_manifest(
        list(reversed(rows)), "random", 17, 2)
    assert first == second
    assert manifest == reversed_manifest
    assert manifest["n"] == 2 and manifest["n_full_test"] == 3
    assert manifest["selection"] == "sequence_hash_ascending_before_prediction"
    assert manifest["sample_ids"] == [row["sample_id"] for row in manifest["records"]]
    expected = sorted(rows, key=lambda row: mech.common.sequence_hash(row["seq"]))[:2]
    assert [row["label"] for row in manifest["records"]] == [row["label"] for row in expected]
    assert set(row["label"] for row in manifest["records"]) <= {1.25, -0.5, 3.0}


def test_regression_metrics_and_source_run_ids():
    metrics = mech.regression_metrics([1, 2, 3], [1, 2, 3])
    assert metrics["pearson_r"] == pytest.approx(1.0)
    assert metrics["mse"] == pytest.approx(0.0)
    assert mech.source_run_id("lora", "random", 17) == \
        "ft_rinalmomicro_mrl_lora_s17_random_bestval_v1"
    assert mech.source_run_id("full", "family", 17) == \
        "ft_rinalmomicro_mrl_full_s17_family_lr1e-05_bestval_v1"


def make_checkpoint(tmp_path):
    source_backbone = torch.nn.Linear(3, 1)
    source_head = make_head("per-seq", 3, 1)
    result_dir = tmp_path / "source"
    result_dir.mkdir()
    vp.save_best_checkpoint(result_dir / "best.ckpt", source_backbone, source_head,
                            epoch=1, best_epoch=1, best_val=0.2)
    result = {
        "protocol": "bestval_v1", "best_checkpoint": "best.ckpt",
        "best_epoch": 1, "best_val": 0.2, "epoch_val_losses": [0.3, 0.2],
        "acceptance_eligible": True, "smoke": False,
    }
    row = {"status": "done", "best_epoch": 1, "best_val": 0.2,
           "best_checkpoint": "best.ckpt"}
    return source_backbone, source_head, result_dir, result, row


def test_restore_post_checks_ledger_and_every_tensor(tmp_path, monkeypatch):
    source_backbone, source_head, result_dir, result, row = make_checkpoint(tmp_path)
    target_backbone = torch.nn.Linear(3, 1)
    target_head = make_head("per-seq", 3, 1)
    evidence = mech.restore_post(target_backbone, target_head, result_dir,
                                 result, row, "cpu")
    assert evidence["restored_tensor_match"] is True
    for key, value in target_backbone.state_dict().items():
        assert torch.equal(value, source_backbone.state_dict()[key])
    for key, value in target_head.state_dict().items():
        assert torch.equal(value, source_head.state_dict()[key])
    with torch.no_grad():
        next(iter(target_backbone.parameters())).add_(1)
    monkeypatch.setattr(vp, "load_backbone_state_dict", lambda *args: None)
    with pytest.raises(ValueError, match="恢复后 tensor 不一致"):
        mech.restore_post(target_backbone, target_head, result_dir, result, row, "cpu")
    with pytest.raises(ValueError, match="ledger done"):
        mech.restore_post(target_backbone, target_head, result_dir, result, None, "cpu")


def fake_states(manifest="same"):
    states = []
    for index, strategy in enumerate(("full", "pre", "lora")):
        y = np.asarray([0.1, 0.2, 0.3, 0.4], dtype=np.float32)
        prediction = y + index
        arrays = {
            "sample_ids": np.asarray(["a", "b", "c", "d"]),
            "y_true": y,
            "prediction": prediction,
            "residual": prediction - y,
            "cls": np.full((4, 3), index, dtype=np.float32),
            "head_embedding": np.full((4, 2), index + 1, dtype=np.float32),
            "split": np.asarray("random"),
            "seed": np.asarray(17),
        }
        states.append((strategy, arrays, manifest, "source_" + strategy, index / 10))
    return states


def test_aligned_regression_is_joint_and_has_no_classification_silhouette(
        tmp_path, monkeypatch):
    calls = []

    class FakeTSNE:
        def __init__(self, **kwargs):
            calls.append(kwargs)

        def fit_transform(self, values):
            return np.arange(len(values) * 2).reshape(len(values), 2)

    import sklearn.manifold
    monkeypatch.setattr(sklearn.manifold, "TSNE", FakeTSNE)
    summary = mech.aligned_regression(fake_states(), tmp_path / "aligned")
    assert summary["classification_silhouette"] is None
    assert len(calls) == 2
    assert all(call["random_state"] == 17 for call in calls)
    path = Path(summary["path"])
    assert path.suffix == ".npz" and path.is_file()
    with np.load(path, allow_pickle=False) as data:
        assert data["tsne_cls"].shape == (12, 2)
        assert data["tsne_head"].shape == (12, 2)
        assert data["state"].tolist() == ["pre"] * 4 + ["lora"] * 4 + ["full"] * 4
        assert data["source_run_ids"].tolist() == ["source_pre", "source_lora", "source_full"]
        assert data["color_mode"].item() == "true_mrl_continuous"
        assert "silhouette" not in data.files
    bad = fake_states()
    bad[0] = (bad[0][0], bad[0][1], "different", bad[0][3], bad[0][4])
    with pytest.raises(ValueError, match="manifest"):
        mech.aligned_regression(bad, tmp_path / "bad.npz")


class DummyTokenizer:
    def __call__(self, seqs, padding=True, truncation=True, max_length=64,
                 return_tensors="pt"):
        width = min(max_length, max(map(len, seqs)))
        input_ids = torch.zeros((len(seqs), width), dtype=torch.long)
        attention = torch.zeros((len(seqs), width), dtype=torch.long)
        for index, seq in enumerate(seqs):
            n = min(width, len(seq))
            input_ids[index, :n] = torch.arange(1, n + 1)
            attention[index, :n] = 1
        return {"input_ids": input_ids, "attention_mask": attention}


class DummyBackbone(torch.nn.Module):
    def forward(self, input_ids, attention_mask):
        values = input_ids.float().unsqueeze(-1)
        hidden = torch.cat([values, values + 1, values + 2], dim=-1)
        return SimpleNamespace(last_hidden_state=hidden)


def test_extract_keeps_full_test_and_sample_arrays_aligned():
    backbone = DummyBackbone()
    head = make_head("per-seq", 3, 1)
    rows = [{"seq": seq, "label": float(index)}
            for index, seq in enumerate(("A", "AC", "ACG", "ACGU"))]
    full, sample = mech.extract(backbone, head, DummyTokenizer(), rows,
                                "cpu", n_samples=2, batch_size=3)
    assert len(full["sample_ids"]) == 4
    assert len(sample["sample_ids"]) == 2
    assert np.array_equal(sample["sample_ids"], full["sample_ids"][:2])
    assert np.array_equal(sample["prediction"], full["prediction"][:2])
    assert np.allclose(sample["residual"], sample["prediction"] - sample["y_true"])
    assert sample["cls"].shape == (2, 3)
    assert sample["head_embedding"].shape == (2, 3)
