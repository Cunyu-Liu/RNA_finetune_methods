import csv
import json
from pathlib import Path
import sys

import numpy as np
import pytest
from scipy.special import expit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import plot_mechanism_ssp as plotter


FULL_HASH = "a" * 64
MANIFEST_HASH = "b" * 64
SAMPLING = "pair_id_lexicographic_per_class_cap_2_before_prediction"


def source_run_id(state, split="random", seed=17):
    extra = ("_pairalign_bestval_v1" if state == "lora" else
             "_lr1e-05_pairalign_bestval_v1")
    return "ft_rinalmomicro_secondarystructure_%s_s%d_%s%s" % (
        state, seed, split, extra)


def aligned_arrays(split="random", seed=17):
    states = np.repeat(["pre", "lora", "full"], 4)
    logits = np.tile(np.asarray([-2.0, 0.2, 1.0, 3.0]), 3) + np.repeat(
        [0.0, 0.5, 1.0], 4)
    return {
        "tsne": np.arange(24, dtype=np.float64).reshape(12, 2),
        "head_input": np.arange(48, dtype=np.float32).reshape(12, 4),
        "pair_ids": np.tile([
            "a:0000:0001", "a:0000:0002", "a:0001:0002", "b:0000:0001"], 3),
        "sequence_ids": np.tile(["a", "a", "a", "b"], 3),
        "base_i": np.tile([0, 0, 1, 0], 3).astype(np.int64),
        "base_j": np.tile([1, 2, 2, 1], 3).astype(np.int64),
        "token_i": np.tile([1, 1, 2, 1], 3).astype(np.int64),
        "token_j": np.tile([2, 3, 3, 2], 3).astype(np.int64),
        "state": states,
        "labels": np.tile([0, 1, 0, 1], 3).astype(np.int64),
        "logits": logits,
        "probabilities": expit(logits),
        "task": np.asarray("secondary-structure"),
        "split": np.asarray(split),
        "seed": np.asarray(seed, dtype=np.int64),
        "max_len": np.asarray(192, dtype=np.int64),
        "pair_alignment": np.asarray(plotter.PAIR_ALIGNMENT),
        "full_test_sha256": np.asarray(FULL_HASH),
        "test_manifest_sha256": np.asarray(MANIFEST_HASH),
        "sampling": np.asarray(SAMPLING),
        "metric_scope": np.asarray(plotter.METRIC_SCOPE),
        "full_class_support": np.asarray('{"0":20,"1":4}'),
        "source_run_ids": np.asarray([
            plotter.PRE_SOURCE, source_run_id("lora", split, seed),
            source_run_id("full", split, seed)]),
        "full_f1": np.asarray([0.01, 0.81, 0.79]),
        "full_precision": np.asarray([0.02, 0.82, 0.78]),
        "full_recall": np.asarray([0.03, 0.80, 0.80]),
        "full_threshold": np.asarray([0.3, 0.4, 0.5]),
        "full_val_f1": np.asarray([0.04, 0.77, 0.76]),
        "color_mode": np.asarray("ssp_pair_gold_label"),
        "tsne_perplexity": np.asarray(3),
        "tsne_random_state": np.asarray(17),
    }


def write_aligned(path, **kwargs):
    arrays = aligned_arrays(**kwargs)
    np.savez(path, **arrays)
    return arrays


def rewrite(path, arrays):
    np.savez(path, **arrays)


@pytest.mark.parametrize("split", ["random", "family"])
def test_load_projection_validates_identity_sigmoid_support_and_sources(
        tmp_path, split):
    path = tmp_path / (split + ".npz")
    write_aligned(path, split=split)
    projection = plotter.load_projection(path)
    assert projection["task"] == "secondary-structure"
    assert projection["split"] == split
    assert projection["n"] == 4
    assert projection["max_len"] == 192
    assert projection["full_class_support"] == {"0": 20, "1": 4}
    assert projection["sample_class_support"] == {"0": 2, "1": 2}
    assert projection["source_run_ids"].tolist() == [
        plotter.PRE_SOURCE, source_run_id("lora", split),
        source_run_id("full", split)]
    assert np.allclose(projection["probabilities"], expit(projection["logits"]))
    for key in ("full_f1", "full_precision", "full_recall",
                "full_threshold", "full_val_f1"):
        assert projection[key].shape == (3,)
        assert np.isfinite(projection[key]).all()


