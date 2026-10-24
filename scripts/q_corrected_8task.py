#!/usr/bin/env python3
"""B20-corrected spliceai/degradation/ssi canonical cell runner."""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import math
import os
from pathlib import Path
import shlex
import subprocess
import sys
import time
from dataclasses import dataclass
from types import SimpleNamespace

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from rnafteval import finetune_regbase, finetune_spl, ledger

SPLICE_MODELS = (
    "RiNALMo-micro", "RiNALMo-mega", "RiNALMo-650M", "ERNIE-RNA",
    "RNA-FM", "RNA-Sc-300M", "NucleicBERT",
)
REG_MODELS = tuple(m for m in SPLICE_MODELS if m != "RiNALMo-micro")
STRATEGIES = ("frozen", "lora", "full")
SPLITS = ("random", "family")
SEEDS = (17, 29, 43)
ARTIFACTS_ROOT = Path(finetune_spl.ROOT) / "artifacts"
LOG_ROOT = Path("/root/rnaft/logs/q_corrected_8task")
SPLICE_TIMEOUT_S = 24 * 60 * 60
REGBASE_TIMEOUT_S = 12 * 60 * 60


@dataclass(frozen=True)
class Cell:
    task: str
    model: str
    strategy: str
    split: str
    seed: int

    @property
    def key(self):
        return self.task, self.model, self.strategy, self.seed, self.split

    @property
    def epochs(self):
        return 6 if self.task == "spliceai" else 10

    @property
    def lr_arg(self):
        return "1e-5" if self.strategy == "full" else "3e-4"

    @property
    def lr(self):
        return float(self.lr_arg)

    @property
    def batch_size(self):
        if self.task != "spliceai":
            return 8
        if self.model == "NucleicBERT":
            return 8
        if self.strategy == "full" and self.model in (
                "RiNALMo-650M", "RiNALMo-mega"):
            return 8
        return 16

    @property
    def timeout_s(self):
        return SPLICE_TIMEOUT_S if self.task == "spliceai" else REGBASE_TIMEOUT_S

    @property
    def metric(self):
        return "MACRO_F1" if self.task == "spliceai" else "PCC"


def canonical_cells():
    cells = []
    for model in SPLICE_MODELS:
        tasks = ("spliceai",) if model == "RiNALMo-micro" else (
            "spliceai", "degradation", "ssi")
        for strategy in STRATEGIES:
            for split in SPLITS:
                for seed in SEEDS:
                    for task in tasks:
                        cells.append(Cell(task, model, strategy, split, seed))
    return cells


def runner_for(cell):
    return finetune_spl if cell.task == "spliceai" else finetune_regbase


def rid_for(cell):
    args = SimpleNamespace(lr=cell.lr, rank=8, n_train=0,
                           epochs=cell.epochs, smoke=False)
    extra = runner_for(cell)._run_extra(args)
    return ledger.run_id(cell.model, cell.task, cell.strategy, cell.seed,
                         cell.split, extra=extra)


def result_path(cell):
    return ARTIFACTS_ROOT / rid_for(cell) / "result.json"


def build_command(cell, device=0):
    module = ("rnafteval.finetune_spl" if cell.task == "spliceai"
              else "rnafteval.finetune_regbase")
    return [
        sys.executable, "-m", module,
        "--model", cell.model, "--task", cell.task,
        "--strategy", cell.strategy, "--seed", str(cell.seed),
        "--split", cell.split, "--device", str(device),
        "--epochs", str(cell.epochs), "--batch-size", str(cell.batch_size),
        "--lr", cell.lr_arg,
    ]


def child_env():
    env = os.environ.copy()
    required = ["/root/rnaft/pypath", str(REPO_ROOT), "/home/cunyuliu/rna-sc"]
    old = env.get("PYTHONPATH", "").split(os.pathsep)
    env["PYTHONPATH"] = os.pathsep.join(
        dict.fromkeys(p for p in required + old if p))
    env.setdefault("HF_HOME", "/root/hf_home")
    env.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
    env.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
    return env


def result_error(cell, payload, rid):
    if not isinstance(payload, dict):
        return "result JSON is not an object"
    expected = {
        "run_id": rid, "task": cell.task, "model": cell.model,
        "seed": cell.seed, "split": cell.split,
    }
    errors = ["%s mismatch" % key for key, value in expected.items()
              if payload.get(key) != value]
    if payload.get("metric") != cell.metric:
        errors.append("primary metric mismatch")
    value = payload.get("value")
    try:
        finite = (not isinstance(value, bool)
                  and isinstance(value, (int, float)) and math.isfinite(value))
    except (TypeError, ValueError, OverflowError):
        finite = False
    if not finite:
        errors.append("primary metric value is not finite numeric")
    return "; ".join(errors)


