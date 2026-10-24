import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import e6_mlm15_proof as proof
import quarantine_20261024 as quarantine
from rnafteval import export_e6v2, ledger


def result_payload(rid, protocol, task=None):
    payload = {
        "run_id": rid, "model": "RiNALMo-micro", "strategy": "lora",
        "seed": 17, "mask_rate": 0.15, "pre_nll_a": 1.0,
        "pre_nll_b": 1.01, "noise_band": 0.01, "post_nll": 1.2,
        "delta_nll": 0.2, "protocol": protocol,
    }
    if task is not None:
        payload["task"] = task
    return payload


def write_result(tmp_path, payload):
    (tmp_path / "result.json").write_text(json.dumps(payload))


@pytest.fixture
def proof_rows(monkeypatch):
    rows = {}
    monkeypatch.setattr(proof.ledger, "by_run_id", rows.get)
    return rows


def test_proof_default_v1_cli_and_rid(tmp_path, proof_rows, capsys):
    rid = ledger.run_id("RiNALMo-micro", "e6-forgetting", "lora", 17,
                        "s0-heldout", extra="_mlm15fix")
    proof_rows[rid] = {"run_id": rid, "status": "done"}
    write_result(tmp_path, result_payload(rid, "E6-v1-fixed-mask-mlm: test"))

    proof.main([str(tmp_path), "RiNALMo-micro", "lora", "17"])
    assert "E6_PROOF_OK " + rid in capsys.readouterr().out


def test_proof_v2_options_check_task_protocol_and_corrected_rid(
        tmp_path, proof_rows, capsys):
    extra = "_taskm6a_s0_mlm15fix"
    rid = ledger.run_id("RiNALMo-micro", "e6-forgetting", "lora", 17,
                        "s0-heldout", extra=extra)
    assert rid.endswith(extra)
    assert "_e6forgetting_" in rid
    proof_rows[rid] = {"run_id": rid, "status": "done"}
    write_result(tmp_path, result_payload(
        rid, "E6-v2-fixed-mask-mlm: test", task="modification"))

    proof.main([
        str(tmp_path), "RiNALMo-micro", "lora", "17",
        "--ledger-task", "e6-forgetting", "--extra", extra,
        "--result-task", "modification",
        "--protocol-prefix", "E6-v2-fixed-mask-mlm",
    ])
    assert "E6_PROOF_OK " + rid in capsys.readouterr().out


def test_proof_rejects_v2_task_mismatch(tmp_path, proof_rows):
    extra = "_taskm6a_s0_mlm15fix"
    rid = ledger.run_id("RiNALMo-micro", "e6-forgetting", "lora", 17,
                        "s0-heldout", extra=extra)
    proof_rows[rid] = {"run_id": rid, "status": "done"}
    write_result(tmp_path, result_payload(
        rid, "E6-v2-fixed-mask-mlm: test", task="noncoding-rna-family"))
    with pytest.raises(SystemExit, match="result mismatch: task"):
        proof.verify(tmp_path, "RiNALMo-micro", "lora", 17, extra=extra,
                     result_task="modification",
                     protocol_prefix="E6-v2-fixed-mask-mlm")


def fake_queue_runtime(tmp_path):
    state = tmp_path / "state"
    state.mkdir()
    calls = tmp_path / "calls.jsonl"
    log = tmp_path / "queue.log"
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_py = fake_bin / "fake_python"
    fake_py.write_text("""#!/usr/bin/env python3
import json
import os
from pathlib import Path
import sys

args = sys.argv[1:]
with open(os.environ["FAKE_CALLS"], "a") as fh:
    fh.write(json.dumps(args) + "\\n")
state = Path(os.environ["FAKE_STATE"])
if args and args[0].endswith("e6_mlm15_proof.py"):
    model, strategy, seed = args[2:5]
    marker = state / (model + "_" + strategy + "_" + seed + ".done")
    raise SystemExit(0 if marker.exists() else 1)
if args[:2] == ["-m", "rnafteval.e6_forget_task"]:
    def option(name):
        return args[args.index(name) + 1]
    model = option("--model")
    strategy = option("--strategy")
    seed = option("--seed")
    key = model + ":" + strategy + ":" + seed
    if os.environ.get("FAIL_CELL") == key:
        raise SystemExit(9)
    (state / (model + "_" + strategy + "_" + seed + ".done")).touch()
    raise SystemExit(0)
raise SystemExit(2)
""")
    fake_py.chmod(0o755)
    fake_timeout = fake_bin / "timeout"
    fake_timeout.write_text("#!/bin/sh\nshift\nexec \"$@\"\n")
    fake_timeout.chmod(0o755)
    env = os.environ.copy()
    env.update({
        "R": str(tmp_path / "runtime"), "REPO": str(tmp_path),
        "PY": str(fake_py), "LOG": str(log),
        "FAKE_STATE": str(state), "FAKE_CALLS": str(calls),
        "PATH": str(fake_bin) + os.pathsep + env.get("PATH", ""),
    })
    return env, state, calls, log


def run_queue(env):
    return subprocess.run(
        ["bash", str(ROOT / "scripts" / "q_e6_v2_mlm15fix.sh")],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=20)


