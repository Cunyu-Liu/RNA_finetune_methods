import json
from collections import Counter
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest
import torch

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
    val_losses = [1.0, 0.8, 0.62, 0.61, 0.605, 0.602]
    payload = {
        "run_id": q.rid_for(cell), "task": cell.task, "model": cell.model,
        "seed": cell.seed, "split": cell.split, "strategy": cell.strategy,
        "metric": cell.metric, "value": 0.75, "n_train": 100, "smoke": False,
        "protocol": q.vp.PROTOCOL, "loss_source": "validation",
        "epoch_train_losses": [0.5] * len(val_losses),
        "epoch_val_losses": val_losses, "epochs_trained": len(val_losses),
        "status": "CONVERGED", "stop_reason": q.vp.STOP_REASON, "n_val": 12,
        "min_delta": q.vp.MIN_DELTA, "patience": q.vp.PATIENCE,
        "abs_floor": q.vp.ABS_FLOOR,
        "runtime": {
            "cuda_available": True, "cuda_device": "cuda:0",
            "cuda_device_name": "unit-test-metadata", "cuda_runtime_version": "test",
            "tokenizer_class": "unit.TestTokenizer",
            "tokenizer_name_or_path": "unit-test-tokenizer",
            "tokenizer_vocab_size": 12,
        },
    }
    payload.update(updates)
    return payload


def write_result(cell, payload=None, raw=None):
    path = q.result_path(cell)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(raw if raw is not None else json.dumps(
        payload or result_payload(cell)))
    return path


def mark_done(runtime, cell, payload=None):
    payload = payload or result_payload(cell)
    runtime.rows[q.rid_for(cell)] = {
        "run_id": q.rid_for(cell), "status": "done",
        "protocol": q.vp.PROTOCOL, "stop_reason": q.vp.STOP_REASON,
        "convergence_status": "CONVERGED",
        "epoch_val_losses": payload["epoch_val_losses"],
    }


def test_ledger_convergence_status_is_required(runtime, monkeypatch):
    cell = make_cell()
    make_double_proof(runtime, cell)
    runtime.rows[q.rid_for(cell)].pop("convergence_status")
    monkeypatch.setattr(q.subprocess, "run",
                        lambda *args, **kwargs: pytest.fail("must not rerun"))
    outcome = q.run_cell(cell)
    assert not outcome["ok"] and "CONVERGED status" in outcome["reason"]


def write_plateau(cell, payload=None):
    payload = payload or result_payload(cell)
    path = q.plateau_path(cell)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "run_id": q.rid_for(cell), "protocol": q.vp.PROTOCOL,
        "loss_source": "validation",
        "epoch_train_losses": payload["epoch_train_losses"],
        "epoch_val_losses": payload["epoch_val_losses"],
        "updated_epoch": payload["epochs_trained"] - 1,
        "status": payload["status"], "stop_reason": payload["stop_reason"],
        "min_delta": q.vp.MIN_DELTA, "patience": q.vp.PATIENCE,
        "abs_floor": q.vp.ABS_FLOOR,
    }))
    return path


def make_double_proof(runtime, cell):
    payload = result_payload(cell)
    mark_done(runtime, cell, payload)
    write_plateau(cell, payload)
    return write_result(cell, payload)


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
    assert "--epochs" not in cmd
    assert "--converge" in cmd
    assert cmd[cmd.index("--batch-size") + 1] == "8"
    assert cmd[cmd.index("--lr") + 1] == "1e-5"
    assert cmd[cmd.index("--device") + 1] == "2"
    assert q.rid_for(spl).endswith("_b20fix_lr1e-05_valplateau_v2")

    reg = make_cell(task="degradation", model="NucleicBERT", strategy="lora")
    cmd = q.build_command(reg)
    assert cmd[1:3] == ["-m", "rnafteval.finetune_regbase"]
    assert "--epochs" not in cmd
    assert "--converge" in cmd
    assert cmd[cmd.index("--batch-size") + 1] == "8"
    assert cmd[cmd.index("--lr") + 1] == "3e-4"
    assert q.rid_for(reg).endswith("_b20fix_valplateau_v2")
    bestval = q.rid_for(reg, "bestval")
    assert bestval.endswith("_b20fix_bestval_v1")
    assert bestval != q.rid_for(reg)
    cmd = q.build_command(reg, convergence_mode="bestval")
    assert cmd[cmd.index("--convergence-mode") + 1] == "bestval"
    assert q.result_path(reg) != q.result_path(reg, "bestval")


