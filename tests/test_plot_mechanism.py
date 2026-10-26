import csv
import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import plot_mechanism as plotter


def aligned_file(tmp_path):
    n = 8
    ids = np.asarray(["sample-%d" % index for index in range(n)])
    labels = np.asarray([0, 1] * (n // 2))
    states = np.concatenate([np.full(n, state) for state in plotter.STATES])
    base = np.arange(n * 4, dtype=np.float32).reshape(n, 4) / 10
    cls = np.concatenate([base + index * 3 for index in range(3)])
    head = cls + 0.25
    coordinates = np.arange(n * 6, dtype=np.float32).reshape(n * 3, 2)
    path = tmp_path / "aligned.npz"
    np.savez(path, sample_ids=np.tile(ids, 3), labels=np.tile(labels, 3),
             state=states, cls=cls, head_embedding=head, tsne=coordinates,
             tsne_perplexity=np.asarray(5), tsne_random_state=np.asarray(17),
             split=np.asarray("random"), seed=np.asarray(17),
             test_manifest_sha256=np.asarray("manifest-test"))
    return path, coordinates


def test_cls_plot_exports_all_coordinates_and_metadata(tmp_path, monkeypatch):
    class DeterministicTSNE:
        def __init__(self, n_components, random_state, perplexity):
            assert (n_components, random_state, perplexity) == (2, 17, 5)

        def fit_transform(self, values):
            return values[:, :2] + 1

    import sklearn.manifold
    monkeypatch.setattr(sklearn.manifold, "TSNE", DeterministicTSNE)
    source, _ = aligned_file(tmp_path)
    projection = plotter.load_projection(source, "cls")
    assert projection["coordinates"].shape == (24, 2)
    assert projection["n"] == 8 and projection["split"] == "random"
    metadata = plotter.plot_projection(projection, tmp_path / "ncrna_cls", "cls")
    assert metadata["n_per_state"] == 8
    assert set(metadata["silhouette"]) == set(plotter.STATES)
    for suffix in (".png", ".pdf", "_coordinates.csv", "_metadata.json"):
        assert (tmp_path / ("ncrna_cls" + suffix)).is_file()
    with open(tmp_path / "ncrna_cls_coordinates.csv") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 24
    assert {row["state"] for row in rows} == set(plotter.STATES)
    assert all(row["test_manifest_sha256"] == "manifest-test" for row in rows)
    saved = json.loads((tmp_path / "ncrna_cls_metadata.json").read_text())
    assert saved["interpretation"] == "descriptive_only_no_head_causality"


def test_head_plot_uses_existing_joint_coordinates(tmp_path):
    source, expected = aligned_file(tmp_path)
    projection = plotter.load_projection(source, "head")
    assert np.array_equal(projection["coordinates"], expected)
    plotter.plot_projection(projection, tmp_path / "ncrna_head", "head")
    with open(tmp_path / "ncrna_head_coordinates.csv") as handle:
        rows = list(csv.DictReader(handle))
    assert [float(row["tsne_1"]) for row in rows] == pytest.approx(expected[:, 0])
    assert [float(row["tsne_2"]) for row in rows] == pytest.approx(expected[:, 1])
