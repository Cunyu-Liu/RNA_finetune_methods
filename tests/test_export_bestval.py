import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import export_bestval as exporter


def row(tmp_path, rid="ft_valid", **updates):
    value = {
        "run_id": rid, "model": "RiNALMo-micro", "task": "mrl",
        "strategy": "lora", "split": "random", "seed": 17,
        "protocol": "bestval_v1", "status": "done", "metric": "PEARSON_R",
        "value": 0.8, "n_train": 20000, "n_val": 100, "n_test": 100,
        "best_epoch": 3, "best_val": 0.4, "epochs_trained": 7,
        "wall_sec": 10.0, "peak_mem_mb": 1000.0, "lr": 0.0003,
        "stop_reason": "validation_no_improvement_patience",
        "out_dir": str(tmp_path / rid), "runtime": {
            "cuda_device": "cuda:0", "cuda_device_name": "RTX 5090",
            "cuda_runtime_version": "12.8",
            "tokenizer_name_or_path": "rinalmo-micro",
        },
    }
    value.update(updates)
    return value


def test_export_requires_complete_proof_and_preserves_source(tmp_path, monkeypatch):
    valid = row(tmp_path)
    invalid = row(tmp_path, "ft_invalid")
    missing_metric = row(tmp_path, "ft_missing_metric", metric=None)
    monkeypatch.setattr(exporter.queue, "proof_state", lambda job: (
        ("complete", "") if job.rid == "ft_valid" else ("conflict", "bad checkpoint")))
    accepted, rejected = exporter.collect([
        valid, invalid, missing_metric, row(tmp_path, "ft_smoke", status="running"),
        row(tmp_path, "ft_e6", split="s0-heldout")])
    assert [item["run_id"] for item in accepted] == ["ft_valid"]
    assert accepted[0]["artifact_dir"] == valid["out_dir"]
    assert accepted[0]["best_checkpoint"].endswith("best.ckpt")
    assert accepted[0]["cuda_device_name"] == "RTX 5090"
    assert {item["run_id"] for item in rejected} == {"ft_invalid", "ft_missing_metric"}
    assert all(item["run_id"] != "ft_e6" for item in accepted + rejected)


def test_export_writes_accepted_csv_and_rejected_json(tmp_path, monkeypatch):
    valid = row(tmp_path)
    monkeypatch.setattr(exporter, "collect", lambda: ([valid], [{"run_id": "bad", "reason": "x"}]))
    output = tmp_path / "accepted.csv"
    rejected = tmp_path / "rejected.json"
    assert exporter.main(["--output", str(output), "--rejected-output", str(rejected)]) == 0
    with output.open() as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 1 and rows[0]["run_id"] == "ft_valid"
    assert json.loads(rejected.read_text())[0]["run_id"] == "bad"
