import csv
import json
from pathlib import Path
import sys

import numpy as np
import pytest
from scipy.special import softmax

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import plot_mechanism_crispr as plotter


def write_aligned(path, color_mode="crispr_off_target_label"):
    states = np.repeat(["pre", "lora", "full"], 4)
    ids = np.tile(["a", "b", "c", "d"], 3)
    labels = np.tile([0, 1, 0, 1], 3)
    logits = np.tile([[1.0, -1.0], [-1.0, 1.0]], (6, 1))
    probabilities = softmax(logits, axis=-1)
    np.savez(
        path,
        tsne_cls=np.arange(24).reshape(12, 2),
        tsne_head=np.arange(24).reshape(12, 2) + 10,
        sample_ids=ids,
        state=states,
        labels=labels,
        probabilities=probabilities,
        logits=logits,
        full_pr_auc=np.asarray([0.05, 0.65, 0.06]),
        full_roc_auc=np.asarray([0.5, 0.8, 0.73]),
        source_run_ids=np.asarray(["pre_source", "lora_source", "full_source"]),
        color_mode=np.asarray(color_mode),
        sampling=np.asarray("positive_cap_256_then_negative_hash_fill"),
        split=np.asarray("random"),
        seed=np.asarray(17),
        test_manifest_sha256=np.asarray("manifest"),
        tsne_perplexity=np.asarray(3),
        tsne_random_state=np.asarray(17),
    )


def test_load_projection_validates_binary_softmax_and_metrics(tmp_path):
    path = tmp_path / "aligned.npz"
    write_aligned(path)
    projection = plotter.load_projection(path, "cls")
    assert projection["n"] == 4
    assert projection["probabilities"].shape == (12, 2)
    assert projection["full_pr_auc"].tolist() == [0.05, 0.65, 0.06]
    assert projection["sampling"].startswith("positive_cap_256")


def test_plot_exports_support_and_full_test_scope(tmp_path):
    path = tmp_path / "aligned.npz"
    write_aligned(path)
    projection = plotter.load_projection(path, "head")
    metadata = plotter.plot_projection(projection, tmp_path / "crispr_head", "head")
    assert metadata["classification_silhouette"] is None
    assert metadata["label_support"]["lora"] == {"positive": 2, "negative": 2}
    assert metadata["metric_scope"].endswith("full_test")
    assert metadata["visualization_enrichment"] is True
    for suffix in (".png", ".pdf", "_coordinates.csv", "_metadata.json"):
        assert (tmp_path / ("crispr_head" + suffix)).is_file()
    with open(tmp_path / "crispr_head_coordinates.csv") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 12
    assert rows[0]["sampling"] == "positive_cap_256_then_negative_hash_fill"
    assert rows[-1]["source_run_id"] == "full_source"
    assert len(json.loads(rows[0]["probabilities_json"])) == 2
    saved = json.loads((tmp_path / "crispr_head_metadata.json").read_text())
    assert saved["full_pr_auc"]["lora"] == pytest.approx(0.65)


def test_plot_rejects_bad_labels_and_probabilities(tmp_path):
    path = tmp_path / "aligned.npz"
    write_aligned(path)
    with np.load(path) as data:
        arrays = {key: data[key] for key in data.files}
    arrays["labels"] = arrays["labels"] + 1
    np.savez(path, **arrays)
    with pytest.raises(ValueError, match="0/1"):
        plotter.load_projection(path, "cls")
    path = tmp_path / "aligned_valid.npz"
    write_aligned(path)
    with np.load(path) as data:
        arrays = {key: data[key] for key in data.files}
    arrays["probabilities"] = np.full_like(arrays["probabilities"], 0.5)
    np.savez(path, **arrays)
    with pytest.raises(ValueError, match="softmax"):
        plotter.load_projection(path, "cls")
    path = tmp_path / "aligned_color.npz"
    write_aligned(path, color_mode="categorical")
    with pytest.raises(ValueError, match="off-target"):
        plotter.load_projection(path, "cls")
