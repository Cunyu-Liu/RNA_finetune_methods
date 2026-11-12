import json
from types import SimpleNamespace

import pytest

from summarize_nucleicbert_tuned import summarize_split


def make_jobs(tmp_path, tuned_lr):
    jobs = []
    for arm, lr in (("default", "3e-5"), ("tuned", tuned_lr)):
        for seed in (17, 29, 43):
            rid = f"ft_{arm}_{seed}_{lr}"
            result = tmp_path / f"{rid}.json"
            value = 0.08 + seed / 10000 + (0.001 if arm == "tuned" else 0)
            result.write_text(json.dumps({
                "seed": seed, "value": value, "mse": 1.0, "best_val": 0.9,
                "epochs_trained": 4, "acceptance_eligible": True,
            }))
            jobs.append(SimpleNamespace(
                task="mrl", model="NucleicBERT", strategy="full", split="family",
                protocol="bestval_v1", seed=seed, lr=lr, rid=rid,
                n_train=20000, args=["--batch-size", "8"], result_path=result,
            ))
    return jobs[:3], jobs[3:]


def selection():
    return {"test_metric_used": False,
            "rows": [{"model": "NucleicBERT", "split": "family", "selected_lr": "3e-4"}]}


def test_pairs_same_seed_and_computes_paired_delta(tmp_path, monkeypatch):
    import summarize_nucleicbert_tuned as summary

    monkeypatch.setattr(summary, "proof_state", lambda job: ("complete", ""))
    monkeypatch.setattr(summary, "is_valid", lambda path, rid: True)
    defaults, tuned = make_jobs(tmp_path, "3e-4")
    document = summarize_split(defaults, tuned, selection(), tmp_path, "family")
    assert document["n_pairs"] == 3
    assert document["tuned_minus_default_mean"] == pytest.approx(0.001)
    assert document["unique_prediction_rids"] == 6
    assert document["test_metric_used_for_selection"] is False


def test_missing_prediction_proof_blocks_summary(tmp_path, monkeypatch):
    import summarize_nucleicbert_tuned as summary

    monkeypatch.setattr(summary, "proof_state", lambda job: ("complete", ""))
    monkeypatch.setattr(summary, "is_valid", lambda path, rid: False)
    defaults, tuned = make_jobs(tmp_path, "3e-4")
    with pytest.raises(ValueError, match="missing independent prediction proof"):
        summarize_split(defaults, tuned, selection(), tmp_path, "family")


def test_selected_lr_mismatch_blocks_summary(tmp_path, monkeypatch):
    import summarize_nucleicbert_tuned as summary

    monkeypatch.setattr(summary, "proof_state", lambda job: ("complete", ""))
    monkeypatch.setattr(summary, "is_valid", lambda path, rid: True)
    defaults, tuned = make_jobs(tmp_path, "1e-5")
    with pytest.raises(ValueError, match="differs from frozen validation selection"):
        summarize_split(defaults, tuned, selection(), tmp_path, "family")
