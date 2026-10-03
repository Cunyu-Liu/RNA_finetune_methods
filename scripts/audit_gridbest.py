import json

rows = [json.loads(l) for l in open("/mnt/cunyuliu/rna-ft-eval/ledger.jsonl") if l.strip()]
# Exclude A8 default-LR arm (3e-4) which is the INTENTIONAL contrast group; focus on tuned-arm compliance
# tuned arm = _lr suffix rows (or lr in {1e-5, 3e-5}); default arm = 3e-4/0.0003 (A8 对照组, 有意保留)
models = {}
for r in rows:
    if r.get("strategy") != "full" or r.get("status") != "done": continue
    if r.get("task") == "noncoding-rna-family" and r.get("seed") == 101 and r.get("split") == "random":
        lr = str(r.get("lr"))
        if lr in ("0.0003", "3e-4"):  # 3e-4 grid point is the A8 arm, not a grid candidate for tuned
            continue
        models.setdefault(r.get("model"), {})[lr] = r.get("value")

print("=== s101 grid (tuned candidates only 1e-5/3e-5/1e-4) ===")
best = {}
for m, lrs in sorted(models.items()):
    bl = max(lrs, key=lambda k: lrs[k] or -1)
    best[m] = bl
    print("  %-16s %s best=%s" % (m, {k: round(v,3) for k,v in lrs.items()}, bl))

print("\n=== TUNED-ARM formal runs using NON-best LR (真违规: tuned 臂必须用 grid-best) ===")
viol = {}
for r in rows:
    if r.get("strategy") != "full" or r.get("status") != "done": continue
    if r.get("task") != "noncoding-rna-family" or r.get("seed") in (101, 999, 998): continue
    m = r.get("model")
    if m not in best: continue
    used = str(r.get("lr"))
    if used in ("0.0003", "3e-4"):  # default arm — intentional A8 contrast, OK
        continue
    if used != best[m]:
        key = (m, r.get("split"), used, best[m])
        viol.setdefault(key, []).append((r.get("seed"), r.get("value")))

for (m, sp, used, b), seeds in sorted(viol.items()):
    print("  %-16s %-7s used=%s but grid-best=%s  seeds=%s" % (m, sp, used, b, [(s, round(v,3) if v else v) for s,v in seeds]))
print("\nreal violations:", len(viol))
