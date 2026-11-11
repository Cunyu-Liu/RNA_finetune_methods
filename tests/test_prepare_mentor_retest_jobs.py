import json
from pathlib import Path

from prepare_mentor_retest_jobs import main


def test_registries_have_unique_jobs_and_expected_protocols():
    main()
    root = Path(__file__).resolve().parents[1] / "scripts"
    p0 = json.loads((root / "main_remaining_650m_18_jobs_20261111.json").read_text())
    external = json.loads((root / "mrl_external_tuning_default_28_jobs_20261111.json").read_text())
    tuned = json.loads((root / "mrl_external_tuned_12_required_20261111.json").read_text())
    assert len(p0) == 18
    assert len(external) == 28
    assert tuned["required_jobs"] == 12
    for jobs in (p0, external):
        assert len({job["rid"] for job in jobs}) == len(jobs)
        assert len({job["result_dir"] for job in jobs}) == len(jobs)
        assert all(job["protocol"] == "bestval_v1" for job in jobs)
        assert all(job["result_dir"].startswith("/teams/HoulabData_1788502323/liucunyu/rna-ft-eval/artifacts/") for job in jobs)
        assert all(job["result_dir"].endswith(job["rid"]) for job in jobs)
    assert {job["model"] for job in external} == {"NucleicBERT", "AIDO.RNA-1.6B"}
    assert all("_reval20261111" in job["rid"] for job in external)
    aido = next(job for job in external if job["model"] == "AIDO.RNA-1.6B")
    assert aido["need_gb"] == 32
    assert "--batch-size" in aido["args"] or "-bs" in aido["args"] or any("batch" in arg for arg in aido["args"])
