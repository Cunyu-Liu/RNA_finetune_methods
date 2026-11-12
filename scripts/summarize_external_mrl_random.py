"""Summarize NucleicBERT MRL runs and independent prediction proofs by split."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from expansion_queue import load_jobs, proof_state
from monitor_mrl_external_predictions import evaluation_path, is_valid


def summarize_jobs(jobs, source, predictions_dir, split):
    jobs = [job for job in jobs if job.model == "NucleicBERT" and job.split == split]
    if len(jobs) != 7:
        raise ValueError(f"NucleicBERT {split} requires 4 tuning + 3 formal jobs")
    tuning, formal, validated = [], [], 0
    for job in jobs:
        state, reason = proof_state(job)
        if state != "complete":
            raise ValueError(f"incomplete {split} cell: {job.rid}: {state}: {reason}")
        result = json.loads(job.result_path.read_text())
        row = {"rid": job.rid, "lr": job.lr, "seed": job.seed,
               "best_val": result["best_val"], "pearson_r": result["value"],
               "mse": result["mse"], "best_epoch": result["best_epoch"],
               "epochs_trained": result["epochs_trained"],
               "peak_mem_mb": result["peak_mem_mb"]}
        (formal if job.seed in (17, 29, 43) else tuning).append(row)
        if not is_valid(evaluation_path(Path(predictions_dir), job.rid), job.rid):
            raise ValueError("missing independent prediction proof: " + job.rid)
        validated += 1
    if len(tuning) != 4 or {row["seed"] for row in formal} != {17, 29, 43}:
        raise ValueError(f"invalid tuning/formal coverage for {split}")
    default_lrs = {row["lr"] for row in formal}
    if len(default_lrs) != 1:
        raise ValueError("formal default jobs must share one LR")
    default_lr = default_lrs.pop()
    default_candidates = [row for row in tuning if row["lr"] == default_lr]
    if len(default_candidates) != 1:
        raise ValueError("formal default LR must have one tuning candidate")
    selected = min(tuning, key=lambda row: (row["best_val"], float(row["lr"])))
    values = [row["pearson_r"] for row in formal]
    interpretation = (
        "NucleicBERT random MRL only; all four LR candidates are near zero, not a global model conclusion"
        if split == "random" else
        "NucleicBERT family MRL default full has low positive Pearson r; tuned formal comparison is separate"
    )
    return {
        "revision": f"20261113_nucleicbert_mrl_{split}_v1",
        "model": "NucleicBERT", "task": "mrl", "split": split,
        "strategy": "full", "protocol": "bestval_v1",
        "train_batch_size": 8, "evaluation_batch_size": 16,
        "n_complete": len(jobs), "prediction_revalidation_passed": validated,
        "source_registry": str(source),
        "source_registry_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "tuning": tuning, "formal": formal,
        "default_lr": default_lr,
        "default_best_val": default_candidates[0]["best_val"],
        "tuned_selection_lr": selected["lr"],
        "tuned_selected_best_val": selected["best_val"],
        "tuned_matches_default": selected["lr"] == default_lr,
        "formal_mean": float(np.mean(values)),
        "formal_sample_sd": float(np.std(values, ddof=1)),
        "interpretation": interpretation,
        "tuned_comparison": "default reused" if selected["lr"] == default_lr else "pending",
        "aido_status": "deferred_na",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", choices=("random", "family"), default="random")
    parser.add_argument("--jobs-json", required=True)
    parser.add_argument("--predictions-dir", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = Path(args.jobs_json)
    summary = summarize_jobs(load_jobs(source), source, args.predictions_dir, args.split)
    args.output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
