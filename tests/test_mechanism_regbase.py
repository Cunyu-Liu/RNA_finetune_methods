import copy
import json
import math
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pytest
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import mechanism_regbase as mech
from rnafteval.strategies import TokenHead


EVIDENCE = {"protocol": "bestval_v1", "validation_source": "train_holdout",
            "status": "OK"}


class DummyTokenizer:
    cls_token_id = 90
    eos_token_id = 91
    pad_token_id = 0
    all_special_ids = (0, 90, 91)
    base_ids = {"A": 1, "C": 2, "G": 3, "U": 4, "T": 4, "N": 5}

    def __call__(self, seqs, padding=True, truncation=True, max_length=192,
                 return_tensors="pt"):
        rows = []
        for seq in seqs:
            core = [self.base_ids[base] for base in seq]
            if truncation:
                core = core[:max(0, max_length - 2)]
            rows.append([self.cls_token_id] + core + [self.eos_token_id])
        width = max(map(len, rows))
        input_ids, attention = [], []
        for row in rows:
            pad_n = width - len(row)
            input_ids.append(row + [self.pad_token_id] * pad_n)
            attention.append([1] * len(row) + [0] * pad_n)
        return {"input_ids": torch.tensor(input_ids),
                "attention_mask": torch.tensor(attention)}

    def get_special_tokens_mask(self, ids, already_has_special_tokens=False):
        assert already_has_special_tokens
        return [int(token_id in self.all_special_ids) for token_id in ids]


class DummyBackbone(torch.nn.Module):
    def forward(self, input_ids, attention_mask):
        values = input_ids.float().unsqueeze(-1)
        hidden = torch.cat((values, values + 1, values + 2), dim=-1)
        return SimpleNamespace(last_hidden_state=hidden)


def make_head():
    torch.manual_seed(7)
    return TokenHead(3, 1, hidden=32)


def manifest_for(rows, task="degradation", cap=4, max_len=192):
    return mech.make_token_manifest(
        DummyTokenizer(), rows, task, "random", 17, cap, EVIDENCE,
        max_len=max_len, batch_size=2)


def test_source_rids_are_exact_and_task_isolated():
    assert mech.source_run_id("degradation", "lora", "random", 17) == \
        "ft_rinalmomicro_degradation_lora_s17_random_b20fix_bestval_v1"
    assert mech.source_run_id("degradation", "full", "family", 17) == \
        "ft_rinalmomicro_degradation_full_s17_family_b20fix_lr1e-05_bestval_v1"
    assert mech.source_run_id("ssi", "lora", "random", 17) == \
        "ft_rinalmomicro_ssi_lora_s17_random_b20fix_bestval_v1"
    assert mech.source_run_id("ssi", "full", "family", 17) == \
        "ft_rinalmomicro_ssi_full_s17_family_b20fix_lr1e-05_bestval_v1"
    assert mech.diagnostic_run_id("degradation", "pre", "random", 17) != \
        mech.diagnostic_run_id("ssi", "pre", "random", 17)


@pytest.mark.parametrize("task", mech.TASKS)
def test_random_reconstruction_ignores_official_validation_and_orders_steps(
        task, tmp_path, monkeypatch):
    train = [{"seq": "train-%d" % index, "labels": [float(index)]}
             for index in range(6)]
    test = [{"seq": "test-%d" % index, "labels": [0.5]}
            for index in range(2)]
    official_val = [{"seq": test[0]["seq"], "labels": [99.0]}]
    events = []
    loader = mech.deg_task if task == "degradation" else mech.ssi_task

    def load(path):
        events.append(("loader", path))
        return {"train": train, "validation": official_val, "test": test}

    def holdout(rows, seed):
        events.append(("holdout", rows, seed))
        return rows[:4], rows[4:]

    def sample(rows, n_train, seed):
        events.append(("sample", rows, n_train, seed))
        return rows[:2]

    monkeypatch.setattr(loader, "load_official_split", load)
    if task == "ssi":
        monkeypatch.setattr(loader, "split_train_validation_by_sequence", holdout)
    else:
        monkeypatch.setattr(mech, "split_train_validation", holdout)
    monkeypatch.setattr(mech, "seeded_sample", sample)
    parts, evidence = mech.load_task_parts(
        task, "random", seed=17, n_train=2, data_root=tmp_path)
    assert [event[0] for event in events] == ["loader", "holdout", "sample"]
    assert events[1][1] is train and events[1][2] == 17
    assert events[2][1] == train[:4] and events[2][2:] == (2, 17)
    assert parts["train"] == train[:2]
    assert parts["val"] == train[4:]
    assert parts["test"] is test
    assert official_val[0] not in parts["val"]
    assert evidence["validation_source"] == "train_holdout"
    assert evidence["ignored_source_validation_rows"] == 1
    assert evidence["train_sampling"] == {
        "method": "seeded_sample", "n_train": 2, "seed": 17,
        "rows_before": 4, "rows_after": 2}
    assert (evidence["n_train"], evidence["n_val"], evidence["n_test"]) == (2, 2, 2)
    assert evidence["canonical_n_train"] == 0 and evidence["max_len"] == 192
    if task == "degradation":
        assert "requested_n_train" not in evidence
    if task == "ssi":
        assert evidence["requested_n_train"] == 2
        assert evidence["validation_grouping"] == mech.ssi_task.RANDOM_GROUPING
        assert evidence["same_sequence_records_preserved"] is True
        assert evidence["input_same_sequence_rows"] == {"train": 0, "test": 0}


