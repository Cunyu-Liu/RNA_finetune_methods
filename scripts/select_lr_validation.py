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


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tuning-jobs", required=True)
    parser.add_argument("--selection-output", required=True)
    parser.add_argument("--jobs-output", required=True)
    args = parser.parse_args(argv)
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
        for job in sorted(items, key=lambda item: float(item.lr), reverse=True):
            state, reason = queue.proof_state(job)
            if state != "complete":
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
        if len(candidates) == 4:
            selected = min(candidates, key=lambda row: (row["best_val"], float(row["lr"])))
            rows.append({
                "task": task, "model": model, "split": split,
                "selected_lr": selected["lr"],
                "selected_best_val": selected["best_val"],
                "selected_rid": selected["rid"],
                "candidates": candidates,
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
