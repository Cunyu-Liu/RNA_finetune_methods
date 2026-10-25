#!/usr/bin/env python3
"""valplateau_v1 convergence audit (spec §10.14-⑤).

Reads plateau.json (written atomically per epoch by the runners) and
classifies each cell as converged / not-converged per a preregistered
min_delta + patience rule, or legacy when no plateau.json exists.

Rules (frozen, do not tune post hoc):
  - A cell is CONVERGED if the last `patience` epochs all sit within
    min_delta (relative) of the best (lowest) loss seen so far.
  - A cell is NOT_CONVERGED otherwise (loss still materially decreasing).
  - LEGACY: no plateau.json (fixed-epoch runs before 2026-10-25) —
    reported separately, never pooled with audited cells.
  - Instability guard: NaN or non-finite losses make the cell INVALID.

Exit codes: 0 = all audited cells converged; 1 = at least one
not-converged/invalid; 2 = usage error.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path

ROOT = "/root/rna-ft-eval"
E6_DIR = os.path.join(ROOT, "artifacts", "e6")

MIN_DELTA = 0.02   # relative improvement threshold (2%)
PATIENCE = 3       # trailing epochs that must be flat


def classify(losses, min_delta=MIN_DELTA, patience=PATIENCE):
    """Return (status, detail) for a list of per-epoch train losses."""
    if not losses:
        return "EMPTY", "no epochs recorded"
    if any(not math.isfinite(x) for x in losses):
        return "INVALID", "non-finite epoch loss"
    if len(losses) < patience + 1:
        return "TOO_SHORT", "n=%d < patience+1=%d" % (len(losses),
                                                      patience + 1)
    best = min(losses)
    if best <= 0:
        return "INVALID", "non-positive loss cannot use relative delta"
    tail = losses[-patience:]
    if all(x <= best * (1.0 + min_delta) for x in tail):
        # flat tail at (or near) the running best → converged
        return "CONVERGED", "tail within %.1f%% of best %.4f" % (
            min_delta * 100, best)
    return "NOT_CONVERGED", "tail still improving (best %.4f, tail %s)" % (
        best, ["%.4f" % x for x in tail])


def audit_cell(result_dir, min_delta, patience):
    p = Path(result_dir) / "plateau.json"
    rj = Path(result_dir) / "result.json"
    cell = os.path.basename(result_dir)
    if not rj.exists():
        return cell, "NO_RESULT", "result.json missing"
    if not p.exists():
        # legacy protocol: fixed-epoch run predating plateau persistence
        return cell, "LEGACY", "no plateau.json (fixed-epoch protocol)"
    try:
        d = json.loads(p.read_text())
    except (ValueError, OSError) as e:
        return cell, "INVALID", "plateau.json unreadable: %s" % e
    losses = d.get("epoch_train_losses", [])
    if d.get("protocol") != "valplateau_v1":
        return cell, "INVALID", "unknown protocol %r" % d.get("protocol")
    status, detail = classify(losses, min_delta, patience)
    return cell, status, detail


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--e6-root", default=E6_DIR)
    ap.add_argument("--min-delta", type=float, default=MIN_DELTA,
                    help="relative improvement threshold")
    ap.add_argument("--patience", type=int, default=PATIENCE,
                    help="flat-tail epochs required for convergence")
    ap.add_argument("--json-out", default=None,
                    help="optional path for machine-readable report")
    args = ap.parse_args(argv)

    cells = []
    root = Path(args.e6_root)
    if not root.is_dir():
        print("no e6 artifacts dir: %s" % root, file=sys.stderr)
        return 2
    for d in sorted(root.iterdir()):
        if not d.is_dir():
            continue
        cells.append(audit_cell(str(d), args.min_delta, args.patience))

    counts = {}
    for _cell, status, _detail in cells:
        counts[status] = counts.get(status, 0) + 1
    for cell, status, detail in cells:
        print("%-14s %-13s %s" % (status, cell[:48], detail))
    print("SUMMARY", json.dumps(counts, sort_keys=True))
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(
            [{"cell": c, "status": s, "detail": d} for c, s, d in cells],
            indent=2))
    bad = counts.get("NOT_CONVERGED", 0) + counts.get("INVALID", 0)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