def test_ssi_sequence_grouped_holdout_preserves_conflicting_same_sequence_labels():
    rows = [{"seq": "A", "labels": np.asarray([0.0], dtype=np.float32)},
            {"seq": "A", "labels": np.asarray([1.0], dtype=np.float32)}]
    rows += [{"seq": chr(66 + index), "labels": np.asarray([float(index)], dtype=np.float32)}
             for index in range(8)]
    train, val = mech.ssi_task.split_train_validation_by_sequence(rows, seed=17)
    assert len(train) + len(val) == len(rows)
    mech.assert_no_overlap(train, val, unit="seq")
    a_rows = [row for row in train + val if row["seq"] == "A"]
    assert len(a_rows) == 2
    assert len({row["cluster"] for row in a_rows}) == 1
    assert ({row["cluster"] for row in a_rows} <= {row["cluster"] for row in train}
            or {row["cluster"] for row in a_rows} <= {row["cluster"] for row in val})
    assert sorted(float(row["labels"][0]) for row in a_rows) == [0.0, 1.0]
    assert all(row["cluster"] == mech.ssi_task.seq_hash(row["seq"])
               for row in train + val)
    assert mech.ssi_task.same_sequence_record_counts(rows) == 1


def test_ssi_duplicate_test_records_keep_unique_ids_and_record_weighted_mcrmse():
    rows = [{"seq": "AC", "labels": np.asarray([0.0, 0.0], dtype=np.float32)},
            {"seq": "AC", "labels": np.asarray([1.0, 1.0], dtype=np.float32)}]
    ordered, manifest, selected = manifest_for(rows, task="ssi", cap=20)
    assert len(ordered) == manifest["n_full_records"] == 2
    assert manifest["n_unique_sequences"] == 1
    assert len(set(manifest["record_ids"])) == 2
    assert len(set(manifest["token_ids"])) == len(manifest["token_ids"])
    full, sample = mech.extract(
        DummyBackbone(), make_head(), DummyTokenizer(), ordered, "cpu", "ssi", manifest,
        selected, batch_size=2, max_len=192)
    assert len(set(full["token_ids"])) == len(full["token_ids"])
    assert len(set(full["sequence_ids"])) == 2
    assert sample["token_ids"].tolist() == manifest["token_ids"]
    metrics = mech.regression_metrics(
        full["y_true"], full["prediction"], full["sequence_ids"])
    per_record = []
    for record_id in manifest["record_ids"]:
        keep = full["sequence_ids"] == record_id
        per_record.append(float(np.mean(
            (full["prediction"][keep] - full["y_true"][keep]) ** 2)))
    assert np.isclose(metrics["mcrmse"], np.sqrt(np.mean(per_record)))
    sequence_hash = mech.common.sequence_hash("AC")
    assert sequence_hash + ":0000" in manifest["record_ids"]
    assert sequence_hash + ":0001" in manifest["record_ids"]


def test_ssi_source_data_evidence_must_match_reconstruction():
    evidence = {
        "protocol": "bestval_v1", "task": "ssi", "split": "random", "seed": 17,
        "holdout_seed": 17, "validation_source": "train_holdout",
        "validation_grouping": mech.ssi_task.RANDOM_GROUPING,
        "same_sequence_records_preserved": True, "ignored_source_validation_rows": 1,
        "input_rows": {"train": 6, "test": 2, "validation_ignored": 1},
        "input_same_sequence_rows": {"train": 1, "test": 0},
        "canonical_n_train": 0, "requested_n_train": 0, "max_len": 192,
        "train_sampling": {"method": "seeded_sample", "n_train": 0, "seed": 17,
                           "rows_before": 4, "rows_after": 4},
        "n_train": 4, "n_val": 2, "n_test": 2,
        "output_rows": {"train": 4, "val": 2, "test": 2}, "status": "OK",
    }
    result = {"task": "ssi", "split": "random", "data_evidence": dict(evidence)}
    checked = mech.source_data_evidence(result, evidence)
    assert checked["source_data_evidence_present"] is True
    assert checked["source_data_evidence_note"] == "matched_reconstructed_sequence_grouped_split"
    result["data_evidence"]["input_same_sequence_rows"] = {"train": 0, "test": 0}
    with pytest.raises(ValueError, match="input_same_sequence_rows"):
        mech.source_data_evidence(result, evidence)


