from pathlib import Path
import os
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import e6_phase as phase


@pytest.fixture
def runtime(tmp_path, monkeypatch):
    model_file = tmp_path / "models.active"
    model_file.write_text("RiNALMo-micro\n")
    result_root = tmp_path / "artifacts" / "e6"
    done = set()
    calls = []

    def fake_verify(result_dir, model, strategy, seed):
        key = model, strategy, seed
        calls.append(key)
        assert result_dir == result_root / ("%s_%s_s%d_mlm15fix" % (
            model, strategy, seed))
        if key not in done:
            raise SystemExit("mock double proof missing")
        return "rid-" + model

    monkeypatch.setattr(phase.proof, "verify", fake_verify)

    def run():
        return phase.main([
            "--model-file", str(model_file),
            "--result-root", str(result_root),
        ])

    return SimpleNamespace(
        model_file=model_file, result_root=result_root, done=done,
        calls=calls, run=run)


def complete_models(runtime, models):
    runtime.done.update(phase.cells_for(models))


def test_incomplete_first_phase_does_not_advance(runtime, capsys):
    assert runtime.run() == 0
    assert runtime.model_file.read_text() == "RiNALMo-micro\n"
    assert len(runtime.calls) == 6
    output = capsys.readouterr().out
    assert "PENDING models=RiNALMo-micro complete=0/6" in output
    assert "ADVANCE" not in output and "COMPLETE\n" not in output


def test_one_missing_cell_blocks_advance_and_is_reported(runtime, capsys):
    complete_models(runtime, phase.PHASES[0])
    missing = ("RiNALMo-micro", "full", 29)
    runtime.done.remove(missing)

    assert runtime.run() == 0
    assert runtime.model_file.read_text() == "RiNALMo-micro\n"
    output = capsys.readouterr().out
    assert "complete=5/6" in output
    assert "PENDING RiNALMo-micro full s29" in output


def test_each_phase_advances_once_and_all_thirty_cells_complete(
        runtime, capsys):
    expected_files = (
        "ERNIE-RNA RNA-FM\n",
        "RiNALMo-mega\n",
        "RiNALMo-650M\n",
        "COMPLETE\n",
    )
    for models, expected in zip(phase.PHASES, expected_files):
        complete_models(runtime, models)
        capsys.readouterr()
        assert runtime.run() == 0
        assert runtime.model_file.read_text() == expected

    assert len(runtime.calls) == 30
    assert runtime.done == {
        cell for models in phase.PHASES for cell in phase.cells_for(models)
    }
    assert capsys.readouterr().out == "COMPLETE\n"

    assert runtime.run() == 0
    assert capsys.readouterr().out == "COMPLETE\n"
    assert len(runtime.calls) == 30
    assert runtime.model_file.read_text() == "COMPLETE\n"


def test_phase_update_uses_atomic_replace(runtime, monkeypatch):
    complete_models(runtime, phase.PHASES[0])
    replacements = []
    real_replace = os.replace

    def spy_replace(src, dst):
        replacements.append((src, dst))
        real_replace(src, dst)

    monkeypatch.setattr(phase.os, "replace", spy_replace)
    assert runtime.run() == 0

    assert len(replacements) == 1
    src, dst = replacements[0]
    assert Path(src).parent == runtime.model_file.parent
    assert Path(src) != runtime.model_file
    assert not Path(src).exists()
    assert Path(dst) == runtime.model_file
    assert runtime.model_file.read_text() == "ERNIE-RNA RNA-FM\n"
    assert not list(runtime.model_file.parent.glob("*.tmp"))
