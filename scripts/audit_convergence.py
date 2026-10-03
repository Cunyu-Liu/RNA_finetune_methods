import json, os, glob, re, collections

R = "/mnt/cunyuliu/rna-ft-eval"
rows = [json.loads(l) for l in open(R + "/ledger.jsonl") if l.strip()]
done = [r for r in rows if r.get("status") == "done" and not r.get("smoke", False)]

# pass 2: scan ALL logs for run_id mentions followed by epoch lines OR standalone "epoch N loss" blocks
# Many queue scripts print run_id then run the module whose stdout goes to same log.
# Robust approach: for each log, track last-seen "cell/run" context lines:
#   patterns that set context: "RUN ...|model|strat|seed|split", OR a line containing "ft_...._s.._.." (run_id itself)
# then attribute epoch lines to most recent run_id-like token in the same file.
pat_rid = re.compile(r"(ft_[a-z0-9]+_[a-z]+(?:_[a-z\-]+)?_[a-z\-]+_s\d+_\w+(?:_lr[0-9e.\-]+)?)")
pat_ep = re.compile(r"^epoch (\d+) loss ([0-9.]+)\s*$")

traces = collections.defaultdict(list)
for lf in sorted(glob.glob(R + "/logs/*.log")):
    try:
        lines = open(lf, errors="ignore").read().splitlines()
    except Exception:
        continue
    cur = None
    for ln in lines:
        m = pat_ep.match(ln.strip())
        if m and cur:
            traces[cur].append((int(m.group(1)), float(m.group(2))))
            continue
        m = pat_rid.search(ln)
        if m:
            cur = m.group(1)
print("run_ids with traces (pass2):", len(traces))
witht = {k: v for k, v in traces.items() if len(v) >= 2}
print("with >=2 epochs:", len(witht))

matched, underfit, dropping, no_trace = 0, [], [], []
for r in done:
    rid = r.get("run_id","")
    if "e6" in rid or "collapse" in rid:
        continue
    tr = witht.get(rid)
    if not tr:
        no_trace.append(rid)
        continue
    matched += 1
    best = {}
    for ep, l in tr:
        best[ep] = min(best.get(ep, 1e9), l)
    eps = sorted(best)
    if len(eps) < 3:
        continue
    ls = [best[e] for e in eps]
    last, prev = ls[-1], ls[-2]
    drop_last = (prev - last) / max(prev, 1e-9)
    if last > 0.9 and drop_last > 0.05:
        underfit.append((rid, len(eps), ls))
    elif drop_last > 0.15:
        dropping.append((rid, len(eps), ls))

print("matched:", matched, "no_trace:", len(no_trace))
cnt = collections.Counter()
for rid in no_trace:
    m = re.match(r"ft_[a-z0-9]+_[a-z]+_([a-z\-]+)_s\d+_", rid)
    if m: cnt[m.group(1)] += 1
print("no_trace by strategy:", dict(cnt))
print("\n=== UNDERFIT-FLAG (last>0.9 & drop>5%) — count:", len(underfit))
for rid, n, ls in sorted(underfit):
    print("  %-62s ep%-3d tail=%s drop=%.1f%%" % (rid, n, " -> ".join("%.3f"%x for x in ls[-4:]), 100*(ls[-2]-ls[-1])/max(ls[-2],1e-9)))
print("\n=== STILL-DROPPING >15% — count:", len(dropping))
json.dump({"underfit":underfit, "dropping":dropping, "no_trace":no_trace, "matched": matched}, open("/tmp/conv_audit.json","w"), indent=1)
print("wrote /tmp/conv_audit.json")