@pytest.mark.parametrize("task", mech.TASKS)
def test_family_reconstruction_reads_only_train_test_with_clusters(
        task, tmp_path, monkeypatch):
    path = tmp_path / "family_splits" / (task + ".parquet")
    path.parent.mkdir()
    path.write_bytes(b"synthetic-family-table")
    sequences = ["train-%d" % index for index in range(6)] + ["official-val"] + [
        "test-0", "test-1"]
    sides = ["train"] * 6 + ["val"] + ["test"] * 2
    clusters = ["tr-%d" % index for index in range(6)] + ["ignored", "te-0", "te-1"]
    table = {"seq": sequences, "labels": [[float(index)] for index in range(9)],
             "split": sides, "cluster_id": clusters}
    events = []

    def read_table(actual_path):
        events.append(("parquet", actual_path))
        return SimpleNamespace(to_pydict=lambda: table)

    def holdout(rows, seed):
        events.append(("holdout", rows, seed))
        return rows[:4], rows[4:]

    def sample(rows, n_train, seed):
        events.append(("sample", rows, n_train, seed))
        return rows[:3]

    monkeypatch.setattr(mech.pq, "read_table", read_table)
    monkeypatch.setattr(mech, "split_train_validation", holdout)
    monkeypatch.setattr(mech, "seeded_sample", sample)
    parts, evidence = mech.load_task_parts(
        task, "family", seed=17, n_train=3, data_root=tmp_path)
    assert [event[0] for event in events] == ["parquet", "holdout", "sample"]
    assert events[0][1] == path and events[1][2] == 17
    assert events[2][2:] == (3, 17)
    assert len(parts["train"]) == 3 and len(parts["val"]) == 2
    assert len(parts["test"]) == 2
    assert all(row["cluster"].startswith("tr-") for row in parts["train"])
    assert {row["cluster"] for row in parts["test"]} == {"te-0", "te-1"}
    assert all(row["labels"].dtype == np.float32
               for rows in parts.values() for row in rows)
    assert "official-val" not in {row["seq"] for rows in parts.values() for row in rows}
    assert evidence["ignored_source_validation_rows"] == 1
    assert evidence["family_parquet_sha256"] == mech.common.sha256_file(path)
    assert evidence["cluster_cross_split_overlap"] == {
        "train_val": 0, "train_test": 0, "val_test": 0}


def test_source_identity_counts_and_missing_data_evidence_are_explicit():
    parts = {"train": [{}, {}], "val": [{}], "test": [{}, {}, {}]}
    rid = mech.source_run_id("degradation", "lora", "random", 17)
    result = {"run_id": rid, "model": mech.MODEL, "task": "degradation",
              "strategy": "lora", "split": "random", "seed": 17,
              "metric": "PCC", "lr": 3e-4, "rank": 8,
              "n_train": 2, "n_val": 1, "n_test": 3}
    row = dict(result, status="done")
    assert mech.validate_source(result, row, rid, "degradation", "lora",
                                "random", 17, parts) == {
                                    "n_train": 2, "n_val": 1, "n_test": 3}
    evidence = mech.source_data_evidence(result)
    assert evidence["source_data_evidence_present"] is False
    assert "missing_in_source_result" in evidence["source_data_evidence_note"]
    assert "not_claimed" in evidence["source_data_evidence_note"]
    for field, value in (("task", "ssi"), ("n_train", 1), ("n_val", 2),
                         ("n_test", 2), ("run_id", "other")):
        changed = dict(result, **{field: value})
        with pytest.raises(ValueError):
            mech.validate_source(changed, row, rid, "degradation", "lora",
                                 "random", 17, parts)


