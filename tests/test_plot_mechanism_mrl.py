import csv
import json
from pathlib import Path
import sys

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import plot_mechanism_mrl as plotter


def write_aligned(path, color_mode="true_mrl_continuous"):
    states = np.repeat(["pre", "lora", "full"], 4)
    ids = np.tile(["a", "b", "c", "d"], 3)
    y = np.tile([0.1, 0.2, 0.3, 0.4], 3)
    prediction = y + np.repeat([0.0, 0.1, -0.1], 4)
    np.savez(
        path,
        tsne_cls=np.arange(24).reshape(12, 2),
        tsne_head=np.arange(24).reshape(12, 2) + 10,
        sample_ids=ids,
        state=states,
        y_true=y,
        prediction=prediction,
        residual=prediction - y,
        full_pearson=np.asarray([0.01, 0.81, 0.79]),
        source_run_ids=np.asarray(["pre_source", "lora_source", "full_source"]),
        color_mode=np.asarray(color_mode),
        split=np.asarray("random"),
        seed=np.asarray(17),
        test_manifest_sha256=np.asarray("manifest"),
        tsne_perplexity=np.asarray(3),
        tsne_random_state=np.asarray(17),
    )


def test_load_projection_preserves_continuous_values_and_source_ids(tmp_path):
    path = tmp_path / "aligned.npz"
    write_aligned(path)
    projection = plotter.load_projection(path, "cls")
    assert projection["n"] == 4
    assert projection["coordinates"].shape == (12, 2)
    assert projection["source_run_ids"].tolist() == [
        "pre_source", "lora_source", "full_source"]
    assert np.allclose(projection["residual"],
                       projection["prediction"] - projection["y_true"])


def test_plot_exports_every_point_without_classification_silhouette(tmp_path):
    path = tmp_path / "aligned.npz"
    write_aligned(path)
    projection = plotter.load_projection(path, "head")
    metadata = plotter.plot_projection(projection, tmp_path / "mrl_head", "head")
    assert metadata["classification_silhouette"] is None
    assert metadata["color_mode"] == "true_mrl_continuous"
    assert metadata["source_run_ids"]["lora"] == "lora_source"
    for suffix in (".png", ".pdf", "_coordinates.csv", "_metadata.json"):
        assert (tmp_path / ("mrl_head" + suffix)).is_file()
    with open(tmp_path / "mrl_head_coordinates.csv") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 12
    assert rows[0]["source_run_id"] == "pre_source"
    assert rows[-1]["source_run_id"] == "full_source"
    assert float(rows[-1]["residual"]) == pytest.approx(-0.1)
    saved = json.loads((tmp_path / "mrl_head_metadata.json").read_text())
    assert saved["full_test_pearson"]["lora"] == pytest.approx(0.81)


def test_plot_rejects_wrong_color_mode_and_invalid_residual(tmp_path):
    path = tmp_path / "aligned.npz"
    write_aligned(path, color_mode="categorical")
    with pytest.raises(ValueError, match="continuous"):
        plotter.load_projection(path, "cls")
    path = tmp_path / "aligned_valid.npz"
    write_aligned(path)
    with np.load(path) as data:
        arrays = {key: data[key] for key in data.files}
    arrays["residual"] = arrays["residual"] + 1
    np.savez(path, **arrays)
    with pytest.raises(ValueError, match="residual"):
        plotter.load_projection(path, "cls")
