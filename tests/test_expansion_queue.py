import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import expansion_queue as q


VAL_LOSSES = [1.0, 0.8, 0.62, 0.61, 0.605, 0.602]


def job_dict(tmp_path, **updates):
    value = {
        "task": "degradation", "model": "RNA-FM", "strategy": "lora",
        "split": "random", "seed": 17, "lr": "3e-4", "rank": 8,
        "n_train": 0, "protocol": q.vp.PROTOCOL,
        "module": "rnafteval.finetune_regbase",
        "args": ["--converge", "--lr", "3e-4", "--rank", "8"],
        "rid": "ft_test_degradation_valplateau_v2",
        "result_dir": str(tmp_path / "artifacts" / "cell"), "need_gb": 8,
    }
    value.update(updates)
    return value


def make_job(tmp_path, **updates):
    return q._parse_job(job_dict(tmp_path, **updates), 0)


def result_dict(job, **updates):
    value = {
        "run_id": job.rid, "model": job.model, "task": job.task,
        "strategy": job.strategy, "seed": job.seed, "split": job.split,
        "protocol": q.vp.PROTOCOL, "loss_source": "validation",
        "status": "CONVERGED", "stop_reason": q.vp.STOP_REASON,
        "value": 0.75, "n_train": 100, "n_val": 20, "smoke": False,
        "acceptance_eligible": True, "epoch_val_losses": VAL_LOSSES,
        "epoch_train_losses": [0.5] * len(VAL_LOSSES),
        "epochs_trained": len(VAL_LOSSES),
        "min_delta": q.vp.MIN_DELTA, "patience": q.vp.PATIENCE,
        "abs_floor": q.vp.ABS_FLOOR,
        "runtime": {
            "cuda_available": True, "cuda_device": "cuda:0",
            "cuda_device_name": "mock RTX 5090", "cuda_runtime_version": "test",
            "tokenizer_class": "mock.Tokenizer",
            "tokenizer_name_or_path": "mock-tokenizer",
            "tokenizer_vocab_size": 12,
        },
    }
    value.update(updates)
    return value


@pytest.fixture
def proof_env(tmp_path, monkeypatch):
    job = make_job(tmp_path)
    rows = {}
    monkeypatch.setattr(q.ledger, "by_run_id", lambda rid: rows.get(rid))
    monkeypatch.setattr(q.torch.cuda, "mem_get_info", lambda device: (32 * q.GI, 32 * q.GI))
    monkeypatch.setenv("RNAFT_CODE_GIT_SHA", "test-sha")
    return SimpleNamespace(job=job, rows=rows)


def write_proof(env, result_updates=None, plateau_updates=None, ledger_updates=None):
    job = env.job
    result = result_dict(job, **(result_updates or {}))
    job.result_dir and Path(job.result_dir).mkdir(parents=True, exist_ok=True)
    job.result_path.write_text(json.dumps(result))
    plateau = {
        "run_id": job.rid, "protocol": q.vp.PROTOCOL,
        "loss_source": "validation", "status": "CONVERGED",
        "stop_reason": q.vp.STOP_REASON, "min_delta": q.vp.MIN_DELTA,
        "patience": q.vp.PATIENCE, "abs_floor": q.vp.ABS_FLOOR,
        "epoch_val_losses": result["epoch_val_losses"],
        "epoch_train_losses": result["epoch_train_losses"],
        "updated_epoch": len(result["epoch_val_losses"]) - 1,
    }
    plateau.update(plateau_updates or {})
    job.plateau_path.write_text(json.dumps(plateau))
    row = {
        "run_id": job.rid, "status": "done", "protocol": q.vp.PROTOCOL,
        "stop_reason": q.vp.STOP_REASON, "convergence_status": "CONVERGED",
        "epoch_val_losses": result["epoch_val_losses"],
        "epoch_train_losses": result["epoch_train_losses"],
    }
    row.update(ledger_updates or {})
    env.rows[job.rid] = row
    return result


