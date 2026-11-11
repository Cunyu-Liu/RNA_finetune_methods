import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from monitor_rinalmo_forgetting import METRICS, valid_result


def test_requires_complete_finite_checkpoint_proof(tmp_path):
    checkpoint = tmp_path / "best.ckpt"
    checkpoint.write_bytes(b"checkpoint")
    record = {"evaluation_id": "e6ckpt_test", "source_job": {"rid": "ft_source"},
              "result_dir": str(tmp_path)}
    result = {"run_id": "e6ckpt_test", "source_rid": "ft_source",
              "protocol": "E6-checkpoint-fixed-mask-mlm-v1",
              "restored_tensor_match": True, "acceptance_eligible": True,
              "cuda": {"cuda_available": True}, "holdout_sha256": "a"*64,
              "source_checkpoint": str(checkpoint),
              **{key: 0.1 for key in METRICS}}
    path = tmp_path / "result.json"
    path.write_text(json.dumps(result))
    assert valid_result(record)
    result["delta_nll"] = float("nan")
    path.write_text(json.dumps(result))
    assert not valid_result(record)


def test_missing_result_is_pending(tmp_path):
    assert not valid_result({"evaluation_id": "e6ckpt_test",
                             "source_job": {"rid": "ft_source"},
                             "result_dir": str(tmp_path)})
