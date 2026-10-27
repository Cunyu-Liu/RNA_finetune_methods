import csv
import json
from pathlib import Path
import sys

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import plot_mechanism_regbase as plotter


def source_run_id(task, state, split="random", seed=17):
    extra = ("_b20fix_bestval_v1" if state == "lora" else
             "_b20fix_lr1e-05_bestval_v1")
    return "ft_rinalmomicro_%s_%s_s%d_%s%s" % (
        task, state, seed, split, extra)


def aligned_arrays(task="degradation", split="random", seed=17):
    states = np.repeat(["pre", "lora", "full"], 4)
    y_true = np.tile([0.125, -0.5, 1.75, 0.333], 3)
    prediction = y_true + np.repeat([0.2, -0.1, 0.05], 4)
    return {
        "tsne": np.arange(24, dtype=np.float64).reshape(12, 2),
        "token_embedding": np.arange(36, dtype=np.float32).reshape(12, 3),
        "token_ids": np.tile(["a:0000", "a:0001", "b:0000", "b:0001"], 3),
        "sequence_ids": np.tile(["a", "a", "b", "b"], 3),
        "base_positions": np.tile([0, 1, 0, 1], 3).astype(np.int64),
        "token_positions": np.tile([1, 2, 1, 2], 3).astype(np.int64),
        "state": states,
        "y_true": y_true,
        "prediction": prediction,
        "residual": prediction - y_true,
        "task": np.asarray(task),
        "split": np.asarray(split),
        "seed": np.asarray(seed, dtype=np.int64),
        "n_full_tokens": np.asarray(8, dtype=np.int64),
        "n_sample_tokens": np.asarray(4, dtype=np.int64),
        "full_test_sha256": np.asarray("full-test-hash"),
        "test_manifest_sha256": np.asarray("manifest-hash"),
        "source_run_ids": np.asarray([
            plotter.PRE_SOURCE,
            source_run_id(task, "lora", split, seed),
            source_run_id(task, "full", split, seed),
        ]),
        "full_pcc": np.asarray([0.01, 0.81, 0.79]),
        "full_mcrmse": np.asarray([0.9, 0.2, 0.25]),
        "color_mode": np.asarray("y_true_continuous"),
        "tsne_perplexity": np.asarray(3),
        "tsne_random_state": np.asarray(17),
    }


def write_aligned(path, **kwargs):
    arrays = aligned_arrays(**kwargs)
    np.savez(path, **arrays)
    return arrays


def rewrite(path, arrays):
    np.savez(path, **arrays)


@pytest.mark.parametrize("task,target", [
    ("degradation", "deg_Mg_pH10"),
    ("ssi", "struct_true"),
])
def test_load_projection_preserves_continuous_regression_and_task_target(
        tmp_path, task, target):
    path = tmp_path / (task + ".npz")
    write_aligned(path, task=task)
    projection = plotter.load_projection(path, task=task)
    assert projection["task"] == task
    assert projection["target"] == target
    assert projection["n"] == 4
    assert projection["n_full_tokens"] == 8
    assert projection["n_sample_tokens"] == 4
    assert np.unique(projection["y_true"]).size == 4
    assert not np.issubdtype(projection["y_true"].dtype, np.integer)
    assert np.allclose(projection["residual"],
                       projection["prediction"] - projection["y_true"])
    assert projection["full_pcc"].shape == (3,)
    assert projection["full_mcrmse"].shape == (3,)
    with pytest.raises(ValueError, match="task"):
        plotter.load_projection(
            path, task="ssi" if task == "degradation" else "degradation")