def test_bestval_proof_requires_matching_checkpoint_and_ledger(runtime):
    cell = make_cell(task="degradation", model="NucleicBERT", strategy="lora")
    values = [1.0, 0.5, 0.7, 0.8, 0.9]
    rid = q.rid_for(cell, "bestval")
    payload = result_payload(
        cell, run_id=rid, protocol=q.vp.BESTVAL_PROTOCOL,
        stop_reason=q.vp.BESTVAL_STOP_REASON, epoch_val_losses=values,
        epoch_train_losses=[0.5] * 5, epochs_trained=5,
        best_epoch=1, best_val=0.5, stale_epochs=3,
        best_checkpoint="best.ckpt", acceptance_eligible=True)
    path = q.result_path(cell, "bestval")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload))
    q.plateau_path(cell, "bestval").write_text(json.dumps({
        "run_id": rid, "protocol": q.vp.BESTVAL_PROTOCOL,
        "loss_source": "validation", "epoch_train_losses": [0.5] * 5,
        "epoch_val_losses": values, "updated_epoch": 4,
        "best_epoch": 1, "best_val": 0.5, "stale_epochs": 3,
        "best_checkpoint": "best.ckpt",
        "status": "CONVERGED", "stop_reason": q.vp.BESTVAL_STOP_REASON,
        "min_delta": q.vp.MIN_DELTA, "patience": q.vp.PATIENCE,
        "abs_floor": q.vp.ABS_FLOOR}))
    state = {
        "backbone": {"weight": torch.tensor([2.0])},
        "head": {"weight": torch.tensor([3.0])},
        "epoch": 1, "best_epoch": 1, "best_val": 0.5,
    }
    torch.save(state, q.checkpoint_path(cell, "bestval"))
    row = dict(q.vp.result_ledger_fields(payload), status="done", run_id=rid)
    runtime.rows[rid] = row
    assert q.proof_state(cell, "bestval") == ("complete", "")
    row["best_epoch"] = 4
    assert q.proof_state(cell, "bestval") == (
        "conflict", "ledger/result best_epoch differs")
    row["best_epoch"] = 1
    state["best_epoch"] = 4
    torch.save(state, q.checkpoint_path(cell, "bestval"))
    assert "best.ckpt best_epoch" in q.proof_state(cell, "bestval")[1]
    state["best_epoch"] = 1
    torch.save(state, q.checkpoint_path(cell, "bestval"))
    payload.pop("acceptance_eligible")
    path.write_text(json.dumps(payload))
    assert "acceptance_eligible" in q.proof_state(cell, "bestval")[1]


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
    payload = result_payload(cell)
    write_result(cell, payload)
    write_plateau(cell, payload)
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


def test_new_cell_waits_at_exclusive_boundary_with_rate_limited_log(
        runtime, tmp_path, monkeypatch):
    cell = make_cell()
    flag = tmp_path / "EXCLUSIVE_AIDO"
    flag.write_text("active")
    monkeypatch.setattr(q, "EXCLUSIVE_AIDO", flag)
    sleeps = []

    def fake_sleep(seconds):
        sleeps.append(seconds)
        if len(sleeps) == 2:
            flag.unlink()

    def fake_run(*args, **kwargs):
        assert not flag.exists()
        return SimpleNamespace(returncode=9)

    monkeypatch.setattr(q.time, "sleep", fake_sleep)
    monkeypatch.setattr(q.subprocess, "run", fake_run)
    outcome = q.run_cell(cell)
    assert outcome["status"] == "failed"
    assert sleeps == [q.EXCLUSIVE_POLL_S, q.EXCLUSIVE_POLL_S]
    text = Path(outcome["log_path"]).read_text()
    assert text.count("WAIT EXCLUSIVE_AIDO") == 1


