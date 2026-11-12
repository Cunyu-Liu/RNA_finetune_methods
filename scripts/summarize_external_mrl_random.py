"""Summarize NucleicBERT random MRL runs and independent prediction proofs."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from expansion_queue import load_jobs, proof_state
from monitor_mrl_external_predictions import evaluation_path, is_valid


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs-json", required=True)
    parser.add_argument("--predictions-dir", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = Path(args.jobs_json)
    jobs = [job for job in load_jobs(source) if job.model == "NucleicBERT" and job.split == "random"]
    if len(jobs) != 7:
        raise ValueError("NucleicBERT random requires 4 tuning + 3 formal jobs")
    tuning, formal, validated = [], [], 0
    for job in jobs:
        state, reason = proof_state(job)
        if state != "complete":
            raise ValueError(f"incomplete random cell: {job.rid}: {state}: {reason}")
        result = json.loads(job.result_path.read_text())
        row = {"rid": job.rid, "lr": job.lr, "seed": job.seed,
               "best_val": result["best_val"], "pearson_r": result["value"],
               "mse": result["mse"], "best_epoch": result["best_epoch"],
               "epochs_trained": result["epochs_trained"],
               "peak_mem_mb": result["peak_mem_mb"]}
        (formal if job.seed in (17, 29, 43) else tuning).append(row)
        if not is_valid(evaluation_path(Path(args.predictions_dir), job.rid), job.rid):
            raise ValueError("missing independent prediction proof: " + job.rid)
        validated += 1
    values = [row["pearson_r"] for row in formal]
    selected = min(tuning, key=lambda row: (row["best_val"], float(row["lr"])))
    summary = {
        "revision": "20261112_nucleicbert_mrl_random_v1",
        "model": "NucleicBERT", "task": "mrl", "split": "random",
        "strategy": "full", "protocol": "bestval_v1",
        "train_batch_size": 8, "evaluation_batch_size": 16,
        "n_complete": len(jobs), "prediction_revalidation_passed": validated,
        "source_registry": str(source), "source_registry_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "tuning": tuning, "formal": formal,
        "default_lr": selected["lr"],
        "default_best_val": selected["best_val"],
        "formal_mean": float(np.mean(values)), "formal_sample_sd": float(np.std(values, ddof=1)),
        "interpretation": "NucleicBERT random MRL only; all four LR candidates are near zero, not a global model conclusion",
        "pending": "AIDO random/family",
    }
    args.output.write_text(json.dumps(summary, ensure_ascii=False, indent=2)+"\n")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
