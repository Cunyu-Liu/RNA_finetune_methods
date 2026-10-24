#!/usr/bin/env python3
"""Advance the corrected E6 model phase only after real double proofs."""
from __future__ import annotations

import argparse
import fcntl
import os
from pathlib import Path
import sys
import tempfile

import e6_mlm15_proof as proof

PHASES = (
    ("RiNALMo-micro",),
    ("ERNIE-RNA", "RNA-FM"),
    ("RiNALMo-mega",),
    ("RiNALMo-650M",),
)
STRATEGIES = ("lora", "full")
SEEDS = (17, 29, 43)
DEFAULT_MODEL_FILE = Path("/root/rnaft/e6_mlm15_models.active")
DEFAULT_RESULT_ROOT = Path("/root/rna-ft-eval/artifacts/e6")


def cells_for(models):
    return [
        (model, strategy, seed)
        for seed in SEEDS
        for model in models
        for strategy in STRATEGIES
    ]


def read_models(path):
    models = tuple(path.read_text().split())
    if models == ("COMPLETE",) or models in PHASES:
        return models
    raise ValueError("invalid E6 model phase: " + " ".join(models))


def atomic_write(path, text):
    fd, tmp_name = tempfile.mkstemp(
        dir=str(path.parent), prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_name, path)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
        raise


def pending_cells(models, result_root):
    pending = []
    for model, strategy, seed in cells_for(models):
        result_dir = result_root / ("%s_%s_s%d_mlm15fix_seedfix" % (
            model, strategy, seed))
        try:
            proof.verify(result_dir, model, strategy, seed)
        except SystemExit as exc:
            reason = str(exc)
        except Exception as exc:
            reason = "%s: %s" % (type(exc).__name__, exc)
        else:
            continue
        reason = " ".join(reason.split()) or "double proof failed"
        pending.append((model, strategy, seed, reason))
    return pending


def advance(model_file, result_root):
    lock_path = Path(str(model_file) + ".lock")
    with lock_path.open("a+") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        try:
            models = read_models(model_file)
            if models == ("COMPLETE",):
                print("COMPLETE")
                return
            # Recheck earlier phases too: a new protocol generation or a
            # quarantined cell must retarget to the earliest incomplete phase.
            # Any model-file change still happens only here, under the lock.
            for candidate in PHASES:
                pending = pending_cells(candidate, result_root)
                if not pending:
                    continue
                if models != candidate:
                    atomic_write(model_file, " ".join(candidate) + chr(10))
                    print("E6_PHASE RETARGET %s -> %s" % (
                        " ".join(models), " ".join(candidate)))
                total = len(cells_for(candidate))
                print("E6_PHASE PENDING models=%s complete=%d/%d" % (
                    " ".join(candidate), total - len(pending), total))
                for model, strategy, seed, reason in pending:
                    print("PENDING %s %s s%d: %s" % (
                        model, strategy, seed, reason))
                return
            if models != ("COMPLETE",):
                atomic_write(model_file, "COMPLETE" + chr(10))
            print("COMPLETE")
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-file", type=Path, default=DEFAULT_MODEL_FILE)
    parser.add_argument("--result-root", type=Path, default=DEFAULT_RESULT_ROOT)
    args = parser.parse_args(argv)
    try:
        advance(args.model_file, args.result_root)
    except (OSError, ValueError) as exc:
        print("E6_PHASE_ERROR %s" % exc, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
