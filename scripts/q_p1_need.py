#!/usr/bin/env python3
"""Print P1 gap status: groups=N cells_done=X/111 missing=Y  (ledger-authoritative)."""
import json
P = "/mnt/cunyuliu/rna-ft-eval/ledger.jsonl"
rows = []
for l in open(P):
    l = l.strip()
    if not l:
        continue
    try:
        rows.append(json.loads(l))
    except Exception:
        pass

def has(task, model, strat, seed, split, lr):
    for r in rows:
        if (r.get("model") == model and r.get("task") == task and r.get("strategy") == strat
                and r.get("seed") == seed and r.get("split") == split and r.get("status") == "done"):
            if strat == "full" and lr is not None:
                try:
                    if abs(float(r.get("lr", 0)) - float(lr)) > 1e-12:
                        continue
                except Exception:
                    continue
            return True
    return False

groups = {}
def add(task, model, strat, split, lr):
    k = "%s|%s|%s|%s|%s" % (task, model, strat, split, lr)
    groups[k] = sum(1 for s in (17, 29, 43) if has(task, model, strat, s, split, lr))

for st in ("frozen", "lora", "full"):
    for sp in ("random", "family"):
        add("mrl", "RNA-Sc-1M", st, sp, "3e-05" if st == "full" else None)
for sp in ("random", "family"):
    add("modification", "RiNALMo-mega", "frozen", sp, None)
for st in ("frozen", "lora", "full"):
    add("modification", "RNA-Sc-1M", st, "family", "3e-05" if st == "full" else None)
for m in ("RNA-Sc-30M", "RNA-Sc-100M"):
    for sp in ("random", "family"):
        add("modification", m, "frozen", sp, None)
for st in ("frozen", "lora"):
    for sp in ("random", "family"):
        add("secondary-structure", "RiNALMo-mega", st, sp, None)
for m in ("RNA-Sc-1M", "RNA-Sc-30M", "RNA-Sc-100M"):
    for st in ("frozen", "lora", "full"):
        for sp in ("random", "family"):
            add("secondary-structure", m, st, sp, "3e-05" if st == "full" else None)

done = sum(groups.values()); tot = len(groups) * 3
gaps = [k for k, v in groups.items() if v < 3]
print("groups=%d cells_done=%d/%d missing=%d remaining_groups=%d" % (len(groups), done, tot, tot - done, len(gaps)))
for k in gaps:
    print("  gap", k, "done=%d/3" % groups[k])
