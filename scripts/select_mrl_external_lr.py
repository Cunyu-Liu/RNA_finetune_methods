#!/usr/bin/env python3
import argparse
import collections
import hashlib
import json
from pathlib import Path

from expansion_jobs import job_for
from expansion_queue import load_jobs, proof_state
from select_lr_validation import load_invalid_candidates

LRS = ("3e-4", "1e-4", "3e-5", "1e-5")
MODEL_SETTINGS = {
    "NucleicBERT": {"default_lr": "3e-5", "batch": 8, "need_gb": 18},
    "AIDO.RNA-1.6B": {"default_lr": "1e-5", "batch": 1, "need_gb": 31},
}


def select_groups(jobs, state_fn=proof_state, invalid_documents=None):
    invalid_documents = invalid_documents or {}
    groups = collections.defaultdict(list)
    for job in jobs:
        if job.seed == 101:
            groups[(job.model, job.split)].append(job)
    rows = []
    incomplete = []
    for (model, split), items in sorted(groups.items()):
        candidates = []
        invalid = []
        if len(items) != 4:
            incomplete.append({"model": model, "split": split,
                               "reason": f"expected 4 LR tuning cells, got {len(items)}"})
            continue
        for job in sorted(items, key=lambda item: float(item.lr), reverse=True):
            state, reason = state_fn(job)
            if state != "complete":
                if job.rid in invalid_documents:
                    invalid.append(invalid_documents[job.rid])
                else:
                    incomplete.append({"rid": job.rid, "state": state, "reason": reason})
                continue
            result = json.loads(job.result_path.read_text())
            best_val = result.get("best_val")
            if not isinstance(best_val, (int, float)):
                raise ValueError(f"missing best_val for {job.rid}")
            candidates.append({
                "lr": job.lr, "best_val": float(best_val), "rid": job.rid,
                "best_epoch": result.get("best_epoch"),
                "test_value_for_report_only": result.get("value"),
            })
        if candidates and len(candidates) + len(invalid) == 4:
            selected = min(candidates, key=lambda row: (row["best_val"], float(row["lr"])))
            rows.append({"model": model, "split": split, "selected_lr": selected["lr"],
                         "selected_best_val": selected["best_val"], "selected_rid": selected["rid"],
                         "candidates": candidates, "invalid_candidates": invalid})
    if incomplete:
        return {"status": "incomplete", "missing": incomplete}, []
    if len(rows) != 4:
        raise ValueError(f"expected 4 model×split groups, got {len(rows)}")
    return {"status": "complete", "selection_metric": "best_val (held-out validation loss)",
            "test_metric_used": False, "tie_rule": "minimum best_val, then lower LR",
            "invalid_candidate_rule": "only independent CUDA constant-output proofs; excluded from selection",
            "rows": rows}, rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tuning-default-jobs", required=True)
    parser.add_argument("--selection-output", required=True)
    parser.add_argument("--jobs-output", required=True)
    parser.add_argument("--invalid-candidate", action="append", default=[])
    args = parser.parse_args()
    invalid_documents = load_invalid_candidates(args.invalid_candidate)
    source = Path(args.tuning_default_jobs)
    jobs = load_jobs(source)
    if len(jobs) != 28:
        raise ValueError(f"expected 28 tuning/default jobs, got {len(jobs)}")
    summary, selected = select_groups(jobs, invalid_documents=invalid_documents)
    if summary["status"] != "complete":
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        raise SystemExit(1)
    summary["source_sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    tuned_jobs = []
    for row in selected:
        settings = MODEL_SETTINGS[row["model"]]
        for seed in (17, 29, 43):
            job = job_for("mrl", row["model"], "full", row["split"], seed,
                          lr=row["selected_lr"], out_suffix="_reval20261111",
                          batch_size=settings["batch"], need_gb=settings["need_gb"],
                          artifact_root="/teams/HoulabData_1788502323/liucunyu/rna-ft-eval/artifacts")
            job["rid"] += "_reval20261111"
            job["result_dir"] = str(Path(job["result_dir"]).with_name(job["rid"]))
            tuned_jobs.append(job)
    if len(tuned_jobs) != 12 or len({job["rid"] for job in tuned_jobs}) != 12:
        raise ValueError("tuned job generation failed uniqueness check")
    for path, value in ((Path(args.selection_output), summary), (Path(args.jobs_output), tuned_jobs)):
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
        temporary.replace(path)
    print(json.dumps({"selection": summary, "tuned_jobs": len(tuned_jobs)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