def test_job_key_covers_all_cell_dimensions_and_duplicate_rids(tmp_path):
    path = tmp_path / "jobs.json"
    original = job_dict(tmp_path)
    path.write_text(json.dumps([original]))
    jobs = q.load_jobs(path)
    assert len(jobs[0].job_key) == 64
    for key, value in (("model", "other"), ("task", "ssi"),
                       ("strategy", "full"), ("split", "family"),
                       ("seed", 29), ("lr", "1e-5"), ("rank", 16),
                       ("n_train", 100), ("protocol", "e6-forgetting")):
        changed = dict(original)
        changed[key] = value
        if key == "protocol":
            value = q.vp.BESTVAL_PROTOCOL
            changed[key] = value
        changed_path = tmp_path / (key + ".json")
        changed_path.write_text(json.dumps([changed]))
        assert q.load_jobs(changed_path)[0].job_key != jobs[0].job_key
    path.write_text(json.dumps([original, original]))
    with pytest.raises(q.RegistryError, match="duplicate job_key"):
        q.load_jobs(path)


def test_only_complete_proof_can_done_skip(proof_env, monkeypatch):
    job = proof_env.job
    write_proof(proof_env, ledger_updates={"status": "invalid"})
    monkeypatch.setattr(q.subprocess, "Popen",
                        lambda *args, **kwargs: pytest.fail("must not launch"))
    assert q.dispatch([job], state_dir=Path(job.result_dir).parent / "state") == 1
    write_proof(proof_env)
    state_dir = Path(job.result_dir).parent / "complete-state"
    assert q.dispatch([job], state_dir=state_dir) == 0
    records = [json.loads(line) for line in (state_dir / "manifest.jsonl").read_text().splitlines()]
    assert records[-1]["status"] == "skipped"
    assert records[-1]["reason"] == "complete proof"


@pytest.mark.parametrize("ledger_status", ["cancelled", "invalid", "legacy"])
def test_non_done_ledger_status_is_not_done_skip(proof_env, ledger_status):
    write_proof(proof_env, ledger_updates={"status": ledger_status})
    state, reason = q.proof_state(proof_env.job)
    assert state == "conflict" and "ledger is not done" in reason


@pytest.mark.parametrize("mutation,match", [
    ({"smoke": True}, "smoke"),
    ({"protocol": "valplateau_v1"}, "protocol"),
    ({"status": "RUNNING"}, "status"),
    ({"runtime": {"cuda_available": True, "cuda_device": "cpu",
                  "cuda_device_name": "CPU", "tokenizer_class": "mock",
                  "tokenizer_name_or_path": "mock", "tokenizer_vocab_size": 12}},
     "not CUDA"),
    ({"runtime": None}, "runtime evidence"),
])
def test_bad_result_evidence_is_rejected(proof_env, mutation, match):
    write_proof(proof_env, result_updates=mutation)
    state, reason = q.proof_state(proof_env.job)
    assert state == "conflict" and match in reason


@pytest.mark.parametrize("runtime_updates,match", [
    ({"cuda_available": False}, "CUDA availability"),
    ({"cuda_device": "cpu"}, "not CUDA"),
    ({"cuda_device_name": ""}, "device name"),
    ({"tokenizer_class": ""}, "tokenizer_class"),
    ({"tokenizer_name_or_path": ""}, "tokenizer_name_or_path"),
    ({"tokenizer_vocab_size": 0}, "tokenizer_vocab_size"),
])
def test_incomplete_cuda_or_tokenizer_runtime_is_rejected(
        proof_env, runtime_updates, match):
    result = result_dict(proof_env.job)
    result["runtime"].update(runtime_updates)
    write_proof(proof_env, result_updates={"runtime": result["runtime"]})
    state, reason = q.proof_state(proof_env.job)
    assert state == "conflict" and match in reason


def test_mismatched_curve_and_missing_ledger_evidence_are_rejected(proof_env):
    result = write_proof(proof_env, plateau_updates={
        "epoch_val_losses": list(VAL_LOSSES[:-1]) + [0.5]})
    state, reason = q.proof_state(proof_env.job)
    assert state == "conflict" and "epoch_val_losses differ" in reason
    write_proof(proof_env, ledger_updates={"epoch_val_losses": [1.0]})
    state, reason = q.proof_state(proof_env.job)
    assert state == "conflict" and "ledger/result epoch_val_losses differ" in reason
    write_proof(proof_env, ledger_updates={"convergence_status": "RUNNING"})
    state, reason = q.proof_state(proof_env.job)
    assert state == "conflict" and "convergence_status" in reason


def test_done_ledger_with_bad_result_is_conflict_not_skip(proof_env):
    write_proof(proof_env, result_updates={"value": float("nan")})
    state, reason = q.proof_state(proof_env.job)
    assert state == "conflict" and "finite" in reason


