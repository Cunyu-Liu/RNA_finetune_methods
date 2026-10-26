import json
from types import SimpleNamespace

import pytest
import torch

import valplateau as vp
from rnafteval import valplateau as convergence


def write_v2(result_dir, val_losses, train_losses=None, status="CONVERGED",
             stop_reason=vp.STOP_REASON):
    result_dir.mkdir(parents=True, exist_ok=True)
    if train_losses is None:
        train_losses = [1.0] * len(val_losses)
    common = {
        "protocol": vp.PROTOCOL,
        "loss_source": "validation",
        "epoch_train_losses": train_losses,
        "epoch_val_losses": val_losses,
        "epochs_trained": len(val_losses),
        "status": status,
        "stop_reason": stop_reason, "min_delta": vp.MIN_DELTA,
        "patience": vp.PATIENCE, "abs_floor": vp.ABS_FLOOR,
    }
    (result_dir / "result.json").write_text(json.dumps(common))
    plateau = dict(common)
    plateau.pop("epochs_trained")
    plateau["updated_epoch"] = len(val_losses) - 1
    (result_dir / "plateau.json").write_text(json.dumps(plateau))


def test_converged_flat_tail():
    s, d = vp.classify([1.0, 0.8, 0.62, 0.61, 0.605, 0.602])
    assert s == "CONVERGED", d


def test_converged_low_loss_oscillation_dual_criteria():
    s, detail = vp.classify([1.0, 0.5, 0.2, 0.05, 0.0209, 0.015, 0.0131])
    assert s == "CONVERGED", detail


def test_not_converged_low_loss_still_large_drops():
    s, _ = vp.classify([1.0, 0.5, 0.2, 0.06, 0.05, 0.03, 0.01])
    assert s == "NOT_CONVERGED"


def test_not_converged_still_improving():
    s, _ = vp.classify([1.0, 0.8, 0.6, 0.4, 0.2, 0.1])
    assert s == "NOT_CONVERGED"


def test_too_short_empty_nan_and_non_numeric():
    assert vp.classify([])[0] == "EMPTY"
    assert vp.classify([0.5])[0] == "TOO_SHORT"
    assert vp.classify([1.0, float("nan"), 0.5, 0.5, 0.5])[0] == "INVALID"
    assert vp.classify([1.0, "0.5", 0.5, 0.5, 0.5])[0] == "INVALID"


def test_legacy_without_plateau(tmp_path):
    (tmp_path / "result.json").write_text("{}")
    cell, status, _ = vp.audit_cell(str(tmp_path), 0.02, 3)
    assert status == "LEGACY", (cell, status)


def test_no_result_json(tmp_path):
    cell, status, _ = vp.audit_cell(str(tmp_path), 0.02, 3)
    assert status == "NO_RESULT"


def test_v1_train_only_can_never_converge(tmp_path):
    (tmp_path / "result.json").write_text("{}")
    (tmp_path / "plateau.json").write_text(json.dumps({
        "protocol": "valplateau_v1",
        "epoch_train_losses": [1.0, 0.9, 0.85, 0.845, 0.844]}))
    _c, status, detail = vp.audit_cell(str(tmp_path), 0.02, 3)
    assert status == "TRAIN_ONLY"
    assert "epoch_train_losses" in detail


def test_v2_reads_validation_not_train_loss(tmp_path):
    write_v2(tmp_path, [1.0, 0.8, 0.6, 0.4, 0.2, 0.1],
             train_losses=[0.5] * 6, status="RUNNING", stop_reason=None)
    _c, status, detail = vp.audit_cell(str(tmp_path), 0.02, 3)
    assert status == "NOT_CONVERGED"
    assert detail.startswith("validation:")


def test_v2_converged_requires_result_and_plateau_agreement(tmp_path):
    write_v2(tmp_path, [1.0, 0.8, 0.62, 0.61, 0.605, 0.602])
    _c, status, _d = vp.audit_cell(str(tmp_path))
    assert status == "CONVERGED"

    result = json.loads((tmp_path / "result.json").read_text())
    result["epoch_val_losses"][-1] = 0.5
    (tmp_path / "result.json").write_text(json.dumps(result))
    _c, status, detail = vp.audit_cell(str(tmp_path))
    assert status == "INVALID"
    assert "curves differ" in detail