def test_b20_extract_excludes_special_pad_and_uses_right_truncated_positions():
    rows = [{"seq": "ACGUAC", "labels": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]},
            {"seq": "AC", "labels": [1.1, 1.2]}]
    ordered, manifest, selected = manifest_for(rows, cap=8, max_len=5)
    backbone, head = DummyBackbone(), make_head()
    full, sample = mech.extract(
        backbone, head, DummyTokenizer(), ordered, "cpu", "degradation",
        manifest, selected, batch_size=2, max_len=5)
    assert len(full["y_true"]) == 5
    for row in rows:
        sequence_id = mech.common.sequence_hash(row["seq"])
        keep = full["sequence_ids"] == sequence_id
        expected_n = min(len(row["seq"]), 3)
        assert full["base_positions"][keep].tolist() == list(range(expected_n))
        assert full["token_positions"][keep].tolist() == list(range(1, expected_n + 1))
        assert np.allclose(full["y_true"][keep], row["labels"][:expected_n])
        assert 0 not in full["token_positions"][keep]
    assert set(full["token_positions"]) <= {1, 2, 3}
    assert not np.any(full["y_true"] == 0)
    for index, token_id in enumerate(sample["token_ids"]):
        record = next(record for record in selected if record["token_id"] == token_id)
        row = ordered[record["seq_index"]]
        enc = DummyTokenizer()([row["seq"]], truncation=True, max_length=5,
                               return_tensors="pt")
        expected_hidden = backbone(**enc).last_hidden_state[
            0, record["token_position"]].numpy()
        assert np.allclose(sample["token_embedding"][index], expected_hidden)
        expected_prediction = head(
            backbone(**enc).last_hidden_state,
            enc["attention_mask"] == 0).squeeze(-1)[0, record["token_position"]]
        assert sample["prediction"][index] == pytest.approx(
            expected_prediction.item(), abs=1e-6)


def test_short_labels_are_degradation_only_and_b20_task_flag_is_exact(monkeypatch):
    row = {"seq": "ACGUAC", "labels": [0.125, -0.25, 0.75]}
    calls = []
    real_align = mech.align_base_labels

    def observed_align(tokenizer, enc, rows, max_len, **kwargs):
        calls.append((max_len, kwargs["allow_short_labels"]))
        return real_align(tokenizer, enc, rows, max_len, **kwargs)

    monkeypatch.setattr(mech, "align_base_labels", observed_align)
    _ordered, manifest, _selected = manifest_for([row], "degradation", cap=4, max_len=8)
    assert manifest["n_full_tokens"] == 3
    assert [record["y_true"] for record in manifest["records"]] == [
        float(np.float32(value)) for value in row["labels"]]
    with pytest.raises(ValueError, match="B20 label/sequence mismatch"):
        manifest_for([row], "ssi", cap=4, max_len=8)
    assert calls == [(8, True), (8, False)]


def test_metrics_use_global_pcc_and_sequence_equal_weight_mcrmse():
    y = np.asarray([1, 2, 10, 3, 4, 5], dtype=np.float32)
    p = np.asarray([1, 4, 7, 3, 6, 3], dtype=np.float32)
    sequence_ids = np.asarray(["a", "a", "b", "c", "c", "c"])
    metrics = mech.regression_metrics(y, p, sequence_ids)
    y_centered = y - y.sum() / len(y)
    p_centered = p - p.sum() / len(p)
    expected_pcc = float((y_centered * p_centered).sum() / np.sqrt(
        (y_centered ** 2).sum() * (p_centered ** 2).sum()))
    expected_mcrmse = math.sqrt((2.0 + 9.0 + 8.0 / 3.0) / 3.0)
    global_rmse = math.sqrt(21.0 / 6.0)
    assert metrics["pcc"] == pytest.approx(expected_pcc, abs=1e-7)
    assert metrics["mcrmse"] == pytest.approx(expected_mcrmse, abs=1e-7)
    assert metrics["mcrmse"] != pytest.approx(global_rmse)
    nonfinite = p.copy()
    nonfinite[0] = np.nan
    with pytest.raises(FloatingPointError):
        mech.regression_metrics(y, nonfinite, sequence_ids)


def test_source_reconciliation_checks_both_metrics_and_rejects_nonfinite():
    metrics = {"pcc": 0.75, "mcrmse": 0.2}
    source = {"value": 0.75, "mcrmse": 0.2}
    assert mech.reconcile_source_metrics(metrics, source) is True
    assert mech.source_metrics_match(
        {"pcc": 0.750001, "mcrmse": 0.200001}, source)
    for changed in ({"pcc": 0.8}, {"mcrmse": 0.3}, {"pcc": float("nan")}):
        candidate = dict(metrics, **changed)
        assert not mech.source_metrics_match(candidate, source)
        with pytest.raises(ValueError, match="PCC/MCRMSE"):
            mech.reconcile_source_metrics(candidate, source)