def test_plot_exports_pair_positions_probabilities_full_metrics_and_metadata(tmp_path):
    path = tmp_path / "aligned.npz"
    write_aligned(path)
    projection = plotter.load_projection(path)
    metadata = plotter.plot_projection(projection, tmp_path / "ssp")
    for suffix in (".png", ".pdf", "_coordinates.csv", "_metadata.json"):
        assert (tmp_path / ("ssp" + suffix)).is_file()
    assert (tmp_path / "ssp.pdf").read_bytes().startswith(b"%PDF")
    assert metadata["classification_silhouette"] is None
    assert metadata["class_names"] == {"0": "unpaired", "1": "paired"}
    assert metadata["label_support"]["lora"] == {"unpaired": 2, "paired": 2}
    assert metadata["source_reconciliation_metrics"] == [
        "f1", "precision", "recall", "threshold", "val_f1"]
    assert metadata["pre_reference_head_seed"] == 201
    assert metadata["pre_non_zero_shot"] is True
    assert "not_zero_shot" in metadata["pre_prediction_head"]
    assert metadata["full_support"] == {
        "pairs": 24, "positive_pairs": 4, "negative_pairs": 20}
    assert metadata["sample_support"] == {
        "pairs": 4, "positive_pairs": 2, "negative_pairs": 2}
    assert metadata["n_per_state"] == metadata["n_sample_pairs"] == 4
    assert metadata["n_full_pairs"] == 24
    assert plotter.plt.rcParams["savefig.dpi"] == 300
    assert plotter.plt.rcParams["pdf.fonttype"] == 42

    with open(tmp_path / "ssp_coordinates.csv", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        for field in ("base_i", "base_j", "token_i", "token_j", "label", "logit",
                      "probability", "full_f1", "full_precision", "full_recall",
                      "full_threshold", "full_val_f1", "source_run_id",
                      "full_test_sha256", "test_manifest_sha256"):
            assert field in reader.fieldnames
    assert len(rows) == 12
    assert rows[0]["pair_id"] == "a:0000:0001"
    assert rows[0]["base_i"] == "0" and rows[0]["base_j"] == "1"
    assert rows[0]["token_i"] == "1" and rows[0]["token_j"] == "2"
    assert rows[0]["class_name"] == "unpaired"
    assert float(rows[0]["probability"]) == pytest.approx(expit(-2.0))
    assert rows[0]["source_run_id"] == plotter.PRE_SOURCE
    assert rows[0]["full_test_sha256"] == FULL_HASH
    assert rows[0]["test_manifest_sha256"] == MANIFEST_HASH
    assert rows[5]["state"] == "lora" and rows[5]["class_name"] == "paired"
    assert float(rows[5]["full_f1"]) == pytest.approx(0.81)
    assert float(rows[5]["full_precision"]) == pytest.approx(0.82)
    assert float(rows[5]["full_recall"]) == pytest.approx(0.80)
    assert float(rows[5]["full_threshold"]) == pytest.approx(0.4)
    assert float(rows[5]["full_val_f1"]) == pytest.approx(0.77)
    assert rows[5]["n_full_pairs"] == "24" and rows[5]["n_sample_pairs"] == "4"
    saved = json.loads((tmp_path / "ssp_metadata.json").read_text())
    assert saved["full_f1"]["lora"] == pytest.approx(0.81)
    assert saved["full_threshold"]["full"] == pytest.approx(0.5)
    assert saved["source_run_ids"] == metadata["source_run_ids"]


def test_three_panels_hide_pre_reference_metrics_and_use_full_test_caption(
        tmp_path, monkeypatch):
    path = tmp_path / "aligned.npz"
    write_aligned(path)
    projection = plotter.load_projection(path)
    captured = {}
    save_calls = []
    real_savefig = plotter.plt.Figure.savefig

    def capture(figure, *args, **kwargs):
        save_calls.append((str(args[0]), kwargs))
        if str(args[0]).endswith(".png"):
            captured["figure"] = figure
        return real_savefig(figure, *args, **kwargs)

    monkeypatch.setattr(plotter.plt.Figure, "savefig", capture)
    plotter.plot_projection(projection, tmp_path / "ssp")
    axes = captured["figure"].axes[:3]
    assert len(axes) == 3
    assert "F1" not in axes[0].get_title()
    assert "0.010" not in axes[0].get_title()
    assert "full-test pair-F1=0.810" in axes[1].get_title()
    assert "full-test pair-F1=0.790" in axes[2].get_title()
    figure_text = "\n".join(text.get_text() for text in captured["figure"].texts)
    assert "Balanced pair view" in figure_text
    assert "metrics only on full reconstructed test" in figure_text
    assert "not CLS or sampled prevalence" in figure_text
    png_kwargs = next(kwargs for path, kwargs in save_calls if path.endswith(".png"))
    assert png_kwargs["dpi"] == 300


@pytest.mark.parametrize("field", [
    "pair_ids", "sequence_ids", "base_i", "base_j", "token_i", "token_j", "labels",
])
def test_cross_state_pair_identity_position_and_label_mismatch_is_rejected(
        tmp_path, field):
    path = tmp_path / (field + ".npz")
    arrays = write_aligned(path)
    if field in ("pair_ids", "sequence_ids"):
        arrays[field][4] = "wrong"
    elif field == "labels":
        arrays[field][4] = 1 - arrays[field][4]
    else:
        arrays[field][4] += 1
    rewrite(path, arrays)
    with pytest.raises(ValueError):
        plotter.load_projection(path)


@pytest.mark.parametrize("field,values", [
    ("task", ["secondary-structure", "secondary-structure", "mrl"]),
    ("split", ["random", "random", "family"]),
    ("seed", [17, 17, 29]),
    ("max_len", [192, 192, 128]),
    ("full_test_sha256", [FULL_HASH, FULL_HASH, "c" * 64]),
    ("test_manifest_sha256", [MANIFEST_HASH, MANIFEST_HASH, "d" * 64]),
    ("sampling", [SAMPLING, SAMPLING, "other_sampling"]),
])
def test_cross_state_task_identity_hash_and_sampling_mismatch_is_rejected(
        tmp_path, field, values):
    path = tmp_path / (field + ".npz")
    arrays = write_aligned(path)
    arrays[field] = np.asarray(values)
    rewrite(path, arrays)
    with pytest.raises(ValueError, match=field):
        plotter.load_projection(path)


def test_invalid_labels_pair_positions_and_pair_id_are_rejected(tmp_path):
    path = tmp_path / "aligned.npz"
    arrays = write_aligned(path)
    arrays["labels"] = arrays["labels"] + 1
    rewrite(path, arrays)
    with pytest.raises(ValueError, match="0=unpaired"):
        plotter.load_projection(path)

    arrays = aligned_arrays()
    arrays["labels"] = arrays["labels"].astype(np.float64)
    rewrite(path, arrays)
    with pytest.raises(ValueError, match="标签"):
        plotter.load_projection(path)

    arrays = aligned_arrays()
    arrays["base_i"][0] = arrays["base_j"][0]
    rewrite(path, arrays)
    with pytest.raises(ValueError, match="base_i < base_j"):
        plotter.load_projection(path)

    arrays = aligned_arrays()
    arrays["token_i"] = arrays["token_i"].astype(np.float64)
    rewrite(path, arrays)
    with pytest.raises(ValueError, match="token_i"):
        plotter.load_projection(path)

    arrays = aligned_arrays()
    arrays["pair_ids"][0] = "a:0000:0002"
    rewrite(path, arrays)
    with pytest.raises(ValueError, match="pair_id"):
        plotter.load_projection(path)


def test_probability_must_be_sigmoid_of_logit(tmp_path):
    path = tmp_path / "aligned.npz"
    arrays = write_aligned(path)
    arrays["probabilities"] = np.full(12, 0.5)
    rewrite(path, arrays)
    with pytest.raises(ValueError, match="sigmoid"):
        plotter.load_projection(path)


@pytest.mark.parametrize("field", [
    "tsne", "head_input", "logits", "probabilities", "full_f1",
    "full_precision", "full_recall", "full_threshold", "full_val_f1",
])
def test_nonfinite_coordinates_embeddings_probabilities_and_metrics_are_rejected(
        tmp_path, field):
    path = tmp_path / (field + ".npz")
    arrays = write_aligned(path)
    arrays[field] = arrays[field].astype(np.float64).copy()
    arrays[field].flat[0] = np.nan
    rewrite(path, arrays)
    with pytest.raises(ValueError):
        plotter.load_projection(path)


@pytest.mark.parametrize("field", [
    "full_f1", "full_precision", "full_recall", "full_threshold", "full_val_f1",
])
def test_full_metrics_must_be_length_three(tmp_path, field):
    path = tmp_path / (field + ".npz")
    arrays = write_aligned(path)
    arrays[field] = np.asarray([0.1, 0.2])
    rewrite(path, arrays)
    with pytest.raises(ValueError, match=field):
        plotter.load_projection(path)


def test_source_run_ids_are_checked_for_all_states(tmp_path):
    path = tmp_path / "aligned.npz"
    for index in range(3):
        arrays = aligned_arrays()
        arrays["source_run_ids"][index] = "wrong-source"
        rewrite(path, arrays)
        with pytest.raises(ValueError, match="source_run_ids"):
            plotter.load_projection(path)


def test_full_sample_support_boundary_allows_full_cap_and_rejects_class_shortfall(
        tmp_path):
    path = tmp_path / "aligned.npz"
    arrays = write_aligned(path)
    arrays["full_class_support"] = np.asarray('{"0":2,"1":2}')
    rewrite(path, arrays)
    projection = plotter.load_projection(path)
    assert projection["full_class_support"] == {"0": 2, "1": 2}

    arrays["full_class_support"] = np.asarray('{"0":1,"1":3}')
    rewrite(path, arrays)
    with pytest.raises(ValueError, match="class support"):
        plotter.load_projection(path)

    arrays["full_class_support"] = np.asarray('{"0":1,"1":1}')
    rewrite(path, arrays)
    with pytest.raises(ValueError, match="full-test pair"):
        plotter.load_projection(path)
