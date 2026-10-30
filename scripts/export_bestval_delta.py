#!/usr/bin/env python3
"""Incremental best-val export: keep an accepted base CSV and append only new done cells.

Why: scripts/export_bestval.py re-runs queue.proof_state (which loads best.ckpt) for every
ledger row, so a full re-export costs tens of minutes once the ledger grows. Figures only
need accepted rows; existing accepted rows are already audited once and their artifacts do
not change. This delta exporter:

  1. loads the accepted base CSV (must contain run_id),
  2. for every ledger row with protocol=bestval_v1, status=done, not e6/s0-heldout and not
     already in the base, checks the artifact directory: result.json + plateau.json +
     best.ckpt exist and result.json carries metric/value,
  3. writes base rows (byte-identical fields) + new accepted rows, and a rejected JSON.

It does NOT replace the full proof audit for a final release; use export_bestval.py before
freezing a paper table.
"""
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

from rnafteval import ledger

FIELDS = (
    "run_id", "model", "task", "strategy", "split", "seed", "metric", "value",
    "n_train", "n_val", "n_test", "best_epoch", "best_val", "epochs_trained",
    "wall_sec", "peak_mem_mb", "lr", "protocol", "stop_reason", "artifact_dir",
    "resolved_artifact_dir", "result_path", "best_checkpoint", "cuda_device",
    "cuda_device_name", "cuda_runtime_version", "tokenizer_name_or_path",
)


def load_base(path):
    with open(path, newline="") as handle:
        rows = list(csv.DictReader(handle))
    return rows, {row["run_id"] for row in rows}


def new_row(row):
    out_dir = Path(row["out_dir"])
    result = out_dir / "result.json"
    plateau = out_dir / "plateau.json"
    best = out_dir / "best.ckpt"
    missing = [p.name for p in (result, plateau, best) if not p.exists()]
    if missing:
        raise ValueError("missing artifacts: " + ",".join(missing))
    payload = json.loads(result.read_text())
    metric = row.get("metric")
    value = row.get("value")
    if value is None and isinstance(payload.get("metric"), dict):
        value = payload["metric"].get(metric, payload["metric"].get("value"))
    if value is None and isinstance(payload.get("metrics"), dict):
        value = payload["metrics"].get(metric)
    if value is None:
        raise ValueError("primary metric value is missing")
    runtime = row.get("runtime") or payload.get("runtime") or {}
    built = {key: row.get(key) for key in FIELDS
             if key not in ("artifact_dir", "resolved_artifact_dir", "result_path",
                            "best_checkpoint", "cuda_device", "cuda_device_name",
                            "cuda_runtime_version", "tokenizer_name_or_path")}
    built |= {
        "value": value,
        "artifact_dir": str(out_dir),
        "resolved_artifact_dir": str(out_dir.resolve()),
        "result_path": str(result),
        "best_checkpoint": str(best),
        "cuda_device": runtime.get("cuda_device"),
        "cuda_device_name": runtime.get("cuda_device_name"),
        "cuda_runtime_version": runtime.get("cuda_runtime_version"),
        "tokenizer_name_or_path": runtime.get("tokenizer_name_or_path"),
    }
    return built


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, help="已验收的 best-val CSV")
    parser.add_argument("--output", required=True)
    parser.add_argument("--rejected-output", required=True)
    args = parser.parse_args(argv)

    base_rows, seen = load_base(args.base)
    added, rejected = [], []
    for row in ledger.summary():
        if row.get("protocol") != "bestval_v1" or row.get("status") != "done":
            continue
        if row.get("task") == "e6-forgetting" or row.get("split") == "s0-heldout":
            continue
        if row["run_id"] in seen:
            continue
        try:
            added.append(new_row(row))
            seen.add(row["run_id"])
        except (KeyError, TypeError, ValueError, OSError) as exc:
            rejected.append({"run_id": row.get("run_id"), "reason": str(exc)})

    merged = sorted(base_rows + added, key=lambda r: r["run_id"])
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    tmp = output.with_name(output.name + ".tmp")
    with tmp.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for row in merged:
            writer.writerow({key: row.get(key) for key in FIELDS})
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, output)
    Path(args.rejected_output).write_text(json.dumps(rejected, indent=2))
    print(json.dumps({"base": len(base_rows), "added": len(added), "rejected": len(rejected),
                      "total": len(merged), "output": args.output}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
