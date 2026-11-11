import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import expansion_jobs


def test_new_job_uses_configured_artifact_root(tmp_path, monkeypatch):
    monkeypatch.setattr(expansion_jobs, "ROOT", tmp_path)
    monkeypatch.setattr(expansion_jobs.ledger, "by_run_id", lambda rid: None)
    job = expansion_jobs.job_for("mrl", "RiNALMo-micro", "full", "random", 999,
                                 out_suffix="_unit")
    assert job["result_dir"] == str(tmp_path / job["rid"])


def test_done_and_running_jobs_keep_their_evidence_paths(tmp_path, monkeypatch):
    monkeypatch.setattr(expansion_jobs, "ROOT", Path(
        "/teams/HoulabData_1788502323/liucunyu/rna-ft-eval/artifacts"))
    for status in ("done", "running"):
        legacy = tmp_path / status
        monkeypatch.setattr(expansion_jobs.ledger, "by_run_id",
                            lambda rid: {"status": status, "out_dir": str(legacy)})
        job = expansion_jobs.job_for("mrl", "RiNALMo-micro", "lora", "random", 999,
                                     out_suffix="_unit")
        assert job["result_dir"] == str(legacy)


def test_failed_legacy_row_does_not_redirect_new_job(tmp_path, monkeypatch):
    monkeypatch.setattr(expansion_jobs, "ROOT", tmp_path / "new")
    monkeypatch.setattr(expansion_jobs.ledger, "by_run_id",
                        lambda rid: {"status": "failed", "out_dir": "/root/old"})
    job = expansion_jobs.job_for("mrl", "RiNALMo-micro", "lora", "random", 999,
                                 out_suffix="_unit")
    assert job["result_dir"] == str(tmp_path / "new" / job["rid"])


def test_explicit_root_is_independent_of_legacy_shell_env(tmp_path, monkeypatch):
    monkeypatch.setenv("RNAFT_ARTIFACT_ROOT", "/root/rna-ft-eval/artifacts")
    monkeypatch.setattr(expansion_jobs.ledger, "by_run_id", lambda rid: None)
    job = expansion_jobs.job_for("mrl", "RiNALMo-micro", "full", "random", 999,
                                 out_suffix="_unit", artifact_root=tmp_path)
    assert job["result_dir"] == str(tmp_path / job["rid"])
