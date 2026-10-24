import fcntl
import json
import math
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import exclusive_aido as a


@pytest.fixture
def runtime(tmp_path, monkeypatch):
    monkeypatch.setattr(a, "ARTIFACTS_ROOT", tmp_path / "artifacts")
    monkeypatch.setattr(a, "FLAG", tmp_path / "EXCLUSIVE_AIDO")
    monkeypatch.setattr(a, "LOCK_PATH", tmp_path / "exclusive.lock")
    monkeypatch.setattr(a, "AUDIT_SCRIPT", tmp_path / "audit_1016.py")
    monkeypatch.setattr(a, "DRAIN_STABLE_S", 0)
    monkeypatch.setattr(a, "POLL_S", 0)
    rows = {}
    monkeypatch.setattr(a.ledger, "by_run_id", rows.get)
    real_drain = a.wait_for_drain
    monkeypatch.setattr(a, "wait_for_drain", lambda: None)
    real_audit = a.audit_status
    monkeypatch.setattr(a, "audit_status", lambda: (True, ""))
    return SimpleNamespace(rows=rows, real_drain=real_drain,
                           real_audit=real_audit)


def result_payload(**updates):
    payload = {
        "run_id": a.RUN_ID, "model": a.MODEL, "task": a.TASK,
        "strategy": a.STRATEGY, "seed": a.SEED, "split": a.SPLIT,
        "lr": a.LR, "epochs": a.EPOCHS,
        "metric": "PEARSON_R", "value": 0.75,
    }
    payload.update(updates)
    return payload


def write_result(payload=None, raw=None):
    path = a.result_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(raw if raw is not None else json.dumps(
        payload if payload is not None else result_payload()))
    return path


def make_proof(runtime):
    runtime.rows[a.RUN_ID] = result_payload(status="done")
    return write_result()


def test_command_and_rid_match_the_only_allowed_protocol():
    assert a.RUN_ID == "ft_aidorna16b_mrl_full_s43_random_lr1e-05"
    cmd = a.training_command()
    assert cmd[1:3] == ["-m", "rnafteval.finetune_mrl"]
    assert cmd[cmd.index("--model") + 1] == "AIDO.RNA-1.6B"
    assert cmd[cmd.index("--task") + 1] == "mrl"
    assert cmd[cmd.index("--seed") + 1] == "43"
    assert cmd[cmd.index("--epochs") + 1] == "3"
    assert cmd[cmd.index("--batch-size") + 1] == "1"
    assert cmd[cmd.index("--lr") + 1] == "1e-05"
    assert a.TIMEOUT_S == 43200


def test_complete_double_proof_never_reruns_and_cleans_flag(runtime, monkeypatch):
    make_proof(runtime)
    monkeypatch.setattr(a.subprocess, "run",
                        lambda *args, **kwargs: pytest.fail("must not train"))
    assert a.main([]) == 0
    assert not a.FLAG.exists()


def test_existing_child_natural_completion_is_rechecked_after_drain(
        runtime, monkeypatch):
    calls = []

    def child_finished():
        calls.append("drained")
        make_proof(runtime)

    monkeypatch.setattr(a, "wait_for_drain", child_finished)
    monkeypatch.setattr(a.subprocess, "run",
                        lambda *args, **kwargs: pytest.fail("child must not be duplicated"))
    assert a.main([]) == 0
    assert calls == ["drained"]
    assert not a.FLAG.exists()


def test_drain_requires_child_exit_and_safe_gpu(runtime, monkeypatch):
    monkeypatch.setattr(a, "wait_for_drain", runtime.real_drain)
    process_checks = iter([[321], []])
    gpu_checks = iter([(12000, ["321"]), (0, [])])
    monkeypatch.setattr(a, "training_processes", lambda: next(process_checks))
    monkeypatch.setattr(a, "gpu_state", lambda: next(gpu_checks))
    a.wait_for_drain()
    assert next(process_checks, None) is None
    assert next(gpu_checks, None) is None


