import json
from collections import Counter
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import q_corrected_8task as q


def make_cell(task="spliceai", model="RNA-FM", strategy="frozen",
              split="random", seed=17):
    return q.Cell(task, model, strategy, split, seed)


@pytest.fixture
def runtime(tmp_path, monkeypatch):
    monkeypatch.setattr(q, "ARTIFACTS_ROOT", tmp_path / "artifacts")
    monkeypatch.setattr(q, "LOG_ROOT", tmp_path / "logs")
    rows = {}
    monkeypatch.setattr(q.ledger, "by_run_id", lambda rid: rows.get(rid))
    return SimpleNamespace(rows=rows)


def result_payload(cell, **updates):
    payload = {
        "run_id": q.rid_for(cell), "task": cell.task, "model": cell.model,
        "seed": cell.seed, "split": cell.split, "strategy": cell.strategy,
        "metric": cell.metric, "value": 0.75,
    }
    payload.update(updates)
    return payload


def write_result(cell, payload=None, raw=None):
    path = q.result_path(cell)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(raw if raw is not None else json.dumps(
        payload or result_payload(cell)))
    return path


def mark_done(runtime, cell):
    runtime.rows[q.rid_for(cell)] = {
        "run_id": q.rid_for(cell), "status": "done",
    }


def make_double_proof(runtime, cell):
    mark_done(runtime, cell)
    return write_result(cell)


def test_canonical_counts_and_cell_and_rid_uniqueness():
    cells = q.canonical_cells()
    assert Counter(c.task for c in cells) == {
        "spliceai": 126, "degradation": 108, "ssi": 108,
    }
    assert len(cells) == len({c.key for c in cells}) == 342
    assert len({q.rid_for(c) for c in cells}) == 342
    assert {c.task for c in cells if c.model == "RiNALMo-micro"} == {"spliceai"}
    for task in ("degradation", "ssi"):
        assert {c.model for c in cells if c.task == task} == set(q.REG_MODELS)


def test_epochs_learning_rates_batch_sizes_and_timeouts():
    for cell in q.canonical_cells():
        assert cell.epochs == (6 if cell.task == "spliceai" else 10)
        assert cell.lr_arg == ("1e-5" if cell.strategy == "full" else "3e-4")
        assert cell.lr == (1e-5 if cell.strategy == "full" else 3e-4)
        assert cell.timeout_s == (86400 if cell.task == "spliceai" else 43200)
        if cell.task != "spliceai":
            assert cell.batch_size == 8
        else:
            conservative = (cell.model == "NucleicBERT" or
                            (cell.strategy == "full" and cell.model in
                             ("RiNALMo-650M", "RiNALMo-mega")))
            assert cell.batch_size == (8 if conservative else 16)


def test_commands_and_rid_tags_follow_existing_runners():
    spl = make_cell(model="RiNALMo-650M", strategy="full", split="family", seed=43)
    cmd = q.build_command(spl, device=2)
    assert cmd[1:3] == ["-m", "rnafteval.finetune_spl"]
    assert cmd[cmd.index("--epochs") + 1] == "6"
    assert cmd[cmd.index("--batch-size") + 1] == "8"
    assert cmd[cmd.index("--lr") + 1] == "1e-5"
    assert cmd[cmd.index("--device") + 1] == "2"
    assert "_b20fix_lr1e-05_ep6" in q.rid_for(spl)

    reg = make_cell(task="degradation", model="NucleicBERT", strategy="lora")
    cmd = q.build_command(reg)
    assert cmd[1:3] == ["-m", "rnafteval.finetune_regbase"]
    assert cmd[cmd.index("--epochs") + 1] == "10"
    assert cmd[cmd.index("--batch-size") + 1] == "8"
    assert cmd[cmd.index("--lr") + 1] == "3e-4"
    assert "_b20fix_ep10" in q.rid_for(reg)


def test_nonzero_subprocess_failure_env_and_audit_log(runtime, monkeypatch):
    cell = make_cell()
    seen = {}

    def fake_run(cmd, **kwargs):
        seen.update(cmd=cmd, kwargs=kwargs)
        return SimpleNamespace(returncode=9)

    monkeypatch.setenv("HF_HOME", "/custom/hf")
    monkeypatch.setenv("PYTHONPATH", "/existing/python")
    monkeypatch.setattr(q.subprocess, "run", fake_run)
    outcome = q.run_cell(cell, device=3)

    assert outcome["status"] == "failed" and not outcome["ok"]
    assert outcome["rc"] == 9 and outcome["wall_sec"] >= 0
    assert seen["kwargs"]["timeout"] == 86400
    assert seen["kwargs"]["cwd"] == str(q.REPO_ROOT)
    env = seen["kwargs"]["env"]
    assert env["HF_HOME"] == "/custom/hf"
    assert env["PYTHONPATH"].split(":")[:3] == [
        "/root/rnaft/pypath", str(q.REPO_ROOT), "/home/cunyuliu/rna-sc",
    ]
    assert env["PYTHONPATH"].endswith("/existing/python")
    text = Path(outcome["log_path"]).read_text()
    record = json.loads(next(line[7:] for line in text.splitlines()
                             if line.startswith("RECORD ")))
    assert "COMMAND " in text and record["command"] == seen["cmd"]
    assert record["rc"] == 9 and record["wall_sec"] >= 0
    assert record["result_path"] == str(q.result_path(cell))


