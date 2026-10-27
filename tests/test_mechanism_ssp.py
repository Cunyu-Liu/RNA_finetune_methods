import json
from pathlib import Path
import random
import sys
from types import SimpleNamespace

import numpy as np
import pytest
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import mechanism_ssp as mech
from rnafteval import finetune_ssp


class DummyTokenizer:
    prefix = (90,)
    suffix = (91,)
    pad_token_id = 0
    cls_token_id = 90
    eos_token_id = 91
    all_special_ids = (0, 90, 91)
    base_ids = {"A": 1, "C": 2, "G": 3, "U": 4, "T": 4, "N": 5}

    def get_special_tokens_mask(self, ids, already_has_special_tokens=False):
        assert already_has_special_tokens
        return [int(token_id in self.all_special_ids) for token_id in ids]

    def __call__(self, seqs, padding=True, truncation=True, max_length=192,
                 return_tensors="pt"):
        rows = []
        for seq in seqs:
            core = [self.base_ids[base] for base in seq]
            if truncation:
                core = core[:max(0, max_length - len(self.prefix) - len(self.suffix))]
            rows.append(list(self.prefix) + core + list(self.suffix))
        width = max(map(len, rows))
        input_ids, attention = [], []
        for row in rows:
            pad_n = width - len(row)
            input_ids.append(row + [self.pad_token_id] * pad_n)
            attention.append([1] * len(row) + [0] * pad_n)
        return {"input_ids": torch.tensor(input_ids),
                "attention_mask": torch.tensor(attention)}


class DummyBackbone(torch.nn.Module):
    def forward(self, input_ids, attention_mask):
        values = input_ids.float() / 100
        hidden = torch.stack((values, values + 1, values + 2,
                              attention_mask.float()), dim=-1)
        return SimpleNamespace(last_hidden_state=hidden)


def make_rows():
    return [
        {"id": "long", "seq": "ACGUAC", "L": 6,
         "pairs": [(0, 5), (1, 2), (0, 3)]},
        {"id": "short", "seq": "AC", "L": 2, "pairs": [(0, 1)]},
        {"id": "middle", "seq": "GGUU", "L": 4, "pairs": [(0, 3)]},
    ]


def test_b20_manifest_excludes_special_padding_and_right_truncates_pairs():
    _ordered, manifest, _selected = mech.make_pair_manifest(
        make_rows()[:2], DummyTokenizer(), "random", 17,
        pair_cap=16, batch_size=2, max_len=5)
    sequences = {row["source_id"]: row for row in manifest["sequences"]}
    assert sequences["long"]["base_token_positions"] == [1, 2, 3]
    assert sequences["short"]["base_token_positions"] == [1, 2]
    assert sequences["long"]["n_bases"] == 3
    assert sequences["long"]["n_positive_pairs"] == 1
    assert manifest["n_full_pairs"] == 4
    assert manifest["n_full_positive_pairs"] == 2
    long_records = [row for row in manifest["records"]
                    if row["source_id"] == "long"]
    assert {(row["base_i"], row["base_j"], row["label"])
            for row in long_records} == {(0, 1, 0), (0, 2, 0), (1, 2, 1)}
    assert all(0 < row["token_i"] < row["token_j"] < 5
               for row in manifest["records"])
    assert not any(row["base_i"] == 0 and row["base_j"] == 5
                   for row in long_records)


def test_pair_features_are_exact_pairhead_input_and_swap_symmetric():
    torch.manual_seed(7)
    head = finetune_ssp.PairHead(4, hidden=3)
    hidden = torch.randn(6, 4)
    token_i = torch.tensor([1, 2, 4, 0])
    token_j = torch.tensor([3, 4, 5, 2])
    features = mech.pair_features(head, hidden, token_i, token_j)
    z = torch.nn.functional.gelu(head.proj(hidden))
    zi, zj = z[token_i], z[token_j]
    expected = torch.cat((torch.minimum(zi, zj), torch.maximum(zi, zj),
                          zi * zj, torch.maximum(zi, zj) - torch.minimum(zi, zj)), dim=-1)
    assert features.shape == (4, 12)
    assert torch.equal(features, expected)
    scores = head(hidden.unsqueeze(0), torch.zeros(1, 6, dtype=torch.bool))[0]
    assert torch.allclose(mech.pair_logits(head, features),
                          scores[token_i, token_j], rtol=1e-6, atol=1e-7)
    swapped = mech.pair_features(head, hidden, token_j, token_i)
    assert torch.equal(features, swapped)
    assert torch.allclose(mech.pair_logits(head, features),
                          mech.pair_logits(head, swapped), rtol=0, atol=0)