def test_continuous_manifest_is_deterministic_and_cap_does_not_change_full_test():
    rows = [{"seq": "ACG", "labels": [0.125, -0.5, 1.75]},
            {"seq": "AAA", "labels": [0.333, 0.666, -0.125]},
            {"seq": "CC", "labels": [2.25, -1.5]}]
    ordered_a, manifest_a, selected_a = manifest_for(rows, cap=2)
    ordered_b, manifest_b, selected_b = manifest_for(list(reversed(rows)), cap=2)
    assert ordered_a == ordered_b
    assert manifest_a == manifest_b
    assert selected_a == selected_b
    assert manifest_a["n"] == manifest_a["n_sample_tokens"] == 2
    assert manifest_a["n_full_tokens"] == 8
    assert manifest_a["label_sampling"] == "continuous_unbinned_unstratified"
    assert all(isinstance(record["y_true"], float)
               for record in manifest_a["records"])
    _ordered, manifest_c, selected_c = manifest_for(rows, cap=4)
    assert manifest_c["full_test_sha256"] == manifest_a["full_test_sha256"]
    assert manifest_c["n_full_tokens"] == manifest_a["n_full_tokens"]
    assert manifest_c["token_ids"][:2] == manifest_a["token_ids"]
    assert len(selected_c) == 4
    for bad_cap in (0, -1, True):
        with pytest.raises(ValueError, match="positive integer"):
            manifest_for(rows, cap=bad_cap)

    backbone, head = DummyBackbone(), make_head()
    full_a, sample_a = mech.extract(
        backbone, head, DummyTokenizer(), ordered_a, "cpu", "degradation",
        manifest_a, selected_a, batch_size=2)
    full_c, sample_c = mech.extract(
        backbone, head, DummyTokenizer(), ordered_a, "cpu", "degradation",
        manifest_c, selected_c, batch_size=2)
    for key in ("token_ids", "sequence_ids", "base_positions", "token_positions",
                "y_true", "prediction", "residual"):
        assert np.array_equal(full_a[key], full_c[key])
    metrics_a = mech.regression_metrics(
        full_a["y_true"], full_a["prediction"], full_a["sequence_ids"])
    metrics_c = mech.regression_metrics(
        full_c["y_true"], full_c["prediction"], full_c["sequence_ids"])
    assert metrics_a == metrics_c
    assert len(sample_a["y_true"]) == 2 and len(sample_c["y_true"]) == 4


def fake_states(task="degradation", split="random", seed=17):
    states = []
    token_ids = np.asarray(["a:0000", "a:0001", "b:0000", "b:0001"])
    sequence_ids = np.asarray(["a", "a", "b", "b"])
    base_positions = np.asarray([0, 1, 0, 1], dtype=np.int64)
    token_positions = np.asarray([1, 2, 1, 2], dtype=np.int64)
    y = np.asarray([0.1, 0.2, 0.3, 0.4], dtype=np.float32)
    evidence = json.dumps(EVIDENCE, sort_keys=True)
    for index, strategy in enumerate(("full", "pre", "lora")):
        prediction = (y + np.float32(0.1 + index / 10)).astype(np.float32)
        arrays = {
            "token_ids": token_ids.copy(), "sequence_ids": sequence_ids.copy(),
            "base_positions": base_positions.copy(),
            "token_positions": token_positions.copy(), "y_true": y.copy(),
            "prediction": prediction, "residual": prediction - y,
            "token_embedding": (np.arange(12, dtype=np.float32).reshape(4, 3)
                                + index * 20),
            "task": np.asarray(task), "split": np.asarray(split),
            "seed": np.asarray(seed, dtype=np.int64),
            "n_full_tokens": np.asarray(6, dtype=np.int64),
            "n_sample_tokens": np.asarray(4, dtype=np.int64),
            "full_test_sha256": np.asarray("full-test-hash"),
            "test_manifest_sha256": np.asarray("same-manifest"),
            "split_evidence": np.asarray(evidence),
            "selection": np.asarray("token_id_before_prediction"),
        }
        source = (mech.PRE_SOURCE if strategy == "pre" else
                  mech.source_run_id(task, strategy, split, seed))
        metrics = {"pcc": 0.5 + index / 10, "mcrmse": 0.2 + index / 10}
        diagnostic = {
            "status": "diagnostic", "model": mech.MODEL, "task": task,
            "strategy": strategy, "split": split, "seed": seed,
            "source_run_id": None if strategy == "pre" else source,
            "reference_head_seed": 201 if strategy == "pre" else None,
            "full_test_metric_match": None if strategy == "pre" else True,
            "checkpoint": None if strategy == "pre" else {
                "restored_tensor_match": True, "checkpoint_proof": "ok"},
            "source_proof": None if strategy == "pre" else {"state": "complete"},
            "metrics_full": metrics,
        }
        states.append((strategy, arrays, "same-manifest", source, metrics, diagnostic))
    return states


