#!/usr/bin/env python3
"""Export only fully proven best-validation downstream results for figures."""
from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "scripts"))

import expansion_queue as queue
from rnafteval import ledger

FIELDS = (
    "run_id", "model", "task", "strategy", "split", "seed", "metric", "value",
    "n_train", "n_val", "n_test", "best_epoch", "best_val", "epochs_trained",
    "wall_sec", "peak_mem_mb", "lr", "protocol", "stop_reason", "artifact_dir",
    "resolved_artifact_dir", "result_path", "best_checkpoint", "cuda_device",
    "cuda_device_name", "cuda_runtime_version", "tokenizer_name_or_path",
)


def as_job(row):
    return queue._parse_job({
        "task": row["task"], "model": row["model"], "strategy": row["strategy"],
        "split": row["split"], "seed": row["seed"], "protocol": "bestval_v1",
        "rid": row["run_id"], "result_dir": row["out_dir"], "need_gb": 1,
        "module": "rnafteval.finetune_one", "expected_metric": row.get("metric"),
        "args": ["--converge", "--convergence-mode", "bestval",
                 "--patience", str(row.get("patience", 3)),
                 "--min-delta", str(row.get("min_delta", 0.02))],
    }, 0)


def collect(rows=None):
    accepted, rejected = [], []
    candidates = ledger.summary() if rows is None else rows
    for row in candidates:
        if row.get("protocol") != "bestval_v1" or row.get("status") != "done":
            continue
        if row.get("task") == "e6-forgetting":
            continue
        try:
            if not row.get("metric"):
                raise ValueError("primary metric is missing")
            state, reason = queue.proof_state(as_job(row))
            if state != "complete":
                raise ValueError(reason or state)
            runtime = row.get("runtime") or {}
            accepted.append({
                key: row.get(key) for key in FIELDS
                if key not in ("artifact_dir", "resolved_artifact_dir", "result_path",
                               "best_checkpoint", "cuda_device", "cuda_device_name",
                               "cuda_runtime_version", "tokenizer_name_or_path")
            } | {
                "artifact_dir": row["out_dir"],
                "resolved_artifact_dir": str(Path(row["out_dir"]).resolve()),
                "result_path": str(Path(row["out_dir"]) / "result.json"),
                "best_checkpoint": str(Path(row["out_dir"]) / "best.ckpt"),
                "cuda_device": runtime.get("cuda_device"),
                "cuda_device_name": runtime.get("cuda_device_name"),
                "cuda_runtime_version": runtime.get("cuda_runtime_version"),
                "tokenizer_name_or_path": runtime.get("tokenizer_name_or_path"),
            })
        except (KeyError, TypeError, ValueError) as exc:
            rejected.append({"run_id": row.get("run_id"), "reason": str(exc)})
    accepted.sort(key=lambda row: row["run_id"])
    return accepted, rejected


def write_csv(path, rows, fields):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in fields})
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--rejected-output", required=True)
    args = parser.parse_args(argv)
    accepted, rejected = collect()
    write_csv(args.output, accepted, FIELDS)
    Path(args.rejected_output).parent.mkdir(parents=True, exist_ok=True)
    temporary = args.rejected_output + ".tmp"
    with open(temporary, "w") as handle:
        json.dump(rejected, handle, indent=2)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, args.rejected_output)
    print(json.dumps({"accepted": len(accepted), "rejected": len(rejected),
                      "output": args.output, "rejected_output": args.rejected_output},
                     indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
