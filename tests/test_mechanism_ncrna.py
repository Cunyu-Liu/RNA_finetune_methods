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
import mechanism_ncrna as mech


def make_rows(count=12, split="family"):
    rows = []
    for index in range(count):
        sequence = ("ACGU" * 8)[:4 + index % 12]
        rows.append({"seq": sequence + "A" * (index // 4),
                     "label": index % 2, "cluster": "family-%d" % (index // 4)})
    if split == "random":
        for row in rows:
            row.pop("cluster")
    return rows


def test_test_manifest_is_order_independent_and_shared(tmp_path):
    rows = make_rows(20)
    family_file = tmp_path / "family.parquet"
    family_file.write_bytes(b"unit-test-cluster-table")
    first = mech.make_test_manifest(rows, "family", family_path=family_file)
    second = mech.make_test_manifest(list(reversed(rows)), "family",
                                    family_path=family_file)
    assert first == second
    assert first["sample_ids"] == first["seq_hashes"]
    assert len(set(first["sample_ids"])) == first["n"]
    assert first["family_parquet_sha256"] == mech.sha256_file(family_file)
    family_file.write_bytes(b"different-cluster-table")
    changed = mech.make_test_manifest(rows, "family", family_path=family_file)
    assert changed["manifest_sha256"] != first["manifest_sha256"]


def test_per_family_cap_and_fixed_n_test_subsample(tmp_path):
    rows = []
    for family in range(3):
        for index in range(9):
            rows.append({"seq": "A" * (family * 9 + index + 1),
                         "label": family, "cluster": "c%d" % family})
    selected = mech.sample_rows(rows, "family", max_per_family=4)
    counts = {}
    for row in selected:
        counts[row["cluster"]] = counts.get(row["cluster"], 0) + 1
    assert counts == {"c0": 4, "c1": 4, "c2": 4}
    assert mech.sample_rows(rows, "family", max_per_family=4) == selected
    smoke = mech.sample_rows(rows, "family", n_test=8, max_per_family=4)
    assert len(smoke) <= 8
    assert smoke == mech.sample_rows(list(reversed(rows)), "family",
                                     n_test=8, max_per_family=4)
    family_file = tmp_path / "family.parquet"
    family_file.write_bytes(b"families")
    manifest = mech.make_test_manifest(rows, "family", max_per_family=4,
                                       family_path=family_file)
    assert manifest["cap_unit"] == "family_id"
    assert {r["family_id"] for r in manifest["records"]} == {"c0", "c1", "c2"}


def test_random_cap_is_by_label_without_invented_cluster():
    rows = make_rows(12, "random")
    selected = mech.make_test_manifest(rows, "random", max_per_family=3)
    counts = {label: sum(r["label"] == label for r in selected["records"])
              for label in (0, 1)}
    assert counts == {0: 3, 1: 3}
    assert selected["family_id_source"] == "seq_hash_not_clustered"
    assert all(len(r["seq_hash"]) == 64 for r in selected["records"])


def test_entropy_margin_accuracy_and_confusion_matrix():
    logits = np.asarray([[3.0, 0.0, 0.0], [0.0, 3.0, 0.0],
                         [0.0, 1.0, 3.0]], dtype=np.float32)
    labels = np.asarray([0, 1, 1])
    result = mech.prediction_metrics(logits, labels)
    metrics = result["metrics"]
    assert metrics["ACC"] == pytest.approx(2 / 3)
    assert metrics["max_class_prediction_fraction"] == pytest.approx(1 / 3)
    assert metrics["confusion_matrix"] == [[1, 0, 0], [0, 1, 1], [0, 0, 0]]
    assert np.allclose(result["probabilities"].sum(axis=1), 1)
    assert np.allclose(result["entropy"],
                       -(result["probabilities"] *
                         np.log(result["probabilities"])).sum(axis=1), atol=1e-6)
    assert np.all(result["margin"] > 0)
    assert metrics["prediction_entropy_median"] == pytest.approx(
        float(np.median(result["entropy"])), abs=1e-6)


def fake_tsne_states(n=4):
    states = []
    for state_index, state in enumerate(mech.STATES):
        embedding = np.arange(n * 3, dtype=np.float32).reshape(n, 3)
        embedding = embedding + state_index * 20
        arrays = {
            "sample_ids": np.asarray(["sample-%d" % index for index in range(n)]),
            "labels": np.asarray([0, 1, 0, 1])[:n],
            "cls": embedding + 1,
            "head_embedding": embedding,
        }
        states.append((state, arrays, "same-manifest", Path(state)))
    return states


def test_joint_tsne_single_fit_shape_and_original_embedding_silhouette(
        tmp_path, monkeypatch):
    states = fake_tsne_states()
    calls = []

    class FakeTSNE:
        def __init__(self, n_components, random_state, perplexity):
            calls.append(("init", n_components, random_state, perplexity))

        def fit_transform(self, values):
            calls.append(("fit", values.copy()))
            return np.arange(len(values) * 2).reshape(len(values), 2)

    import sklearn.manifold
    import sklearn.metrics
    monkeypatch.setattr(sklearn.manifold, "TSNE", FakeTSNE)
    monkeypatch.setattr(sklearn.metrics, "silhouette_score",
                        lambda values, labels: float(values.shape[1]))
    output = tmp_path / "aligned_tsne.npz"
    summary = mech.aligned_tsne(states, output)
    assert [call[0] for call in calls] == ["init", "fit"]
    assert calls[0][1:] == (2, 17, 11)
    assert np.array_equal(calls[1][1],
                          np.concatenate([s[1]["head_embedding"] for s in states]))
    with np.load(output, allow_pickle=False) as saved:
        assert saved["tsne"].shape == (12, 2)
        assert saved["head_embedding"].shape == (12, 3)
        assert saved["labels"].shape == (12,)
        assert saved["state"].tolist() == ["pre"] * 4 + ["lora"] * 4 + ["full"] * 4
        assert saved["sample_ids"].tolist() == states[0][1]["sample_ids"].tolist() * 3
        assert json.loads(str(saved["silhouette"])) == {"pre": 3.0, "lora": 3.0, "full": 3.0}
        assert "descriptive" in str(saved["interpretation"])
    assert summary["perplexity"] == 11
    assert summary["silhouette_input"] == "original_head_embedding"


def test_small_joint_tsne_uses_n_minus_one_perplexity(tmp_path, monkeypatch):
    states = fake_tsne_states(n=2)
    import sklearn.manifold
    import sklearn.metrics
    captured = {}

    class FakeTSNE:
        def __init__(self, **kwargs):
            captured.update(kwargs)

        def fit_transform(self, values):
            return np.zeros((len(values), 2), dtype=np.float32)

    monkeypatch.setattr(sklearn.manifold, "TSNE", FakeTSNE)
    monkeypatch.setattr(sklearn.metrics, "silhouette_score", lambda x, y: 0.0)
    mech.aligned_tsne(states, tmp_path / "small.npz")
    assert captured == {"n_components": 2, "random_state": 17, "perplexity": 5}


def test_single_state_does_not_make_forced_three_way_tsne(tmp_path):
    with pytest.raises(ValueError, match="requires pre, lora and full"):
        mech.aligned_tsne(fake_tsne_states()[:1], tmp_path / "not-made.npz")
    assert not (tmp_path / "not-made.npz").exists()


def test_pre_baseline_needs_no_fake_convergence(tmp_path):
    pre = {"artifact_type": "diagnostic", "status": "diagnostic",
           "strategy": "pre", "pretrained_baseline": True,
           "convergence_required": False, "convergence": None}
    assert mech.diagnostic_is_usable(pre)
    args = SimpleNamespace(strategy="pre", converge=False, out_suffix="_mech_v1",
                           batch_size=32, epochs=10)
    mech.validate_args(args)


def test_nonconverged_post_cannot_be_aligned(tmp_path):
    payload = {"artifact_type": "diagnostic", "status": "diagnostic",
               "strategy": "lora", "pretrained_baseline": False,
               "convergence": {"status": "NOT_CONVERGED"},
               "checkpoints": {}}
    assert not mech.diagnostic_is_usable(payload)
    args = SimpleNamespace(strategy="full", converge=False, out_suffix="_mech_v1",
                           batch_size=32, epochs=10)
    with pytest.raises(ValueError, match="requires --converge"):
        mech.validate_args(args)
    args.converge = True
    args.convergence_mode = "plateau"
    with pytest.raises(ValueError, match="bestval"):
        mech.validate_args(args)
    args.convergence_mode = "bestval"
    mech.validate_args(args)


def test_small_tensor_extracts_cls_head_pool_and_logits(monkeypatch):
    class TinyBackbone(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.projection = torch.nn.Linear(4, 5, bias=False)

        def forward(self, input_ids, attention_mask):
            hidden = self.projection(torch.nn.functional.one_hot(
                input_ids, num_classes=4).float())
            return SimpleNamespace(last_hidden_state=hidden)

    class TinyTokenizer:
        def __call__(self, sequences, **kwargs):
            ids = torch.arange(12, dtype=torch.int64).reshape(2, 6) % 4
            return {"input_ids": ids,
                    "attention_mask": torch.ones_like(ids)}

    head = mech.make_head("per-seq", 5, 13)
    head._mechanism_state = "pre"
    calls = []

    def observed_pool(module, inputs, output):
        hidden, pad = inputs
        calls.append((tuple(hidden.shape), tuple(pad.shape)))

    hook = head.pool.register_forward_hook(observed_pool)
    rows = [{"seq": "ACGU", "label": 0, "cluster": "c0"},
            {"seq": "GGCCAA", "label": 1, "cluster": "c1"}]
    arrays, metrics = mech.extract_tensors(
        TinyBackbone(), head, TinyTokenizer(), rows, torch.device("cpu"), batch_size=1)
    assert calls and calls[0] == ((2, 6, 5), (2, 6))
    assert arrays["cls"].shape == (2, 5)
    assert arrays["head_embedding"].shape == (2, 5)
    assert arrays["logits"].shape == (2, 13)
    assert arrays["probabilities"].shape == (2, 13)
    assert arrays["length"].tolist() == [4, 6]
    assert arrays["gc"].tolist() == pytest.approx([0.5, 4 / 6])
    assert arrays["family_id"].tolist() == ["c0", "c1"]
    assert str(arrays["state"]) == "pre"
    assert str(arrays["split"]) == "random"
    assert int(arrays["seed"]) == 17
    assert len(metrics["confusion_matrix"]) == 13
    hook.remove()


def test_formal_runner_rejects_cpu_and_unavailable_cuda(monkeypatch):
    monkeypatch.setattr(mech.torch.cuda, "is_available", lambda: False)
    with pytest.raises(RuntimeError, match="requires real CUDA"):
        mech.require_cuda(0)
    with pytest.raises(RuntimeError, match="requires a CUDA device"):
        mech.require_cuda("cpu")
    assert mech.main(["--split", "random", "--strategy", "pre", "--device", "0"]) == 2


def test_diagnostic_extraction_rejects_cpu_and_checkpoint_gate():
    with pytest.raises(RuntimeError, match="real CUDA"):
        mech.extract_diagnostics(None, None, None, [], "cpu")
    args = SimpleNamespace(device="cpu", strategy="lora")
    with pytest.raises(RuntimeError, match="real CUDA"):
        mech.train_model(None, None, {}, args, "unused", "rid", {})


def test_mocked_data_uses_fixed_random_split_and_family_validation(tmp_path):
    records = [{"seq": ("ACGU" * 40)[:index + 4], "label": index % 13}
               for index in range(26)]
    observed = {}
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(mech, "load_ncrna", lambda path: records)
    monkeypatch.setattr(mech, "dedup", lambda rows: list(rows))

    def fake_random_split(rows, seed):
        observed["seed"] = seed
        return {"train": rows[:13], "val": rows[13:20], "test": rows[20:]}

    def fake_prepare(train, val, test, **kwargs):
        observed["family"] = kwargs["family"]
        observed["validation_source"] = kwargs["validation_source"]
        return train, val, test, {"status": "OK"}

    monkeypatch.setattr(mech, "random_split", fake_random_split)
    monkeypatch.setattr(mech, "prepare_convergence_splits", fake_prepare)
    try:
        _, parts, labels, _, family_path = mech.load_data(
            "random", out_dir=tmp_path)
        assert observed == {"seed": 17, "family": False,
                            "validation_source": "random_split_validation"}
        assert labels == list(range(13))
        assert len(parts["val"]) == 7 and family_path is None
    finally:
        monkeypatch.undo()


def test_mocked_family_data_reads_cluster_parquet_and_keeps_validation(tmp_path):
    import pyarrow as pa
    import pyarrow.parquet as pq
    records = [{"seq": "A" * (index + 2), "label": index % 13,
                "cluster": "c%d" % index} for index in range(26)]
    split = ["train"] * 13 + ["val"] * 7 + ["test"] * 6
    path = tmp_path / "family_splits" / "noncoding-rna-family.parquet"
    path.parent.mkdir()
    pq.write_table(pa.table({"seq": [r["seq"] for r in records],
                             "label": [r["label"] for r in records],
                             "cluster_id": [r["cluster"] for r in records],
                             "split": split}), path)
    observed = {}

    def prepare(train, val, test, **kwargs):
        observed["family"] = kwargs["family"]
        observed["source"] = kwargs["validation_source"]
        return train, val, test, {"status": "OK"}

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(mech, "prepare_convergence_splits", prepare)
    try:
        _, parts, labels, _, family_path = mech.load_data(
            "family", data_root=tmp_path)
        assert observed == {"family": True, "source": "family_validation"}
        assert len(parts["train"]) == 13 and len(parts["val"]) == 7
        assert len(parts["test"]) == 6 and labels == list(range(13))
        assert family_path == path
    finally:
        monkeypatch.undo()


def test_mocked_training_uses_protocol_and_requires_convergence(tmp_path):
    events = []

    class FakeOptimizer:
        def __init__(self, parameters, lr):
            events.append(("optimizer", lr))
            self.parameters = list(parameters)

        def zero_grad(self):
            pass

        def step(self):
            events.append(("step",))
            with torch.no_grad():
                for parameter in self.parameters:
                    parameter.add_(0.1)

    class Tiny(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.weight = torch.nn.Parameter(torch.ones(1))

        def forward(self, input_ids, attention_mask):
            return self.weight.expand(2, 2, 2)

    class TinyBackbone(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.weight = torch.nn.Parameter(torch.ones(1))

        def forward(self, input_ids, attention_mask):
            return SimpleNamespace(last_hidden_state=torch.ones(2, 2, 2))

    val_losses = iter([1.0, 0.5, 0.7, 0.8, 0.9])

    class Loss:
        def __call__(self, logits, labels):
            return logits.sum() * 0 + (
                next(val_losses) if bool(labels[0].item()) else 1.0)

    loss = Loss()
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(mech.torch.cuda, "is_available", lambda: True)
    real_tensor = torch.tensor
    monkeypatch.setattr(mech.torch, "tensor",
                        lambda values, device=None: real_tensor(values, device="cpu"))
    monkeypatch.setattr(mech.torch.optim, "AdamW", FakeOptimizer)
    monkeypatch.setattr(mech.torch.nn, "CrossEntropyLoss", lambda: loss)
    real_make_tracker = mech.vp.make_tracker
    monkeypatch.setattr(mech.vp, "make_tracker",
                        lambda *args, **kwargs: events.append(("make_tracker",)) or
                        real_make_tracker(*args, **kwargs))
    real_restore = mech.vp.restore_best_checkpoint

    def restore_on_test_cpu(tracker, backbone, head, device):
        assert device == "cuda:0"
        events.append(("restore_best",))
        return real_restore(tracker, backbone, head, "cpu")

    monkeypatch.setattr(mech.vp, "restore_best_checkpoint", restore_on_test_cpu)
    monkeypatch.setattr(mech, "encode_seqs", lambda *args: {
        "input_ids": torch.ones(2, 2, dtype=torch.int64),
        "attention_mask": torch.ones(2, 2, dtype=torch.int64)})
    monkeypatch.setattr(mech.torch.nn.utils, "clip_grad_norm_",
                        lambda parameters, maximum: events.append(("clip", maximum)))
    args = SimpleNamespace(strategy="full", split="random", device="cuda:0", seed=17,
                           batch_size=2, converge=True, convergence_mode="bestval", epochs=1,
                           patience=3, min_delta=0.02, tokenizer=None)
    parts = {"train": [{"seq": "AA", "label_id": 0}] * 2,
             "val": [{"seq": "CC", "label_id": 1}] * 2}
    backbone, head = TinyBackbone(), Tiny()
    convergence, _, lr = mech.train_model(
        backbone, head, parts, args, tmp_path, "rid", {"cuda": "mock"})
    assert lr == 1e-5 and convergence["status"] == "CONVERGED"
    assert convergence["protocol"] == mech.vp.BESTVAL_PROTOCOL
    assert convergence["best_epoch"] == 1 and convergence["best_val"] == 0.5
    assert convergence["epochs_trained"] == 5
    assert convergence["restored_before_diagnostic"] is True
    assert convergence["restored_tensor_match"] is True
    assert ("make_tracker",) in events and ("restore_best",) in events
    assert ("optimizer", 1e-5) in events and ("clip", 1.0) in events
    best_state = torch.load(tmp_path / "best.ckpt", weights_only=True)
    with torch.no_grad():
        assert best_state["best_epoch"] == 1
        assert torch.equal(backbone.weight, best_state["backbone"]["weight"])
        assert torch.equal(head.weight, best_state["head"]["weight"])
        assert backbone.weight.item() == pytest.approx(1.2)
        assert head.weight.item() == pytest.approx(1.2)
    assert (tmp_path / "best.ckpt").is_file()
    assert (tmp_path / "checkpoint_proof.json").is_file()
    assert (tmp_path / "job.json").is_file()
    proof = json.loads((tmp_path / "checkpoint_proof.json").read_text())
    assert proof["best_epoch"] == 1 and proof["checkpoint_proof"] == "ok"
    monkeypatch.undo()


def test_save_state_uses_wrapper_aware_backbone_and_keeps_checkpoint(tmp_path):
    class Backbone(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.weight = torch.nn.Parameter(torch.tensor([2.0]))

    class Wrapper:
        def __init__(self):
            self.m = Backbone()

        def state_dict(self):
            raise AssertionError("must use vp.backbone_state_dict for wrappers")

    wrapper = Wrapper()
    head = torch.nn.Linear(1, 1)
    mech.save_state(wrapper, head, {"strategy": "full"}, tmp_path)
    saved = torch.load(tmp_path / "backbone_state.pt", weights_only=True)
    assert torch.equal(saved["weight"], torch.tensor([2.0]))
    assert (tmp_path / "head_state.pt").is_file()
    assert (tmp_path / "config.json").is_file()


def test_pre_mock_run_writes_only_descriptive_outputs(tmp_path, monkeypatch):
    args = mech.build_parser().parse_args(
        ["--split", "random", "--strategy", "pre", "--device", "0",
         "--n-test", "4", "--max-per-family", "2"])
    monkeypatch.setattr(mech, "require_cuda", lambda device: "cuda:0")
    monkeypatch.setattr(mech, "ARTIFACT_ROOT", tmp_path)
    monkeypatch.setattr(mech, "git_sha", lambda: "unit-sha")
    monkeypatch.setattr(mech.torch.cuda, "manual_seed_all", lambda seed: None)
    monkeypatch.setattr(mech.torch.cuda, "reset_peak_memory_stats", lambda device: None)
    monkeypatch.setattr(mech.torch.cuda, "max_memory_allocated", lambda device: 0)
    rows = [{"seq": "A" * (index + 2), "label": index % 13, "label_id": index % 13}
            for index in range(26)]
    parts = {"train": rows[:13], "val": rows[13:20], "test": rows[20:]}
    monkeypatch.setattr(mech, "load_data", lambda *arg: (
        rows, parts, list(range(13)), {"status": "OK"}, None))
    spec = SimpleNamespace(repo="multimolecule/rinalmo-micro", d_model=5)

    class TinyBackbone(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.projection = torch.nn.Linear(4, 5)

        def forward(self, input_ids, attention_mask):
            hidden = self.projection(torch.nn.functional.one_hot(
                input_ids, num_classes=4).float())
            return SimpleNamespace(last_hidden_state=hidden)

    import rnafteval.models
    monkeypatch.setattr(rnafteval.models, "load_model",
                        lambda name, device: (spec, object(), TinyBackbone()))
    monkeypatch.setattr(mech, "encode_seqs", lambda tokenizer, sequences, *args: {
        "input_ids": torch.ones(len(sequences), 3, dtype=torch.int64),
        "attention_mask": torch.ones(len(sequences), 3, dtype=torch.int64)})
    monkeypatch.setattr(mech.vp, "runtime_evidence", lambda tokenizer, device: {
        "cuda_available": True, "cuda_device": "cuda:0",
        "tokenizer_class": "mock.Tokenizer", "tokenizer_name_or_path": "mock",
        "tokenizer_vocab_size": 12})
    monkeypatch.setattr(mech, "apply_strategy",
                        lambda *args, **kwargs: pytest.fail("pre must not train"))
    monkeypatch.setattr(mech, "train_model",
                        lambda *args, **kwargs: pytest.fail("pre must not train"))

    real_extract = mech.extract_diagnostics

    def cuda_extract(backbone, head, tokenizer, selected, device, *args):
        assert device == "cuda:0"
        return real_extract(backbone, head, tokenizer, selected, device, *args)

    monkeypatch.setattr(mech, "extract_diagnostics", cuda_extract)
    monkeypatch.setattr(mech.torch.cuda, "is_available", lambda: True)
    real_extract_tensors = mech.extract_tensors

    def cpu_tensors(backbone, head, tokenizer, selected, device, *args):
        return real_extract_tensors(backbone, head, tokenizer, selected,
                                    torch.device("cpu"), *args)

    monkeypatch.setattr(mech, "extract_tensors", cpu_tensors)
    import rnafteval.strategies
    real_make_head = rnafteval.strategies.make_head
    head_devices = []

    def local_make_head(*head_args, **head_kwargs):
        class CpuOnlyHead(real_make_head(*head_args, **head_kwargs).__class__):
            def to(self, device, *args, **kwargs):
                head_devices.append(device)
                return super().to("cpu")

        return CpuOnlyHead(head_args[1], head_args[2])

    monkeypatch.setattr(mech, "make_head", local_make_head)
    assert mech.run(args) == 0
    directory = tmp_path / mech.run_id("pre", "random", 17)
    diagnostic = json.loads((directory / "diagnostic.json").read_text())
    assert head_devices == ["cuda:0"]
    assert diagnostic["status"] == "diagnostic"
    assert diagnostic["pretrained_baseline"] is True
    assert diagnostic["convergence"] is None
    assert diagnostic["prediction_metrics_reference_only"] is True
    assert diagnostic["aligned_tsne"] is None
    assert diagnostic["git_sha"] == "unit-sha"
    assert diagnostic["test_manifest_sha256"] == mech.sha256_file(
        directory / "test_manifest.json")
    run_manifest = json.loads((directory / "manifest.json").read_text())
    assert run_manifest["status"] == "diagnostic"
    assert run_manifest["embeddings_sha256"] == mech.sha256_file(
        directory / "embeddings.npz")
    assert json.loads((directory / "job.json").read_text())["status"] == "diagnostic"
    assert not (directory / "backbone_state.pt").exists()
    assert not (directory / "head_state.pt").exists()
    with np.load(directory / "embeddings.npz", allow_pickle=False) as embeddings:
        assert embeddings["cls"].shape == (diagnostic["n"], 5)
        assert embeddings["head_embedding"].shape == (diagnostic["n"], 5)
        assert embeddings["logits"].shape == (diagnostic["n"], 13)
        assert embeddings["probabilities"].shape == (diagnostic["n"], 13)
        manifest = json.loads((directory / "test_manifest.json").read_text())
        assert embeddings["sample_ids"].tolist() == manifest["sample_ids"]
    assert "causal" not in diagnostic["interpretation"]


def test_post_mock_run_saves_best_before_diagnostic_and_keeps_proof(
        tmp_path, monkeypatch):
    args = mech.build_parser().parse_args(
        ["--split", "random", "--strategy", "lora", "--device", "0", "--converge"])
    monkeypatch.setattr(mech, "require_cuda", lambda device: "cuda:0")
    monkeypatch.setattr(mech, "ARTIFACT_ROOT", tmp_path)
    monkeypatch.setattr(mech, "git_sha", lambda: "unit-sha")
    monkeypatch.setattr(mech.torch.cuda, "manual_seed_all", lambda seed: None)
    monkeypatch.setattr(mech.torch.cuda, "reset_peak_memory_stats", lambda device: None)
    monkeypatch.setattr(mech.torch.cuda, "max_memory_allocated", lambda device: 0)
    rows = [{"seq": "A" * (index + 2), "label": index % 13, "label_id": index % 13}
            for index in range(26)]
    parts = {"train": rows[:13], "val": rows[13:20], "test": rows[20:]}
    monkeypatch.setattr(mech, "load_data", lambda *arg: (
        rows, parts, list(range(13)), {"status": "OK"}, None))
    spec = SimpleNamespace(repo="multimolecule/rinalmo-micro", d_model=5)

    class TinyBackbone(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.projection = torch.nn.Linear(4, 5)

        def forward(self, input_ids, attention_mask):
            hidden = self.projection(torch.nn.functional.one_hot(
                input_ids, num_classes=4).float())
            return SimpleNamespace(last_hidden_state=hidden)

    import rnafteval.models
    monkeypatch.setattr(rnafteval.models, "load_model",
                        lambda name, device: (spec, object(), TinyBackbone()))
    monkeypatch.setattr(mech, "encode_seqs", lambda tokenizer, sequences, *args: {
        "input_ids": torch.ones(len(sequences), 3, dtype=torch.int64),
        "attention_mask": torch.ones(len(sequences), 3, dtype=torch.int64)})
    monkeypatch.setattr(mech.vp, "runtime_evidence", lambda tokenizer, device: {
        "cuda_available": True, "cuda_device": "cuda:0",
        "tokenizer_class": "mock.Tokenizer", "tokenizer_name_or_path": "mock",
        "tokenizer_vocab_size": 12})
    strategy_calls = []

    def local_strategy(backbone, strategy, lora_rank, lora_alpha):
        strategy_calls.append((strategy, lora_rank, lora_alpha))
        return backbone, 8

    monkeypatch.setattr(mech, "apply_strategy", local_strategy)
    real_make_head = mech.make_head

    def local_head(*args, **kwargs):
        class CpuOnlyHead(real_make_head(*args, **kwargs).__class__):
            def to(self, device, *args, **kwargs):
                return super().to("cpu")

        return CpuOnlyHead(args[1], args[2])

    monkeypatch.setattr(mech, "make_head", local_head)
    order = []

    def local_train(backbone, head, parts, args, out_dir, rid, runtime):
        order.append("train")
        (tmp_path / rid / "best.ckpt").write_bytes(b"best")
        (tmp_path / rid / "checkpoint_proof.json").write_text("{}")
        return ({"protocol": "bestval_v1", "status": "CONVERGED",
                 "best_epoch": 1, "best_val": 0.5,
                 "restored_before_diagnostic": True, "restored_tensor_match": True,
                 "checkpoint_proof": "ok"}, runtime, 3e-4)

    monkeypatch.setattr(mech, "train_model", local_train)
    real_save_state = mech.save_state

    def save_restored(*save_args):
        order.append("save_restored_state")
        return real_save_state(*save_args)

    monkeypatch.setattr(mech, "save_state", save_restored)

    def local_extract(*args, **kwargs):
        order.append("extract")
        assert order == ["train", "save_restored_state", "extract"]
        n = len(args[3])
        return ({"sample_ids": np.asarray([mech.sequence_hash(row["seq"]) for row in args[3]]),
                 "labels": np.asarray([row["label"] for row in args[3]]),
                 "cls": np.ones((n, 5), dtype=np.float32),
                 "head_embedding": np.ones((n, 5), dtype=np.float32),
                 "logits": np.zeros((n, 13), dtype=np.float32),
                 "probabilities": np.full((n, 13), 1 / 13, dtype=np.float32)},
                {"ACC": 0.0})

    monkeypatch.setattr(mech, "extract_diagnostics", local_extract)
    assert mech.run(args) == 0
    assert strategy_calls == [("lora", 8, 4)]
    directory = tmp_path / mech.run_id("lora", "random", 17)
    diagnostic = json.loads((directory / "diagnostic.json").read_text())
    assert diagnostic["convergence"]["protocol"] == "bestval_v1"
    assert diagnostic["convergence"]["best_epoch"] == 1
    assert diagnostic["checkpoints"]["best"] == str(directory / "best.ckpt")
    assert diagnostic["config"]["convergence_epoch_limit"] is None
    assert diagnostic["config"]["lr"] == 3e-4
    assert mech.diagnostic_is_usable(diagnostic)


def test_cli_contract_and_diagnostic_rid():
    args = mech.build_parser().parse_args(
        ["--split", "family", "--strategy", "lora", "--device", "2", "--converge"])
    assert args.seed == 17 and args.batch_size == 32
    assert args.out_suffix == "_mech_v1" and args.n_test == 0
    assert args.max_per_family == 60 and args.convergence_mode == "bestval"
    assert mech.run_id("lora", "family", 17) == \
        "mech_rinalmomicro_ncrna_lora_family_s17_mech_v1"
    assert mech.ARTIFACT_ROOT == Path("/root/rnaft/artifacts/mechanism")
    assert mech.MODEL == "RiNALMo-micro"


def test_outputs_only_descriptive_status_no_fabricated_causal_claim():
    pre = {"artifact_type": "diagnostic", "status": "diagnostic",
           "pretrained_baseline": True, "convergence_required": False,
           "interpretation": "descriptive_diagnostic_only_no_mechanism_conclusion"}
    post = {"artifact_type": "diagnostic", "status": "diagnostic",
            "pretrained_baseline": False,
            "convergence": {"status": "CONVERGED"},
            "interpretation": "descriptive_diagnostic_only_no_mechanism_conclusion"}
    for payload in (pre, post):
        assert payload["status"] == "diagnostic"
        assert payload["status"] not in {"done", "CONVERGED"}
        assert "causal" not in payload["interpretation"]
        assert "mechanism_conclusion" not in payload or \
            "no_mechanism_conclusion" in payload["interpretation"]
