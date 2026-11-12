import json
from pathlib import Path

from prepare_mentor_retest_jobs import main


def test_registries_have_unique_jobs_and_expected_protocols():
    main()
    root = Path(__file__).resolve().parents[1] / "scripts"
    p0 = json.loads((root / "main_remaining_650m_18_jobs_20261111.json").read_text())
    external = json.loads((root / "mrl_external_nuc_tuning_default_14_jobs_20261112.json").read_text())
    tuned = json.loads((root / "mrl_nuc_tuned_6_required_20261112.json").read_text())
    summary = json.loads((root / "mentor_retest_jobs_20261111_summary.json").read_text())
    assert len(p0) == 18
    assert len(external) == 14
    assert tuned["required_jobs"] == 6
    assert summary["deferred_models"] == ["AIDO.RNA-1.6B"]
    assert summary["deferred_cells"] == 14
    for jobs in (p0, external):
        assert len({job["rid"] for job in jobs}) == len(jobs)
        assert len({job["result_dir"] for job in jobs}) == len(jobs)
        assert all(job["protocol"] == "bestval_v1" for job in jobs)
        assert all(job["result_dir"].startswith("/teams/HoulabData_1788502323/liucunyu/rna-ft-eval/artifacts/") for job in jobs)
        assert all(job["result_dir"].endswith(job["rid"]) for job in jobs)
    assert {job["model"] for job in external} == {"NucleicBERT"}
    assert all(job["rid"].count("_reval20261111") == 1 for job in external)
    assert all(job["need_gb"] == 12 for job in external)
