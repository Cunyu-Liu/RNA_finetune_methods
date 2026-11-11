import json

from mentor_followup_monitor import DORA, write_dora_registry


def test_dora_registry_contains_240_unique_jobs():
    write_dora_registry()
    jobs = json.loads(DORA.read_text())
    assert len(jobs) == 240
    assert {job["strategy"] for job in jobs} == {"dora"}
    assert len({job["rid"] for job in jobs}) == 240
    assert len({job["result_dir"] for job in jobs}) == 240
    assert all(job["result_dir"].startswith(
        "/teams/HoulabData_1788502323/liucunyu/") for job in jobs)


def test_forgetting_stage_starts_once_and_does_not_restart_failure(tmp_path, monkeypatch):
    import io
    from types import SimpleNamespace
    import mentor_followup_monitor as monitor

    monkeypatch.setattr(monitor, "STATE", tmp_path)
    monkeypatch.setattr(monitor, "E6_STATE", tmp_path / "state.json")
    monkeypatch.setattr(monitor, "E6_PID", tmp_path / "monitor.pid")
    monkeypatch.setattr(monitor.subprocess, "run",
                        lambda *args, **kwargs: SimpleNamespace(stdout=""))
    calls = []
    monkeypatch.setattr(monitor.subprocess, "Popen",
                        lambda *args, **kwargs: calls.append(kwargs) or SimpleNamespace(pid=123))
    assert monitor.ensure_e6_queue(io.StringIO()) is False
    assert len(calls) == 1
    assert json.loads((tmp_path / "monitor.pid").read_text())["pid"] == 123
    import pytest
    with pytest.raises(RuntimeError, match="exited before 39"):
        monitor.ensure_e6_queue(io.StringIO())
    assert len(calls) == 1


def test_forgetting_complete_skips_launch(tmp_path, monkeypatch):
    import io
    import mentor_followup_monitor as monitor

    state = tmp_path / "state.json"
    state.write_text(json.dumps({"total": 39, "completed": 39}))
    monkeypatch.setattr(monitor, "E6_STATE", state)
    assert monitor.ensure_e6_queue(io.StringIO()) is True


def test_forgetting_waits_for_prior_stages(monkeypatch):
    import io
    import mentor_followup_monitor as monitor

    monkeypatch.setattr(monitor, "ensure_queue", lambda *args: False)
    monkeypatch.setattr(monitor, "ensure_e6_queue",
                        lambda log: (_ for _ in ()).throw(AssertionError("stage skipped")))
    assert monitor.run_once(io.StringIO()) == "p0_running"
