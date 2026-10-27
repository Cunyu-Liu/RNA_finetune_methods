from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pytest
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import mechanism_crispr as mech
from rnafteval.strategies import make_head


def test_evidence_preserves_binary_support_and_cluster_contract():
    parts = {
        "train": [{"seq": "AA", "label": 0, "cluster": "a"},
                  {"seq": "AC", "label": 1, "cluster": "b"}],
        "val": [{"seq": "AG", "label": 0, "cluster": "c"}],
        "test": [{"seq": "AU", "label": 1, "cluster": "d"}],
    }
    evidence = mech.build_evidence(parts, "family")
    assert evidence["status"] == "OK"
    assert evidence["protocol"] == "bestval_v1"
    assert evidence["split_source"] == "family_validation"
    assert evidence["deduplicated"] is True
    assert evidence["label_support"]["train"] == {"0": 1, "1": 1}
    assert evidence["label_support"]["test"] == {"0": 0, "1": 1}
    assert set(evidence["cluster_cross_split_overlap"]) == {
        "train_val", "train_test", "val_test"}


def test_manifest_enrichment_is_deterministic_and_covers_small_boundaries():
    rows = [{"seq": seq, "label": label}
            for seq, label in (("A", 1), ("AC", 1), ("AG", 1), ("AU", 1),
                               ("TA", 0), ("TG", 0))]
    _ordered, manifest, selected = mech.make_manifest(rows, "random", 17, 10, 2)
    assert len(selected) == 6
    assert manifest["sample_positive"] == 4
    assert manifest["sample_negative"] == 2
    assert manifest["visualization_enrichment"] is True
    larger = [{"seq": f"A{index}", "label": int(index < 5)} for index in range(20)]
    _ordered2, manifest2, selected2 = mech.make_manifest(larger, "random", 17, 8, 3)
    assert len(selected2) == 8
    assert manifest2["sample_positive"] == 3
    assert manifest2["sample_negative"] == 5
    _ordered3, reversed_manifest, reversed_selected = mech.make_manifest(
        list(reversed(larger)), "random", 17, 8, 3)
    assert manifest2 == reversed_manifest
    assert selected2 == reversed_selected


def test_crispr_metrics_use_pr_and_roc_not_accuracy():
    labels = np.asarray([0, 0, 1, 1])
    probabilities = np.asarray([[0.9, 0.1], [0.8, 0.2], [0.1, 0.9], [0.2, 0.8]])
    metrics = mech.crispr_metrics(labels, probabilities)
    assert metrics["pr_auc"] == pytest.approx(1.0)
    assert metrics["roc_auc"] == pytest.approx(1.0)
    assert metrics["confusion_matrix"] == [[2, 0], [0, 2]]
    assert metrics["positive_support"] == 2
    assert metrics["predicted_positive"] == 2


def fake_states():
    states = []
    for index, strategy in enumerate(("full", "pre", "lora")):
        arrays = {
            "sample_ids": np.asarray(["a", "b", "c", "d"]),
            "labels": np.asarray([0, 1, 0, 1]),
            "probabilities": np.full((4, 2), 0.5, dtype=np.float32),
            "logits": np.zeros((4, 2), dtype=np.float32),
            "cls": np.full((4, 3), index, dtype=np.float32),
            "head_embedding": np.full((4, 2), index + 1, dtype=np.float32),
            "split": np.asarray("random"),
            "seed": np.asarray(17),
        }
        metrics = {"pr_auc": 0.5 + index / 10, "roc_auc": 0.6 + index / 10}
        states.append((strategy, arrays, "same", "source_" + strategy, metrics))
    return states


def test_aligned_crispr_keeps_enrichment_out_of_metrics(tmp_path, monkeypatch):
    class FakeTSNE:
        def __init__(self, **kwargs):
            pass

        def fit_transform(self, values):
            return np.zeros((len(values), 2))

    import sklearn.manifold
    monkeypatch.setattr(sklearn.manifold, "TSNE", FakeTSNE)
    summary = mech.aligned_crispr(fake_states(), tmp_path / "aligned")
    assert summary["classification_silhouette"] is None
    with np.load(summary["path"], allow_pickle=False) as data:
        assert data["labels"].shape == (12,)
        assert data["probabilities"].shape == (12, 2)
        assert data["state"].tolist() == ["pre"] * 4 + ["lora"] * 4 + ["full"] * 4
        assert data["source_run_ids"].tolist() == ["source_pre", "source_lora", "source_full"]
        assert data["sampling"].item() == "positive_cap_256_then_negative_hash_fill"
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


def test_extract_uses_manifest_indices_not_first_n():
    backbone = DummyBackbone()
    head = make_head("per-seq", 3, 2)
    rows = [{"seq": seq, "label": index % 2}
            for index, seq in enumerate(("A", "AC", "ACG", "ACGU"))]
    full, sample = mech.extract(backbone, head, DummyTokenizer(), rows,
                                "cpu", selected_indices=[1, 3], batch_size=3)
    assert len(full["sample_ids"]) == 4
    assert len(sample["sample_ids"]) == 2
    assert np.array_equal(sample["sample_ids"], full["sample_ids"][[1, 3]])
    assert np.array_equal(sample["labels"], full["labels"][[1, 3]])
    assert sample["cls"].shape == (2, 3)
    assert sample["head_embedding"].shape == (2, 3)


def test_crispr_source_run_ids():
    assert mech.source_run_id("lora", "random", 17) == \
        "ft_rinalmomicro_crisprofftarget_lora_s17_random_bestval_v1"
    assert mech.source_run_id("full", "family", 17) == \
        "ft_rinalmomicro_crisprofftarget_full_s17_family_lr1e-05_bestval_v1"