def install_fake_tsne(monkeypatch, calls):
    class FakeTSNE:
        def __init__(self, **kwargs):
            calls.append(("init", kwargs))

        def fit_transform(self, values):
            calls.append(("fit", values.copy()))
            return np.arange(len(values) * 2).reshape(len(values), 2)

    import sklearn.manifold
    monkeypatch.setattr(sklearn.manifold, "TSNE", FakeTSNE)


def test_three_state_joint_tsne_is_aligned_and_descriptive(tmp_path, monkeypatch):
    calls = []
    install_fake_tsne(monkeypatch, calls)
    summary = mech.aligned_regression(
        fake_states(), tmp_path / "aligned", task="degradation")
    assert [call[0] for call in calls] == ["init", "fit"]
    assert calls[0][1]["random_state"] == 17
    assert calls[1][1].shape == (12, 3)
    assert summary["classification_silhouette"] is None
    assert summary["n_full_tokens"] == 6
    with np.load(summary["path"], allow_pickle=False) as saved:
        assert saved["tsne"].shape == (12, 2)
        assert saved["state"].tolist() == ["pre"] * 4 + ["lora"] * 4 + ["full"] * 4
        assert saved["token_ids"].shape == (12,)
        assert saved["base_positions"].shape == (12,)
        assert saved["token_positions"].shape == (12,)
        assert saved["y_true"].dtype != np.int64
        assert saved["prediction"].shape == saved["residual"].shape == (12,)
        assert saved["source_run_ids"].tolist() == [
            mech.PRE_SOURCE,
            mech.source_run_id("degradation", "lora", "random", 17),
            mech.source_run_id("degradation", "full", "random", 17)]
        assert saved["n_full_tokens"].item() == 6
        assert saved["n_sample_tokens"].item() == 4
        assert str(saved["color_mode"]) == "y_true_continuous"
        assert "silhouette" not in saved.files
        assert "probabilities" not in saved.files


@pytest.mark.parametrize("mutation,match", [
    ("manifest", "manifest"),
    ("token", "token_id"),
    ("label", "labels"),
    ("base_position", "token_id"),
    ("token_position", "token/position"),
    ("task", "task"),
    ("split", "split"),
    ("seed", "seed"),
    ("nonfinite", "non-finite"),
    ("residual", "residual"),
    ("source", "source RID"),
    ("metric_nonfinite", "non-finite"),
    ("metric_proof", "proof"),
    ("tensor_proof", "proof"),
    ("registry_proof", "proof"),
])
def test_alignment_rejects_hash_identity_label_position_and_proof_errors(
        mutation, match, tmp_path, monkeypatch):
    states = fake_states()
    index = 0  # full post state
    strategy, arrays, manifest, source, metrics, diagnostic = states[index]
    if mutation == "manifest":
        states[index] = (strategy, arrays, "different", source, metrics, diagnostic)
    elif mutation == "token":
        arrays["token_ids"][0] = "wrong"
    elif mutation == "label":
        arrays["y_true"][0] += 1
        arrays["residual"] = arrays["prediction"] - arrays["y_true"]
    elif mutation == "base_position":
        arrays["base_positions"][0] = 3
    elif mutation == "token_position":
        arrays["token_positions"][0] = 4
    elif mutation in ("task", "split", "seed"):
        value = {"task": "ssi", "split": "family", "seed": 29}[mutation]
        arrays[mutation] = np.asarray(value)
    elif mutation == "nonfinite":
        arrays["prediction"][0] = np.nan
    elif mutation == "residual":
        arrays["residual"][0] += 1
    elif mutation == "source":
        states[index] = (strategy, arrays, manifest, "wrong-source", metrics, diagnostic)
    elif mutation == "metric_nonfinite":
        metrics["pcc"] = float("nan")
    elif mutation == "metric_proof":
        diagnostic["full_test_metric_match"] = None
    elif mutation == "tensor_proof":
        diagnostic["checkpoint"]["restored_tensor_match"] = False
    elif mutation == "registry_proof":
        diagnostic["source_proof"]["state"] = "running"
    install_fake_tsne(monkeypatch, [])
    with pytest.raises((ValueError, FloatingPointError), match=match):
        mech.aligned_regression(states, tmp_path / (mutation + ".npz"))
    assert not (tmp_path / (mutation + ".npz")).exists()


