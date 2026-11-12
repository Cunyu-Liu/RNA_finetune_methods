import json
from types import SimpleNamespace

import pytest

from summarize_external_mrl_random import summarize_jobs


def make_jobs(tmp_path):
    jobs = []
    for split in ("random", "family"):
        for seed, lr in ((101, "3e-4"), (101, "1e-4"), (101, "3e-5"),
                         (101, "1e-5"), (17, "3e-5"), (29, "3e-5"), (43, "3e-5")):
            rid = f"ft_{split}_{seed}_{lr}"
            result = tmp_path / f"{rid}.json"
            best_val = {"3e-4": 0.1, "1e-4": 0.2, "3e-5": 0.3, "1e-5": 0.4}[lr]
            result.write_text(json.dumps({
                "best_val": best_val, "value": 0.087 if seed != 101 else 0.1,
                "mse": 0.9, "best_epoch": 0, "epochs_trained": 4,
                "peak_mem_mb": 7730.5,
            }))
            jobs.append(SimpleNamespace(
                model="NucleicBERT", split=split, seed=seed, lr=lr,
                rid=rid, result_path=result))
    return jobs


def test_family_summary_separates_default_from_tuned_selection(tmp_path, monkeypatch):
    import summarize_external_mrl_random as summary

    monkeypatch.setattr(summary, "proof_state", lambda job: ("complete", ""))
    monkeypatch.setattr(summary, "is_valid", lambda path, rid: True)
    source = tmp_path / "jobs.json"
    source.write_text("[]")
    document = summarize_jobs(make_jobs(tmp_path), source, tmp_path, "family")
    assert document["default_lr"] == "3e-5"
    assert document["default_best_val"] == 0.3
    assert document["tuned_selection_lr"] == "3e-4"
    assert document["tuned_selected_best_val"] == 0.1
    assert document["tuned_matches_default"] is False
    assert document["tuned_comparison"] == "pending"
    assert document["formal_mean"] == pytest.approx(0.087)
    assert document["prediction_revalidation_passed"] == 7
    assert document["aido_status"] == "deferred_na"


def test_summary_rejects_missing_prediction_proof(tmp_path, monkeypatch):
    import summarize_external_mrl_random as summary

    monkeypatch.setattr(summary, "proof_state", lambda job: ("complete", ""))
    monkeypatch.setattr(summary, "is_valid", lambda path, rid: False)
    source = tmp_path / "jobs.json"
    source.write_text("[]")
    with pytest.raises(ValueError, match="missing independent prediction proof"):
        summarize_jobs(make_jobs(tmp_path), source, tmp_path, "family")
