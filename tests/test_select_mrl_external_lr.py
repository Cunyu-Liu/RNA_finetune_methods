import json
from types import SimpleNamespace

from select_mrl_external_lr import select_groups


def make_jobs(tmp_path):
    jobs = []
    for model in ("NucleicBERT", "AIDO.RNA-1.6B"):
        for split in ("random", "family"):
            for index, lr in enumerate(("3e-4", "1e-4", "3e-5", "1e-5")):
                rid = f"{model}_{split}_{lr}"
                result = tmp_path / f"{rid}.json"
                result.write_text(json.dumps({"best_val": 0.4 - index * 0.1, "value": 0.99 if lr == "3e-4" else 0.1}))
                jobs.append(SimpleNamespace(seed=101, model=model, split=split, lr=lr, rid=rid, result_path=result))
    return jobs


def test_selects_validation_not_test_and_covers_four_groups(tmp_path):
    summary, rows = select_groups(make_jobs(tmp_path), state_fn=lambda job: ("complete", ""))
    assert summary["status"] == "complete"
    assert len(rows) == 4
    assert all(row["selected_lr"] == "1e-5" for row in rows)
    assert all(row["candidates"][0]["test_value_for_report_only"] == 0.99
               for row in rows)


def test_incomplete_group_blocks_selection(tmp_path):
    jobs = make_jobs(tmp_path)
    jobs[0].seed = 17
    summary, rows = select_groups(jobs, state_fn=lambda job: ("complete", ""))
    assert summary["status"] == "incomplete"
    assert not rows


def test_cuda_constant_candidate_is_excluded_not_selected(tmp_path):
    jobs = make_jobs(tmp_path)
    invalid = {job.rid: {"candidate_eligible": False} for job in jobs if job.lr == "3e-4"}
    state = lambda job: ("running", "no result") if job.rid in invalid else ("complete", "")
    summary, rows = select_groups(jobs, state_fn=state, invalid_documents=invalid)
    assert summary["status"] == "complete"
    assert len(rows) == 4
    assert all(row["selected_lr"] == "1e-5" for row in rows)
    assert all(len(row["invalid_candidates"]) == 1 for row in rows)
    assert all(len(row["candidates"]) == 3 for row in rows)


def test_constant_failure_without_proof_blocks_selection(tmp_path):
    jobs = make_jobs(tmp_path)
    state = lambda job: ("running", "no result") if job.lr == "3e-4" else ("complete", "")
    summary, rows = select_groups(jobs, state_fn=state)
    assert summary["status"] == "incomplete"
    assert not rows


def test_nuc_only_two_groups_are_supported(tmp_path):
    jobs = [job for job in make_jobs(tmp_path) if job.model == "NucleicBERT"]
    summary, rows = select_groups(jobs, state_fn=lambda job: ("complete", ""),
                                  expected_groups=2)
    assert summary["status"] == "complete"
    assert len(rows) == 2
    assert all(row["model"] == "NucleicBERT" for row in rows)