def test_e6_forgetting_does_not_require_generic_value(proof_env):
    job = make_job(Path(proof_env.job.result_dir).parents[1],
                   task="e6-forgetting", rid="ft_e6_test",
                   result_dir=str(Path(proof_env.job.result_dir).parent / "e6"))
    proof_env.job = job
    write_proof(proof_env, result_updates={"value": None, "n_train": None})
    assert q.proof_state(job)[0] == "complete"


def test_nonexistent_result_dir_fake_proof_is_rejected(proof_env):
    proof_env.rows[proof_env.job.rid] = {
        "run_id": proof_env.job.rid, "status": "done",
        "protocol": q.vp.PROTOCOL, "convergence_status": "CONVERGED",
        "stop_reason": q.vp.STOP_REASON, "epoch_val_losses": VAL_LOSSES,
    }
    assert not Path(proof_env.job.result_dir).exists()
    state, reason = q.proof_state(proof_env.job)
    assert state == "conflict" and "missing" in reason
    assert q.verify_jobs([proof_env.job]) == 1


def test_dry_run_prints_commands_without_process_or_writes(tmp_path, monkeypatch, capsys):
    jobs_path = tmp_path / "jobs.json"
    jobs_path.write_text(json.dumps([job_dict(tmp_path)]))
    monkeypatch.setattr(q.subprocess, "Popen",
                        lambda *args, **kwargs: pytest.fail("dry-run launched process"))
    monkeypatch.setattr(q.subprocess, "run",
                        lambda *args, **kwargs: pytest.fail("dry-run launched process"))
    monkeypatch.setattr(q.subprocess, "check_output",
                        lambda *args, **kwargs: pytest.fail("dry-run ran git"))
    monkeypatch.setattr(q.torch.cuda, "mem_get_info",
                        lambda device: pytest.fail("dry-run queried GPU"))
    monkeypatch.setattr(q.ledger, "by_run_id",
                        lambda rid: pytest.fail("dry-run read ledger"))
    state_dir = tmp_path / "must-not-exist"
    assert q.main(["--jobs-json", str(jobs_path), "--dry-run",
                   "--device", "2", "--state-dir", str(state_dir)]) == 0
    output = capsys.readouterr().out
    assert "--device 2" in output and "need_gb" in output and "unique" in output
    assert not state_dir.exists()
    assert not Path(job_dict(tmp_path)["result_dir"]).exists()


class FakeProcess:
    def __init__(self, pid=4321, rc=0):
        self.pid = pid
        self.rc = rc
        self.returncode = None

    def poll(self):
        self.returncode = self.rc
        return self.returncode


