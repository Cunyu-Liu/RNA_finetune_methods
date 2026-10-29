#!/usr/bin/env python3
"""Calibrate expansion need_gb from measured ledger peaks, with provenance."""
from __future__ import annotations

import argparse
import collections
import datetime
import json
import math
import os
from pathlib import Path
import shutil

from rnafteval import ledger


def need_for(peak_mb):
    return max(3, math.ceil(float(peak_mb) * 1.3 / 1000.0) + 1)


def calibrate_jobs(jobs, rows, allow_fallback=False):
    exact = collections.defaultdict(list)
    fallback = collections.defaultdict(list)
    for row in rows:
        if row.get("status") != "done" or not row.get("peak_mem_mb"):
            continue
        try:
            peak = float(row["peak_mem_mb"])
        except (TypeError, ValueError):
            continue
        if not math.isfinite(peak) or peak <= 0:
            continue
        exact[(row.get("model"), row.get("task"), row.get("strategy"))].append(peak)
        fallback[(row.get("model"), row.get("strategy"))].append((row.get("task"), peak))

    changes = []
    calibrated = []
    for original in jobs:
        job = dict(original)
        model, task, strategy = job["model"], job["task"], job["strategy"]
        exact_peaks = exact.get((model, task, strategy), [])
        scope = None
        evidence_tasks = [task]
        if exact_peaks:
            peaks = exact_peaks
            scope = "exact_model_task_strategy"
        elif allow_fallback:
            evidence = fallback.get((model, strategy), [])
            evidence_tasks = sorted({item[0] for item in evidence if item[0]})
            if len(evidence) >= 3 and len(evidence_tasks) >= 2:
                peaks = [item[1] for item in evidence]
                scope = "model_strategy_cross_task_max"
        if scope is None:
            calibrated.append(job)
            continue
        peak = max(peaks)
        old = job.get("need_gb")
        new = need_for(peak)
        job["need_gb"] = new
        calibrated.append(job)
        changes.append({
            "rid": job["rid"], "old_need_gb": old, "new_need_gb": new,
            "peak_mem_mb": peak, "evidence_runs": len(peaks), "scope": scope,
            "evidence_tasks": evidence_tasks,
        })
    counts = collections.Counter(change["scope"] for change in changes)
    audit = {
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "formula": "max(3, ceil(max_peak_MB * 1.3 / 1000) + 1)",
        "fallback_allowed": allow_fallback,
        "fallback_rule": "same model+strategy, >=3 done runs across >=2 tasks; use maximum peak",
        "jobs": len(jobs), "changed": sum(
            change["old_need_gb"] != change["new_need_gb"] for change in changes),
        "evidence_counts": dict(counts), "changes": changes,
    }
    return calibrated, audit


def atomic_json(path, value):
    path = Path(path)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n")
    os.replace(temporary, path)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plans", nargs="+")
    parser.add_argument("--allow-fallback", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    rows = ledger.summary()
    for plan in args.plans:
        path = Path(plan)
        jobs = json.loads(path.read_text())
        calibrated, audit = calibrate_jobs(jobs, rows, args.allow_fallback)
        print(json.dumps({"plan": str(path), "jobs": len(jobs),
                          "changed": audit["changed"],
                          "evidence_counts": audit["evidence_counts"]}, indent=2))
        if args.apply:
            backup = path.with_name(path.name + ".pre_need_calibration")
            if not backup.exists():
                shutil.copy2(path, backup)
            atomic_json(path, calibrated)
            atomic_json(path.with_name(path.name + ".need_calibration.json"), audit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
