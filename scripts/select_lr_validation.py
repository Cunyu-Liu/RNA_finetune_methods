#!/usr/bin/env python3
"""Select full-FT learning rates from complete seed-101 validation evidence."""
from __future__ import annotations

import argparse
import collections
import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import sys

import expansion_jobs as jobspec
import expansion_queue as queue


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n")
    os.replace(temporary, path)


def load_invalid_candidates(paths):
    documents = {}
    for path in paths:
        data = json.loads(Path(path).read_text())
        rid = data.get("run_id")
        if not isinstance(rid, str) or rid in documents:
            raise ValueError(f"invalid or duplicate collapse RID: {rid}")
        if data.get("nonfinite_reason") != "constant_prediction":
            raise ValueError(f"unsupported invalid-candidate reason for {rid}")
        if data.get("candidate_eligible") is not False:
            raise ValueError(f"invalid candidate was not explicitly excluded for {rid}")
        if data.get("cuda_available") is not True or data.get("split_evidence_match") is not True:
            raise ValueError(f"missing CUDA or split proof for {rid}")
        if data.get("plateau_status") != "CONVERGED":
            raise ValueError(f"collapse checkpoint is not converged for {rid}")
        if not isinstance(data.get("n_test"), int) or data["n_test"] <= 0:
            raise ValueError(f"invalid test size for {rid}")
        if not math.isfinite(data.get("y_pred_std", float("nan"))) or data["y_pred_std"] >= 1e-6:
            raise ValueError(f"prediction is not constant for {rid}")
        documents[rid] = data
    return documents


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tuning-jobs", required=True)
    parser.add_argument("--selection-output", required=True)
    parser.add_argument("--jobs-output", required=True)
    parser.add_argument("--invalid-candidate", action="append", default=[],
                        help="independent CUDA proof of a non-selectable constant-output candidate")
    args = parser.parse_args(argv)
    invalid_documents = load_invalid_candidates(args.invalid_candidate)
    source = Path(args.tuning_jobs)
    jobs = queue.load_jobs(source)
    if len(jobs) != 320:
        raise ValueError(f"expected 320 tuning jobs, found {len(jobs)}")
    groups = collections.defaultdict(list)
    for job in jobs:
        groups[(job.task, job.model, job.split)].append(job)
    if len(groups) != 80 or any(len(items) != 4 for items in groups.values()):
        raise ValueError("tuning registry must contain 80 groups of four LRs")

    rows = []
    incomplete = []
    for (task, model, split), items in sorted(groups.items()):
        candidates = []
        invalid = []
        for job in sorted(items, key=lambda item: float(item.lr), reverse=True):
            state, reason = queue.proof_state(job)
            if state != "complete":
                if job.rid in invalid_documents:
                    invalid.append(invalid_documents[job.rid])
                else:
                    incomplete.append({"rid": job.rid, "state": state, "reason": reason})
                continue
            result = json.loads(job.result_path.read_text())
            best_val = result.get("best_val")
            if not isinstance(best_val, (int, float)) or not math.isfinite(best_val):
                raise ValueError(f"invalid validation loss for {job.rid}: {best_val}")
            candidates.append({
                "lr": job.lr, "best_val": float(best_val), "rid": job.rid,
                "best_epoch": result.get("best_epoch"),
            })
        if candidates and len(candidates) + len(invalid) == 4:
            selected = min(candidates, key=lambda row: (row["best_val"], float(row["lr"])))
            rows.append({
                "task": task, "model": model, "split": split,
                "selected_lr": selected["lr"],
                "selected_best_val": selected["best_val"],
                "selected_rid": selected["rid"],
                "candidates": candidates,
                "invalid_candidates": invalid,
            })
    if incomplete:
        print(json.dumps({"status": "incomplete", "missing": incomplete}, indent=2))
        return 1
    if len(rows) != 80:
        raise ValueError(f"selection covers {len(rows)} groups instead of 80")

    formal_jobs = jobspec.lr_tuned_jobs(rows)
    if len(formal_jobs) != 240 or len({job["rid"] for job in formal_jobs}) != 240:
        raise ValueError("formal tuned-LR registry is incomplete or contains duplicate RIDs")
    document = {
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "source_registry": str(source),
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "selection_metric": "best_val (held-out validation loss)",
        "test_metric_used": False,
        "invalid_candidate_rule": "only independent CUDA constant-output proofs; excluded from selection and accepted ledger",
        "tie_rule": "minimum best_val, then lower LR for exact ties",
        "rows": rows,
    }
    atomic_json(args.jobs_output, formal_jobs)
    atomic_json(args.selection_output, document)
    print(json.dumps({"status": "complete", "groups": len(rows),
                      "formal_jobs": len(formal_jobs),
                      "selection_output": args.selection_output,
                      "jobs_output": args.jobs_output}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
