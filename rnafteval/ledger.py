"""Run registry ledger — forked pattern from rna-sc ledger.py (Z5, flock-safe).

Tracks every (model, task, strategy, seed, split) combination:
  claim() refuses duplicate launches; update() keeps one row per run.
Artifacts root: /mnt/cunyuliu/rna-ft-eval
"""
from __future__ import annotations

import contextlib
import datetime
import fcntl
import json
import os

ROOT = "/mnt/cunyuliu/rna-ft-eval"
LEDGER = os.path.join(ROOT, "ledger.jsonl")
LOCK = os.path.join(ROOT, "ledger.lock")

FORMAL_SEEDS = (17, 29, 43)
TUNING_SEED = 101
STRATEGIES = ("frozen", "lora", "head-only", "full")
SPLITS = ("random", "family")


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


@contextlib.contextmanager
def _locked():
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    with open(LOCK, "a") as lf:
        fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lf.fileno(), fcntl.LOCK_UN)


def _load() -> list[dict]:
    if not os.path.exists(LEDGER):
        return []
    rows = []
    with open(LEDGER) as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return rows


def _write(rows: list[dict]) -> None:
    tmp = LEDGER + ".tmp"
    with open(tmp, "w") as fh:
        for r in rows:
            fh.write(json.dumps(r, default=str) + "\n")
    os.replace(tmp, LEDGER)


def run_id(model: str, task: str, strategy: str, seed: int, split: str,
           extra: str = "") -> str:
    return "ft_%s_%s_%s_s%d_%s%s" % (
        model.replace("-", "").replace(".", "").lower(),
        task.replace("_", "").replace("-", "").lower(),
        strategy.replace("-", "").lower(), seed, split, extra)


def claim(model: str, task: str, strategy: str, seed: int, split: str,
          device: int = -1, out_dir: str = "", note: str = "",
          extra: str = "") -> dict:
    rid = run_id(model, task, strategy, seed, split, extra)
    with _locked():
        rows = _load()
        for r in rows:
            if r["run_id"] == rid and r.get("status") in ("running", "done"):
                return {"claimed": False, "reason": "already %s" % r["status"],
                        "row": r}
        row = {"run_id": rid, "model": model, "task": task,
               "strategy": strategy, "seed": seed, "split": split,
               "device": device, "out_dir": out_dir, "status": "pending",
               "updated_utc": _now(), "note": note}
        if extra:
            row["extra"] = extra
        rows.append(row)
        _write(rows)
    return {"claimed": True, "row": row}


def update(run_id: str, status: str, **fields) -> dict | None:
    out = None
    with _locked():
        rows = _load()
        for r in rows:
            if r["run_id"] == run_id:
                r["status"] = status
                r["updated_utc"] = _now()
                r.update(fields)
                out = r
        _write(rows)
    return out


def by_run_id(rid: str) -> dict | None:
    for r in _load():
        if r["run_id"] == rid:
            return r
    return None


def summary() -> list[dict]:
    return _load()


def counts_by(strategy: str | None = None) -> dict:
    out: dict[str, int] = {}
    for r in _load():
        if strategy and r.get("strategy") != strategy:
            continue
        out[r.get("status", "?")] = out.get(r.get("status", "?"), 0) + 1
    return out


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "list":
        for r in summary():
            print(json.dumps(r))
    else:
        for strat in ["all"] + list(STRATEGIES):
            print(strat, counts_by(None if strat == "all" else strat))