def test_v2_rejects_running_result_even_with_flat_plateau(tmp_path):
    write_v2(tmp_path, [1.0, 0.8, 0.62, 0.61, 0.605, 0.602])
    result = json.loads((tmp_path / "result.json").read_text())
    result["status"] = "RUNNING"
    (tmp_path / "result.json").write_text(json.dumps(result))
    _c, status, detail = vp.audit_cell(str(tmp_path))
    assert status == "NOT_CONVERGED"
    assert "result status" in detail



def test_v2_running_plateau_is_not_complete(tmp_path):
    write_v2(tmp_path, [1.0, 0.8, 0.62, 0.61, 0.605, 0.602],
             status="RUNNING", stop_reason=None)
    _c, status, _d = vp.audit_cell(str(tmp_path))
    assert status == "NOT_CONVERGED"


def test_wrong_protocol_rejected(tmp_path):
    (tmp_path / "result.json").write_text("{}")
    (tmp_path / "plateau.json").write_text(json.dumps({
        "protocol": "other", "epoch_val_losses": [1, 1, 1]}))
    _c, status, _d = vp.audit_cell(str(tmp_path), 0.02, 3)
    assert status == "INVALID"


def test_main_exit_code_only_v2_converged_is_success(tmp_path, capsys):
    good = tmp_path / "good_cell"
    write_v2(good, [1.0, 0.8, 0.62, 0.61, 0.605, 0.602])
    out = tmp_path / "report.json"
    rc = vp.main(["--e6-root", str(tmp_path), "--json-out", str(out)])
    assert rc == 0
    assert "CONVERGED" in capsys.readouterr().out
    data = json.loads(out.read_text())
    assert data[0]["status"] == "CONVERGED"


def test_main_train_only_is_nonzero(tmp_path, capsys):
    legacy = tmp_path / "legacy_cell"
    legacy.mkdir()
    (legacy / "result.json").write_text("{}")
    (legacy / "plateau.json").write_text(json.dumps({
        "protocol": "valplateau_v1", "epoch_train_losses": [1, 1, 1, 1]}))
    assert vp.main(["--e6-root", str(tmp_path)]) == 1
    output = capsys.readouterr().out
    assert "TRAIN_ONLY" in output and "CONVERGED" not in output


def test_main_accepts_single_cell_and_rejects_empty_root(tmp_path, capsys):
    write_v2(tmp_path, [1.0, 0.8, 0.62, 0.61, 0.605, 0.602])
    assert vp.main(["--e6-root", str(tmp_path)]) == 0
    assert "CONVERGED" in capsys.readouterr().out
    empty = tmp_path / "empty"
    empty.mkdir()
    assert vp.main(["--e6-root", str(empty)]) == 1
    assert "EMPTY" in capsys.readouterr().out


def test_tracker_epoch_zero_replaces_legacy_and_unbounded_loop_stops_on_val(
        tmp_path):
    stale = {
        "protocol": "valplateau_v1", "epoch_train_losses": [9.0, 8.0],
        "epoch_val_losses": [99.0], "updated_epoch": 99,
        "status": "CONVERGED", "stop_reason": "legacy",
    }
    (tmp_path / "plateau.json").write_text(json.dumps(stale))
    tracker = convergence.PlateauTracker(tmp_path, run_id="new-v2-rid")
    args = SimpleNamespace(converge=True, epochs=1)
    val_curve = iter([1.0, 0.8, 0.6, 0.62, 0.61, 0.605, 0.602])
    stopped = False
    for epoch in convergence.training_epochs(args):
        if tracker.record(epoch, 0.5, next(val_curve)):
            stopped = True
            break
    assert stopped
    assert epoch > args.epochs
    assert tracker.stop_reason == convergence.STOP_REASON
    saved = json.loads((tmp_path / "plateau.json").read_text())
    assert saved["run_id"] == "new-v2-rid"
    assert saved["protocol"] == "valplateau_v2"
    assert saved["loss_source"] == "validation"
    assert saved["epoch_train_losses"] == [0.5] * 7
    assert saved["epoch_val_losses"] == [1.0, 0.8, 0.6, 0.62, 0.61, 0.605, 0.602]
    assert saved["updated_epoch"] == 6
    assert saved["status"] == "CONVERGED"
    assert tracker.result_fields()["epochs_trained"] == 7


