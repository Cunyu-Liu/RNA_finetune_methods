import json
from types import SimpleNamespace

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
        "stop_reason": stop_reason,
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