def test_pooled_pair_f1_is_not_macro_and_threshold_is_strict():
    # Per-sequence F1 values are 1 and 0 (macro 0.5); pooled F1 is 8/9.
    labels = np.asarray([1, 1, 1, 1, 1])
    probabilities = np.asarray([0.9, 0.9, 0.9, 0.9, 0.1])
    metrics = mech.pooled_pair_metrics(labels, probabilities, 0.5)
    assert metrics == {"precision": 1.0, "recall": 0.8, "f1": 0.8889,
                       "tp": 4, "fp": 0, "fn": 1}
    assert metrics["f1"] != 0.5
    assert mech.pooled_pair_metrics([1], [0.5], 0.5)["f1"] == 0.0
    assert mech.pooled_pair_metrics([1], [0.5], 0.4)["f1"] == 1.0


def test_validation_threshold_grid_keeps_first_tie():
    threshold, val_f1 = mech.select_threshold(
        [1, 0, 1, 0], [0.9, 0.1, 0.8, 0.2], thresholds=(0.3, 0.4, 0.5))
    assert threshold == 0.3
    assert val_f1 == pytest.approx(1.0)
    assert mech.THRESHOLDS == (0.05, 0.1, 0.2, 0.3, 0.4,
                               0.5, 0.6, 0.7, 0.8, 0.9)


def test_manifest_is_deterministic_and_cap_does_not_change_full_metrics():
    tokenizer = DummyTokenizer()
    ordered, first, selected = mech.make_pair_manifest(
        make_rows(), tokenizer, "random", 17, pair_cap=1)
    ordered_reversed, repeated, selected_repeated = mech.make_pair_manifest(
        list(reversed(make_rows())), tokenizer, "random", 17, pair_cap=1)
    assert ordered == ordered_reversed
    assert first == repeated
    assert selected == selected_repeated
    assert first["n"] == 2
    assert first["sample_class_support"] == {"0": 1, "1": 1}
    _ordered2, second, selected2 = mech.make_pair_manifest(
        make_rows(), tokenizer, "random", 17, pair_cap=2)
    assert second["full_test_sha256"] == first["full_test_sha256"]
    assert second["n_full_pairs"] == first["n_full_pairs"]
    assert second["n_full_positive_pairs"] == first["n_full_positive_pairs"]
    assert second["n"] > first["n"]
    torch.manual_seed(11)
    backbone = DummyBackbone()
    head = finetune_ssp.PairHead(4)
    full1, sample1 = mech.extract(
        backbone, head, tokenizer, ordered, "cpu", selected, batch_size=2)
    full2, sample2 = mech.extract(
        backbone, head, tokenizer, ordered, "cpu", selected2, batch_size=2)
    for key in full1:
        assert np.array_equal(full1[key], full2[key]), key
    assert mech.pooled_pair_metrics(full1["labels"], full1["probabilities"], 0.5) == \
        mech.pooled_pair_metrics(full2["labels"], full2["probabilities"], 0.5)
    assert len(sample2["pair_ids"]) > len(sample1["pair_ids"])
    assert mech.validate_pair_arrays(sample1, first)
    assert mech.validate_pair_arrays(sample2, second)


def fake_states(manifest="same"):
    states = []
    pair_ids = np.asarray(["a:0000:0001", "a:0000:0002",
                           "a:0001:0002", "b:0000:0001"])
    for index, strategy in enumerate(("full", "pre", "lora")):
        logits = np.asarray([-2.0, 0.2, 1.0, 3.0], dtype=np.float32) + index
        probabilities = torch.sigmoid(torch.tensor(logits)).numpy()
        arrays = {
            "pair_ids": pair_ids,
            "sequence_ids": np.asarray(["a", "a", "a", "b"]),
            "base_i": np.asarray([0, 0, 1, 0]),
            "base_j": np.asarray([1, 2, 2, 1]),
            "token_i": np.asarray([1, 1, 2, 1]),
            "token_j": np.asarray([2, 3, 3, 2]),
            "labels": np.asarray([0, 1, 0, 1]),
            "logits": logits,
            "probabilities": probabilities,
            "head_input": np.full((4, 4), index + 1, dtype=np.float32),
            "split": np.asarray("random"), "seed": np.asarray(17),
        }
        metrics = {"f1": 0.5 + index / 10, "precision": 0.6,
                   "recall": 0.4, "threshold": 0.3, "val_f1": 0.55}
        states.append((strategy, arrays, manifest, "source_" + strategy, metrics))
    return states


