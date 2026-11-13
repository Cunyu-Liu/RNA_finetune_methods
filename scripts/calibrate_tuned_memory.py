#!/usr/bin/env python3
import argparse
import copy
import hashlib
import json
import math
import os
from pathlib import Path


def without_lr(args):
    result = []
    skip = False
    for arg in args:
        if skip:
            skip = False
            continue
        if arg == "--lr":
            skip = True
            continue
        if arg.startswith("--lr="):
            continue
        result.append(arg)
    return result


def calibrate_group(job, sources, selection, result_loader, margin=None):
    key = (job["task"], job["model"], job["split"])
    if (selection["task"], selection["model"], selection["split"]) != key:
        raise ValueError("selection group mismatch")
    candidates = []
    for accepted in selection["candidates"]:
        source = sources[accepted["rid"]]
        if (source["task"], source["model"], source["split"], source["seed"],
                source["strategy"], source["protocol"]) != (
                job["task"], job["model"], job["split"], 101, "full", "bestval_v1"):
            raise ValueError("memory source scientific identity mismatch: " + source["rid"])
        if without_lr(source["args"]) != without_lr(job["args"]):
            raise ValueError("memory source training arguments differ: " + source["rid"])
        result = result_loader(source)
        if (result["run_id"] != source["rid"] or result["protocol"] != "bestval_v1"
                or result["status"] != "CONVERGED" or result["smoke"] is not False
                or result["runtime"]["cuda_available"] is not True):
            raise ValueError("invalid CUDA training peak proof: " + source["rid"])
        peak = result["peak_mem_mb"]
        if isinstance(peak, bool) or not isinstance(peak, (int, float)) or not math.isfinite(peak) or peak <= 0:
            raise ValueError("invalid training peak: " + source["rid"])
        candidates.append({"rid": source["rid"], "peak_mem_mb": peak})
    if not candidates:
        raise ValueError("no accepted memory source for " + str(key))
    peak = max(row["peak_mem_mb"] for row in candidates)
    if margin is None:
        margin = 1.5 if peak < 12000 else 1.2
    reserve = max(2.0, math.ceil((peak * margin / 1024) * 2) / 2)
    calibrated = copy.deepcopy(job)
    calibrated["need_gb"] = min(float(job["need_gb"]), reserve)
    evidence = {"task": job["task"], "model": job["model"], "split": job["split"],
                "old_need_gb": job["need_gb"], "new_need_gb": calibrated["need_gb"],
                "max_peak_mem_mb": peak, "margin": margin, "candidates": candidates}
    return calibrated, evidence


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tuned-jobs", type=Path, required=True)
    parser.add_argument("--selection-json", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--backup", type=Path)
    args = parser.parse_args()
    selection_path = args.selection_json
    selection = json.loads(selection_path.read_text())
    if selection["test_metric_used"] is not False:
        raise ValueError("selection must exclude test metrics")
    source_path = Path(selection["source_registry"])
    if hashlib.sha256(source_path.read_bytes()).hexdigest() != selection["source_sha256"]:
        raise ValueError("LR tuning registry changed after selection")
    sources = {job["rid"]: job for job in json.loads(source_path.read_text())}
    tuned = json.loads(args.tuned_jobs.read_text())
    tuned_input_sha256 = hashlib.sha256(args.tuned_jobs.read_bytes()).hexdigest()
    selected = {(row["task"], row["model"], row["split"]): row for row in selection["rows"]}
    if len(tuned) != 240 or len(selected) != 80:
        raise ValueError("expected 240 tuned jobs and 80 selection groups")
    calibrated, evidence = [], []
    for job in tuned:
        key = (job["task"], job["model"], job["split"])
        if key not in selected:
            raise ValueError("missing selection group: " + str(key))
        new_job, proof = calibrate_group(
            job, sources, selected[key],
            lambda source: json.loads((Path(source["result_dir"]) / "result.json").read_text()))
        calibrated.append(new_job)
        evidence.append(proof)
    if len({job["rid"] for job in calibrated}) != 240:
        raise ValueError("calibrated registry contains duplicate RIDs")
    for old, new in zip(tuned, calibrated):
        changed = {key for key in old if old[key] != new[key]}
        if changed != {"need_gb"}:
            raise ValueError("calibration changed non-memory fields: " + old["rid"])
    if args.output.resolve() == args.tuned_jobs.resolve():
        if not args.backup:
            raise ValueError("in-place calibration requires --backup")
        if not args.backup.exists():
            args.backup.write_bytes(args.tuned_jobs.read_bytes())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(json.dumps(calibrated, indent=2) + "\n")
    os.replace(temporary, args.output)
    grouped = {}
    for row in evidence:
        key = (row["task"], row["model"], row["split"])
        if key in grouped and grouped[key] != row:
            raise ValueError("seed memory calibration differs within group: " + str(key))
        grouped[key] = row
    report = {
        "jobs": len(calibrated), "groups": len(grouped),
        "margin_policy": "1.5 below 12000MB; 1.2 at or above 12000MB",
        "rounding_gib": 0.5, "minimum_gib": 2.0,
        "source_registry": str(source_path),
        "source_sha256": selection["source_sha256"],
        "selection_sha256": hashlib.sha256(selection_path.read_bytes()).hexdigest(),
        "tuned_input_sha256": tuned_input_sha256,
        "tuned_output_sha256": hashlib.sha256(args.output.read_bytes()).hexdigest(),
        "evidence": list(grouped.values()),
        "scope": "Scheduling reserve only; model, data, LR, protocol, seed and scientific results unchanged",
    }
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"jobs": len(calibrated), "groups": len(grouped),
                      "old_need_gb": sorted({job["need_gb"] for job in tuned}),
                      "new_need_gb": sorted({job["need_gb"] for job in calibrated}),
                      "report": str(args.report)}, indent=2))


if __name__ == "__main__":
    main()
