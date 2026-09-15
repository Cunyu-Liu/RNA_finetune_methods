"""Preprint figures from ledger: C1 matrix heatmap + C4 delta bars + LR grid.

Outputs (status/figs/):
  fig_c1_matrix.{png,pdf}  — strategy performance heatmap (random arm)
  fig_c4_delta.{png,pdf}   — Δ(random−family) by task x strategy (C4 core)
  fig_lr_grid.{png,pdf}    — LR grid, model x strategy curves (A8)

Usage: python -m rnafteval.figures [--out status/figs]
"""
from __future__ import annotations

import argparse
import collections
import json
import os

ROOT = "/mnt/cunyuliu/rna-ft-eval"


def collect():
    from rnafteval.export_c4 import cells, baselines
    return cells(), baselines()


def task_label(task: str) -> str:
    return (task.replace("noncoding-rna-family", "ncRNA\n(classification)")
            .replace("secondary-structure", "SSP\n(structure)")
            .replace("modification", "m6A\n(per-base)"))


def model_label(model: str) -> str:
    return {"RNA-Sc-10M": "RNA-Sc-10M\n(10M)", "RiNALMo-micro": "RiNALMo\n(33M)",
            "ERNIE-RNA": "ERNIE-RNA", "RNA-FM": "RNA-FM",
            "SpliceBERT": "SpliceBERT"}.get(model, model)


def fig_c1(c, base, outdir):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    models = sorted({k[0] for k in c})
    tasks = ["noncoding-rna-family", "modification", "secondary-structure"]
    strats = ["frozen", "lora", "full"]
    # rows: (model, task); cols: strategy; random arm values
    rows = [(m, t) for m in models for t in tasks
            if any((m, t, s, "random") in c for s in strats)]
    M = np.full((len(rows), len(strats)), np.nan)
    for i, (m, t) in enumerate(rows):
        for j, s in enumerate(strats):
            d = c.get((m, t, s, "random"))
            if d:
                M[i, j] = sum(d.values()) / len(d)
    fig, ax = plt.subplots(figsize=(6, 0.55 * len(rows) + 1.6))
    im = ax.imshow(M, cmap="RdYlGn", aspect="auto", vmin=0, vmax=1)
    ax.set_xticks(range(len(strats)), strats)
    ax.set_yticks(range(len(rows)),
                  ["%s  %s" % (model_label(m), task_label(t)) for m, t in rows])
    for i in range(len(rows)):
        for j in range(len(strats)):
            if not np.isnan(M[i, j]):
                # baseline marker: box the cell if beats best baseline
                t = rows[i][1]
                b = base.get((t, "random"))
                if b is not None and M[i, j] > b:
                    ax.add_patch(plt.Rectangle((j - .5, i - .5), 1, 1,
                                               fill=False, ec="black", lw=2))
                ax.text(j, i, "%.3f" % M[i, j], ha="center", va="center",
                        fontsize=8)
    # baseline annotations on right
    for i, (m, t) in enumerate(rows):
        b = base.get((t, "random"))
        if b is not None:
            ax.text(len(strats) - 0.3, i, "base\n%.3f" % b, fontsize=6,
                    va="center", ha="left", color="gray")
    ax.set_title("C1: fine-tuning gains (random split, 3-seed mean);\n"
                 "black box = beats strongest traditional baseline")
    fig.colorbar(im, ax=ax, shrink=0.8, label="ACC/AUC/F1")
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(outdir, "fig_c1_matrix.%s" % ext), dpi=200)
    plt.close(fig)


def fig_c4(c, base, outdir):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    entries = []
    for (m, t, s, split), seeds in c.items():
        if s not in ("frozen", "lora", "full") or split != "random":
            continue
        fam = c.get((m, t, s, "family"))
        if not fam:
            continue
        rm = sum(seeds.values()) / len(seeds)
        fm = sum(fam.values()) / len(fam)
        entries.append((m, t, s, rm - fm))
    entries.sort(key=lambda e: (e[1], e[0], e[2]))
    labels = ["%s %s\n%s" % (model_label(m), task_label(t).replace("\n", " "), s)
              for m, t, s, _ in entries]
    vals = [e[3] for e in entries]
    fig, ax = plt.subplots(figsize=(9, 0.5 * len(entries) + 1.5))
    colors = ["#c0392b" if v > 0.1 else ("#e67e22" if v > 0.03 else "#27ae60")
              for v in vals]
    ax.barh(range(len(vals)), vals, color=colors)
    ax.set_yticks(range(len(vals)), labels, fontsize=7)
    ax.axvline(0, color="black", lw=1)
    ax.set_xlabel("Δ(random − family): positive = leak-sensitive")
    ax.set_title("C4: leakage × strategy interaction — task granularity "
                 "determines collapse\n(red: collapse >0.1; orange: mild; "
                 "green: robust)")
    ax.invert_yaxis()
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(outdir, "fig_c4_delta.%s" % ext), dpi=200)
    plt.close(fig)


def fig_lr(outdir):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rows = [json.loads(l) for l in open(os.path.join(ROOT, "ledger.jsonl"))
            if l.strip()]
    data = collections.defaultdict(list)
    for r in rows:
        if r.get("seed") != 101 or r.get("status") != "done":
            continue
        rid = r["run_id"]
        if "_lr" not in rid:
            continue
        lr = float(rid.split("_lr")[1])
        data[(r["model"], r["strategy"], r["task"])].append((lr, r["value"]))
    fig, ax = plt.subplots(figsize=(7, 5))
    palette = {("RNA-Sc-10M", "full"): "#2980b9",
               ("RNA-Sc-10M", "lora"): "#9b59b6",
               ("RiNALMo-micro", "full"): "#c0392b",
               ("RiNALMo-micro", "lora"): "#e67e22"}
    for (model, strat, task), pts in sorted(data.items()):
        if task != "noncoding-rna-family":
            continue
        pts.sort()
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        ax.plot(xs, ys, "o-", label="%s %s" % (model, strat),
                color=palette.get((model, strat)))
    ax.set_xscale("log")
    ax.set_xlabel("learning rate (log)")
    ax.set_ylabel("ACC (ncRNA, seed 101)")
    ax.set_title("A8 LR grid: scale × strategy × LR interaction\n"
                 "full-FT sweet spot shifts left with model scale; "
                 "LoRA needs high LR")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(outdir, "fig_lr_grid.%s" % ext), dpi=200)
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "status", "figs"))
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    c, base = collect()
    fig_c1(c, base, args.out)
    fig_c4(c, base, args.out)
    fig_lr(args.out)
    print("figures written to", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