def test_tracker_train_flat_validation_decreasing_never_converges(tmp_path):
    tracker = convergence.PlateauTracker(tmp_path)
    args = SimpleNamespace(converge=True, epochs=2)
    for epoch in convergence.training_epochs(args):
        converged = tracker.record(epoch, 0.5, 1.0 / (epoch + 1))
        assert not converged
        if epoch == 7:
            break
    saved = json.loads((tmp_path / "plateau.json").read_text())
    assert saved["status"] == "RUNNING"
    assert saved["stop_reason"] is None
    assert saved["updated_epoch"] == 7


def test_tracker_nonfinite_validation_is_fatal(tmp_path):
    tracker = convergence.PlateauTracker(tmp_path)
    try:
        tracker.record(0, 0.5, float("nan"))
    except FloatingPointError:
        pass
    else:
        raise AssertionError("NaN validation loss must abort convergence")
    assert not (tmp_path / "plateau.json").exists()


def test_legacy_epoch_iterator_remains_fixed():
    assert list(convergence.training_epochs(
        SimpleNamespace(converge=False, epochs=3))) == [0, 1, 2]


def bestval_args(tmp_path, mode="bestval", converge=True):
    return SimpleNamespace(convergence_mode=mode, converge=converge,
                           patience=3, min_delta=0.02, epochs=1)


def overfitting_tracker(tmp_path, callback=None):
    saved = [] if callback is None else callback
    tracker = convergence.BestValTracker(
        tmp_path, run_id="bestval-rid",
        save_best=lambda **kwargs: saved.append(kwargs))
    for epoch in convergence.training_epochs(bestval_args(tmp_path)):
        stop = tracker.record(epoch, 1.0 / (epoch + 1),
                              [1.0, 0.5, 0.7, 0.8, 0.9, 0.2][epoch])
        if epoch == 4:
            assert stop
            break
    return tracker, saved


def test_bestval_overfit_stops_at_patience_and_selects_not_last(tmp_path):
    tracker, saved = overfitting_tracker(tmp_path)
    assert tracker.best_epoch == 1 and tracker.best_val == 0.5
    assert tracker.stale_epochs == 3
    assert len(tracker.val_losses) == 5 and len(saved) == 2
    assert tracker.val_losses[-1] != tracker.best_val
    assert tracker.stop_reason == convergence.BESTVAL_STOP_REASON
    plateau = json.loads((tmp_path / "plateau.json").read_text())
    result = tracker.result_fields()
    assert result["protocol"] == convergence.BESTVAL_PROTOCOL
    for key in ("best_epoch", "best_val", "stale_epochs", "status",
                "stop_reason", "epoch_val_losses"):
        assert plateau[key] == result[key]
    fields = convergence.result_ledger_fields(
        dict(result, run_id="bestval-rid"))
    assert fields["best_epoch"] == result["best_epoch"] == 1
    assert fields["convergence_status"] == "CONVERGED"
    assert "status" not in fields


def test_bestval_improvement_resets_stale_and_epoch_zero_resets(tmp_path):
    saved = []
    tracker = convergence.BestValTracker(
        tmp_path, save_best=lambda **kwargs: saved.append(kwargs))
    curve = [1.0, 0.5, 0.6, 0.7, 0.4, 0.5, 0.6, 0.7]
    stopped = [tracker.record(i, 0.1, value) for i, value in enumerate(curve)]
    assert stopped == [False] * 7 + [True]
    assert saved[2]["epoch"] == 4 and tracker.best_epoch == 4
    assert tracker.stale_epochs == 3 and len(saved) == 3
    tracker.record(0, 0.1, 2.0)
    assert tracker.best_epoch == 0 and tracker.stale_epochs == 0
    assert tracker.val_losses == [2.0] and tracker.status == "RUNNING"


