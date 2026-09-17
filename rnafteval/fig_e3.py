"""E3 学习曲线图（T3.1.5）——C3 翻转点可视化。

x = 标注量（log 轴: 10 / 100 / 1000 / full=6859）, y = family
切分 ACC, 每策略一条线, 每模型一个面板。3 种子均值 + min-max
误差带。full 列小数据档用默认 LR（A8 崩溃, 图注声明）。

用法: python -m rnafteval.fig_e3 [--out status/figs]
"""
from __future__ import annotations

import argparse
import collections
import json
import os

ROOT = "/mnt/cunyuliu/rna-ft-eval"
FULL_N = {"ncrna": 6859}
MODEL_LABEL = {"rinalmomicro": "RiNALMo-micro (33M)",
               "rnasc10m": "RNA-Sc-10M (10M)"}
ORDER = ["rinalmomicro", "rnasc10m"]


def e3_cells() -> dict:
    rows = [json.loads(l) for l in open(os.path.join(
        ROOT, "ledger.jsonl")) if l.strip()]
    data = collections.defaultdict(dict)
    fullvals = collections.defaultdict(dict)
    for r in rows:
        if r.get("status") != "done" or r.get("smoke"):
            continue
        rid = r["run_id"]
        parts = rid.split("_")
        if "noncodingrnafamily" not in rid:
            continue
        model, strat = parts[1], parts[3]
        seed = parts[4][1:]
        if "_e3" in rid:
            n = int(rid.rsplit("_e3", 1)[1])
            data[(model, n, strat)][seed] = float(r["value"])
        elif (r.get("seed") in (17, 29, 43) and rid.endswith("_family")
              and "_lr" not in rid):
            fullvals[(model, strat)][seed] = float(r["value"])
    for (model, strat), d in fullvals.items():
        data[(model, FULL_N["ncrna"], strat)] = d
    return data


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "status", "figs"))
    args = ap.parse_args()
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    data = e3_cells()
    models = [m for m in ORDER if any(k[0] == m for k in data)]
    fig, axes = plt.subplots(1, len(models),
                             figsize=(5.2 * len(models), 4.2),
                             squeeze=False)
    colors = {"frozen": "#27ae60", "lora": "#2980b9", "full": "#c0392b"}
    for ax, model in zip(axes[0], models):
        for strat in ["frozen", "lora", "full"]:
            xs, ys, lo, hi = [], [], [], []
            for n in [10, 100, 1000, FULL_N["ncrna"]]:
                d = data.get((model, n, strat))
                if d and len(d) >= 2:
                    vals = list(d.values())
                    xs.append(n)
                    ys.append(sum(vals) / len(vals))
                    lo.append(min(vals))
                    hi.append(max(vals))
            if xs:
                ax.plot(xs, ys, "-o", color=colors[strat], label=strat,
                        markersize=5)
                ax.fill_between(xs, lo, hi, color=colors[strat],
                                alpha=0.15, linewidth=0)
        ax.set_xscale("log")
        ax.axhline(1 / 13, color="gray", ls=":", lw=1)
        ax.text(10, 1 / 13 + 0.01, "chance 1/13", fontsize=7,
                color="gray")
        ax.set_xlabel("labeled sequences (cluster-level subsample)")
        ax.set_ylabel("ACC (family split)")
        ax.set_title(MODEL_LABEL.get(model, model) + " — E3 axis")
        ax.legend(fontsize=8, loc="lower right")
        ax.grid(alpha=0.25)
    fig.suptitle("C3: label-budget × strategy (family split, 3-seed "
                 "mean±range)\nfull-FT small-n arms at default LR "
                 "(collapse per A8 — see log)", fontsize=10)
    fig.tight_layout()
    os.makedirs(args.out, exist_ok=True)
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(args.out, "fig_e3_curves.%s" % ext),
                    dpi=200)
    plt.close(fig)
    print("written:", os.path.join(args.out, "fig_e3_curves.{png,pdf}"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
