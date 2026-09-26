#!/usr/bin/env python3
"""Generic plan progress: usage q_plan_need.py <plan.json> -> lines: missing=N total=T done=D"""
import sys, json
P = json.load(open(sys.argv[1]))
rows = []
for l in open("/mnt/cunyuliu/rna-ft-eval/ledger.jsonl"):
    l = l.strip()
    if not l: continue
    try: rows.append(json.loads(l))
    except Exception: pass
def has(t, m, s, sd, sp, lr):
    for r in rows:
        if (r.get("model") == m and r.get("task") == t and r.get("strategy") == s
                and r.get("seed") == sd and r.get("split") == sp and r.get("status") == "done"):
            if s == "full" and lr is not None:
                try:
                    if abs(float(r.get("lr", 0)) - float(lr)) > 1e-12: continue
                except Exception: continue
            return True
    return False
runs = P["runs"]; done = 0
for r in runs:
    if has(r["task"], r["model"], r["strategy"], r["seed"], r["split"], r.get("lr")):
        done += 1
print("missing=%d total=%d done=%d" % (len(runs) - done, len(runs), done))
