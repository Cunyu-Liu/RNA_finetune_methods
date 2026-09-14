"""Aggregate ledger -> C1/C4 summary tables (mean over seeds, direction check).

Output: /mnt/cunyuliu/rna-ft-eval/status/summary.md + summary.json
Usage: PYTHONPATH=... python -m rnafteval.summarize
"""
from __future__ import annotations

import collections
import json
import os

ROOT = "/mnt/cunyuliu/rna-ft-eval"
LEDGER = os.path.join(ROOT, "ledger.jsonl")


def main() -> int:
    rows = [json.loads(l) for l in open(LEDGER) if l.strip()]
    done = [r for r in rows if r.get("status") == "done"
            and not r["run_id"].endswith("_smoke") and "_s999" not in r["run_id"]]

    # cell = (model, task, strategy, split) -> {seed: value}
    cells: dict[tuple, dict[int, float]] = collections.defaultdict(dict)
    for r in done:
        key = (r["model"], r["task"], r["strategy"], r["split"])
        v = r.get("value")
        if v is not None:
            cells[key][r["seed"]] = float(v)

    # baselines
    baselines = {}
    for task in ("noncoding-rna-family",):
        for split in ("random", "family"):
            p = os.path.join(ROOT, "artifacts",
                             "baseline_%s_%s.json" % (task, split))
            if os.path.exists(p):
                b = json.load(open(p))
                baselines[(task, split)] = max(b["results"].values())

    out_lines = ["# RNA-ft-eval 汇总（自动生成）", ""]
    table = {}
    for key in sorted(cells):
        model, task, strat, split = key
        vals = list(cells[key].values())
        mean = sum(vals) / len(vals)
        n = len(vals)
        # direction consistency vs frozen (same model/task/split)
        frozen = cells.get((model, task, "frozen", split))
        dir_ok = ""
        if frozen and strat != "frozen" and n >= 3 and len(frozen) >= 3:
            fm = sum(frozen.values()) / len(frozen)
            wins = sum(1 for v in vals if v > fm)
            if wins == n:
                dir_ok = "↑*"
            elif wins == 0:
                dir_ok = "↓*"
            else:
                dir_ok = "±"
        base = baselines.get((task, split))
        delta_base = ("%.3f" % (mean - base)) if base is not None else ""
        out_lines.append(
            "| %s | %s | %s | %s | %.4f | %d seeds | %s | %s |" % (
                model, task.replace("noncoding-rna-family", "ncRNA"),
                strat, split, mean, n, dir_ok, delta_base))
        table["%s|%s|%s|%s" % key] = {
            "mean": mean, "n_seeds": n, "seeds": cells[key],
            "delta_vs_strongest_baseline": (mean - base) if base else None,
        }

    header = ["| model | task | strategy | split | mean | seeds | dir | ΔLM−基线 |",
              "|---|---|---|---|---|---|---|---|"]
    lines = header + out_lines
    out_lines = lines + ["", "基线：%s" % json.dumps(
        {"%s|%s" % k: round(v, 4) for k, v in baselines.items()}, ensure_ascii=False)]
    out_lines.append("")
    out_lines.append("注：dir=与 frozen 的 3 种子方向一致性（* = 方向一致）；"
                     "ΔLM−基线 = 该策略均值 − 最强传统基线。smoke run 不入表。")

    os.makedirs(os.path.join(ROOT, "status"), exist_ok=True)
    with open(os.path.join(ROOT, "status", "summary.md"), "w") as fh:
        fh.write("\n".join(out_lines) + "\n")
    with open(os.path.join(ROOT, "status", "summary.json"), "w") as fh:
        json.dump(table, fh, indent=2, ensure_ascii=False)
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