def test_exclusive_wait_rechecks_proof_from_detached_old_child(
        runtime, tmp_path, monkeypatch):
    cell = make_cell()
    flag = tmp_path / "EXCLUSIVE_AIDO"
    flag.write_text("active")
    monkeypatch.setattr(q, "EXCLUSIVE_AIDO", flag)

    def old_child_finished(_seconds):
        make_double_proof(runtime, cell)
        flag.unlink()

    monkeypatch.setattr(q.time, "sleep", old_child_finished)
    monkeypatch.setattr(q.subprocess, "run",
                        lambda *args, **kwargs: pytest.fail("must not duplicate child"))
    outcome = q.run_cell(cell)
    assert outcome["status"] == "skipped" and outcome["ok"]


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


def test_verify_complete_is_read_only_and_requires_all_342_double_proofs(
        runtime, monkeypatch, capsys):
    cells = q.canonical_cells()
    assert len(cells) == 342
    for cell in cells:
        make_double_proof(runtime, cell)
    monkeypatch.setattr(
        q.subprocess, "run",
        lambda *args, **kwargs: pytest.fail("verify-complete launched training"))

    assert q.main(["--verify-complete"]) == 0
    assert "CORRECTED_3TASK_VERIFY_COMPLETE tasks=3 cells=342" in capsys.readouterr().out

    missing = cells[-1]
    runtime.rows[q.rid_for(missing)]["status"] = "running"
    assert q.main(["--verify-complete"]) == 1
    output = capsys.readouterr().out
    assert "CORRECTED_3TASK_VERIFY_INCOMPLETE tasks=3 cells=342 complete=341 incomplete=1" in output
    assert not q.LOG_ROOT.exists()


def test_proof_rejects_missing_plateau_and_legacy_train_only(runtime):
    cell = make_cell()
    payload = result_payload(cell)
    mark_done(runtime, cell, payload)
    write_result(cell, payload)
    state, reason = q.proof_state(cell)
    assert state == "conflict" and "plateau.json is missing" in reason

    q.plateau_path(cell).write_text(json.dumps({
        "protocol": "valplateau_v1", "epoch_train_losses": [0.5] * 6,
    }))
    state, reason = q.proof_state(cell)
    assert state == "conflict" and "protocol mismatch" in reason


def test_proof_rejects_flat_train_but_still_improving_validation(runtime):
    cell = make_cell()
    payload = result_payload(
        cell, epoch_train_losses=[0.5] * 6,
        epoch_val_losses=[1.0, 0.8, 0.6, 0.4, 0.2, 0.1])
    mark_done(runtime, cell, payload)
    write_result(cell, payload)
    write_plateau(cell, payload)
    state, reason = q.proof_state(cell)
    assert state == "conflict"
    assert "validation curve is not converged" in reason


def test_old_corrected_result_cannot_satisfy_new_rid(runtime):
    cell = make_cell()
    args = SimpleNamespace(lr=cell.lr, rank=8, n_train=0,
                           epochs=cell.epochs, smoke=False)
    old_extra = q.runner_for(cell)._run_extra(args)
    old_rid = q.ledger.run_id(cell.model, cell.task, cell.strategy, cell.seed,
                              cell.split, extra=old_extra)
    old_dir = q.ARTIFACTS_ROOT / old_rid
    old_dir.mkdir(parents=True)
    (old_dir / "result.json").write_text(json.dumps(result_payload(cell)))
    runtime.rows[old_rid] = {"run_id": old_rid, "status": "done"}

    assert old_rid != q.rid_for(cell)
    assert not q.result_path(cell).exists()
    assert q.proof_state(cell)[0] == "runnable"


def test_proof_requires_tokenizer_cuda_and_ledger_validation_evidence(runtime):
    cell = make_cell()
    payload = result_payload(cell, runtime=None)
    mark_done(runtime, cell, payload)
    write_result(cell, payload)
    write_plateau(cell, payload)
    state, reason = q.proof_state(cell)
    assert state == "conflict" and "runtime evidence is missing" in reason

    make_double_proof(runtime, cell)
    runtime.rows[q.rid_for(cell)]["epoch_val_losses"] = [1.0]
    state, reason = q.proof_state(cell)
    assert state == "conflict" and "ledger/result validation curves differ" in reason
