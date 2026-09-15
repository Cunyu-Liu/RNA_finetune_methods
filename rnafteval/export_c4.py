"""Export C1/C4 analysis tables (ledger -> markdown/CSV for preprint figs).

C4 core: per (model, task, strategy): random mean vs family mean, Δ, and
3-seed direction consistency. Pairs with baselines where available.

Usage: python -m rnafteval.export_c4 [--out status/c4_table.md]
"""
from __future__ import annotations

import argparse
import collections
import json
import os

ROOT = "/mnt/cunyuliu/rna-ft-eval"
LEDGER = os.path.join(ROOT, "ledger.jsonl")


def cells() -> dict:
    rows = [json.loads(l) for l in open(LEDGER) if l.strip()]
    out: dict[tuple, dict[int, float]] = collections.defaultdict(dict)
    for r in rows:
        if r.get("status") != "done" or r.get("smoke"):
            continue
        if "_s101_" in r["run_id"]:
            continue  # tuning runs excluded from formal matrix
        v = r.get("value")
        if v is None:
            continue
        key = (r["model"], r["task"], r["strategy"], r["split"])
        out[key][r["seed"]] = float(v)
    return out


def baselines() -> dict:
    b = {}
    for task in ("noncoding-rna-family", "modification", "secondary-structure"):
        for split in ("random", "family"):
            p = os.path.join(ROOT, "artifacts",
                             "baseline_%s_%s.json" % (task, split))
            if os.path.exists(p):
                try:
                    d = json.load(open(p))
                    vals = []
                    for v in d.get("results", {}).values():
                        if isinstance(v, dict):
                            vals.append(v.get("f1", v.get("auc", 0)))
                        else:
                            vals.append(v)
                    if vals:
                        b[(task, split)] = max(vals)
                except Exception:
                    pass
    return b


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "status", "c4_table.md"))
    args = ap.parse_args()

    c = cells()
    base = baselines()

    # group: (model, task, strategy) -> {split: (mean, n, seeds, min, max)}
    grouped: dict[tuple, dict[str, dict]] = collections.defaultdict(dict)
    for (model, task, strat, split), seeds in c.items():
        if strat not in ("frozen", "lora", "full"):
            continue
        vals = list(seeds.values())
        grouped[(model, task, strat)][split] = {
            "mean": sum(vals) / len(vals), "n": len(vals),
            "min": min(vals), "max": max(vals),
            "seeds": sorted(seeds.items()),
        }

    lines = ["# C4 表：Δ(随机−家族) × 策略（3 种子均值；n<3 标注）", ""]
    hdr = ("| model | task | strategy | random | family | Δ(rand−fam) | "
           "base(random) | base(family) | seeds |")
    lines += [hdr, "|" + "---|" * 9]
    csv = ["model,task,strategy,random_mean,family_mean,delta,base_random,base_family,n_random,n_family"]
    for (model, task, strat), sides in sorted(grouped.items()):
        r = sides.get("random")
        f = sides.get("family")
        if not r:
            continue
        rm = r["mean"]
        fm = f["mean"] if f else None
        delta = rm - fm if fm is not None else None
        br = base.get((task, "random"))
        bf = base.get((task, "family"))
        n = "%d/%d" % (r["n"], f["n"] if f else 0)
        def fmt(x, nd=3):
            return ("%.3f" % x) if x is not None else "—"
        lines.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            model, task, strat, fmt(rm), fmt(fm), fmt(delta),
            fmt(br), fmt(bf), n))
        csv.append("%s,%s,%s,%.4f,%s,%s,%s,%s,%d,%d" % (
            model, task, strat, rm,
            ("%.4f" % fm) if fm is not None else "",
            ("%.4f" % delta) if delta is not None else "",
            ("%.4f" % br) if br is not None else "",
            ("%.4f" % bf) if bf is not None else "",
            r["n"], f["n"] if f else 0))

    lines += ["", "注：Δ>0 = 家族切分受损（泄漏敏感）；Δ≈0/<0 = 家族切分不敏感。"
              "基线 = 最强传统基线（k-mer LGBM / bracket+LGBM pair）。"]
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as fh:
        fh.write("\n".join(lines) + "\n")
    with open(args.out.replace(".md", ".csv"), "w") as fh:
        fh.write("\n".join(csv) + "\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