def test_mocked_runner_saves_restores_then_tests_best_weights(tmp_path):
    calls = []
    core = torch.nn.Linear(2, 1)
    head = torch.nn.Linear(1, 1)
    args = bestval_args(tmp_path)

    def save_best(epoch, val_loss):
        calls.append(("save", epoch))
        convergence.save_best_checkpoint(
            tmp_path / "best.ckpt", core, head,
            epoch=epoch, best_epoch=epoch, best_val=val_loss)

    tracker = convergence.make_tracker(tmp_path, args, "rid", save_best)
    for epoch in convergence.training_epochs(args):
        with torch.no_grad():
            core.weight.fill_(epoch + 1)
            head.weight.fill_(epoch + 1)
        if tracker.record(epoch, 0.1, [1.0, 0.5, 0.7, 0.8, 0.9][epoch]):
            break
    if args.converge and args.convergence_mode == "bestval":
        convergence.restore_best_checkpoint(tracker, core, head)
        calls.append(("restore", tracker.best_epoch))
    calls.append(("test", float(core.weight[0, 0].detach()),
                  float(head.weight[0, 0].detach())))
    assert calls[:3] == [("save", 0), ("save", 1), ("restore", 1)]
    assert calls[-1] == ("test", 2.0, 2.0)
    assert calls.index(("restore", 1)) < len(calls) - 1


def test_bestval_requires_converge_at_startup_and_default_plateau_is_unchanged():
    with pytest.raises(ValueError, match="requires --converge"):
        convergence.validate_convergence_args(
            SimpleNamespace(convergence_mode="bestval", converge=False))
    convergence.validate_convergence_args(
        SimpleNamespace(convergence_mode="plateau", converge=False))
    assert convergence.protocol_tag(SimpleNamespace(converge=False)) == ""
    assert convergence.protocol_tag(
        SimpleNamespace(converge=True)) == "_valplateau_v2"
    assert convergence.protocol_tag(
        SimpleNamespace(converge=True, convergence_mode="bestval")) == "_bestval_v1"


def test_make_tracker_protocols_do_not_mix(tmp_path):
    plateau = convergence.make_tracker(
        tmp_path, bestval_args(tmp_path, mode="plateau"), "rid", None)
    assert type(plateau) is convergence.PlateauTracker
    bestval = convergence.make_tracker(
        tmp_path, bestval_args(tmp_path), "rid", lambda **kwargs: None)
    assert type(bestval) is convergence.BestValTracker


class _MWrapper:
    def __init__(self, model):
        self.m = model


class _LoraLike(torch.nn.Module):
    def __init__(self, model):
        super().__init__()
        self.base_model = model
        self.lora_A = torch.nn.Parameter(torch.zeros(2, 3))

    def forward(self, x):
        return self.base_model(x) + x @ self.lora_A.T

    def get_base_model(self):
        return self.base_model

    def state_dict(self, *args, **kwargs):
        return {"lora_A": self.lora_A.detach()}


@pytest.mark.parametrize("kind", ["full", "lora", "wrapper"])
def test_best_checkpoint_restores_best_not_last_weights(tmp_path, kind):
    torch.manual_seed(17)
    core = _LoraLike(torch.nn.Linear(3, 2)) if kind == "lora" \
        else torch.nn.Linear(3, 2)
    backbone = _MWrapper(core) if kind == "wrapper" else core
    head = torch.nn.Linear(2, 1)

    def save_best(epoch, val_loss):
        convergence.save_best_checkpoint(
            tmp_path / "best.ckpt", backbone, head,
            epoch=epoch, best_epoch=epoch, best_val=val_loss)

    tracker = convergence.BestValTracker(tmp_path, save_best=save_best)
    for epoch, value in enumerate([1.0, 0.5, 0.7, 0.8, 0.9]):
        with torch.no_grad():
            parameter = core.lora_A if kind == "lora" else core.weight
            parameter.fill_(epoch + 1)
            head.weight.fill_(epoch + 10)
        if tracker.record(epoch, 0.1, value):
            break
    parameter = core.lora_A if kind == "lora" else core.weight
    assert parameter.flatten()[0].item() == 5
    convergence.restore_best_checkpoint(tracker, backbone, head)
    assert torch.equal(parameter, torch.full_like(parameter, 2))
    assert torch.equal(head.weight, torch.full_like(head.weight, 11))
    evaluated_weight = core.lora_A.clone() if kind == "lora" else core.weight.clone()
    assert torch.equal(evaluated_weight, torch.full_like(evaluated_weight, 2))
    state = torch.load(tmp_path / "best.ckpt", map_location="cpu",
                       weights_only=True)
    assert state["best_epoch"] == tracker.best_epoch == 1
    assert state["best_val"] == tracker.best_val == 0.5


