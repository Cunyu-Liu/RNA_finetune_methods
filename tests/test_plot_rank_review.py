import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import plot_rank_review as review


def legacy_rows():
    rows = []
    for task in review.TASKS:
        for model in review.MODELS:
            for rank in review.RANKS:
                for seed in (17, 29, 43):
                    extra = "" if rank == 8 else "_r%d" % rank
                    rows.append({
                        "run_id": review.ledger.run_id(
                            model, task, "lora", seed, "random", extra),
                        "model": model, "task": task, "strategy": "lora",
                        "split": "random", "status": "done", "smoke": False,
                        "protocol": None, "extra": extra, "metric": "F1",
                        "value": 0.5 + rank / 100, "seed": seed,
                        "out_dir": "/artifacts/" + model,
                    })
    return rows


def rank8_rows():
    return {"protocol": "bestval_v1_fixedsplit", "rows": [
        {"split": split, "seed": seed, "ACC": 0.9 + seed / 1000,
         "proof": "ledger_result_curve_checkpoint_3_pass"}
        for split in ("random", "family") for seed in (17, 29, 43)]}


def test_legacy_filter_excludes_modification_and_new_protocol():
    rows = legacy_rows()
    rows.append(dict(rows[0], task="modification"))
    rows.append(dict(rows[0], protocol="bestval_v1"))
    selected = review.collect_legacy(rows)
    assert len(selected) == 108
    assert all(row["task"] != "modification" for row in selected)
    assert all(row["protocol"] == "legacy_fixed_epoch" for row in selected)
    tuning = dict(rows[0], seed=101)
    tuning["run_id"] = review.ledger.run_id(
        tuning["model"], tuning["task"], "lora", 101, "random", tuning["extra"])
    assert len(review.collect_legacy(rows + [tuning])) == 108
    missing_smoke = dict(rows[0])
    del missing_smoke["smoke"]
    assert len(review.collect_legacy([missing_smoke])) == 1


def test_review_plot_uses_real_groups_and_quarantines_modification(tmp_path):
    legacy = review.collect_legacy(legacy_rows())
    metadata = review.plot_review(legacy, rank8_rows(), tmp_path / "rank_review")
    assert metadata["legacy_groups"] == 36
    assert metadata["modification"].startswith("legacy_per_base_quarantined")
    assert (tmp_path / "rank_review.png").is_file()
    assert (tmp_path / "rank_review.pdf").is_file()
    saved = json.loads((tmp_path / "rank_review_metadata.json").read_text())
    assert saved["rank8_protocol"] == "bestval_v1_fixedsplit"


def test_incomplete_legacy_group_is_rejected():
    rows = [row for row in review.collect_legacy(legacy_rows())
            if not (row["task"] == "mrl" and row["model"] == "RNA-FM"
                    and row["rank"] == 16 and row["seed"] == 43)]
    with pytest.raises(ValueError, match="requires 3 seeds"):
        review.grouped(rows, "mrl", "RNA-FM", 16)
