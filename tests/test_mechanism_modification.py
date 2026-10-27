from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pytest
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import mechanism_modification as mech
from rnafteval.strategies import make_head


def test_manifest_preserves_multilabel_and_m6a_view():
    rows = [{"seq": "ACGU", "labels": [0] * 7 + [1] + [0] * 4},
            {"seq": "AAAA", "labels": [1] * 7 + [0] + [1] * 4}]
    ordered, manifest = mech.make_manifest(rows, "random", 17, 2)
    reversed_ordered, reversed_manifest = mech.make_manifest(
        list(reversed(rows)), "random", 17, 2)
    assert ordered == reversed_ordered
    assert manifest == reversed_manifest
    assert len(manifest["records"][0]["labels"]) == 12
    assert {record["m6a_label"] for record in manifest["records"]} == {0, 1}
    assert manifest["label_semantics"].endswith("m6A index 7")


def test_modification_metrics_separate_source_and_valid_only_means():
    y = np.zeros((4, 12), dtype=int)
    y[:, 0] = [0, 0, 1, 1]
    y[:, 1] = 1
    y[:, 7] = [0, 1, 0, 1]
    probabilities = np.full((4, 12), 0.5)
    probabilities[:, 0] = [0.1, 0.2, 0.8, 0.9]
    probabilities[:, 7] = [0.1, 0.9, 0.2, 0.8]
    metrics = mech.modification_metrics(y, probabilities)
    assert metrics["m6a_auc"] == pytest.approx(1.0)
    assert metrics["aucs_by_modification"][0] == pytest.approx(1.0)
    assert metrics["aucs_by_modification"][1] is None
    assert metrics["aucs_source_compatible"][1] == 0.5
    assert metrics["valid_label_mask"][0] is True
    assert metrics["valid_label_mask"][1] is False
    assert metrics["mean_auc"] == pytest.approx((10 * 0.5 + 2) / 12)
    assert metrics["mean_auc_valid"] == pytest.approx(1.0)
    assert metrics["positive_support"][1] == 4
    assert metrics["negative_support"][1] == 0


def fake_states():
    states = []
    labels = np.zeros((4, 12), dtype=np.float32)
    labels[:, 7] = [0, 1, 0, 1]
    for index, strategy in enumerate(("full", "pre", "lora")):
        arrays = {
            "sample_ids": np.asarray(["a", "b", "c", "d"]),
            "labels": labels,
            "probabilities": np.full((4, 12), index / 10, dtype=np.float32),
            "logits": np.full((4, 12), index, dtype=np.float32),
            "cls": np.full((4, 3), index, dtype=np.float32),
            "head_embedding": np.full((4, 2), index + 1, dtype=np.float32),
            "split": np.asarray("random"),
            "seed": np.asarray(17),
        }
        metrics = {"m6a_auc": 0.5 + index / 10, "mean_auc": 0.6 + index / 10}
        states.append((strategy, arrays, "same", "source_" + strategy, metrics))
    return states


def test_aligned_modification_is_m6a_view_not_softmax(tmp_path, monkeypatch):
    calls = []

    class FakeTSNE:
        def __init__(self, **kwargs):
            calls.append(kwargs)

        def fit_transform(self, values):
            return np.zeros((len(values), 2))

    import sklearn.manifold
    monkeypatch.setattr(sklearn.manifold, "TSNE", FakeTSNE)
    summary = mech.aligned_modification(fake_states(), tmp_path / "aligned")
    assert len(calls) == 2
    assert summary["classification_silhouette"] is None
    with np.load(summary["path"], allow_pickle=False) as data:
        assert data["labels"].shape == (12, 12)
        assert data["m6a_label"].shape == (12,)
        assert data["probabilities"].shape == (12, 12)
        assert data["state"].tolist() == ["pre"] * 4 + ["lora"] * 4 + ["full"] * 4
        assert data["source_run_ids"].tolist() == ["source_pre", "source_lora", "source_full"]
        assert data["color_mode"].item() == "m6a_label_index_7"
        assert "silhouette" not in data.files
    bad = fake_states()
    bad[0][1]["labels"] = bad[0][1]["labels"].copy()
    bad[0][1]["labels"][0, 7] = 1
    with pytest.raises(ValueError, match="标签"):
        mech.aligned_modification(bad, tmp_path / "bad.npz")


class DummyTokenizer:
    def __call__(self, seqs, padding=True, truncation=True, max_length=128,
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


def test_extract_keeps_independent_sigmoid_labels_and_sample_alignment():
    backbone = DummyBackbone()
    head = make_head("per-seq", 3, 12)
    rows = [{"seq": seq, "labels": [index % 2] * 12}
            for index, seq in enumerate(("A", "AC", "ACG", "ACGU"))]
    full, sample = mech.extract(backbone, head, DummyTokenizer(), rows,
                                "cpu", n_samples=2, batch_size=3)
    assert full["labels"].shape == (4, 12)
    assert full["probabilities"].shape == (4, 12)
    assert sample["labels"].shape == (2, 12)
    assert np.array_equal(sample["sample_ids"], full["sample_ids"][:2])
    assert np.allclose(sample["probabilities"], full["probabilities"][:2])
    assert np.allclose(1 / (1 + np.exp(-sample["logits"])), sample["probabilities"],
                       rtol=1e-5, atol=1e-6)
    assert sample["cls"].shape == (2, 3)
    assert sample["head_embedding"].shape == (2, 3)


def test_modification_source_run_ids_include_seqmlfix():
    assert mech.source_run_id("lora", "random", 17) == \
        "ft_rinalmomicro_modification_lora_s17_random_bestval_v1_seqmlfix"
    assert mech.source_run_id("full", "family", 17) == \
        "ft_rinalmomicro_modification_full_s17_family_lr1e-05_bestval_v1_seqmlfix"
