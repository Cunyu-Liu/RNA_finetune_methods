import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from monitor_mrl_external_predictions import evaluation_path, is_valid, evaluation_env


def test_only_complete_prediction_proof_is_reused(tmp_path):
    rid = "ft_external_reval20261111"
    path = evaluation_path(tmp_path, rid)
    path.parent.mkdir(parents=True)
    predictions = path.parent / "predictions.npz"
    predictions.write_bytes(b"test-placeholder")
    value = {"run_id": rid, "full_test_metric_match": True,
             "split_evidence_match": True, "restored_tensor_match": True,
             "cuda_available": True, "y_pred_std": 0.1,
             "predictions": str(predictions)}
    path.write_text(json.dumps(value))
    assert is_valid(path, rid)
    value["full_test_metric_match"] = False
    path.write_text(json.dumps(value))
    assert not is_valid(path, rid)


def test_missing_prediction_file_is_not_reused(tmp_path):
    path = evaluation_path(tmp_path, "ft_external_reval20261111")
    assert not is_valid(path, "ft_external_reval20261111")


def test_evaluation_env_includes_compatible_pypath():
    assert evaluation_env()["PYTHONPATH"].split(":")[0] == "/root/rna-ft-eval/pypath"


def test_evaluation_batch_matches_source_protocol():
    from monitor_mrl_external_predictions import evaluation_batch_size
    assert evaluation_batch_size("NucleicBERT") == 16
    assert evaluation_batch_size("AIDO.RNA-1.6B") == 2