def proof_state(cell):
    """complete = double proof; runnable = no result and ledger not done."""
    rid = rid_for(cell)
    path = result_path(cell)
    row = ledger.by_run_id(rid)
    ledger_done = bool(row and row.get("status") == "done")
    if not path.exists():
        if ledger_done:
            return "conflict", "ledger done but result.json is missing"
        return "runnable", ""
    try:
        with path.open() as fh:
            payload = json.load(fh)
    except (OSError, ValueError) as exc:
        return "conflict", "invalid result.json: %s" % exc
    error = result_error(cell, payload, rid)
    if error:
        return "conflict", error
    if not ledger_done:
        return "conflict", "valid result.json but ledger is not done"
    return "complete", ""


def run_cell(cell, device=0, log_root=None):
    rid = rid_for(cell)
    path = result_path(cell)
    cmd = build_command(cell, device)
    root = LOG_ROOT if log_root is None else Path(log_root)
    log_path = root / cell.task / (cell.model + ".log")
    log_path.parent.mkdir(parents=True, exist_ok=True)

    with log_path.open("a", buffering=1) as log:
        def finish(status, ok, rc, wall, reason=""):
            record = {
                "run_id": rid, "task": cell.task, "model": cell.model,
                "strategy": cell.strategy, "seed": cell.seed,
                "split": cell.split, "command": cmd, "rc": rc,
                "wall_sec": round(wall, 3), "result_path": str(path),
                "log_path": str(log_path), "status": status, "ok": ok,
                "reason": reason,
            }
            print("RECORD " + json.dumps(record, sort_keys=True),
                  file=log, flush=True)
            return record

        state, reason = proof_state(cell)
        if state == "complete":
            return finish("skipped", True, None, 0.0)
        if state == "conflict":
            return finish("failed", False, None, 0.0, reason)

        print("\n=== CELL %s ===\nCOMMAND %s" % (rid, shlex.join(cmd)),
              file=log, flush=True)
        start = time.monotonic()
        try:
            proc = subprocess.run(
                cmd, cwd=str(REPO_ROOT), env=child_env(),
                timeout=cell.timeout_s, stdout=log,
                stderr=subprocess.STDOUT, check=False,
            )
            rc = proc.returncode
            reason = ""
        except subprocess.TimeoutExpired:
            rc = "TIMEOUT"
            reason = "cell timeout %ds" % cell.timeout_s
        except OSError as exc:
            rc = None
            reason = "subprocess launch failed: %s" % exc
        wall = time.monotonic() - start
        if rc != 0:
            return finish("failed", False, rc, wall,
                          reason or "runner exited %s" % rc)
        state, reason = proof_state(cell)
        if state != "complete":
            return finish("failed", False, rc, wall,
                          reason or "rc=0 but ledger/result double proof is incomplete")
        return finish("done", True, rc, wall)


def model_worker(model, cells, device, log_root=None):
    return [run_cell(cell, device, log_root) for cell in cells]


def parse_models(values):
    names = []
    for value in values:
        names.extend(name.strip() for name in value.split(",") if name.strip())
    names = list(dict.fromkeys(names))
    unknown = set(names) - set(SPLICE_MODELS)
    if unknown:
        raise ValueError("unknown models: %s" % ",".join(sorted(unknown)))
    if not names:
        raise ValueError("no models selected")
    return names


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--models", nargs="+",
                        help="model names, space- or comma-separated")
    parser.add_argument("--tasks", nargs="+",
                        choices=("spliceai", "degradation", "ssi"),
                        default=["spliceai", "degradation", "ssi"])
    parser.add_argument("--device", type=int, default=0)
    args = parser.parse_args(argv)
    if args.workers < 1:
        parser.error("--workers must be >= 1")
    try:
        models = parse_models(args.models or list(SPLICE_MODELS))
    except ValueError as exc:
        parser.error(str(exc))

    cells = [c for c in canonical_cells()
             if c.model in set(models) and c.task in set(args.tasks)]
    if not cells:
        parser.error("no cells selected")
    by_model = {m: [c for c in cells if c.model == m] for m in models}
    outcomes, worker_errors = [], []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(model_worker, model, model_cells, args.device): model
            for model, model_cells in by_model.items()
        }
        for future in concurrent.futures.as_completed(futures):
            model = futures[future]
            try:
                outcomes.extend(future.result())
            except Exception as exc:
                worker_errors.append("%s: %s" % (model, exc))

    failures = [o for o in outcomes if not o["ok"]]
    complete = (not worker_errors and not failures
                and len(outcomes) == len(cells))
    if complete:
        skipped = sum(o["status"] == "skipped" for o in outcomes)
        print("CORRECTED_DONE cells=%d ran=%d skipped=%d" %
              (len(cells), len(cells) - skipped, skipped), flush=True)
        return 0

    print("INCOMPLETE cells=%d complete=%d failed=%d worker_errors=%d" %
          (len(cells), sum(o["ok"] for o in outcomes), len(failures),
           len(worker_errors)), flush=True)
    for outcome in sorted(failures, key=lambda o: o["run_id"]):
        print("%s: %s" % (outcome["run_id"], outcome["reason"]),
              file=sys.stderr, flush=True)
    for error in worker_errors:
        print(error, file=sys.stderr, flush=True)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
