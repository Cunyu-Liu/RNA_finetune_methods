import copy
import json
from pathlib import Path
import random
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


class DummyTokenizer:
    cls_token_id = 90
    eos_token_id = 91
    pad_token_id = 0
    all_special_ids = (0, 90, 91)
    base_ids = {"A": 1, "C": 2, "G": 3, "U": 4, "T": 4, "N": 5}

    def __call__(self, seqs, padding=True, truncation=True, max_length=128,
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


def manifest_for(rows, cap=4, max_len=128):
    return mech.make_token_manifest(
        DummyTokenizer(), rows, "random", 17, cap, {"status": "OK"},
        batch_size=2, max_len=max_len)


def test_random_reconstruction_matches_runner_dedup_holdout_and_seed_sample(
        tmp_path, monkeypatch):
    unique_train = [{"seq": seq, "labels": [0], "subset": "train"}
                    for seq in ("AA", "AC", "AG", "AU", "CA", "CC")]
    raw_train = unique_train + [dict(unique_train[0], labels=[2])]
    official_val = [{"seq": "GG", "labels": [1], "subset": "validation"},
                    {"seq": "AA", "labels": [2], "subset": "validation"},
                    {"seq": "GG", "labels": [0], "subset": "validation"}]
    raw_test = [{"seq": seq, "labels": [0], "subset": "test"}
                for seq in ("UU", "GG", "AA", "UU", "CU")]
    calls = []

    def load(path):
        calls.append(path)
        return {"train": raw_train, "validation": official_val, "test": raw_test}

    monkeypatch.setattr(mech.spl_task, "load_official_split", load)
    parts, evidence = mech.load_task_parts(
        "random", seed=29, n_train=3, data_root=tmp_path)
    expected_train, expected_val = mech.split_train_validation(unique_train, seed=17)
    expected_train = random.Random(29).sample(expected_train, 3)
    assert calls == [str(tmp_path / "beacon_raw" / "spliceai" / "data")]
    assert parts["train"] == expected_train
    assert parts["val"] == expected_val
    assert [row["seq"] for row in parts["test"]] == ["UU", "CU"]
    assert all(row["seq"] != "GG" for row in parts["val"])
    assert evidence["random_dedup"] == {
        "train_after_within_dedup": 6,
        "official_validation_after_train_dedup": 1,
        "test_after_train_and_official_validation_dedup": 2,
        "priority": ["train", "official_validation", "test"],
    }
    assert evidence["train_sampling"] == {
        "method": "random.Random(seed).sample_if_n_train_gt_0",
        "n_train": 3, "seed": 29, "rows_before": 5, "rows_after": 3}
    assert evidence["sequence_cross_split_overlap"] == {
        "train_val": 0, "train_test": 0, "val_test": 0}
    canonical, canonical_evidence = mech.load_task_parts(
        "random", seed=29, data_root=tmp_path)
    assert mech.N_TRAIN == 0
    assert canonical["train"] == mech.split_train_validation(unique_train, seed=17)[0]
    assert canonical_evidence["train_sampling"]["rows_after"] == 5


def test_family_reconstruction_reads_train_test_int_labels_and_clusters(
        tmp_path, monkeypatch):
    path = tmp_path / "family_splits" / "spliceai.parquet"
    path.parent.mkdir()
    path.write_bytes(b"synthetic-family-table")
    sequences = ["train-%d" % index for index in range(6)] + ["official-val"] + [
        "test-0", "test-1"]
    sides = ["train"] * 6 + ["val"] + ["test"] * 2
    clusters = ["tr-%d" % index for index in range(6)] + ["ignored", "te-0", "te-1"]
    table = {"seq": sequences, "labels": [[0], [1], [2], [0], [1], [2], [0], [1], [2]],
             "split": sides, "cluster_id": clusters}
    monkeypatch.setattr(mech.pq, "read_table",
                        lambda actual: SimpleNamespace(to_pydict=lambda: table))
    parts, evidence = mech.load_task_parts(
        "family", seed=29, n_train=2, data_root=tmp_path)
    raw_train = [{"seq": sequences[index], "labels": [table["labels"][index][0]],
                  "cluster": clusters[index]} for index in range(6)]
    heldout, expected_val = mech.split_train_validation(raw_train, seed=17)
    assert parts["train"] == random.Random(29).sample(heldout, 2)
    assert parts["val"] == expected_val
    assert len(parts["test"]) == 2
    assert all(type(row["labels"][0]) is int for rows in parts.values() for row in rows)
    assert {row["cluster"] for row in parts["test"]} == {"te-0", "te-1"}
    assert "official-val" not in {row["seq"] for rows in parts.values() for row in rows}
    assert evidence["family_parquet_sha256"] == mech.common.sha256_file(path)
    assert evidence["cluster_cross_split_overlap"] == {
        "train_val": 0, "train_test": 0, "val_test": 0}
    overlapping = {"train": [dict(raw_train[0])], "val": [dict(raw_train[1])],
                   "test": [dict(raw_train[0], seq="other")]}
    with pytest.raises(AssertionError, match="FAMILY OVERLAP"):
        mech.build_split_evidence(overlapping, "family")


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


def valid_source_result(parts):
    rid = mech.source_run_id("lora", "random", 17)
    return {"run_id": rid, "model": mech.MODEL, "task": mech.TASK,
            "strategy": "lora", "split": "random", "seed": 17,
            "metric": "MACRO_F1", "value": 0.75,
            "metric2": "MICRO_F1", "value2": 0.8,
            "n_train": len(parts["train"]), "n_val": len(parts["val"]),
            "n_test": len(parts["test"])}


def test_source_identity_counts_and_missing_data_evidence_are_explicit():
    parts = {"train": [{}, {}], "val": [{}], "test": [{}, {}, {}]}
    result = valid_source_result(parts)
    row = dict(result, status="done")
    assert mech.validate_source_result(
        result, row, result["run_id"], "lora", "random", 17, parts) == {
            "n_train": 2, "n_val": 1, "n_test": 3}
    evidence = mech.source_data_evidence(result)
    assert evidence["source_data_evidence_present"] is False
    assert "missing_in_source_result" in evidence["source_data_evidence_note"]
    assert "not_claimed" in evidence["source_data_evidence_note"]
    for field, value in (("task", "other"), ("n_train", 1), ("n_val", 2),
                         ("n_test", 2), ("run_id", "other"),
                         ("metric2", "AUC")):
        changed = dict(result, **{field: value})
        with pytest.raises(ValueError):
            mech.validate_source_result(changed, row, result["run_id"], "lora",
                                        "random", 17, parts)


def test_micro_f1_not_roc_auc_is_reconciled_against_value2():
    labels = np.asarray([0, 0, 0, 1, 2, 2])
    predicted = np.asarray([0, 0, 0, 1, 2, 0])
    logits = np.eye(3)[predicted] * 4
    metrics = mech.flat_metric(labels, logits)
    assert metrics["macro_f1"] == pytest.approx(53 / 63)
    assert metrics["micro_f1"] == pytest.approx(5 / 6)
    assert metrics["micro_f1"] != pytest.approx(metrics["roc_auc"])
    source = {"value": metrics["macro_f1"], "value2": metrics["micro_f1"]}
    assert all(mech.reconcile_source_metrics(metrics, source).values())
    changed_auc = dict(metrics, roc_auc=1.0 - metrics["roc_auc"])
    assert all(mech.reconcile_source_metrics(changed_auc, source).values())
    with pytest.raises(ValueError, match="MACRO_F1/MICRO_F1"):
        mech.reconcile_source_metrics(metrics, dict(source, value2=metrics["roc_auc"]))
    assert metrics["recalls"] == pytest.approx([1.0, 1.0, 0.5])


def test_token_manifest_is_deterministic_class_capped_and_has_correct_names():
    rows = [
        {"seq": "ACG", "labels": [0, 1, 2]},
        {"seq": "AAA", "labels": [0, 0, 1]},
        {"seq": "CCC", "labels": [2, 0, -100]},
    ]
    ordered, manifest, selected = manifest_for(rows, cap=1)
    ordered2, manifest2, selected2 = manifest_for(list(reversed(rows)), cap=1)
    assert ordered == ordered2
    assert manifest == manifest2
    assert selected == selected2
    assert manifest["n"] == manifest["n_sample_tokens"] == 3
    assert manifest["sample_class_support"] == {"0": 1, "1": 1, "2": 1}
    assert manifest["n_full_tokens"] == 8
    assert manifest["full_class_support"] == {"0": 4, "1": 2, "2": 2}
    assert manifest["class_names"] == ["negative", "acceptor", "donor"]
    assert mech.CLASS_NAMES == ("negative", "acceptor", "donor")
    assert manifest["roc_auc_role"] == mech.ROC_AUC_ROLE
    for bad_cap in (0, -1, True):
        with pytest.raises(ValueError, match="正整数"):
            manifest_for(rows, cap=bad_cap)


def test_b20_manifest_and_extract_use_long_labels_special_pad_and_right_truncation(
        monkeypatch):
    rows = [{"seq": "ACGUAC", "labels": [0, 1, 2, 0, 1, 2]},
            {"seq": "AC", "labels": [2, 0]}]
    calls = []
    real_align = mech.align_base_labels

    def observed_align(tokenizer, enc, batch, max_len, **kwargs):
        calls.append(kwargs["dtype"])
        return real_align(tokenizer, enc, batch, max_len, **kwargs)

    monkeypatch.setattr(mech, "align_base_labels", observed_align)
    ordered, manifest, selected = manifest_for(rows, cap=8, max_len=5)
    torch.manual_seed(7)
    backbone = DummyBackbone()
    head = make_head("per-base", 3, 3)
    full, sample = mech.extract(
        backbone, head, DummyTokenizer(), ordered, "cpu", manifest, selected,
        batch_size=2, max_len=5)
    assert calls and set(calls) == {torch.long}
    assert len(full["labels"]) == 5
    assert manifest["full_class_support"] == {"0": 2, "1": 1, "2": 2}
    for row in rows:
        sequence_id = mech.common.sequence_hash(row["seq"])
        keep = full["sequence_ids"] == sequence_id
        expected_n = min(len(row["seq"]), 3)
        assert full["base_positions"][keep].tolist() == list(range(expected_n))
        assert full["token_positions"][keep].tolist() == list(range(1, expected_n + 1))
        assert full["labels"][keep].tolist() == row["labels"][:expected_n]
        assert 0 not in full["token_positions"][keep]
    assert set(full["token_positions"]) <= {1, 2, 3}
    assert "positions" not in full and "positions" not in sample
    for index, token_id in enumerate(sample["token_ids"]):
        record = next(record for record in selected if record["token_id"] == token_id)
        row = ordered[record["seq_index"]]
        enc = DummyTokenizer()([row["seq"]], truncation=True, max_length=5,
                               return_tensors="pt")
        hidden = backbone(**enc).last_hidden_state
        token_position = record["token_position"]
        assert np.allclose(sample["token_embedding"][index],
                           hidden[0, token_position].numpy())
        expected_logits = head(hidden, enc["attention_mask"] == 0)[0, token_position]
        assert np.allclose(sample["logits"][index], expected_logits.detach().numpy(), atol=1e-6)
        assert record["token_id"].endswith("%04d" % record["base_position"])
    assert np.allclose(softmax(sample["logits"], axis=-1), sample["probabilities"],
                       rtol=1e-5, atol=1e-6)


def test_extract_recomputes_full_hash_token_count_and_class_support():
    rows = [{"seq": "ACG", "labels": [0, 1, 2]},
            {"seq": "AAA", "labels": [0, 0, 1]}]
    ordered, manifest, selected = manifest_for(rows, cap=8)
    backbone, head = DummyBackbone(), make_head("per-base", 3, 3)
    for field, match in (("full_test_sha256", "full-test hash"),
                         ("n_full_tokens", "token count"),
                         ("full_class_support", "class support")):
        changed = copy.deepcopy(manifest)
        if field == "full_test_sha256":
            changed[field] = "wrong"
        elif field == "n_full_tokens":
            changed[field] += 1
        else:
            changed[field]["0"] += 1
        with pytest.raises(ValueError, match=match):
            mech.extract(backbone, head, DummyTokenizer(), ordered, "cpu", changed,
                         selected, batch_size=2)


def test_full_test_hash_binds_task_maxlen_b20_identities_positions_and_labels():
    kwargs = dict(task="spliceai", max_len=128, b20_version=mech.B20_VERSION,
                  sequence_ids=["a", "b"], token_ids=["a:0000"],
                  token_sequence_ids=["a"], base_positions=[0],
                  token_positions=[1], labels=[2])
    digest = mech.compute_full_test_hash(**kwargs)
    changes = (("task", "other"), ("max_len", 129), ("b20_version", "other"),
               ("sequence_ids", ["a", "c"]), ("token_sequence_ids", ["b"]),
               ("base_positions", [1]), ("token_positions", [2]), ("labels", [1]))
    for field, value in changes:
        changed = dict(kwargs, **{field: value})
        assert mech.compute_full_test_hash(**changed) != digest


def fake_states(manifest="same-manifest"):
    states = []
    token_ids = np.asarray(["a:0000", "a:0001", "b:0000", "b:0001"])
    sequence_ids = np.asarray(["a", "a", "b", "b"])
    base_positions = np.asarray([0, 1, 0, 1], dtype=np.int64)
    token_positions = np.asarray([1, 2, 1, 2], dtype=np.int64)
    labels = np.asarray([0, 1, 2, 0], dtype=np.int64)
    for index, strategy in enumerate(("full", "pre", "lora")):
        logits = np.eye(3, dtype=np.float32)[labels] * (index + 1)
        arrays = {
            "token_ids": token_ids.copy(), "sequence_ids": sequence_ids.copy(),
            "base_positions": base_positions.copy(),
            "token_positions": token_positions.copy(), "labels": labels.copy(),
            "probabilities": softmax(logits, axis=-1).astype(np.float32),
            "logits": logits,
            "token_embedding": (np.arange(12, dtype=np.float32).reshape(4, 3)
                                + index * 20),
            "task": np.asarray("spliceai"), "split": np.asarray("random"),
            "seed": np.asarray(17, dtype=np.int64),
            "max_len": np.asarray(128, dtype=np.int64),
            "b20_version": np.asarray(mech.B20_VERSION),
            "n_full_tokens": np.asarray(6, dtype=np.int64),
            "n_sample_tokens": np.asarray(4, dtype=np.int64),
            "full_test_sha256": np.asarray("full-test-hash"),
            "test_manifest_sha256": np.asarray(manifest),
            "selection": np.asarray("token_id_before_prediction"),
        }
        source = mech.PRE_SOURCE if strategy == "pre" else mech.source_run_id(
            strategy, "random", 17)
        metrics = {"macro_f1": 0.5 + index / 10,
                   "micro_f1": 0.55 + index / 10,
                   "roc_auc": 0.6 + index / 10}
        states.append((strategy, arrays, manifest, source, metrics))
    return states


def install_fake_tsne(monkeypatch):
    class FakeTSNE:
        def __init__(self, **kwargs):
            pass

        def fit_transform(self, values):
            return np.zeros((len(values), 2), dtype=np.float32)

    import sklearn.manifold
    monkeypatch.setattr(sklearn.manifold, "TSNE", FakeTSNE)


def test_aligned_spliceai_compares_all_identities_and_exports_micro(tmp_path, monkeypatch):
    install_fake_tsne(monkeypatch)
    summary = mech.aligned_spliceai(fake_states(), tmp_path / "aligned")
    assert summary["classification_silhouette"] is None
    with np.load(summary["path"], allow_pickle=False) as data:
        assert data["token_embedding"].shape == (12, 3)
        assert data["state"].tolist() == ["pre"] * 4 + ["lora"] * 4 + ["full"] * 4
        assert data["source_run_ids"].tolist() == [
            mech.PRE_SOURCE, mech.source_run_id("lora", "random", 17),
            mech.source_run_id("full", "random", 17)]
        assert data["full_micro_f1"].tolist() == pytest.approx([0.65, 0.75, 0.55])
        assert data["base_positions"].shape == data["token_positions"].shape == (12,)
        assert str(data["roc_auc_role"]) == mech.ROC_AUC_ROLE
        assert data["class_names"].tolist() == ["negative", "acceptor", "donor"]
        assert "positions" not in data.files and "cls" not in data.files
    successful = Path(summary["path"]).read_bytes()
    with pytest.raises(FileExistsError, match="拒绝覆盖"):
        mech.aligned_spliceai(fake_states(), summary["path"])
    assert Path(summary["path"]).read_bytes() == successful


@pytest.mark.parametrize("field", ["token_ids", "sequence_ids", "base_positions",
                                   "token_positions", "labels"])
def test_aligned_spliceai_rejects_any_three_state_identity_mismatch(
        tmp_path, monkeypatch, field):
    states = fake_states()
    arrays = states[0][1]
    if field == "token_ids":
        arrays[field][0] = "wrong"
    elif field == "sequence_ids":
        arrays[field][0] = "z"
        arrays["token_ids"][0] = "z:0000"
    elif field == "base_positions":
        arrays[field][0] = 3
        arrays["token_ids"][0] = "a:0003"
    elif field == "token_positions":
        arrays[field][0] += 1
    else:
        arrays[field][0] = 2
    install_fake_tsne(monkeypatch)
    with pytest.raises(ValueError):
        mech.aligned_spliceai(states, tmp_path / (field + ".npz"))
    assert not (tmp_path / (field + ".npz")).exists()


def write_state(root, strategy="pre"):
    item = next(item for item in fake_states() if item[0] == strategy)
    _strategy, original, _hash, source, metrics = item
    arrays = copy.deepcopy(original)
    records = [{"token_id": str(arrays["token_ids"][index]),
                "sequence_id": str(arrays["sequence_ids"][index]),
                "base_position": int(arrays["base_positions"][index]),
                "token_position": int(arrays["token_positions"][index]),
                "label": int(arrays["labels"][index])} for index in range(4)]
    manifest = {
        "artifact_type": "spliceai_token_test_manifest", "model": mech.MODEL,
        "task": mech.TASK, "split": "random", "seed": 17, "max_len": 128,
        "b20_version": mech.B20_VERSION, "n_full_tokens": 6, "n_sample_tokens": 4,
        "token_ids": arrays["token_ids"].tolist(), "records": records,
        "sequence_ids": ["a", "b"], "full_test_sha256": "full-test-hash",
        "full_class_support": {"0": 3, "1": 1, "2": 2},
        "sample_class_support": {"0": 2, "1": 1, "2": 1},
        "class_names": list(mech.CLASS_NAMES),
    }
    manifest["manifest_sha256"] = mech._manifest_digest(manifest)
    arrays["test_manifest_sha256"] = np.asarray(manifest["manifest_sha256"])
    diagnostic = {
        "artifact_type": "spliceai_diagnostic", "status": "diagnostic",
        "model": mech.MODEL, "task": mech.TASK, "strategy": strategy,
        "split": "random", "seed": 17,
        "source_run_id": None if strategy == "pre" else source,
        "reference_head_seed": 201 if strategy == "pre" else None,
        "full_test_metric_match": None if strategy == "pre" else True,
        "checkpoint": None if strategy == "pre" else {
            "restored_tensor_match": True, "checkpoint_proof": "ok"},
        "source_proof": None if strategy == "pre" else {"state": "complete"},
        "metrics_full": metrics, "test_manifest_sha256": manifest["manifest_sha256"],
        "full_test_sha256": "full-test-hash",
    }
    out_dir = root / mech.diagnostic_run_id(strategy, "random", 17)
    out_dir.mkdir(parents=True)
    np.savez(out_dir / "embeddings.npz", **arrays)
    (out_dir / "diagnostic.json").write_text(json.dumps(diagnostic))
    (out_dir / "test_manifest.json").write_text(json.dumps(manifest))
    return out_dir, arrays, manifest, diagnostic


@pytest.mark.parametrize("strategy", ["pre", "lora"])
def test_load_states_recomputes_manifest_and_preserves_complete_post_gate(
        tmp_path, strategy):
    write_state(tmp_path, strategy)
    ready = mech.load_aligned_states("random", 17, artifact_root=tmp_path)
    assert len(ready) == 1 and ready[0][0] == strategy


def test_load_states_requires_manifest_and_rejects_tamper_or_identity_errors(tmp_path):
    out_dir, _arrays, manifest, diagnostic = write_state(tmp_path)
    (out_dir / "test_manifest.json").unlink()
    with pytest.raises(ValueError, match="missing its test manifest"):
        mech.load_aligned_states("random", 17, artifact_root=tmp_path)
    for field, value in (("model", "other"), ("task", "other"),
                         ("strategy", "full"), ("split", "family"), ("seed", 29)):
        out_dir, _arrays, manifest, diagnostic = write_state(tmp_path / field)
        diagnostic[field] = value
        (out_dir / "diagnostic.json").write_text(json.dumps(diagnostic))
        with pytest.raises(ValueError, match="身份"):
            mech.load_aligned_states("random", 17, artifact_root=tmp_path / field)
    out_dir, _arrays, manifest, diagnostic = write_state(tmp_path / "digest")
    manifest["class_names"] = ["negative", "donor", "acceptor"]
    (out_dir / "test_manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="manifest hash"):
        mech.load_aligned_states("random", 17, artifact_root=tmp_path / "digest")


@pytest.mark.parametrize("field", ["token_ids", "sequence_ids", "base_positions",
                                   "token_positions", "labels"])
def test_load_states_checks_every_sample_against_manifest(tmp_path, field):
    out_dir, arrays, _manifest, _diagnostic = write_state(tmp_path)
    if field == "token_ids":
        arrays[field][0] = "wrong"
    elif field == "sequence_ids":
        arrays[field][0] = "z"
        arrays["token_ids"][0] = "z:0000"
    elif field == "base_positions":
        arrays[field][0] = 3
        arrays["token_ids"][0] = "a:0003"
    elif field == "token_positions":
        arrays[field][0] += 1
    else:
        arrays[field][0] = 2
    np.savez(out_dir / "embeddings.npz", **arrays)
    with pytest.raises(ValueError):
        mech.load_aligned_states("random", 17, artifact_root=tmp_path)


def test_load_states_rejects_post_without_metric_checkpoint_or_registry_proof(tmp_path):
    out_dir, _arrays, _manifest, diagnostic = write_state(tmp_path, "lora")
    for mutate in (
            lambda value: value.update(full_test_metric_match=None),
            lambda value: value["checkpoint"].update(restored_tensor_match=False),
            lambda value: value["source_proof"].update(state="running")):
        current = copy.deepcopy(diagnostic)
        mutate(current)
        (out_dir / "diagnostic.json").write_text(json.dumps(current))
        with pytest.raises(ValueError, match="proof|证明"):
            mech.load_aligned_states("random", 17, artifact_root=tmp_path)


def test_source_registry_proof_requires_complete_state_and_same_directory(
        tmp_path, monkeypatch):
    import expansion_queue

    registry = tmp_path / "jobs.json"
    registry.write_text("[]")
    result_dir = tmp_path / "result"
    job = SimpleNamespace(rid="source-rid", result_dir=str(result_dir), job_key="job-key")
    monkeypatch.setattr(expansion_queue, "load_jobs", lambda path: [job])
    monkeypatch.setattr(expansion_queue, "proof_state", lambda job: ("complete", ""))
    ledger_row = {"out_dir": str(result_dir)}
    proof = mech.common.require_complete_source("source-rid", ledger_row, registry)
    assert proof["state"] == "complete"
    assert proof["job_key"] == "job-key"
    assert proof["registry_sha256"] == mech.common.sha256_file(registry)
    with pytest.raises(ValueError, match="out_dir differ"):
        mech.common.require_complete_source(
            "source-rid", {"out_dir": str(tmp_path / "other")}, registry)
    monkeypatch.setattr(expansion_queue, "proof_state", lambda job: ("runnable", ""))
    with pytest.raises(ValueError, match="not complete"):
        mech.common.require_complete_source("source-rid", ledger_row, registry)


def test_failure_after_npz_and_aligned_removes_only_current_unfinished_outputs(
        tmp_path, monkeypatch):
    args = mech.build_parser().parse_args(
        ["--split", "random", "--strategy", "pre", "--device", "0"])
    monkeypatch.setattr(mech, "ARTIFACT_ROOT", tmp_path)
    monkeypatch.setattr(mech.common, "require_cuda", lambda device: "cuda:0")
    monkeypatch.setattr(mech.common, "wait_for_cuda_memory", lambda *args: None)
    monkeypatch.setattr(mech.common, "git_sha", lambda: "unit-sha")
    parts = {"train": [{"seq": "AA", "labels": [0]}],
             "val": [{"seq": "CC", "labels": [1]}],
             "test": [{"seq": "ACG", "labels": [0, 1, 2]}]}
    monkeypatch.setattr(mech, "load_task_parts", lambda *args, **kwargs: (parts, {"status": "OK"}))
    manifest = {
        "task": mech.TASK, "split": "random", "seed": 17, "max_len": 128,
        "b20_version": mech.B20_VERSION, "n_full_tokens": 3, "n_sample_tokens": 1,
        "full_test_sha256": "full-hash", "manifest_sha256": "manifest-hash",
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
        def to(self, device):
            return self

        def eval(self):
            return self

    monkeypatch.setattr(mech, "make_head", lambda *args: FakeHead())
    monkeypatch.setattr(mech.vp, "runtime_evidence", lambda *args: {})
    full = {"labels": np.asarray([0, 1, 2]),
            "logits": np.zeros((3, 3), dtype=np.float32)}
    sample = {"token_ids": np.asarray(["sample"])}
    monkeypatch.setattr(mech, "extract", lambda *args, **kwargs: (full.copy(), sample.copy()))
    monkeypatch.setattr(mech, "flat_metric", lambda *args: {
        "macro_f1": 0.5, "micro_f1": 0.6, "roc_auc": 0.7, "recalls": [0, 0, 0]})
    monkeypatch.setattr(mech, "load_aligned_states", lambda *args: [
        ("lora", {}, "other", "lora-source", {}),
        ("full", {}, "other", "full-source", {})])

    def fake_aligned(states, path):
        mech.save_npz(path, tsne=np.zeros((1, 2)))
        return {"path": str(path)}

    monkeypatch.setattr(mech, "aligned_spliceai", fake_aligned)
    real_write_json = mech.common.write_json

    def fail_diagnostic(path, payload):
        if Path(path).name == "diagnostic.json":
            raise RuntimeError("injected after aligned")
        return real_write_json(path, payload)

    monkeypatch.setattr(mech.common, "write_json", fail_diagnostic)
    with pytest.raises(RuntimeError, match="injected after aligned"):
        mech.run(args)
    out_dir = tmp_path / mech.diagnostic_run_id("pre", "random", 17)
    aligned = tmp_path / "mech_rinalmomicro_spliceai_aligned_random_s17_ckpt_v1.npz"
    for path in (out_dir / "diagnostic.json", out_dir / "predictions.npz",
                 out_dir / "embeddings.npz", aligned):
        assert not path.exists()
    assert json.loads((out_dir / "job.json").read_text())["status"] == "failed"