def test_three_states_share_pairs_and_joint_tsne_uses_sigmoid(tmp_path, monkeypatch):
    calls = []

    class FakeTSNE:
        def __init__(self, **kwargs):
            calls.append(kwargs)

        def fit_transform(self, values):
            calls.append(values.copy())
            return np.zeros((len(values), 2), dtype=np.float32)

    import sklearn.manifold
    monkeypatch.setattr(sklearn.manifold, "TSNE", FakeTSNE)
    summary = mech.aligned_ssp(fake_states(), tmp_path / "aligned")
    assert summary["classification_silhouette"] is None
    assert len(calls) == 2
    with np.load(summary["path"], allow_pickle=False) as data:
        assert data["tsne"].shape == (12, 2)
        assert data["head_input"].shape == (12, 4)
        assert data["state"].tolist() == ["pre"] * 4 + ["lora"] * 4 + ["full"] * 4
        assert data["pair_ids"].tolist() == fake_states()[0][1]["pair_ids"].tolist() * 3
        assert data["source_run_ids"].tolist() == ["source_pre", "source_lora", "source_full"]
        assert np.allclose(data["probabilities"],
                           torch.sigmoid(torch.tensor(data["logits"])).numpy(),
                           rtol=1e-5, atol=1e-6)
        assert "silhouette" not in data.files
        assert "cls" not in data.files
    bad = fake_states()
    bad_arrays = dict(bad[0][1])
    bad_arrays["token_j"] = bad_arrays["token_j"].copy()
    bad_arrays["token_j"][0] += 1
    bad[0] = (bad[0][0], bad_arrays, bad[0][2], bad[0][3], bad[0][4])
    with pytest.raises(ValueError, match="pair 对齐"):
        mech.aligned_ssp(bad, tmp_path / "bad.npz")
    bad_probability = fake_states()
    arrays = dict(bad_probability[0][1])
    arrays["probabilities"] = np.full(4, 0.5, dtype=np.float32)
    bad_probability[0] = (bad_probability[0][0], arrays, *bad_probability[0][2:])
    with pytest.raises(ValueError, match="sigmoid"):
        mech.aligned_ssp(bad_probability, tmp_path / "bad_probability.npz")


def test_source_rids_use_ssp_job_rules_and_cli_records_default_cap():
    assert mech.source_run_id("lora", "random", 17) == \
        "ft_rinalmomicro_secondarystructure_lora_s17_random_pairalign_bestval_v1"
    assert mech.source_run_id("full", "family", 17) == \
        "ft_rinalmomicro_secondarystructure_full_s17_family_lr1e-05_pairalign_bestval_v1"
    with pytest.raises(ValueError, match="post"):
        mech.source_run_id("pre", "random", 17)
    args = mech.build_parser().parse_args(
        ["--split", "random", "--strategy", "pre", "--device", "0"])
    assert args.seed == 17 and args.pair_cap == 512
    assert mech.MAX_LEN == 192 and mech.N_TEST == 400


def test_random_source_parts_keep_official_validation_and_seed_test_draw(monkeypatch):
    calls = []
    rows = {
        "TR0": [{"id": "tr0", "seq": "AA", "pairs": []},
                {"id": "tr1", "seq": "CC", "pairs": []}],
        "VL0": [{"id": "vl", "seq": "GG", "pairs": []}],
        "TS0": [{"id": "ts%d" % i, "seq": "UU" + "A" * i, "pairs": []}
                for i in range(3)],
    }
    monkeypatch.setattr(mech.ssp_task, "load_metadata", lambda: {"present": {}})

    def load_split(name, meta, max_len):
        calls.append((name, max_len))
        return list(rows[name])

    observed = {}

    def prepare(train, val, test, **kwargs):
        observed.update(kwargs)
        observed["val_rows"] = val
        return train, val, test, {"status": "OK", "protocol": "bestval_v1"}

    monkeypatch.setattr(mech.ssp_task, "load_split", load_split)
    monkeypatch.setattr(mech, "prepare_convergence_splits", prepare)
    parts, evidence = mech.load_source_parts("random", 17)
    assert calls == [("TR0", 192), ("VL0", 192), ("TS0", 192)]
    assert observed["validation_source"] == "official_validation"
    assert observed["n_train"] == 2000 and observed["sample_seed"] == 17
    assert observed["protocol"] == "bestval_v1"
    assert parts["val"] == rows["VL0"]
    assert parts["test"] == random.Random(17).sample(rows["TS0"], 3)
    assert evidence["status"] == "OK"


