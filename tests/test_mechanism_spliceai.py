from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pytest
import torch
from scipy.special import softmax

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import mechanism_spliceai as mech
from rnafteval.strategies import make_head


def test_token_manifest_is_deterministic_and_class_capped():
    rows = [
        {"seq": "ACG", "labels": [0, 1, 2]},
        {"seq": "AAA", "labels": [0, 0, 1]},
        {"seq": "CCC", "labels": [2, 0, -100]},
    ]
    ordered, manifest, selected = mech.make_token_manifest(rows, "random", 17, 1)
    ordered2, manifest2, selected2 = mech.make_token_manifest(
        list(reversed(rows)), "random", 17, 1)
    assert ordered == ordered2
    assert manifest == manifest2
    assert selected == selected2
    assert manifest["n"] == 3
    assert manifest["sample_class_support"] == {"0": 1, "1": 1, "2": 1}
    assert manifest["n_full_tokens"] == 8
    assert len(set(manifest["token_ids"])) == 3
    assert manifest["metric_scope"].endswith("full_test")


def test_split_evidence_marks_train_holdout_and_token_support():
    parts = {
        "train": [{"seq": "AA", "labels": [0, 1], "cluster": "a"}],
        "val": [{"seq": "AC", "labels": [0, 2], "cluster": "b"}],
        "test": [{"seq": "AG", "labels": [1, 2], "cluster": "c"}],
    }
    evidence = mech.build_split_evidence(parts, "family")
    assert evidence["validation_source"] == "train_holdout"
    assert evidence["source_data_evidence_present"] is False
    assert evidence["label_support"]["train"] == {"0": 1, "1": 1, "2": 0}
    assert evidence["label_support"]["test"] == {"0": 0, "1": 1, "2": 1}
    assert evidence["status"] == "OK"


def test_flat_metric_matches_multiclass_runner_semantics():
    labels = np.asarray([0, 1, 2, 0, 1, 2])
    logits = np.eye(3)[labels] * 4
    metrics = mech.flat_metric(labels, logits)
    assert metrics["macro_f1"] == pytest.approx(1.0)
    assert metrics["roc_auc"] == pytest.approx(1.0)
    assert metrics["recalls"] == [1.0, 1.0, 1.0]


def fake_states():
    states = []
    for index, strategy in enumerate(("full", "pre", "lora")):
        arrays = {
            "token_ids": np.asarray(["a:0000", "a:0001", "b:0000", "b:0001"]),
            "sequence_ids": np.asarray(["a", "a", "b", "b"]),
            "positions": np.asarray([0, 1, 0, 1]),
            "labels": np.asarray([0, 1, 2, 0]),
            "probabilities": np.full((4, 3), 1 / 3, dtype=np.float32),
            "logits": np.zeros((4, 3), dtype=np.float32),
            "token_embedding": np.full((4, 3), index, dtype=np.float32),
            "split": np.asarray("random"),
            "seed": np.asarray(17),
        }
        metrics = {"macro_f1": 0.5 + index / 10, "roc_auc": 0.6 + index / 10}
        states.append((strategy, arrays, "same", "source_" + strategy, metrics))
    return states


def test_aligned_spliceai_uses_same_tokens_not_cls(tmp_path, monkeypatch):
    calls = []

    class FakeTSNE:
        def __init__(self, **kwargs):
            calls.append(kwargs)

        def fit_transform(self, values):
            return np.zeros((len(values), 2))

    import sklearn.manifold
    monkeypatch.setattr(sklearn.manifold, "TSNE", FakeTSNE)
    summary = mech.aligned_spliceai(fake_states(), tmp_path / "aligned")
    assert len(calls) == 1
    assert summary["classification_silhouette"] is None
    with np.load(summary["path"], allow_pickle=False) as data:
        assert data["token_embedding"].shape == (12, 3)
        assert data["token_ids"].shape == (12,)
        assert data["probabilities"].shape == (12, 3)
        assert data["state"].tolist() == ["pre"] * 4 + ["lora"] * 4 + ["full"] * 4
        assert data["source_run_ids"].tolist() == ["source_pre", "source_lora", "source_full"]
        assert "cls" not in data.files
        assert "silhouette" not in data.files


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


def test_extract_preserves_positions_and_selected_embeddings():
    rows = [
        {"seq": "ACG", "labels": [0, 1, 2]},
        {"seq": "AAA", "labels": [0, 0, 1]},
        {"seq": "CCC", "labels": [2, 0, -100]},
    ]
    ordered, _manifest, selected = mech.make_token_manifest(rows, "random", 17, 2)
    backbone = DummyBackbone()
    head = make_head("per-base", 3, 3)
    full, sample = mech.extract(backbone, head, DummyTokenizer(), ordered,
                                "cpu", selected, batch_size=2)
    assert len(full["labels"]) == 8
    assert full["logits"].shape == (8, 3)
    assert len(sample["token_ids"]) == len(selected)
    assert sample["token_embedding"].shape == (len(selected), 3)
    assert np.allclose(softmax(sample["logits"], axis=-1), sample["probabilities"],
                       rtol=1e-5, atol=1e-6)
    first = selected[0]
    enc = DummyTokenizer()([ordered[first["seq_index"]]["seq"]])
    expected = backbone(**enc).last_hidden_state[0, first["position"]].numpy()
    assert np.allclose(sample["token_embedding"][0], expected)


def test_spliceai_source_run_ids_include_b20fix():
    assert mech.source_run_id("lora", "random", 17) == \
        "ft_rinalmomicro_spliceai_lora_s17_random_b20fix_bestval_v1"
    assert mech.source_run_id("full", "family", 17) == \
        "ft_rinalmomicro_spliceai_full_s17_family_b20fix_lr1e-05_bestval_v1"
