import copy

import pytest

from calibrate_tuned_memory import calibrate_group, without_lr


def job(rid, lr, need=28):
    return {"task": "mrl", "model": "RiNALMo-650M", "split": "family",
            "seed": 17 if rid == "formal" else 101, "strategy": "full",
            "protocol": "bestval_v1", "rid": rid, "need_gb": need,
            "args": ["--batch-size", "4", "--n-train", "20000", "--lr", lr]}


def selection(source_rids):
    return {"task": "mrl", "model": "RiNALMo-650M", "split": "family",
            "candidates": [{"rid": rid} for rid in source_rids]}


def result(rid, peak):
    return {"run_id": rid, "protocol": "bestval_v1", "status": "CONVERGED",
            "smoke": False, "runtime": {"cuda_available": True}, "peak_mem_mb": peak}


def test_calibrates_from_max_matching_cuda_peak_with_margin():
    sources = {rid: job(rid, lr) for rid, lr in (("a", "3e-4"), ("b", "3e-5"))}
    peaks = {"a": 10000.0, "b": 12000.0}
    calibrated, evidence = calibrate_group(
        job("formal", "1e-5"), sources, selection(["a", "b"]),
        lambda source: result(source["rid"], peaks[source["rid"]]))
    assert calibrated["need_gb"] == 14.5
    assert evidence["max_peak_mem_mb"] == 12000.0
    assert calibrated["args"] == job("formal", "1e-5")["args"]


def test_calibration_never_increases_original_reserve():
    sources = {"a": job("a", "3e-4")}
    calibrated, _ = calibrate_group(
        job("formal", "1e-5", need=8), sources, selection(["a"]),
        lambda source: result(source["rid"], 12000.0))
    assert calibrated["need_gb"] == 8


def test_batch_mismatch_and_missing_cuda_are_rejected():
    sources = {"a": job("a", "3e-4")}
    mismatched = copy.deepcopy(sources["a"])
    mismatched["args"][1] = "8"
    with pytest.raises(ValueError, match="arguments differ"):
        calibrate_group(job("formal", "1e-5"), {"a": mismatched}, selection(["a"]),
                        lambda source: result(source["rid"], 12000.0))
    invalid = result("a", 12000.0)
    invalid["runtime"]["cuda_available"] = False
    with pytest.raises(ValueError, match="CUDA"):
        calibrate_group(job("formal", "1e-5"), sources, selection(["a"]),
                        lambda source: invalid)


def test_without_lr_preserves_all_other_arguments():
    assert without_lr(["--lr", "3e-4", "--batch-size", "4", "--lr=1e-5"]) == [
        "--batch-size", "4"]
