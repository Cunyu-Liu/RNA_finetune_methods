"""Sync ledger rows from on-disk result.json when a queue reports

    rc=0 but proof is conflict / valid result proof but ledger is not done

Run on the training host with the same env as the queues. It never invents
numbers: every row it writes must have result.json + plateau.json (CONVERGED)
+ best.ckpt on disk.
"""
from __future__ import annotations

import glob
import json
import os
import sys

sys.path.insert(0, "/home/cunyuliu/rna-ft-eval")
from rnafteval import ledger  # noqa: E402

STATUS_DIR = "/teams/HoulabData_1788502323/liucunyu/rna-ft-eval/status"
REASONS = ("valid result proof but ledger is not done",
           "proof is conflict")


def converged(result_dir):
    rp = os.path.join(result_dir, "result.json")
    pp = os.path.join(result_dir, "plateau.json")
    cp = os.path.join(result_dir, "best.ckpt")
    if not (os.path.exists(rp) and os.path.exists(pp) and os.path.exists(cp)):
        return None, "missing result/plateau/ckpt"
    result = json.load(open(rp))
    plateau = json.load(open(pp))
    if result.get("protocol") != "bestval_v1":
        return None, "protocol is not bestval_v1"
    if result.get("status") != "CONVERGED":
        return None, "result status is %s" % result.get("status")
    if plateau.get("status") != "CONVERGED":
        return None, "plateau status is %s" % plateau.get("status")
    if result.get("best_checkpoint") != "best.ckpt":
        return None, "best_checkpoint is not best.ckpt"
    return result, "ok"


def main(apply=False):
    fixed, skipped = [], []
    for mf in glob.glob(os.path.join(STATUS_DIR, "*", "manifest.jsonl")):
        for line in open(mf):
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            if rec.get("status") != "failed":
                continue
            reason = rec.get("reason") or ""
            if not any(tag in reason for tag in REASONS):
                continue
            rid = rec.get("rid")
            result_dir = rec.get("result_dir") or ""
            result, why = converged(result_dir)
            if result is None:
                skipped.append((rid, why))
                continue
            row = ledger.by_run_id(rid)
            if row is None:
                skipped.append((rid, "ledger row missing"))
                continue
            fixed.append((rid, result.get("metric"), result.get("value"),
                          row.get("status")))
            if apply:
                ledger.update(
                    rid, "done",
                    value=result.get("value"), metric=result.get("metric"),
                    note="20261031 sync: ledger status repaired from "
                         "result/plateau/ckpt proof")
    print("SYNC fixable=%d skipped=%d apply=%s" % (len(fixed), len(skipped), apply))
    for rid, metric, value, old in fixed:
        print("  FIX %s %s=%s (was %s)" % (rid, metric, value, old))
    for rid, why in skipped:
        print("  SKIP %s %s" % (rid, why))
    return 0


if __name__ == "__main__":
    sys.exit(main("--apply" in sys.argv))
