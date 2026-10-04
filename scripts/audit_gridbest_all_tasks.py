import json

rows = [json.loads(l) for l in open("/mnt/cunyuliu/rna-ft-eval/ledger.jsonl") if l.strip()]
TASKS = ["modification", "mrl", "secondary-structure"]

def grid_best(model, task):
    cand = {}
    for r in rows:
        if (r.get("model") == model and r.get("task") == task and r.get("strategy") == "full"
                and r.get("seed") == 101 and r.get("split") == "random" and r.get("status") == "done"):
            lr = str(r.get("lr"))
            if lr in ("0.0003", "3e-4"):
                continue
            cand[lr] = r.get("value")
    if not cand:
        return None, None
    b = max(cand, key=lambda k: cand[k] or -1)
    return b, cand

total_viol = {}
grid_summary = {}
for task in TASKS:
    models = set(r.get("model") for r in rows if r.get("task") == task and r.get("strategy") == "full"
                 and "ck" not in str(r.get("model")))
    for m in sorted(models):
        b, cand = grid_best(m, task)
        grid_summary[(task, m)] = (b, cand)
        if b is None:
            continue
        for sp in ("random", "family"):
            for sd in (17, 29, 43):
                for r in rows:
                    if (r.get("model") == m and r.get("task") == task and r.get("strategy") == "full"
                            and r.get("split") == sp and r.get("seed") == sd and r.get("status") == "done"):
                        lr = str(r.get("lr"))
                        if lr in ("0.0003", "3e-4"):
                            continue
                        if lr != b:
                            key = (m, task, sp, lr, b)
                            total_viol.setdefault(key, []).append((sd, r.get("value")))

print("===== 网格现状（三任务） =====")
for (task, m), (b, cand) in sorted(grid_summary.items()):
    if b:
        print("  %-22s %-16s %s best=%s" % (task, m, {k: round(v, 3) for k, v in cand.items()}, b))
    else:
        print("  %-22s %-16s NO-GRID" % (task, m))

print("\n===== VIOLATIONS（tuned formal 行用非 grid-best LR，跨三任务） =====")
for (m, task, sp, used, want), seeds in sorted(total_viol.items()):
    b, cand = grid_summary[(task, m)]
    gap = (cand.get(want) or 0) - (cand.get(used) or 0)
    print("  %-16s %-22s %-7s used=%s want=%s gap=%.3f seeds=%s" % (
        m, task, sp, used, want, gap, [(s, round(v, 3) if v is not None else None) for s, v in seeds]))
print("\ntotal violation combos:", len(total_viol))
