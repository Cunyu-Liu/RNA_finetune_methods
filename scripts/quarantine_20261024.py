"""Quarantine confirmed-invalid 2026-10-24 results without deleting evidence.

Run with --dry-run first, then --apply. Idempotent for already-quarantined rows.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path

from rnafteval import ledger

B20_TASKS = {"spliceai", "degradation", "ssi"}
B20_MODELS = {
    "RiNALMo-micro", "RiNALMo-mega", "RiNALMo-650M", "ERNIE-RNA",
    "RNA-FM", "SpliceBERT", "NucleicBERT",
}
OFFICIAL_E6 = {"RiNALMo-micro", "RiNALMo-mega", "RiNALMo-650M",
               "ERNIE-RNA", "RNA-FM"}
ARTIFACTS = Path("/root/rnaft/artifacts")
BACKUP = Path("/teams/HoulabData_1788502323/liucunyu/rna-ft-eval/quarantine_20261024")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def atomic_json(path: Path, value) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w") as fh:
        json.dump(value, fh, indent=2, ensure_ascii=False)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def classify(row: dict) -> str | None:
    if row.get("status") not in {"done", "running", "pending"}:
        return None
    rid = row.get("run_id", "")
    if (row.get("task") in B20_TASKS and row.get("model") in B20_MODELS
            and "_b20fix" not in rid):
        return "b20"
    if (row.get("task") == "e6-forgetting"
            and row.get("model") in OFFICIAL_E6 and "_mlm15fix" not in rid):
        return "mlm"
    return None


def result_path(row: dict, kind: str) -> Path:
    if kind == "mlm":
        name = Path(row.get("out_dir", "")).name
        return ARTIFACTS / "e6" / name / "result.json"
    return ARTIFACTS / row["run_id"] / "result.json"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    rows = ledger.summary()
    selected = [(row, classify(row)) for row in rows]
    selected = [(row, kind) for row, kind in selected if kind]
    counts = {}
    for row, kind in selected:
        key = (kind, row["status"])
        counts[key] = counts.get(key, 0) + 1
    print("QUARANTINE_PREVIEW", {f"{k[0]}:{k[1]}": v for k, v in sorted(counts.items())})
    print("AFFECTED_RUNS", len(selected))
    print("ARTIFACTS_PRESENT", sum(result_path(row, kind).is_file()
                                   for row, kind in selected))
    if not args.apply:
        return
    if not selected:
        print("QUARANTINE_ALREADY_COMPLETE")
        return

    BACKUP.mkdir(parents=True, exist_ok=True)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    manifest = {"created_utc": now, "rows": [], "artifacts": []}
    with ledger._locked():
        current = ledger._load()
        atomic_json(BACKUP / "ledger_pre_quarantine.json", current)
        current_by_id = {r["run_id"]: r for r in current}
        actions = {}
        for old, kind in selected:
            row = current_by_id[old["run_id"]]
            source = result_path(row, kind)
            if source.is_file():
                target = source.with_name(
                    "result.invalid_%s.json" % ("b20" if kind == "b20" else "unmasked_mlm"))
                if target.exists():
                    raise RuntimeError("quarantine target already exists: %s" % target)
                actions[row["run_id"]] = (source, target, sha256(source))
        for old, kind in selected:
            row = current_by_id[old["run_id"]]
            previous = row["status"]
            reason = (
                "B20 token/base misalignment: special tokens were supervised "
                "and base labels were offset" if kind == "b20" else
                "Official MLM NLL used unmasked inputs at target positions")
            row.update({
                "previous_status": previous,
                "status": "invalid" if previous == "done" else "cancelled",
                "invalid_reason": reason,
                "invalidated_utc": now,
                "updated_utc": now,
            })
            manifest["rows"].append({
                "run_id": row["run_id"], "kind": kind,
                "previous_status": previous, "new_status": row["status"],
            })
            if row["run_id"] in actions:
                source, target, digest = actions[row["run_id"]]
                os.replace(source, target)
                manifest["artifacts"].append({
                    "run_id": row["run_id"], "from": str(source),
                    "to": str(target), "sha256": digest,
                })
        ledger._write(current)

    verified = [r for r in ledger._load() if classify(r)]
    if verified:
        raise RuntimeError("quarantine verification failed: %d active rows" % len(verified))
    atomic_json(BACKUP / "manifest.json", manifest)
    print("QUARANTINE_OK", {
        "rows": len(manifest["rows"]), "artifacts": len(manifest["artifacts"]),
        "backup": str(BACKUP),
    })


if __name__ == "__main__":
    main()