def test_cross_task_diagnostic_is_rejected_even_with_matching_array_metadata(tmp_path):
    states = fake_states()
    states[0][1]["task"] = np.asarray("ssi")
    states[0][5]["task"] = "ssi"
    with pytest.raises(ValueError, match="task"):
        mech.aligned_regression(states, tmp_path / "cross-task.npz", task="degradation")


@pytest.mark.parametrize("field", ["y_true", "token_positions"])
def test_load_states_checks_labels_and_positions_against_saved_manifest(
        tmp_path, field):
    _strategy, original, _hash, _source, _metrics, original_diagnostic = \
        fake_states()[1]
    arrays = copy.deepcopy(original)
    diagnostic = copy.deepcopy(original_diagnostic)
    records = [{"token_id": str(arrays["token_ids"][index]),
                "sequence_id": str(arrays["sequence_ids"][index]),
                "base_position": int(arrays["base_positions"][index]),
                "token_position": int(arrays["token_positions"][index]),
                "y_true": float(arrays["y_true"][index])} for index in range(4)]
    manifest = {"task": "degradation", "split": "random", "seed": 17,
                "n_full_tokens": 6, "n_sample_tokens": 4,
                "token_ids": arrays["token_ids"].tolist(), "records": records,
                "full_test_sha256": "full-test-hash", "split_evidence": EVIDENCE}
    manifest["manifest_sha256"] = mech.manifest_digest(manifest)
    arrays["test_manifest_sha256"] = np.asarray(manifest["manifest_sha256"])
    diagnostic["test_manifest_sha256"] = manifest["manifest_sha256"]
    out_dir = tmp_path / mech.diagnostic_run_id(
        "degradation", "pre", "random", 17)
    out_dir.mkdir()
    np.savez(out_dir / "embeddings.npz", **arrays)
    (out_dir / "diagnostic.json").write_text(json.dumps(diagnostic))
    (out_dir / "test_manifest.json").write_text(json.dumps(manifest))
    assert len(mech.load_aligned_states(
        "degradation", "random", 17, artifact_root=tmp_path)) == 1
    if field == "y_true":
        arrays["y_true"][0] += 0.25
        arrays["residual"] = arrays["prediction"] - arrays["y_true"]
    else:
        arrays["token_positions"][0] += 1
    np.savez(out_dir / "embeddings.npz", **arrays)
    with pytest.raises(ValueError, match=field + ".*manifest"):
        mech.load_aligned_states("degradation", "random", 17, artifact_root=tmp_path)


def test_load_states_rejects_post_without_metric_or_tensor_proof(tmp_path):
    out_dir = tmp_path / mech.diagnostic_run_id(
        "degradation", "lora", "random", 17)
    out_dir.mkdir()
    np.savez(out_dir / "embeddings.npz", token_ids=np.asarray(["unused"]))
    diagnostic = {
        "status": "diagnostic", "model": mech.MODEL, "task": "degradation",
        "strategy": "lora", "split": "random", "seed": 17,
        "source_run_id": mech.source_run_id("degradation", "lora", "random", 17),
        "full_test_metric_match": None,
        "checkpoint": {"restored_tensor_match": True, "checkpoint_proof": "ok"},
    }
    (out_dir / "diagnostic.json").write_text(json.dumps(diagnostic))
    with pytest.raises(ValueError, match="proof"):
        mech.load_aligned_states("degradation", "random", 17, artifact_root=tmp_path)
    diagnostic["full_test_metric_match"] = True
    diagnostic["checkpoint"] = {"checkpoint_proof": "ok"}
    (out_dir / "diagnostic.json").write_text(json.dumps(diagnostic))
    with pytest.raises(ValueError, match="proof"):
        mech.load_aligned_states("degradation", "random", 17, artifact_root=tmp_path)


def test_pre_reference_head_is_seed201_token_mlp_not_zero_initialized():
    first = mech.fresh_reference_head(4, "cpu")
    first_state = {key: value.clone() for key, value in first.state_dict().items()}
    torch.manual_seed(999)
    second = mech.fresh_reference_head(4, "cpu")
    assert isinstance(first, TokenHead)
    assert first.fc1.out_features == 32 and first.fc2.out_features == 1
    assert all(torch.equal(value, second.state_dict()[key])
               for key, value in first_state.items())
    assert any(torch.count_nonzero(value) for value in first_state.values())