def read_calls(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def test_v2_queue_runs_exactly_six_cells_with_double_proof(tmp_path):
    env, state, calls, log = fake_queue_runtime(tmp_path)
    completed = run_queue(env)
    assert completed.returncode == 0, completed.stderr
    records = read_calls(calls)
    runs = [r for r in records if r[:2] == ["-m", "rnafteval.e6_forget_task"]]
    proofs = [r for r in records if r and r[0].endswith("e6_mlm15_proof.py")]
    assert len(runs) == 6
    assert len(proofs) == 12
    assert len(list(state.glob("*.done"))) == 6
    observed = set()
    for cmd in runs:
        def option(name):
            return cmd[cmd.index(name) + 1]
        strategy = option("--strategy")
        observed.add((option("--model"), strategy, option("--seed")))
        assert option("--task") == "modification"
        assert option("--lr") == ("3e-4" if strategy == "lora" else "1e-5")
        assert option("--epochs") == "3"
        assert option("--batch-size") == "32"
        assert option("--mask-rate") == "0.15"
        assert option("--out-suffix") == "_mlm15fix"
    assert observed == {
        ("RiNALMo-micro", strategy, str(seed))
        for strategy in ("lora", "full") for seed in (17, 29, 43)
    }
    for cmd in proofs:
        assert cmd[cmd.index("--extra") + 1] == "_taskm6a_s0_mlm15fix"
        assert cmd[cmd.index("--result-task") + 1] == "modification"
        assert cmd[cmd.index("--protocol-prefix") + 1] == "E6-v2-fixed-mask-mlm"
    text = log.read_text()
    assert "DONE cells=6/6" in text and "INCOMPLETE" not in text


def test_v2_queue_failure_is_incomplete_and_nonzero(tmp_path):
    env, state, calls, log = fake_queue_runtime(tmp_path)
    env["FAIL_CELL"] = "RiNALMo-micro:lora:29"
    completed = run_queue(env)
    assert completed.returncode != 0
    assert len(list(state.glob("*.done"))) == 5
    text = log.read_text()
    assert "INCOMPLETE cells=5/6" in text and "DONE cells=" not in text


def test_quarantine_classifies_old_official_v2_but_not_corrected():
    old_rid = "ft_rinalmomicro_e6forgetting_lora_s17_s0-heldout_taskm6a_s0"
    old = {"run_id": old_rid, "model": "RiNALMo-micro",
           "task": "modification", "status": "done"}
    assert quarantine.classify(old) == "mlm"
    corrected = dict(old, run_id=old_rid + "_mlm15fix")
    assert quarantine.classify(corrected) is None
    controlled = dict(old, model="RNA-Sc-10M")
    assert quarantine.classify(controlled) is None
    unrelated = dict(old, run_id="ft_rinalmomicro_modification_lora_s17_random")
    assert quarantine.classify(unrelated) is None
    old_v1 = dict(old, task="e6-forgetting")
    assert quarantine.classify(old_v1) == "mlm"


def test_quarantine_backup_names_do_not_overwrite(tmp_path, monkeypatch):
    monkeypatch.setattr(quarantine, "BACKUP", tmp_path)
    stamp = "20261024T010203.123456Z"
    first = quarantine.backup_path("manifest", stamp)
    first.write_text("first")
    second = quarantine.backup_path("manifest", stamp)
    assert first != second
    assert stamp in first.name and stamp in second.name
    assert first.read_text() == "first"


def test_export_keeps_controlled_and_filters_old_official(tmp_path, monkeypatch):
    art = tmp_path / "e6"
    art.mkdir()
    monkeypatch.setattr(export_e6v2, "ART", str(art))

    def put(dirname, model, seed, protocol, delta):
        path = art / dirname
        path.mkdir()
        payload = {"model": model, "strategy": "lora", "seed": seed,
                   "protocol": protocol, "delta_nll": delta}
        if "task-m6a" in dirname:
            payload["task"] = "modification"
        (path / "result.json").write_text(json.dumps(payload))

    put("RNA-Sc-10M_lora_task-m6a_s17", "RNA-Sc-10M", 17,
        "E6-v2: task-origin forgetting", 0.1)
    put("RiNALMo-micro_lora_task-m6a_s17_mlm15fix", "RiNALMo-micro", 17,
        "E6-v2-fixed-mask-mlm: corrected", 0.2)
    put("RiNALMo-micro_lora_task-m6a_s29", "RiNALMo-micro", 29,
        "E6-v2: task-origin forgetting", 99.0)
    put("RiNALMo-micro_lora_s17_mlm15fix", "RiNALMo-micro", 17,
        "E6-v1-fixed-mask-mlm: corrected", 0.3)
    put("RiNALMo-micro_lora_s29", "RiNALMo-micro", 29,
        "E6-v1: unmasked", 99.0)

    data = export_e6v2.collect()
    assert data[("RNA-Sc-10M", "lora", "m6a")][17]["delta_nll"] == 0.1
    assert set(data[("RiNALMo-micro", "lora", "m6a")]) == {17}
    assert data[("RiNALMo-micro", "lora", "m6a")][17]["delta_nll"] == 0.2
    assert set(data[("RiNALMo-micro", "lora", "ncrna")]) == {17}
    assert data[("RiNALMo-micro", "lora", "ncrna")][17]["delta_nll"] == 0.3
