import json
import math
from pathlib import Path

import pytest

import valplateau as vp


def test_converged_flat_tail():
    s, d = vp.classify([1.0, 0.8, 0.62, 0.61, 0.605, 0.602])
    assert s == "CONVERGED", d


def test_converged_low_loss_oscillation_dual_criteria():
    # loss < 0.05: relative 2% is noise-amplifying; abs floor governs
    s, _ = vp.classify([1.0, 0.5, 0.2, 0.05, 0.0209, 0.015, 0.0131])
    assert s == "CONVERGED", _


def test_not_converged_low_loss_still_large_drops():
    s, _ = vp.classify([1.0, 0.5, 0.2, 0.06, 0.05, 0.03, 0.01])
    assert s == "NOT_CONVERGED"


def test_not_converged_still_improving():
    s, _ = vp.classify([1.0, 0.8, 0.6, 0.4, 0.2, 0.1])
    assert s == "NOT_CONVERGED"


def test_too_short_and_empty_and_nan():
    assert vp.classify([])[0] == "EMPTY"
    assert vp.classify([0.5])[0] == "TOO_SHORT"
    assert vp.classify([1.0, float("nan"), 0.5, 0.5, 0.5])[0] == "INVALID"


def test_legacy_without_plateau(tmp_path):
    (tmp_path / "result.json").write_text("{}")
    cell, status, _ = vp.audit_cell(str(tmp_path), 0.02, 3)
    assert status == "LEGACY", (cell, status)


def test_no_result_json(tmp_path):
    cell, status, _ = vp.audit_cell(str(tmp_path), 0.02, 3)
    assert status == "NO_RESULT"


def test_audit_reads_plateau(tmp_path):
    (tmp_path / "result.json").write_text("{}")
    (tmp_path / "plateau.json").write_text(json.dumps({
        "protocol": "valplateau_v1",
        "epoch_train_losses": [1.0, 0.9, 0.85, 0.845, 0.844]}))
    _c, status, _d = vp.audit_cell(str(tmp_path), 0.02, 3)
    assert status == "CONVERGED"


def test_wrong_protocol_rejected(tmp_path):
    (tmp_path / "result.json").write_text("{}")
    (tmp_path / "plateau.json").write_text(json.dumps({
        "protocol": "other", "epoch_train_losses": [1, 1, 1]}))
    _c, status, _d = vp.audit_cell(str(tmp_path), 0.02, 3)
    assert status == "INVALID"


def test_main_exit_code(tmp_path, capsys):
    good = tmp_path / "good_cell"
    good.mkdir()
    (good / "result.json").write_text("{}")
    (good / "plateau.json").write_text(json.dumps({
        "protocol": "valplateau_v1",
        "epoch_train_losses": [1.0, 0.9, 0.85, 0.845, 0.844]}))
    out = tmp_path / "report.json"
    rc = vp.main(["--e6-root", str(tmp_path), "--json-out", str(out)])
    assert rc == 0
    assert "CONVERGED" in capsys.readouterr().out
    data = json.loads(out.read_text())
    assert data[0]["status"] == "CONVERGED"
