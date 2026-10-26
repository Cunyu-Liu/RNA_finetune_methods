#!/usr/bin/env python3
"""Validation-only convergence audit for valplateau_v2 artifacts.

Only a complete v2 validation curve with a matching converged result can be
CONVERGED. Train-only v1 and older fixed-epoch artifacts remain explicitly
LEGACY/TRAIN_ONLY and can never satisfy the new acceptance gate.

Exit codes: 0 = all audited cells converged; 1 = at least one
not-converged/invalid; 2 = usage error.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from rnafteval.valplateau import (
    ABS_FLOOR, LEGACY_PROTOCOL, MIN_DELTA, PATIENCE, PROTOCOL, STOP_REASON,
    classify)

ROOT = "/root/rna-ft-eval"
E6_DIR = os.path.join(ROOT, "artifacts", "e6")


def audit_cell(result_dir, min_delta=MIN_DELTA, patience=PATIENCE,
               abs_floor=ABS_FLOOR):
    p = Path(result_dir) / "plateau.json"
    rj = Path(result_dir) / "result.json"
    cell = os.path.basename(result_dir)
    if not rj.exists():
        return cell, "NO_RESULT", "result.json missing"
    if not p.exists():
        return cell, "LEGACY", "no plateau.json (fixed-epoch protocol)"
    try:
        d = json.loads(p.read_text())
    except (ValueError, OSError) as e:
        return cell, "INVALID", "plateau.json unreadable: %s" % e
    protocol = d.get("protocol")
    if protocol == LEGACY_PROTOCOL:
        return cell, "TRAIN_ONLY", "valplateau_v1 used epoch_train_losses"
    if protocol != PROTOCOL:
        return cell, "INVALID", "unknown protocol %r" % protocol
    if d.get("loss_source") != "validation":
        return cell, "INVALID", "v2 loss_source is not validation"
    losses = d.get("epoch_val_losses", [])
    status, detail = classify(losses, min_delta, patience, abs_floor)
    if status != "CONVERGED":
        return cell, status, "validation: " + detail
    try:
        result = json.loads(rj.read_text())
    except (ValueError, OSError) as e:
        return cell, "INVALID", "result.json unreadable: %s" % e
    if d.get("status") != "CONVERGED" or d.get("stop_reason") != STOP_REASON:
        return cell, "NOT_CONVERGED", "plateau has no converged stop evidence"
    if result.get("protocol") != PROTOCOL:
        return cell, "INVALID", "result protocol is not valplateau_v2"
    if result.get("status") != "CONVERGED":
        return cell, "NOT_CONVERGED", "result status is not CONVERGED"
    if result.get("loss_source") != "validation":
        return cell, "INVALID", "result loss_source is not validation"
    if result.get("epoch_val_losses") != losses:
        return cell, "INVALID", "result/plateau validation curves differ"
    if result.get("stop_reason") != STOP_REASON:
        return cell, "NOT_CONVERGED", "result has no converged stop_reason"
    if result.get("epochs_trained") != len(losses):
        return cell, "INVALID", "epochs_trained does not match validation curve"
    if d.get("updated_epoch") != len(losses) - 1:
        return cell, "INVALID", "updated_epoch does not match validation curve"
    return cell, "CONVERGED", "validation: " + detail


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
    if (root / "result.json").exists() or (root / "plateau.json").exists():
        cells.append(audit_cell(str(root), args.min_delta, args.patience))
    else:
        for d in sorted(root.iterdir()):
            if not d.is_dir():
                continue
            cells.append(audit_cell(str(d), args.min_delta, args.patience))
    if not cells:
        print("EMPTY no artifact cells found")
        if args.json_out:
            Path(args.json_out).write_text("[]")
        return 1

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
    bad = sum(status != "CONVERGED" for _cell, status, _detail in cells)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