def write_bestval(result_dir, mutate=None):
    values = [1.0, 0.5, 0.7, 0.8, 0.9]
    common = {
        "protocol": convergence.BESTVAL_PROTOCOL, "loss_source": "validation",
        "epoch_train_losses": [0.5] * 5, "epoch_val_losses": values,
        "epochs_trained": 5, "status": "CONVERGED", "best_epoch": 1,
        "best_val": 0.5, "stale_epochs": 3, "min_delta": 0.02,
        "patience": 3, "abs_floor": 0.008,
        "stop_reason": convergence.BESTVAL_STOP_REASON,
        "best_checkpoint": "best.ckpt", "acceptance_eligible": True,
        "n_val": 4, "runtime": {"unit_test": True},
    }
    result_dir.mkdir(parents=True, exist_ok=True)
    torch.save({"backbone": {"weight": torch.tensor([2.0])},
                "head": {"weight": torch.tensor([3.0])},
                "epoch": 1, "best_epoch": 1, "best_val": 0.5},
               result_dir / "best.ckpt")
    (result_dir / "result.json").write_text(json.dumps(common))
    plateau = dict(common)
    plateau.pop("epochs_trained")
    plateau["updated_epoch"] = 4
    if mutate:
        mutate(plateau)
    (result_dir / "plateau.json").write_text(json.dumps(plateau))


def test_bestval_audit_requires_complete_checkpoint_and_best_evidence(tmp_path):
    write_bestval(tmp_path)
    assert vp.audit_cell(str(tmp_path))[1] == "CONVERGED"
    result = json.loads((tmp_path / "result.json").read_text())
    result["best_epoch"] = 4
    (tmp_path / "result.json").write_text(json.dumps(result))
    assert vp.audit_cell(str(tmp_path))[1] == "INVALID"
    (tmp_path / "best.ckpt").unlink()
    assert vp.audit_cell(str(tmp_path))[1] == "INVALID"
    for key, value in (("best_epoch", 4), ("best_val", 0.9),
                       ("stop_reason", convergence.STOP_REASON),
                       ("stale_epochs", 2)):
        write_bestval(tmp_path, lambda d, k=key, v=value: d.__setitem__(k, v))
        assert vp.audit_cell(str(tmp_path))[1] in ("INVALID", "NOT_CONVERGED")
    write_bestval(tmp_path, lambda d: d.__setitem__("epoch_val_losses", d["epoch_val_losses"] + [0.2]))
    assert vp.audit_cell(str(tmp_path))[1] in ("INVALID", "NOT_CONVERGED")


def test_shared_checkpoint_proof_accepts_tensors_and_checks_ledger(tmp_path):
    result_dir = tmp_path / "cell"
    write_bestval(result_dir)
    result = json.loads((result_dir / "result.json").read_text())
    row = {"best_epoch": 1, "best_val": 0.5,
           "best_checkpoint": "best.ckpt"}
    assert convergence.checkpoint_proof_error(result_dir, result, row) == ""
    row["best_epoch"] = 4
    assert "ledger/result best_epoch" in convergence.checkpoint_proof_error(
        result_dir, result, row)
    for key, state in (
            ("backbone", {}), ("head", {}),
            ("backbone", {"weight": "not a tensor"})):
        checkpoint = torch.load(result_dir / "best.ckpt", weights_only=True)
        checkpoint[key] = state
        torch.save(checkpoint, result_dir / "best.ckpt")
        assert convergence.checkpoint_proof_error(result_dir, result)
        assert vp.audit_cell(str(result_dir))[1] == "INVALID"
        checkpoint[key] = {"weight": torch.tensor([2.0])}
        torch.save(checkpoint, result_dir / "best.ckpt")
    checkpoint = torch.load(result_dir / "best.ckpt", weights_only=True)
    checkpoint["epoch"] = 4
    torch.save(checkpoint, result_dir / "best.ckpt")
    assert "best.ckpt epoch" in convergence.checkpoint_proof_error(
        result_dir, result)


def test_bestval_ledger_refuses_nonconvergence_and_protocol_reason_mix(tmp_path):
    tracker, _ = overfitting_tracker(tmp_path)
    result = tracker.result_fields()
    assert convergence.result_ledger_fields(result)["convergence_status"] == "CONVERGED"
    with pytest.raises(RuntimeError, match="refusing ledger done"):
        convergence.result_ledger_fields(dict(result, status="RUNNING"))
    with pytest.raises(RuntimeError, match="stop evidence"):
        convergence.result_ledger_fields(
            dict(result, stop_reason=convergence.STOP_REASON))