def test_family_source_parts_backjoin_original_records_and_dedup_by_id(
        tmp_path, monkeypatch):
    path = tmp_path / "secondary-structure.parquet"
    path.write_bytes(b"dummy-parquet")
    monkeypatch.setattr(mech, "FAMILY_PARQUET", path)
    monkeypatch.setattr(mech.ssp_task, "load_metadata", lambda: {"present": {}})
    originals = {
        "a": {"id": "a", "seq": "AA", "pairs": [(0, 1)]},
        "b": {"id": "b", "seq": "CC", "pairs": []},
        "c": {"id": "c", "seq": "GG", "pairs": []},
    }

    def load_split(name, meta, max_len):
        assert max_len == 192
        if name == "TR0":
            return [dict(originals["a"]), dict(originals["b"])]
        if name == "VL0":
            return [dict(originals["a"], seq="DUPLICATE"), dict(originals["c"])]
        return []

    class Table:
        def to_pydict(self):
            return {"id": ["a", "b", "c"],
                    "split": ["train", "val", "test"],
                    "cluster_id": ["ca", "cb", "cc"]}

    import pyarrow.parquet as pq
    monkeypatch.setattr(pq, "read_table", lambda path: Table())
    observed = {}

    def prepare(train, val, test, **kwargs):
        observed.update(train=train, val=val, test=test, kwargs=kwargs)
        return train, val, test, {"status": "OK"}

    monkeypatch.setattr(mech.ssp_task, "load_split", load_split)
    monkeypatch.setattr(mech, "prepare_convergence_splits", prepare)
    parts, _evidence = mech.load_source_parts("family", 17)
    assert observed["kwargs"]["validation_source"] == "family_validation"
    assert observed["kwargs"]["family"] is True
    assert [row["id"] for row in observed["train"]] == ["a"]
    assert observed["train"][0]["seq"] == "AA"
    assert observed["train"][0]["cluster"] == "ca"
    assert observed["val"][0]["cluster"] == "cb"
    assert parts["test"][0]["id"] == "c"


def valid_source_result(parts, evidence, rid="source-rid"):
    return {
        "run_id": rid, "model": mech.MODEL, "task": mech.TASK,
        "strategy": "lora", "split": "random", "seed": 17,
        "metric": "F1", "max_len": 192,
        "pair_alignment": "b20_single_base_token_positions_v1",
        "n_train": len(parts["train"]), "n_val": len(parts["val"]),
        "n_test": len(parts["test"]), "data_evidence": evidence,
    }


def test_source_identity_counts_and_data_evidence_are_required():
    parts = {"train": [{}, {}], "val": [{}], "test": [{}]}
    evidence = {"status": "OK", "validation_source": "official_validation"}
    result = valid_source_result(parts, evidence)
    assert mech.validate_source_result(
        result, parts, evidence, "lora", "random", 17, "source-rid")
    with pytest.raises(ValueError, match="n_val"):
        mech.validate_source_result(
            dict(result, n_val=9), parts, evidence, "lora", "random", 17, "source-rid")
    with pytest.raises(ValueError, match="data_evidence"):
        mech.validate_source_result(
            dict(result, data_evidence={"status": "OK"}), parts, evidence,
            "lora", "random", 17, "source-rid")
    with pytest.raises(ValueError, match="身份"):
        mech.validate_source_result(
            dict(result, strategy="full"), parts, evidence,
            "lora", "random", 17, "source-rid")


def test_source_reconciliation_covers_threshold_val_and_all_test_metrics():
    metrics = {"threshold": 0.3, "val_f1": 0.75, "f1": 0.7,
               "precision": 0.8, "recall": 0.6}
    source = {"threshold": 0.3, "val_f1": 0.75, "value": 0.7,
              "precision": 0.8, "recall": 0.6}
    assert all(mech.reconcile_source_metrics(metrics, source).values())
    with pytest.raises(ValueError, match="对账失败"):
        mech.reconcile_source_metrics(dict(metrics, precision=0.7), source)