def test_cli_requires_positive_token_cap_and_keeps_canonical_defaults():
    argv = ["--task", "degradation", "--split", "random", "--strategy", "pre",
            "--device", "0", "--token-cap", "16"]
    args = mech.build_parser().parse_args(argv)
    assert args.seed == 17 and args.token_cap == 16
    assert mech.N_TRAIN == 0 and mech.MAX_LEN == 192
    mech.validate_args(args)
    with pytest.raises(SystemExit):
        mech.build_parser().parse_args(argv[:-2])
    bad = mech.build_parser().parse_args(argv[:-1] + ["0"])
    with pytest.raises(ValueError, match="positive"):
        mech.validate_args(bad)


def test_failure_after_npz_and_aligned_cleans_current_outputs(tmp_path, monkeypatch):
    args = mech.build_parser().parse_args(
        ["--task", "degradation", "--split", "random", "--strategy", "pre",
         "--device", "0", "--token-cap", "4"])
    monkeypatch.setattr(mech, "ARTIFACT_ROOT", tmp_path)
    monkeypatch.setattr(mech.common, "require_cuda", lambda device: "cuda:0")
    monkeypatch.setattr(mech.common, "wait_for_cuda_memory", lambda *args: None)
    monkeypatch.setattr(mech.common, "git_sha", lambda: "unit-sha")
    parts = {"train": [{"seq": "AA", "labels": [0.1]}],
             "val": [{"seq": "CC", "labels": [0.2]}],
             "test": [{"seq": "GG", "labels": [0.3]}]}
    evidence = {"status": "OK", "protocol": "bestval_v1"}
    monkeypatch.setattr(mech, "load_task_parts", lambda *args, **kwargs: (parts, evidence))
    manifest = {
        "task": "degradation", "split": "random", "seed": 17,
        "n_full_tokens": 1, "n_sample_tokens": 1,
        "full_test_sha256": "full-hash", "manifest_sha256": "manifest-hash",
        "test_manifest_sha256": "manifest-hash", "split_evidence": evidence,
        "selection": "unit",
    }
    monkeypatch.setattr(mech, "make_token_manifest",
                        lambda *args, **kwargs: (parts["test"], manifest, []))
    spec = SimpleNamespace(repo="multimolecule/rinalmo-micro")
    import rnafteval.models
    monkeypatch.setattr(rnafteval.models, "load_model",
                        lambda name, device: (spec, object(), DummyBackbone()))
    monkeypatch.setattr(mech, "encode_seqs", lambda tokenizer, seqs, device, max_len: {
        "input_ids": torch.ones(len(seqs), 2, dtype=torch.long),
        "attention_mask": torch.ones(len(seqs), 2, dtype=torch.long)})

    class FakeHead:
        def eval(self):
            return self

    monkeypatch.setattr(mech, "fresh_reference_head", lambda *args: FakeHead())
    monkeypatch.setattr(mech.vp, "runtime_evidence", lambda *args: {})
    full = {"y_true": np.asarray([0.3], dtype=np.float32),
            "prediction": np.asarray([0.4], dtype=np.float32),
            "sequence_ids": np.asarray(["sequence"])}
    sample = {"y_true": np.asarray([0.3], dtype=np.float32)}
    monkeypatch.setattr(mech, "extract", lambda *args, **kwargs: (full.copy(), sample.copy()))
    monkeypatch.setattr(mech, "regression_metrics", lambda *args: {"pcc": 0.5, "mcrmse": 0.1})
    monkeypatch.setattr(mech, "load_aligned_states", lambda *args: [
        ("lora", {}, "other", "lora-source", {}, {}),
        ("full", {}, "other", "full-source", {}, {})])

    def fake_aligned(states, path, task=None):
        mech.save_npz(path, tsne=np.zeros((1, 2)))
        return {"path": str(path)}

    monkeypatch.setattr(mech, "aligned_regression", fake_aligned)
    real_write_json = mech.common.write_json

    def fail_diagnostic(path, payload):
        if Path(path).name == "diagnostic.json":
            raise RuntimeError("injected after aligned")
        return real_write_json(path, payload)

    monkeypatch.setattr(mech.common, "write_json", fail_diagnostic)
    with pytest.raises(RuntimeError, match="injected after aligned"):
        mech.run(args)
    out_dir = tmp_path / mech.diagnostic_run_id("degradation", "pre", "random", 17)
    aligned = tmp_path / "mech_rinalmomicro_degradation_aligned_random_s17_ckpt_v1.npz"
    for path in (out_dir / "diagnostic.json", out_dir / "predictions.npz",
                 out_dir / "embeddings.npz", aligned):
        assert not path.exists()
    assert json.loads((out_dir / "job.json").read_text())["status"] == "failed"
