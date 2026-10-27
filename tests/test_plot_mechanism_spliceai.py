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
    base_positions = np.tile([0, 1, 0, 1], 3)
    token_positions = np.tile([1, 2, 1, 2], 3)
    labels = np.tile([0, 1, 2, 0], 3)
    logits = np.asarray([[2.0, 0.0, -1.0]] * 12)
    probabilities = softmax(logits, axis=-1)
    np.savez(
        path,
        tsne=np.arange(24).reshape(12, 2),
        token_ids=token_ids,
        sequence_ids=sequence_ids,
        base_positions=base_positions,
        token_positions=token_positions,
        state=states,
        labels=labels,
        probabilities=probabilities,
        logits=logits,
        full_macro_f1=np.asarray([0.3, 0.8, 0.7]),
        full_micro_f1=np.asarray([0.4, 0.75, 0.65]),
        full_roc_auc=np.asarray([0.5, 0.9, 0.85]),
        roc_auc_role=np.asarray(plotter.ROC_AUC_ROLE),
        metric_scope=np.asarray("full_test_macro_micro__ROC_AUC_auxiliary"),
        source_run_ids=np.asarray(["pre_source", "lora_source", "full_source"]),
        color_mode=np.asarray(color_mode),
        sampling=np.asarray("per_class_cap_512_before_prediction"),
        split=np.asarray("random"),
        seed=np.asarray(17),
        full_test_sha256=np.asarray("full-test"),
        test_manifest_sha256=np.asarray("manifest"),
        tsne_perplexity=np.asarray(3),
        tsne_random_state=np.asarray(17),
    )


def test_load_projection_validates_softmax_micro_and_explicit_positions(tmp_path):
    path = tmp_path / "aligned.npz"
    write_aligned(path)
    projection = plotter.load_projection(path)
    assert projection["n"] == 4
    assert projection["probabilities"].shape == (12, 3)
    assert projection["full_macro_f1"].tolist() == [0.3, 0.8, 0.7]
    assert projection["full_micro_f1"].tolist() == [0.4, 0.75, 0.65]
    assert projection["base_positions"].tolist()[:4] == [0, 1, 0, 1]
    assert projection["token_positions"].tolist()[:4] == [1, 2, 1, 2]
    assert "positions" not in projection
    assert projection["roc_auc_role"].startswith("auxiliary")


def test_plot_exports_acceptor_donor_micro_and_base_token_columns(tmp_path):
    path = tmp_path / "aligned.npz"
    write_aligned(path)
    projection = plotter.load_projection(path)
    metadata = plotter.plot_projection(projection, tmp_path / "spliceai")
    assert metadata["classification_silhouette"] is None
    assert metadata["label_support"]["lora"] == {
        "negative": 2, "acceptor": 1, "donor": 1}
    assert metadata["class_names"] == {"0": "negative", "1": "acceptor", "2": "donor"}
    assert metadata["source_reconciliation_metrics"] == ["macro_f1", "micro_f1"]
    assert metadata["roc_auc_role"] == plotter.ROC_AUC_ROLE
    assert metadata["full_micro_f1"]["lora"] == pytest.approx(0.75)
    for suffix in (".png", ".pdf", "_coordinates.csv", "_metadata.json"):
        assert (tmp_path / ("spliceai" + suffix)).is_file()
    with open(tmp_path / "spliceai_coordinates.csv") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        assert "base_position" in reader.fieldnames
        assert "token_position" in reader.fieldnames
        assert "position" not in reader.fieldnames
    assert len(rows) == 12
    assert rows[0]["representation"] == "per_base_token"
    assert rows[0]["token_id"] == "a:0000"
    assert rows[0]["base_position"] == "0" and rows[0]["token_position"] == "1"
    assert rows[1]["class_name"] == "acceptor"
    assert rows[2]["class_name"] == "donor"
    assert rows[5]["state"] == "lora" and rows[5]["full_micro_f1"] == "0.75"
    assert rows[1]["roc_auc_role"] == plotter.ROC_AUC_ROLE
    assert len(json.loads(rows[0]["probabilities_json"])) == 3
    saved = json.loads((tmp_path / "spliceai_metadata.json").read_text())
    assert saved["full_macro_f1"]["lora"] == pytest.approx(0.8)
    assert saved["full_micro_f1"]["lora"] == pytest.approx(0.75)


def test_plot_rejects_bad_labels_probabilities_roles_and_alignment(tmp_path):
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
    path = tmp_path / "aligned_role.npz"
    write_aligned(path)
    with np.load(path) as data:
        arrays = {key: data[key] for key in data.files}
    arrays["roc_auc_role"] = np.asarray("source_metric")
    np.savez(path, **arrays)
    with pytest.raises(ValueError, match="auxiliary"):
        plotter.load_projection(path)
    path = tmp_path / "aligned_position.npz"
    write_aligned(path)
    with np.load(path) as data:
        arrays = {key: data[key] for key in data.files}
    arrays["token_positions"][4] += 1
    np.savez(path, **arrays)
    with pytest.raises(ValueError, match="token_positions"):
        plotter.load_projection(path)
