import csv
import json
from pathlib import Path
import sys

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import plot_mechanism_modification as plotter


def write_aligned(path, color_mode="m6a_label_index_7"):
    states = np.repeat(["pre", "lora", "full"], 4)
    ids = np.tile(["a", "b", "c", "d"], 3)
    labels = np.zeros((12, 12), dtype=np.float32)
    labels[:, 7] = np.tile([0, 1, 0, 1], 3)
    logits = np.linspace(-2, 2, 144).reshape(12, 12).astype(np.float32)
    probabilities = 1 / (1 + np.exp(-logits))
    np.savez(
        path,
        tsne_cls=np.arange(24).reshape(12, 2),
        tsne_head=np.arange(24).reshape(12, 2) + 10,
        sample_ids=ids,
        state=states,
        labels=labels,
        m6a_label=labels[:, 7].astype(int),
        probabilities=probabilities,
        logits=logits,
        full_m6a_auc=np.asarray([0.5, 0.98, 0.97]),
        full_mean_auc=np.asarray([0.5, 0.93, 0.68]),
        source_run_ids=np.asarray(["pre_source", "lora_source", "full_source"]),
        color_mode=np.asarray(color_mode),
        split=np.asarray("random"),
        seed=np.asarray(17),
        test_manifest_sha256=np.asarray("manifest"),
        tsne_perplexity=np.asarray(3),
        tsne_random_state=np.asarray(17),
    )


def test_load_projection_validates_m6a_and_independent_sigmoid(tmp_path):
    path = tmp_path / "aligned.npz"
    write_aligned(path)
    projection = plotter.load_projection(path, "cls")
    assert projection["n"] == 4
    assert projection["labels"].shape == (12, 12)
    assert projection["m6a_label"].sum() == 6
    assert projection["source_run_ids"].tolist() == [
        "pre_source", "lora_source", "full_source"]


def test_plot_exports_all_labels_probabilities_and_support(tmp_path):
    path = tmp_path / "aligned.npz"
    write_aligned(path)
    projection = plotter.load_projection(path, "head")
    metadata = plotter.plot_projection(projection, tmp_path / "mod_head", "head")
    assert metadata["classification_silhouette"] is None
    assert metadata["m6a_support"]["lora"] == {"positive": 2, "negative": 2}
    for suffix in (".png", ".pdf", "_coordinates.csv", "_metadata.json"):
        assert (tmp_path / ("mod_head" + suffix)).is_file()
    with open(tmp_path / "mod_head_coordinates.csv") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 12
    assert len(json.loads(rows[0]["labels_json"])) == 12
    assert len(json.loads(rows[0]["probabilities_json"])) == 12
    assert len(json.loads(rows[0]["logits_json"])) == 12
    assert rows[0]["source_run_id"] == "pre_source"
    assert rows[-1]["source_run_id"] == "full_source"
    saved = json.loads((tmp_path / "mod_head_metadata.json").read_text())
    assert saved["full_m6a_auc"]["lora"] == pytest.approx(0.98)


def test_plot_rejects_wrong_m6a_or_softmax_probabilities(tmp_path):
    path = tmp_path / "aligned.npz"
    write_aligned(path)
    with np.load(path) as data:
        arrays = {key: data[key] for key in data.files}
    arrays["m6a_label"] = 1 - arrays["m6a_label"]
    np.savez(path, **arrays)
    with pytest.raises(ValueError, match="m6a_label"):
        plotter.load_projection(path, "cls")
    path = tmp_path / "aligned_valid.npz"
    write_aligned(path)
    with np.load(path) as data:
        arrays = {key: data[key] for key in data.files}
    arrays["probabilities"] = np.full_like(arrays["probabilities"], 0.5)
    np.savez(path, **arrays)
    with pytest.raises(ValueError, match="sigmoid"):
        plotter.load_projection(path, "cls")
    path = tmp_path / "aligned_color.npz"
    write_aligned(path, color_mode="categorical")
    with pytest.raises(ValueError, match="m6A index 7"):
        plotter.load_projection(path, "cls")
