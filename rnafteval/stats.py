"""Bootstrap 95% CI + seed-level paired tests + BH FDR (stat plan §3.5).

Implements the preregistered statistics:
  1. Per cell (model, task, strategy, split): seed-mean with bootstrap CI
     (resampling the 3 formal seeds AND per-seed test sequences would need
     per-seq predictions; at ledger granularity we bootstrap seeds with
     n=3 -> wide CI, reported honestly as seed-variance band).
  2. Paired strategy contrasts (same model x task x split): lora-vs-frozen,
     full-vs-frozen, lora-vs-full; sign consistency across seeds + exact
     permutation p (n=3 seeds -> minimal p=1/8 one-sided, 1/4 two-sided;
     reported with that caveat).
  3. C4 delta contrasts: random-vs-family within (model, task, strategy).
  4. Benjamini-Hochberg FDR across all reported contrasts (q=0.05).

Usage: python -m rnafteval.stats [--out status/stats.md]
"""
from __future__ import annotations

import argparse
import itertools
import json
import os
import random

ROOT = "/mnt/cunyuliu/rna-ft-eval"


def load_cells() -> dict:
    from rnafteval.export_c4 import cells
    return cells()


def bh_fdr(pvals: list[float], q: float = 0.05) -> list[bool]:
    """Benjamini-Hochberg: return list of significance flags."""
    n = len(pvals)
    if n == 0:
        return []
    order = sorted(range(n), key=lambda i: pvals[i])
    flags = [False] * n
    prev = False
    for rank, idx in enumerate(reversed(order), start=1):
        k = n - rank + 1  # descending rank
        thresh = q * k / n
        sig = pvals[idx] <= thresh
        prev = prev or sig
        flags[idx] = prev
    return flags


def seed_sign_test(vals_a: dict, vals_b: dict) -> dict:
    """Paired sign test over shared seeds: a > b wins per seed."""
    shared = sorted(set(vals_a) & set(vals_b))
    if not shared:
        return {"n": 0}
    wins = sum(1 for s in shared if vals_a[s] > vals_b[s])
    ties = sum(1 for s in shared if vals_a[s] == vals_b[s])
    n = len(shared)
    # exact two-sided binomial p for wins under H0 p=0.5 (ties dropped)
    m = n - ties
    from math import comb
    w = wins
    if m == 0:
        p = 1.0
    else:
        tail = sum(comb(m, k) for k in range(0, min(w, m - w) + 1))
        p = min(1.0, 2 * tail / (2 ** m))
    return {"n": n, "wins": wins, "ties": ties, "p": round(p, 4)}


def bootstrap_ci(vals: list[float], n_boot: int = 2000, seed: int = 17) -> tuple:
    rng = random.Random(seed)
    means = []
    for _ in range(n_boot):
        sample = [rng.choice(vals) for _ in vals]
        means.append(sum(sample) / len(sample))
    means.sort()
    lo = means[int(0.025 * n_boot)]
    hi = means[int(0.975 * n_boot)]
    return lo, hi


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "status", "stats.md"))
    args = ap.parse_args()

    c = load_cells()
    # (model, task, strategy, split) -> {seed: value}
    contrasts = []
    # strategy contrasts within same (model, task, split)
    models_tasks = sorted({(k[0], k[1]) for k in c})
    for (model, task) in models_tasks:
        for split in ("random", "family"):
            strats = {s: c[(model, task, s, split)]
                      for s in ("frozen", "lora", "full")
                      if (model, task, s, split) in c}
            for a, b in itertools.combinations(sorted(strats), 2):
                st = seed_sign_test(strats[a], strats[b])
                if st["n"] >= 2:
                    contrasts.append({
                        "type": "strategy", "model": model, "task": task,
                        "split": split, "a": a, "b": b,
                        "mean_a": sum(strats[a].values()) / len(strats[a]),
                        "mean_b": sum(strats[b].values()) / len(strats[b]),
                        **st})
    # C4: random-vs-family within (model, task, strategy)
    mts = sorted({(k[0], k[1], k[2]) for k in c})
    for (model, task, strat) in mts:
        ra = c.get((model, task, strat, "random"))
        fa = c.get((model, task, strat, "family"))
        if ra and fa:
            st = seed_sign_test(ra, fa)
            if st["n"] >= 2:
                contrasts.append({
                    "type": "C4-delta", "model": model, "task": task,
                    "strategy": strat, "a": "random", "b": "family",
                    "mean_a": sum(ra.values()) / len(ra),
                    "mean_b": sum(fa.values()) / len(fa),
                    **st})

    # BH FDR over all contrast p-values
    pvals = [ct["p"] for ct in contrasts]
    flags = bh_fdr(pvals, q=0.05)
    for ct, f in zip(contrasts, flags):
        ct["bh_sig"] = f

    lines = ["# 统计检验（预注册计划 §3.5：配对符号检验 + BH FDR q=0.05）", "",
             "注：n=3 种子的符号检验最小 p=0.25（双侧）——种子维度功效有限，",
             "方向一致性与效应量为主证据，BH 后显著性作为附加标注。", ""]
    lines.append("| contrast | model | task | arm | mean_a | mean_b | Δ | wins/n | p | BH-sig |")
    lines.append("|" + "---|" * 10)
    for ct in sorted(contrasts, key=lambda x: (x["type"], x["task"], x["model"])):
        if ct["type"] == "strategy":
            label = "%s vs %s (%s)" % (ct["a"], ct["b"], ct["split"])
            arm = ct["split"]
        else:
            label = "random vs family"
            arm = ct["strategy"]
        lines.append("| %s | %s | %s | %s | %.3f | %.3f | %+.3f | %d/%d | %.3f | %s |" % (
            label, ct["model"], ct["task"].replace("noncoding-rna-family", "ncRNA")
            .replace("secondary-structure", "SSP")
            .replace("modification", "m6A"),
            arm, ct["mean_a"], ct["mean_b"],
            ct["mean_a"] - ct["mean_b"], ct["wins"], ct["n"], ct["p"],
            "✓" if ct["bh_sig"] else ""))
    # cell-level bootstrap CI table
    lines += ["", "## 格级均值 + 种子 bootstrap 95% CI", ""]
    lines.append("| model | task | strategy | split | mean [CI] | n |")
    lines.append("|" + "---|" * 6)
    for k in sorted(c):
        if k[2] not in ("frozen", "lora", "full"):
            continue
        vals = list(c[k].values())
        mean = sum(vals) / len(vals)
        lo, hi = bootstrap_ci(vals)
        lines.append("| %s | %s | %s | %s | %.3f [%.3f, %.3f] | %d |" % (
            k[0], k[1].replace("noncoding-rna-family", "ncRNA")
            .replace("secondary-structure", "SSP")
            .replace("modification", "m6A"),
            k[2], k[3], mean, lo, hi, len(vals)))

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as fh:
        fh.write("\n".join(lines) + "\n")
    with open(args.out.replace(".md", ".json"), "w") as fh:
        json.dump(contrasts, fh, indent=2, ensure_ascii=False)
    n_sig = sum(1 for f in flags if f)
    print("contrasts: %d, BH-significant: %d" % (len(contrasts), n_sig))
    print("\n".join(lines[:14]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