def test_running_worker_manifest_has_all_fields_and_git_env(proof_env, monkeypatch):
    seen = {}
    process = FakeProcess(rc=9)

    def fake_popen(command, **kwargs):
        seen.update(command=command, kwargs=kwargs)
        return process

    monkeypatch.setenv("RNAFT_CODE_GIT_SHA", "abc123")
    monkeypatch.setattr(q.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(q.time, "sleep", lambda seconds: None)
    state_dir = Path(proof_env.job.result_dir).parent / "run-state"
    assert q.dispatch([proof_env.job], workers=1, state_dir=state_dir,
                      poll_s=0.01) == 1
    rows = [json.loads(line) for line in (state_dir / "manifest.jsonl").read_text().splitlines()]
    running, failed = rows
    required = {"command", "job_key", "need_gb", "code_git_sha", "pid",
                "start", "end", "rc", "log", "result_dir", "status", "reason"}
    assert required <= set(running) and required <= set(failed)
    assert running["status"] == "running" and running["pid"] == 4321
    assert running["start"] and running["code_git_sha"] == "abc123"
    assert running["command"] == seen["command"] and running["need_gb"] == 8
    assert failed["status"] == "failed" and failed["rc"] == 9
    assert failed["end"] and "exited 9" in failed["reason"]
    assert seen["kwargs"]["env"]["RNAFT_CODE_GIT_SHA"] == "abc123"
    assert Path(failed["log"]).exists()


def test_rc_zero_without_complete_proof_is_failure(proof_env, monkeypatch):
    monkeypatch.setattr(q.subprocess, "Popen", lambda *a, **k: FakeProcess(rc=0))
    monkeypatch.setattr(q.time, "sleep", lambda seconds: None)
    state_dir = Path(proof_env.job.result_dir).parent / "zero-state"
    assert q.dispatch([proof_env.job], state_dir=state_dir, poll_s=0.01) == 1
    row = json.loads((state_dir / "manifest.jsonl").read_text().splitlines()[-1])
    assert row["status"] == "failed" and row["rc"] == 0
    assert "proof is runnable" in row["reason"]


def test_claim_blocked_75_is_recorded_as_skip(proof_env, monkeypatch):
    monkeypatch.setattr(q.subprocess, "Popen", lambda *a, **k: FakeProcess(rc=75))
    monkeypatch.setattr(q.time, "sleep", lambda seconds: None)
    state_dir = Path(proof_env.job.result_dir).parent / "blocked-state"
    assert q.dispatch([proof_env.job], state_dir=state_dir, poll_s=0.01) == 0
    row = json.loads((state_dir / "manifest.jsonl").read_text().splitlines()[-1])
    assert row["status"] == "skipped" and row["rc"] == 75
    assert "claim blocked" in row["reason"]


def test_running_ledger_does_not_start_duplicate(proof_env, monkeypatch):
    proof_env.rows[proof_env.job.rid] = {"run_id": proof_env.job.rid, "status": "running"}
    monkeypatch.setattr(q.subprocess, "Popen",
                        lambda *a, **k: pytest.fail("running job duplicated"))
    state_dir = Path(proof_env.job.result_dir).parent / "running-state"
    assert q.dispatch([proof_env.job], state_dir=state_dir) == 0
    row = json.loads((state_dir / "manifest.jsonl").read_text().splitlines()[-1])
    assert row["status"] == "skipped" and "refusing duplicate" in row["reason"]


def test_same_model_jobs_wait_for_own_inflight_process(proof_env, monkeypatch):
    root = Path(proof_env.job.result_dir).parents[1]
    second = make_job(root, seed=29, rid="ft_test_second",
                      result_dir=str(root / "artifacts" / "second"))
    started = []

    def fake_popen(command, **kwargs):
        started.append(command)
        return FakeProcess(pid=4000 + len(started), rc=75)

    monkeypatch.setattr(q.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(q.time, "sleep", lambda seconds: None)
    state_dir = root / "same-model-state"
    assert q.dispatch([proof_env.job, second], workers=2,
                      state_dir=state_dir, poll_s=0.01) == 0
    assert len(started) == 2
    rows = [json.loads(line) for line in
            (state_dir / "manifest.jsonl").read_text().splitlines()]
    assert [row["status"] for row in rows].count("skipped") == 2


def test_other_models_bypass_same_model_head_of_line_wait(proof_env, monkeypatch):
    root = Path(proof_env.job.result_dir).parents[1]
    second = make_job(root, seed=29, rid="ft_test_second",
                      result_dir=str(root / "artifacts" / "second"))
    third = make_job(root, model="ERNIE-RNA", rid="ft_test_third",
                     result_dir=str(root / "artifacts" / "third"))
    started = []

    class BlockingProcess:
        def __init__(self, pid):
            self.pid = pid
            self.polls = 0

        def poll(self):
            self.polls += 1
            return 75 if len(started) >= 2 or self.polls >= 3 else None

    def fake_popen(command, **kwargs):
        started.append(command)
        return BlockingProcess(5000 + len(started))

    monkeypatch.setattr(q.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(q.time, "sleep", lambda seconds: None)
    state_dir = root / "other-model-state"
    assert q.dispatch([proof_env.job, second, third], workers=2,
                      state_dir=state_dir, poll_s=0.01) == 0
    models = [command[command.index("--model") + 1] for command in started]
    assert models == ["RNA-FM", "ERNIE-RNA", "RNA-FM"]


BESTVAL_LOSSES = [1.0, 0.8, 0.8, 0.8, 0.8]


def write_bestval_proof(env, result_updates=None, plateau_updates=None,
                        ledger_updates=None):
    job = env.job
    result = result_dict(
        job, protocol=q.vp.BESTVAL_PROTOCOL,
        stop_reason=q.vp.BESTVAL_STOP_REASON,
        epoch_val_losses=BESTVAL_LOSSES,
        epoch_train_losses=[0.5] * len(BESTVAL_LOSSES),
        epochs_trained=len(BESTVAL_LOSSES), best_epoch=1, best_val=0.8,
        best_checkpoint="best.ckpt", stale_epochs=3)
    result.update(result_updates or {})
    Path(job.result_dir).mkdir(parents=True, exist_ok=True)
    job.result_path.write_text(json.dumps(result))
    checkpoint = Path(job.result_dir) / "best.ckpt"
    torch.save({"backbone": {"weight": torch.ones(2, 2)},
                "head": {"weight": torch.ones(1, 2)},
                "epoch": result["best_epoch"],
                "best_epoch": result["best_epoch"],
                "best_val": result["best_val"]}, checkpoint)
    plateau = {
        "run_id": job.rid, "protocol": q.vp.BESTVAL_PROTOCOL,
        "loss_source": "validation", "status": "CONVERGED",
        "stop_reason": q.vp.BESTVAL_STOP_REASON,
        "min_delta": q.vp.MIN_DELTA, "patience": q.vp.PATIENCE,
        "abs_floor": q.vp.ABS_FLOOR,
        "epoch_val_losses": result["epoch_val_losses"],
        "epoch_train_losses": result["epoch_train_losses"],
        "updated_epoch": len(result["epoch_val_losses"]) - 1,
        "best_epoch": result.get("best_epoch"), "best_val": result.get("best_val"),
        "best_checkpoint": result.get("best_checkpoint"),
        "stale_epochs": result.get("stale_epochs"),
    }
    plateau.update(plateau_updates or {})
    job.plateau_path.write_text(json.dumps(plateau))
    env.rows[job.rid] = {
        "run_id": job.rid, "status": "done", "protocol": q.vp.BESTVAL_PROTOCOL,
        "stop_reason": q.vp.BESTVAL_STOP_REASON,
        "convergence_status": "CONVERGED",
        "epoch_val_losses": result["epoch_val_losses"],
        "epoch_train_losses": result["epoch_train_losses"],
        "best_epoch": result.get("best_epoch"), "best_val": result.get("best_val"),
        "best_checkpoint": result.get("best_checkpoint"),
        "stale_epochs": result.get("stale_epochs"),
    }
    env.rows[job.rid].update(ledger_updates or {})
    return result


def test_bestval_complete_checkpoint_proof(proof_env):
    proof_env.job = make_job(
        Path(proof_env.job.result_dir).parents[1], protocol=q.vp.BESTVAL_PROTOCOL,
        rid="ft_bestval_test", result_dir=proof_env.job.result_dir + "-bestval")
    write_bestval_proof(proof_env)
    assert q.proof_state(proof_env.job) == ("complete", "")


@pytest.mark.parametrize("result_updates,match", [
    ({"best_epoch": None}, "best_epoch"),
    ({"best_val": None}, "best_val"),
    ({"best_checkpoint": None}, "best_checkpoint"),
    ({"best_checkpoint": "missing.ckpt"}, "missing or empty"),
    ({"best_checkpoint": "../outside.ckpt"}, "escapes result_dir"),
    ({"stop_reason": q.vp.STOP_REASON}, "stop_reason"),
    ({"best_epoch": 0, "best_val": 1.0}, "stopping rule"),
])
def test_bestval_bad_result_proof_is_rejected(proof_env, result_updates, match):
    proof_env.job = make_job(
        Path(proof_env.job.result_dir).parents[1], protocol=q.vp.BESTVAL_PROTOCOL,
        rid="ft_bestval_test", result_dir=proof_env.job.result_dir + "-bestval")
    write_bestval_proof(proof_env, result_updates=result_updates)
    state, reason = q.proof_state(proof_env.job)
    assert state == "conflict" and match in reason


@pytest.mark.parametrize("side", ["plateau", "ledger"])
def test_bestval_checkpoint_three_way_mismatch_is_rejected(proof_env, side):
    proof_env.job = make_job(
        Path(proof_env.job.result_dir).parents[1], protocol=q.vp.BESTVAL_PROTOCOL,
        rid="ft_bestval_test", result_dir=proof_env.job.result_dir + "-bestval")
    updates = {"best_checkpoint": "other.ckpt"}
    Path(proof_env.job.result_dir).mkdir(parents=True, exist_ok=True)
    (Path(proof_env.job.result_dir) / "other.ckpt").write_bytes(b"other")
    write_bestval_proof(proof_env, **{side + "_updates": updates})
    state, reason = q.proof_state(proof_env.job)
    assert state == "conflict" and "best_checkpoint" in reason


def test_bestval_requires_checkpoint_field_in_plateau_and_ledger(proof_env):
    proof_env.job = make_job(
        Path(proof_env.job.result_dir).parents[1], protocol=q.vp.BESTVAL_PROTOCOL,
        rid="ft_bestval_test", result_dir=proof_env.job.result_dir + "-bestval")
    write_bestval_proof(proof_env, plateau_updates={"best_checkpoint": None},
                        ledger_updates={"best_checkpoint": None})
    state, reason = q.proof_state(proof_env.job)
    assert state == "conflict" and "plateau/result best_checkpoint" in reason


def test_bestval_protocol_does_not_use_plateau_classifier(proof_env, monkeypatch):
    proof_env.job = make_job(
        Path(proof_env.job.result_dir).parents[1], protocol=q.vp.BESTVAL_PROTOCOL,
        rid="ft_bestval_test", result_dir=proof_env.job.result_dir + "-bestval")
    write_bestval_proof(proof_env)
    monkeypatch.setattr(q.vp, "classify",
                        lambda losses: pytest.fail("bestval used plateau classifier"))
    assert q.proof_state(proof_env.job)[0] == "complete"


def test_custom_patience_is_used_by_protocol_audit(proof_env):
    proof_env.job = make_job(
        Path(proof_env.job.result_dir).parents[1], protocol=q.vp.BESTVAL_PROTOCOL,
        rid="ft_bestval_test", result_dir=proof_env.job.result_dir + "-bestval",
        args=["--converge", "--patience", "4"])
    write_bestval_proof(proof_env, result_updates={"patience": 4},
                        plateau_updates={"patience": 4})
    state, reason = q.proof_state(proof_env.job)
    assert state == "conflict" and "patience not exhausted" in reason


def test_complementary_registry_excludes_specialized_lane_cells(tmp_path):
    import expansion_jobs as registry
    output = tmp_path / "jobs.json"
    assert registry.main(["--output", str(output)]) == 0
    jobs = json.loads(output.read_text())
    assert len(jobs) == 324
    cells = {(j["model"], j["task"], j["strategy"]) for j in jobs}
    assert not any(task in ("mrl", "modification") and strategy in ("lora", "full")
                   for _model, task, strategy in cells)
    assert ("RiNALMo-micro", "noncoding-rna-family", "lora") not in cells
    assert ("RiNALMo-micro", "noncoding-rna-family", "full") in cells
    assert len({j["rid"] for j in jobs}) == len(jobs)
    assert all("_bestval_v1" in j["rid"] for j in jobs)


def test_complementary_registry_supports_perbase_bestval_main_matrix(tmp_path):
    import expansion_jobs as registry
    output = tmp_path / "perbase-jobs.json"
    assert registry.main(["--output", str(output), "--lane", "all",
                          "--tasks", "spliceai,degradation,ssi"]) == 0
    jobs = json.loads(output.read_text())
    assert len(jobs) == 270
    assert len({j["rid"] for j in jobs}) == len(jobs)
    assert len({j["result_dir"] for j in jobs}) == len(jobs)
    assert all(j["protocol"] == "bestval_v1" for j in jobs)
    modules = {j["task"]: j["module"] for j in jobs}
    assert modules == {
        "spliceai": "rnafteval.finetune_spl",
        "degradation": "rnafteval.finetune_regbase",
        "ssi": "rnafteval.finetune_regbase",
    }


def test_c5c_registry_supports_frozen_only(tmp_path):
    import expansion_jobs as registry
    output = tmp_path / "c5c-frozen-jobs.json"
    assert registry.main(["--output", str(output), "--wave", "c5c-all",
                          "--strategies", "frozen"]) == 0
    jobs = json.loads(output.read_text())
    assert len(jobs) == 1008
    assert len({j["rid"] for j in jobs}) == len(jobs)
    assert {j["strategy"] for j in jobs} == {"frozen"}
    assert {j["lr"] for j in jobs} == {"3e-4"}
    mega_ncrna = next(j for j in jobs if j["model"] == "RiNALMo-mega" and
                      j["task"] == "noncoding-rna-family")
    assert "--batch-size" in mega_ncrna["args"]
    assert mega_ncrna["args"][mega_ncrna["args"].index("--batch-size") + 1] == "16"


def test_equivalence_rnasc_registry_uses_controlled_pair_and_lr(tmp_path):
    import expansion_jobs as registry
    output = tmp_path / "equivalence-rnasc-jobs.json"
    assert registry.main(["--output", str(output), "--wave", "equivalence-rnasc"]) == 0
    jobs = json.loads(output.read_text())
    assert len(jobs) == 672
    assert len({j["rid"] for j in jobs}) == len(jobs)
    assert len({j["result_dir"] for j in jobs}) == len(jobs)
    assert {j["model"] for j in jobs} == {"RNA-Sc-30M", "RNA-Sc-650M"}
    assert {j["task"] for j in jobs} == set(registry.METRICS)
    assert all(j["strategy"] == "full" and j["lr"] == "3e-5"
               for j in jobs if j["model"] == "RNA-Sc-30M")
    assert all(j["strategy"] == "lora" and j["lr"] == "3e-4"
               for j in jobs if j["model"] == "RNA-Sc-650M")
    assert all(j["dense_clusters"] ==
               (j["task"] == "noncoding-rna-family" and j["split"] == "family")
               for j in jobs)
    assert all(j["module"] == "rnafteval.finetune_one"
               for j in jobs if j["task"] == "noncoding-rna-family")


def test_external_memory_release_is_wait_not_permanent_failure(proof_env, monkeypatch):
    readings = iter([(4 * q.GI, 32 * q.GI), (4 * q.GI, 32 * q.GI),
                     (20 * q.GI, 32 * q.GI), (20 * q.GI, 32 * q.GI)])
    monkeypatch.setattr(q.torch.cuda, "mem_get_info", lambda device: next(readings))
    monkeypatch.setattr(q.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(q.subprocess, "Popen", lambda *a, **k: FakeProcess(rc=9))
    state_dir = Path(proof_env.job.result_dir).parent / "memory-wait-state"
    assert q.dispatch([proof_env.job], state_dir=state_dir, poll_s=0.01) == 1
    rows = [json.loads(x) for x in (state_dir / "manifest.jsonl").read_text().splitlines()]
    assert rows[0]["status"] == "running"
    assert rows[-1]["status"] == "failed" and "exited 9" in rows[-1]["reason"]
    assert "initial free budget" not in rows[-1]["reason"]


def test_need_above_total_device_is_rejected_before_launch(proof_env, monkeypatch):
    proof_env.job.need_gb = 40
    monkeypatch.setattr(q.torch.cuda, "mem_get_info", lambda device: (20 * q.GI, 32 * q.GI))
    monkeypatch.setattr(q.subprocess, "Popen",
                        lambda *a, **k: pytest.fail("impossible job launched"))
    state_dir = Path(proof_env.job.result_dir).parent / "memory-total-state"
    assert q.dispatch([proof_env.job], state_dir=state_dir) == 1
    row = json.loads((state_dir / "manifest.jsonl").read_text().splitlines()[-1])
    assert row["status"] == "failed" and "exceeds total device memory" in row["reason"]


def test_artifact_root_env_is_shared_by_registry_and_runners(tmp_path):
    root = str(tmp_path / "team-artifacts")
    env = dict(os.environ, PYTHONPATH=str(ROOT), RNAFT_ARTIFACT_ROOT=root)
    code = (
        "from rnafteval import ledger; "
        "from scripts import expansion_jobs; "
        "j=expansion_jobs.job_for('mrl','RiNALMo-micro','lora','random',17); "
        "print(ledger.ARTIFACT_ROOT); print(j['result_dir'])"
    )
    lines = subprocess.check_output([sys.executable, "-c", code], env=env,
                                    cwd=ROOT, text=True).splitlines()
    assert lines == [root, root + "/ft_rinalmomicro_mrl_lora_s17_random_bestval_v1"]


@pytest.mark.parametrize("module,task", [
    ("rnafteval.finetune_clf", "crispr-off-target"),
    ("rnafteval.finetune_regbase", "degradation"),
    ("rnafteval.finetune_regbase", "ssi"),
])
def test_task_specific_runners_receive_explicit_task(tmp_path, module, task):
    job = make_job(tmp_path, module=module, task=task)
    command = job.build_command(device=0)
    assert command[command.index("--task") + 1] == task