def test_rc_zero_without_double_proof_is_failure(runtime, monkeypatch):
    cell = make_cell()
    monkeypatch.setattr(q.subprocess, "run",
                        lambda *args, **kwargs: SimpleNamespace(returncode=0))
    outcome = q.run_cell(cell)
    assert not outcome["ok"] and outcome["rc"] == 0
    assert "double proof" in outcome["reason"]


def test_timeout_is_failure_even_if_double_proof_appears(runtime, monkeypatch):
    cell = make_cell(task="ssi")
    seen = {}

    def fake_run(cmd, **kwargs):
        seen["timeout"] = kwargs["timeout"]
        make_double_proof(runtime, cell)
        raise subprocess.TimeoutExpired(cmd, kwargs["timeout"])

    monkeypatch.setattr(q.subprocess, "run", fake_run)
    outcome = q.run_cell(cell)
    assert seen["timeout"] == 43200
    assert not outcome["ok"] and outcome["status"] == "failed"
    assert outcome["rc"] == "TIMEOUT" and "timeout" in outcome["reason"]


@pytest.mark.parametrize("mode", ["malformed", "mismatch", "nonfinite"])
def test_rc_zero_bad_result_json_is_failure(runtime, monkeypatch, mode):
    cell = make_cell()

    def fake_run(*args, **kwargs):
        mark_done(runtime, cell)
        if mode == "malformed":
            write_result(cell, raw="{not-json")
        elif mode == "mismatch":
            write_result(cell, result_payload(cell, task="wrong-task"))
        else:
            write_result(cell, result_payload(cell, value=float("nan")))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(q.subprocess, "run", fake_run)
    outcome = q.run_cell(cell)
    assert not outcome["ok"] and outcome["rc"] == 0
    assert outcome["status"] == "failed" and outcome["reason"]


def test_done_ledger_missing_result_conflicts_without_rerun(runtime, monkeypatch):
    cell = make_cell()
    mark_done(runtime, cell)
    calls = []
    monkeypatch.setattr(q.subprocess, "run",
                        lambda *args, **kwargs: calls.append((args, kwargs)))
    outcome = q.run_cell(cell)
    assert not outcome["ok"] and outcome["status"] == "failed"
    assert "missing" in outcome["reason"] and not calls


def test_valid_result_without_ledger_done_conflicts_without_rerun(
        runtime, monkeypatch):
    cell = make_cell()
    write_result(cell)
    monkeypatch.setattr(q.subprocess, "run",
                        lambda *args, **kwargs: pytest.fail("must not rerun"))
    outcome = q.run_cell(cell)
    assert not outcome["ok"] and "ledger is not done" in outcome["reason"]


def test_double_proof_skip_is_reentrant_and_never_launches(runtime, monkeypatch):
    cell = make_cell(task="degradation", strategy="full", split="family")
    make_double_proof(runtime, cell)
    calls = []
    monkeypatch.setattr(q.subprocess, "run",
                        lambda *args, **kwargs: calls.append((args, kwargs)))
    first = q.run_cell(cell)
    second = q.run_cell(cell)
    assert first["ok"] and second["ok"]
    assert first["status"] == second["status"] == "skipped"
    assert first["rc"] is None and not calls


def test_no_selected_cells_is_an_error(runtime):
    with pytest.raises(SystemExit) as exc_info:
        q.main(["--models", "RiNALMo-micro", "--tasks", "degradation"])
    assert exc_info.value.code == 2


def test_main_exit_status_and_reentry(runtime, monkeypatch, capsys):
    cell = make_cell()
    monkeypatch.setattr(q, "canonical_cells", lambda: [cell])
    monkeypatch.setattr(q.subprocess, "run",
                        lambda *args, **kwargs: SimpleNamespace(returncode=4))
    assert q.main(["--models", cell.model, "--workers", "1"]) == 1
    assert "INCOMPLETE" in capsys.readouterr().out

    make_double_proof(runtime, cell)
    assert q.main(["--models", cell.model, "--workers", "1"]) == 0
    captured = capsys.readouterr()
    assert "CORRECTED_DONE" in captured.out and "skipped=1" in captured.out