def test_plot_exports_coordinates_metrics_hashes_and_source_proof(tmp_path):
    path = tmp_path / "aligned.npz"
    write_aligned(path)
    projection = plotter.load_projection(path)
    metadata = plotter.plot_projection(projection, tmp_path / "regbase")
    for suffix in (".png", ".pdf", "_coordinates.csv", "_metadata.json"):
        assert (tmp_path / ("regbase" + suffix)).is_file()
    assert metadata["target"] == "deg_Mg_pH10"
    assert metadata["continuous_unbinned"] is True
    assert metadata["color_mode"] == "y_true_continuous"
    assert metadata["classification_silhouette"] is None
    assert metadata["pre_reference_head_seed"] == 201
    assert metadata["metric_scope"] == "full_test_only_not_CLS_or_sampled_tokens"
    assert "per_base_tokens" in metadata["label_scope"]
    assert metadata["source_proof"]["pre"].endswith(plotter.PRE_SOURCE)
    assert metadata["source_proof"]["full"].endswith(
        source_run_id("degradation", "full"))
    assert plotter.plt.rcParams["savefig.dpi"] == 300
    assert plotter.plt.rcParams["pdf.fonttype"] == 42

    with open(tmp_path / "regbase_coordinates.csv", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        assert "base_position" in reader.fieldnames
        assert "token_position" in reader.fieldnames
        assert "class" not in reader.fieldnames
        assert "label" not in reader.fieldnames
    assert len(rows) == 12
    assert rows[0]["target"] == "deg_Mg_pH10"
    assert rows[0]["base_position"] == "0"
    assert rows[0]["token_position"] == "1"
    assert float(rows[0]["y_true"]) == pytest.approx(0.125)
    assert float(rows[0]["residual"]) == pytest.approx(0.2)
    assert rows[0]["source_run_id"] == plotter.PRE_SOURCE
    assert rows[0]["full_test_sha256"] == "full-test-hash"
    assert rows[0]["test_manifest_sha256"] == "manifest-hash"
    assert rows[0]["n_full_tokens"] == "8"
    assert rows[0]["n_sample_tokens"] == "4"
    assert rows[5]["state"] == "lora"
    assert float(rows[5]["full_pcc"]) == pytest.approx(0.81)
    assert float(rows[5]["full_mcrmse"]) == pytest.approx(0.2)
    assert rows[5]["metric_scope"] == plotter.METRIC_SCOPE
    saved = json.loads((tmp_path / "regbase_metadata.json").read_text())
    assert saved["full_pcc"]["lora"] == pytest.approx(0.81)
    assert saved["full_mcrmse"]["full"] == pytest.approx(0.25)
    assert saved["source_run_ids"] == metadata["source_run_ids"]


def test_three_panels_share_color_axis_and_pre_hides_random_head_metrics(
        tmp_path, monkeypatch):
    path = tmp_path / "aligned.npz"
    write_aligned(path)
    projection = plotter.load_projection(path)
    captured = {}
    real_savefig = plotter.plt.Figure.savefig

    def capture(figure, *args, **kwargs):
        if str(args[0]).endswith(".png"):
            captured["figure"] = figure
        return real_savefig(figure, *args, **kwargs)

    monkeypatch.setattr(plotter.plt.Figure, "savefig", capture)
    metadata = plotter.plot_projection(projection, tmp_path / "regbase")
    figure = captured["figure"]
    axes = figure.axes[:3]
    limits = [axis.collections[0].get_clim() for axis in axes]
    assert limits == [tuple(metadata["color_limits"])] * 3
    assert limits[0] == pytest.approx((-0.5, 1.75))
    assert "PCC" not in axes[0].get_title()
    assert "MCRMSE" not in axes[0].get_title()
    assert "0.010" not in axes[0].get_title()
    assert "full-test PCC=0.810 | MCRMSE=0.200" in axes[1].get_title()
    assert "full-test PCC=0.790 | MCRMSE=0.250" in axes[2].get_title()
    assert figure.axes[-1].get_ylabel() == "deg_Mg_pH10"
    figure_text = "\n".join(text.get_text() for text in figure.texts)
    assert "metrics only on full test; not CLS or sampled tokens" in figure_text
    assert "no classification silhouette" in figure_text


@pytest.mark.parametrize("field", [
    "token_ids", "sequence_ids", "base_positions", "token_positions", "y_true",
])
def test_cross_state_token_position_and_continuous_label_mismatch_is_rejected(
        tmp_path, field):
    path = tmp_path / (field + ".npz")
    arrays = write_aligned(path)
    if field == "token_ids":
        arrays[field][4] = "wrong"
    elif field == "sequence_ids":
        arrays[field][4] = "wrong"
    elif field == "base_positions":
        arrays[field][4] = 3
    elif field == "token_positions":
        arrays[field][4] += 1
    else:
        arrays[field][4] += 0.25
        arrays["residual"][4] = arrays["prediction"][4] - arrays["y_true"][4]
    rewrite(path, arrays)
    with pytest.raises(ValueError):
        plotter.load_projection(path)


@pytest.mark.parametrize("field,values", [
    ("task", ["degradation", "degradation", "ssi"]),
    ("split", ["random", "random", "family"]),
    ("seed", [17, 17, 29]),
    ("full_test_sha256", ["same", "same", "different"]),
    ("test_manifest_sha256", ["same", "same", "different"]),
])
def test_cross_state_task_identity_and_hash_mismatch_is_rejected(
        tmp_path, field, values):
    path = tmp_path / (field + ".npz")
    arrays = write_aligned(path)
    arrays[field] = np.asarray(values)
    rewrite(path, arrays)
    with pytest.raises(ValueError, match=field):
        plotter.load_projection(path)


@pytest.mark.parametrize("field", [
    "tsne", "token_embedding", "y_true", "prediction", "residual",
    "full_pcc", "full_mcrmse",
])
def test_nonfinite_coordinates_embeddings_values_and_metrics_are_rejected(
        tmp_path, field):
    path = tmp_path / (field + ".npz")
    arrays = write_aligned(path)
    arrays[field] = arrays[field].astype(np.float64).copy()
    arrays[field].flat[0] = np.nan
    rewrite(path, arrays)
    with pytest.raises(ValueError):
        plotter.load_projection(path)


def test_residual_metric_shape_color_mode_and_source_identity_are_validated(tmp_path):
    path = tmp_path / "aligned.npz"
    arrays = write_aligned(path)
    arrays["residual"][0] += 1
    rewrite(path, arrays)
    with pytest.raises(ValueError, match="residual"):
        plotter.load_projection(path)

    arrays = aligned_arrays()
    arrays["full_pcc"] = np.asarray([0.1, 0.2])
    rewrite(path, arrays)
    with pytest.raises(ValueError, match="full_pcc"):
        plotter.load_projection(path)

    arrays = aligned_arrays()
    arrays["color_mode"] = np.asarray("binned_class")
    rewrite(path, arrays)
    with pytest.raises(ValueError, match="continuous unbinned"):
        plotter.load_projection(path)

    for index in (0, 1, 2):
        arrays = aligned_arrays()
        arrays["source_run_ids"][index] = "wrong-source"
        rewrite(path, arrays)
        with pytest.raises(ValueError, match="source_run_ids"):
            plotter.load_projection(path)


def test_full_sample_boundary_allows_full_cap_but_rejects_inconsistent_counts(tmp_path):
    path = tmp_path / "aligned.npz"
    arrays = write_aligned(path)
    arrays["n_full_tokens"] = np.asarray(4)
    rewrite(path, arrays)
    assert plotter.load_projection(path)["n_full_tokens"] == 4

    arrays["n_full_tokens"] = np.asarray(3)
    rewrite(path, arrays)
    with pytest.raises(ValueError, match="full-test"):
        plotter.load_projection(path)

    arrays = aligned_arrays()
    arrays["n_sample_tokens"] = np.asarray(3)
    rewrite(path, arrays)
    with pytest.raises(ValueError, match="n_sample_tokens"):
        plotter.load_projection(path)