def test_drain_allows_idle_dispatcher_cuda_context(runtime, monkeypatch):
    monkeypatch.setattr(a, "wait_for_drain", runtime.real_drain)
    monkeypatch.setattr(a, "training_processes", lambda: [])
    monkeypatch.setattr(a, "gpu_state", lambda: (418, ["dispatcher-parent"]))
    a.wait_for_drain()


def test_training_success_requires_double_proof_and_cleans_flag(
        runtime, monkeypatch):
    calls = []

    def fake_train(cmd, **kwargs):
        calls.append((cmd, kwargs))
        assert a.FLAG.exists()
        make_proof(runtime)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(a.subprocess, "run", fake_train)
    assert a.main([]) == 0
    assert len(calls) == 1
    assert calls[0][1]["timeout"] == 43200
    assert not a.FLAG.exists()


def test_failed_attempt_is_retried_without_permanent_flag(runtime, monkeypatch):
    calls = []

    def fake_train(*args, **kwargs):
        calls.append(1)
        if len(calls) == 1:
            return SimpleNamespace(returncode=9)
        make_proof(runtime)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(a.subprocess, "run", fake_train)
    assert a.main([]) == 1
    assert not a.FLAG.exists()
    assert a.main([]) == 0
    assert len(calls) == 2
    assert not a.FLAG.exists()


def test_duplicate_lock_returns_75_without_clearing_active_flag(
        runtime, monkeypatch):
    a.FLAG.write_text("active-owner")
    monkeypatch.setattr(a.subprocess, "run",
                        lambda *args, **kwargs: pytest.fail("duplicate must not train"))
    with a.LOCK_PATH.open("a+") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        assert a.main([]) == 75
    assert a.FLAG.read_text() == "active-owner"


@pytest.mark.parametrize("mode", ["malformed", "mismatch", "nan", "inf"])
def test_invalid_existing_result_is_preserved_and_not_accepted(
        runtime, monkeypatch, mode):
    if mode == "malformed":
        path = write_result(raw="{not-json")
    else:
        updates = {"epochs": 10} if mode == "mismatch" else {
            "value": math.nan if mode == "nan" else math.inf}
        path = write_result(result_payload(**updates))
    before = path.read_bytes()
    monkeypatch.setattr(a.subprocess, "run",
                        lambda *args, **kwargs: pytest.fail("conflict must not train"))
    assert a.main([]) == 1
    assert path.read_bytes() == before
    assert not a.FLAG.exists()


def test_valid_result_without_ledger_done_is_not_overwritten(runtime, monkeypatch):
    path = write_result()
    before = path.read_bytes()
    monkeypatch.setattr(a.subprocess, "run",
                        lambda *args, **kwargs: pytest.fail("must not repair or rerun"))
    assert a.main([]) == 1
    assert path.read_bytes() == before
    assert not a.FLAG.exists()


def test_verify_gate_requires_double_proof_and_audit_zero(runtime, monkeypatch):
    assert a.main(["--verify-complete"]) == 1
    make_proof(runtime)
    monkeypatch.setattr(a, "audit_status", runtime.real_audit)
    audit_calls = []

    def fake_audit(cmd, **kwargs):
        audit_calls.append(cmd)
        return SimpleNamespace(returncode=0, stdout="1\n", stderr="")

    monkeypatch.setattr(a.subprocess, "run", fake_audit)
    assert a.main(["--verify-complete"]) == 1
    monkeypatch.setattr(a.subprocess, "run",
                        lambda *args, **kwargs: SimpleNamespace(
                            returncode=0, stdout="0\n", stderr=""))
    assert a.main(["--verify-complete"]) == 0
    assert audit_calls == [[sys.executable, str(a.AUDIT_SCRIPT)]]
    assert not a.FLAG.exists()


def test_timeout_fails_and_cleans_flag_even_if_proof_appears(
        runtime, monkeypatch):
    seen = {}

    def fake_train(cmd, **kwargs):
        seen.update(kwargs)
        make_proof(runtime)
        raise subprocess.TimeoutExpired(cmd, kwargs["timeout"])

    monkeypatch.setattr(a.subprocess, "run", fake_train)
    assert a.main([]) == 1
    assert seen["timeout"] == 43200
    assert not a.FLAG.exists()
