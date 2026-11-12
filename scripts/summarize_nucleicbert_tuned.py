#!/usr/bin/env python3
import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np

from expansion_queue import load_jobs, proof_state
from monitor_mrl_external_predictions import evaluation_path, is_valid


def complete_result(job, predictions_dir):
    state, reason = proof_state(job)
    if state != "complete":
        raise ValueError(f"incomplete tuned comparison cell: {job.rid}: {state}: {reason}")
    if not is_valid(evaluation_path(Path(predictions_dir), job.rid), job.rid):
        raise ValueError("missing independent prediction proof: " + job.rid)
    result = json.loads(job.result_path.read_text())
    if not math.isfinite(result["value"]) or result.get("acceptance_eligible") is not True:
        raise ValueError("result is not finite and acceptance eligible: " + job.rid)
    return result


def summarize_split(default_jobs, tuned_jobs, selection, predictions_dir, split):
    if selection.get("test_metric_used") is not False:
        raise ValueError("LR selection must explicitly exclude test metrics")
    selected_rows = [row for row in selection["rows"]
                     if row["model"] == "NucleicBERT" and row["split"] == split]
    if len(selected_rows) != 1:
        raise ValueError("missing NucleicBERT LR selection for " + split)
    selected_lr = selected_rows[0]["selected_lr"]
    defaults = {job.seed: job for job in default_jobs
                if job.model == "NucleicBERT" and job.split == split and job.seed in (17, 29, 43)}
    tuned = {job.seed: job for job in tuned_jobs
             if job.model == "NucleicBERT" and job.split == split and job.seed in (17, 29, 43)}
    if set(defaults) != {17, 29, 43} or set(tuned) != {17, 29, 43}:
        raise ValueError("default and tuned must both cover seeds 17/29/43")
    pairs = []
    for seed in (17, 29, 43):
        default_job, tuned_job = defaults[seed], tuned[seed]
        for job in (default_job, tuned_job):
            if (job.task, job.model, job.strategy, job.split, job.protocol) != (
                    "mrl", "NucleicBERT", "full", split, "bestval_v1"):
                raise ValueError("paired job scientific identity mismatch: " + job.rid)
            batch_index = job.args.index("--batch-size") + 1
            if job.args[batch_index] != "8" or job.n_train != 20000:
                raise ValueError("unexpected MRL training protocol: " + job.rid)
        if tuned_job.lr != selected_lr:
            raise ValueError("formal tuned LR differs from frozen validation selection")
        default = complete_result(default_job, predictions_dir)
        tuned_result = complete_result(tuned_job, predictions_dir)
        if (default["seed"], tuned_result["seed"]) != (seed, seed):
            raise ValueError("result seed does not match paired jobs")
        pairs.append({
            "seed": seed, "default_rid": default_job.rid, "tuned_rid": tuned_job.rid,
            "default_lr": default_job.lr, "tuned_lr": tuned_job.lr,
            "default_r": default["value"], "tuned_r": tuned_result["value"],
            "delta_r": tuned_result["value"] - default["value"],
            "default_mse": default["mse"], "tuned_mse": tuned_result["mse"],
            "default_best_val": default["best_val"], "tuned_best_val": tuned_result["best_val"],
            "default_epochs": default["epochs_trained"], "tuned_epochs": tuned_result["epochs_trained"],
            "reused_same_rid": default_job.rid == tuned_job.rid,
        })
    default_lrs = {row["default_lr"] for row in pairs}
    if len(default_lrs) != 1:
        raise ValueError("default jobs do not share one LR")
    deltas = np.array([row["delta_r"] for row in pairs], dtype=float)
    default_values = np.array([row["default_r"] for row in pairs], dtype=float)
    tuned_values = np.array([row["tuned_r"] for row in pairs], dtype=float)
    return {
        "model": "NucleicBERT", "task": "mrl", "split": split,
        "strategy": "full", "protocol": "bestval_v1",
        "default_lr": default_lrs.pop(), "tuned_lr": selected_lr,
        "selection_seed": 101, "selection_metric": "best_val",
        "test_metric_used_for_selection": False,
        "pairs": pairs, "n_pairs": 3,
        "default_mean": float(default_values.mean()),
        "default_sample_sd": float(default_values.std(ddof=1)),
        "tuned_mean": float(tuned_values.mean()),
        "tuned_sample_sd": float(tuned_values.std(ddof=1)),
        "tuned_minus_default_mean": float(deltas.mean()),
        "tuned_minus_default_sample_sd": float(deltas.std(ddof=1)),
        "prediction_checks": 6,
        "unique_prediction_rids": len({row["default_rid"] for row in pairs}
                                      | {row["tuned_rid"] for row in pairs}),
        "interpretation": "Descriptive three-seed paired comparison for this model/task/split/protocol only",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--default-jobs", required=True)
    parser.add_argument("--tuned-jobs", required=True)
    parser.add_argument("--selection-json", required=True)
    parser.add_argument("--predictions-dir", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    default_path, tuned_path = Path(args.default_jobs), Path(args.tuned_jobs)
    selection_path = Path(args.selection_json)
    selection = json.loads(selection_path.read_text())
    defaults, tuned = load_jobs(default_path), load_jobs(tuned_path)
    splits = {job.split for job in tuned}
    if splits != {"random", "family"} or len(tuned) != 6:
        raise ValueError("tuned registry must contain exactly six NucleicBERT split/seed jobs")
    documents = [summarize_split(defaults, tuned, selection, args.predictions_dir, split)
                 for split in ("random", "family")]
    output = {
        "revision": "20261113_nucleicbert_mrl_default_vs_tuned_v1",
        "splits": documents,
        "prediction_checks": sum(row["prediction_checks"] for row in documents),
        "unique_prediction_rids": len({pair["default_rid"] for row in documents for pair in row["pairs"]}
                                      | {pair["tuned_rid"] for row in documents for pair in row["pairs"]}),
        "source_registries": [str(default_path), str(tuned_path)],
        "source_sha256": [hashlib.sha256(path.read_bytes()).hexdigest()
                          for path in (default_path, tuned_path, selection_path)],
        "aido_status": "deferred_na",
    }
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
