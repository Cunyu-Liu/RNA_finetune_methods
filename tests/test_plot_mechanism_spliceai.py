import csv
import json
from pathlib import Path
import sys

import numpy as np
import pytest
from scipy.special import softmax

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import plot_mechanism_spliceai as plotter


def write_aligned(path, color_mode="spliceai_token_class"):
    states = np.repeat(["pre", "lora", "full"], 4)
    token_ids = np.tile(["a:0000", "a:0001", "b:0000", "b:0001"], 3)
    sequence_ids = np.tile(["a", "a", "b", "b"], 3)
    positions = np.tile([0, 1, 0, 1], 3)
    labels = np.tile([0, 1, 2, 0], 3)
    logits = np.asarray([[2.0, 0.0, -1.0]] * 12)
    probabilities = softmax(logits, axis=-1)
    np.savez(
        path,
        tsne=np.arange(24).reshape(12, 2),
        token_ids=token_ids,
        sequence_ids=sequence_ids,
        positions=positions,
        state=states,
        labels=labels,
        probabilities=probabilities,
        logits=logits,
        full_macro_f1=np.asarray([0.3, 0.8, 0.7]),
        full_roc_auc=np.asarray([0.5, 0.9, 0.85]),
        source_run_ids=np.asarray(["pre_source", "lora_source", "full_source"]),
        color_mode=np.asarray(color_mode),
        sampling=np.asarray("per_class_cap_512_before_prediction"),
        split=np.asarray("random"),
        seed=np.asarray(17),
        test_manifest_sha256=np.asarray("manifest"),
        tsne_perplexity=np.asarray(3),
        tsne_random_state=np.asarray(17),
    )


def test_load_projection_validates_three_class_softmax(tmp_path):
    path = tmp_path / "aligned.npz"
    write_aligned(path)
    projection = plotter.load_projection(path)
    assert projection["n"] == 4
    assert projection["probabilities"].shape == (12, 3)
    assert projection["full_macro_f1"].tolist() == [0.3, 0.8, 0.7]
    assert projection["sampling"].startswith("per_class_cap_512")


def test_plot_exports_token_positions_and_support(tmp_path):
    path = tmp_path / "aligned.npz"
    write_aligned(path)
    projection = plotter.load_projection(path)
    metadata = plotter.plot_projection(projection, tmp_path / "spliceai")
    assert metadata["classification_silhouette"] is None
    assert metadata["label_support"]["lora"] == {
        "negative": 2, "donor": 1, "acceptor": 1}
    assert metadata["metric_scope"].endswith("full_test")
    for suffix in (".png", ".pdf", "_coordinates.csv", "_metadata.json"):
        assert (tmp_path / ("spliceai" + suffix)).is_file()
    with open(tmp_path / "spliceai_coordinates.csv") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 12
    assert rows[0]["representation"] == "per_base_token"
    assert rows[0]["token_id"] == "a:0000"
    assert rows[1]["class_name"] == "donor"
    assert len(json.loads(rows[0]["probabilities_json"])) == 3
    saved = json.loads((tmp_path / "spliceai_metadata.json").read_text())
    assert saved["full_macro_f1"]["lora"] == pytest.approx(0.8)


def test_plot_rejects_bad_labels_and_probabilities(tmp_path):
    path = tmp_path / "aligned.npz"
    write_aligned(path)
    with np.load(path) as data:
        arrays = {key: data[key] for key in data.files}
    arrays["labels"] = arrays["labels"] + 1
    np.savez(path, **arrays)
    with pytest.raises(ValueError, match="0/1/2"):
        plotter.load_projection(path)
    path = tmp_path / "aligned_valid.npz"
    write_aligned(path)
    with np.load(path) as data:
        arrays = {key: data[key] for key in data.files}
    arrays["probabilities"] = np.full_like(arrays["probabilities"], 0.5)
    np.savez(path, **arrays)
    with pytest.raises(ValueError, match="softmax"):
        plotter.load_projection(path)
    path = tmp_path / "aligned_color.npz"
    write_aligned(path, color_mode="categorical")
    with pytest.raises(ValueError, match="token class"):
        plotter.load_projection(path)