def test_failure_after_npz_and_aligned_cleans_current_outputs(tmp_path, monkeypatch):
    args = mech.build_parser().parse_args(
        ["--split", "random", "--strategy", "pre", "--device", "0"])
    monkeypatch.setattr(mech, "ARTIFACT_ROOT", tmp_path)
    monkeypatch.setattr(mech.common, "require_cuda", lambda device: "cuda:0")
    monkeypatch.setattr(mech.common, "wait_for_cuda_memory", lambda *args: None)
    monkeypatch.setattr(mech.common, "git_sha", lambda: "unit-sha")
    parts = {"train": [{"id": "tr", "seq": "AA", "pairs": []}],
             "val": [{"id": "vl", "seq": "CC", "pairs": []}],
             "test": [{"id": "ts", "seq": "GG", "pairs": []}]}
    evidence = {"status": "OK", "protocol": "bestval_v1"}
    monkeypatch.setattr(mech, "load_source_parts", lambda *args: (parts, evidence))
    manifest = {"split_evidence": evidence, "n_full_pairs": 3,
                "n_full_positive_pairs": 1, "n_full_sequences": 1,
                "full_test_sha256": "full-hash", "manifest_sha256": "manifest-hash"}
    monkeypatch.setattr(mech, "make_pair_manifest",
                        lambda *args, **kwargs: (parts["test"], manifest, []))
    spec = SimpleNamespace(repo="multimolecule/rinalmo-micro")
    import rnafteval.models
    monkeypatch.setattr(rnafteval.models, "load_model",
                        lambda name, device: (spec, object(), DummyBackbone()))
    monkeypatch.setattr(mech.finetune_ssp, "encode_one",
                        lambda tokenizer, seqs, device, max_len: {
                            "input_ids": torch.ones(len(seqs), 2, dtype=torch.long),
                            "attention_mask": torch.ones(len(seqs), 2, dtype=torch.long)})

    class FakeHead:
        def __init__(self, d_model):
            pass

        def to(self, device):
            return self

        def eval(self):
            return self

    monkeypatch.setattr(mech.finetune_ssp, "PairHead", FakeHead)
    monkeypatch.setattr(mech.vp, "runtime_evidence", lambda *args: {})
    val_full = {"labels": np.asarray([0, 1]),
                "probabilities": np.asarray([0.1, 0.9])}
    full = {"labels": np.asarray([0, 1, 0]),
            "probabilities": np.asarray([0.1, 0.9, 0.2])}
    sample = {"pair_ids": np.asarray(["pair"]), "probabilities": np.asarray([0.9])}

    def fake_extract(*args, **kwargs):
        selected = args[5] if len(args) > 5 else kwargs.get("selected")
        if selected is None:
            return val_full.copy(), None
        return full.copy(), sample.copy()

    monkeypatch.setattr(mech, "extract", fake_extract)
    monkeypatch.setattr(mech, "validate_pair_arrays", lambda *args: True)
    monkeypatch.setattr(mech, "load_aligned_states", lambda *args: [
        ("lora", {}, "other", "lora-source", {}),
        ("full", {}, "other", "full-source", {})])

    def fake_aligned(states, path):
        mech.save_npz(path, tsne=np.zeros((1, 2)))
        return {"path": str(path)}

    monkeypatch.setattr(mech, "aligned_ssp", fake_aligned)
    real_write_json = mech.common.write_json

    def fail_diagnostic(path, payload):
        if Path(path).name == "diagnostic.json":
            raise RuntimeError("injected after aligned")
        return real_write_json(path, payload)

    monkeypatch.setattr(mech.common, "write_json", fail_diagnostic)
    with pytest.raises(RuntimeError, match="injected after aligned"):
        mech.run(args)
    out_dir = tmp_path / mech.run_id("pre", "random", 17)
    aligned = tmp_path / "mech_rinalmomicro_ssp_aligned_random_s17_ckpt_v1.npz"
    for path in (out_dir / "diagnostic.json", out_dir / "predictions.npz",
                 out_dir / "embeddings.npz", aligned):
        assert not path.exists()
    assert json.loads((out_dir / "job.json").read_text())["status"] == "failed"
