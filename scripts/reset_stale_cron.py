#!/usr/bin/env python3
"""Reset stale running tasks (no live finetune process) to pending. Run via cron."""
import sys, subprocess, datetime, importlib.util, os
spec = importlib.util.spec_from_file_location("ledger_mod", "/home/cunyuliu/rna-ft-eval/rnafteval/ledger.py")
led = importlib.util.module_from_spec(spec); spec.loader.exec_module(led)
live = set()
try:
    out = subprocess.check_output(["ps", "-eo", "args"], text=True)
    for l in out.splitlines():
        if "rnafteval.finetune" in l: live.add(l)
except: pass
def has_live(m, s, sd, sp):
    for l in live:
        if ("--model %s " % m) in l and ("--strategy %s " % s) in l and ("--seed %d " % sd) in l and ("--split %s " % sp) in l: return True
    return False
with led._locked():
    rows = led._load()
    reset = []
    for r in rows:
        if r.get("status") == "running":
            m, s, sd, sp = r.get("model"), r.get("strategy"), r.get("seed"), r.get("split")
            if not has_live(m, s, sd, sp):
                r["status"] = "pending"
                r["note"] = "stale-auto-reset %s" % datetime.datetime.now(datetime.timezone.utc).isoformat()[:19]
                r["updated_utc"] = led._now()
                reset.append("%s %s %s s%s" % (m, s, sp, sd))
    led._write(rows)
if reset:
    print("[%s] reset %d stale: %s" % (datetime.datetime.now().isoformat()[:19], len(reset), ", ".join(reset)))
