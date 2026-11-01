"""结论⑤c 8 任务数据量曲线：同一任务内比较 33M-full / 33M-LoRA / 148M-LoRA。

Only cells with >=3 formal seeds are plotted (mean ± 95% CI over seeds);
tasks without tiers stay as explicit "待补" tiles. No interpolation, no zeros.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
WORK = ROOT / "绘图数据" / "current" / "figure_source_data_20261028"
OUT = Path(__file__).resolve().parent

FONT = Path.home() / "Library/Fonts/msyh.ttc"
matplotlib.font_manager.fontManager.addfont(str(FONT))
plt.rcParams["font.family"] = "Microsoft YaHei"
plt.rcParams["axes.unicode_minus"] = False

TASKS = [
    ("noncoding-rna-family", "ncRNA 家族", "ACC"),
    ("crispr-off-target", "CRISPR 脱靶", "PR-AUC"),
    ("modification", "modification", "m6A AUC"),
    ("mrl", "MRL", "Pearson r"),
    ("spliceai", "SpliceAI", "macro-F1"),
    ("secondary-structure", "SSP", "pair-F1"),
    ("degradation", "mRNA 降解", "PCC"),
    ("ssi", "SSI", "PCC"),
]
BUDGETS = [1000, 1500, 2000, 2500, 3000]
MIN_SIGNAL = {"crispr-off-target": 0.2, "spliceai": 1 / 3 + 0.02}
ARMS = [
    ("RiNALMo-micro", "full", "33M full-FT", "#1f4e79", "o"),
    ("RiNALMo-micro", "lora", "33M LoRA", "#4c9f70", "^"),
    ("RiNALMo-mega", "lora", "148M LoRA", "#e07b39", "s"),
]


def latest_export():
    cands = sorted((OUT.parent / "data").glob("bestval_ledger_export_*.csv"),
                   key=lambda p: [int(x) for x in re.split(r"(\d+)", p.name) if x.isdigit()])
    assert cands, "no bestval export"
    return cands[-1]


def load(path):
    df = pd.read_csv(path)
    df = df[df.protocol == "bestval_v1"]
    requested = df.run_id.str.extract(r"_e3(\d+)_", expand=False)
    df["requested_n_train"] = pd.to_numeric(requested).fillna(df.n_train).astype(int)
    df["actual_n_train"] = df.n_train.astype(int)
    df = df[df.requested_n_train.isin(BUDGETS)]
    df = df[df.seed.isin([17, 29, 43])]
    df = df[df.lr.isin([1e-5, 3e-4, 0.00001, 0.0003])]
    df = df[~df.run_id.str.contains("_smoke|_diag|_noshuffle|_r4_|_r16_|_dense")]
    df = df[~df.run_id.str.endswith("_seqmlfix")]
    df = df[~df.artifact_dir.astype(str).str.contains("/home/cunyuliu/rna-ft-eval/artifacts")]
    return df


def curve(df, task, split, model, strategy):
    sub = df[(df.task == task) & (df.split == split) & (df.model == model) &
             (df.strategy == strategy)]
    g = sub.groupby("requested_n_train").agg(
        mean=("value", "mean"), std=("value", "std"), count=("value", "count"),
        actual_min=("actual_n_train", "min"), actual_max=("actual_n_train", "max"),
    ).reset_index()
    g = g[g["count"] >= 3].sort_values("requested_n_train")
    g["ci"] = 1.96 * g["std"] / g["count"].pow(0.5)
    return g


def main(split="random"):
    path = latest_export()
    df = load(path)
    fig, axes = plt.subplots(2, 4, figsize=(13.6, 5.1), dpi=200)
    tiles = []
    for ax, (task, label, metric) in zip(axes.flat, TASKS):
        curves = [(c, curve(df, task, split, m, s)) for m, s, c, _col, _mk in ARMS]
        usable = sum(1 for _c, g in curves if len(g) >= 3)
        floor = MIN_SIGNAL.get(task)
        peak = max((g["mean"].max() for _c, g in curves if len(g)), default=0)
        if floor is not None and peak < floor:
            message = "正例过少" if task == "crispr-off-target" else "近随机基线"
            detail = "1000–3000 档 PR-AUC≈基线\n需 ≥6000 档" \
                if task == "crispr-off-target" else "近随机输出不算有效趋势"
            ax.text(0.5, 0.55, message, ha="center", va="center", fontsize=13,
                    color="#8a8a8a", transform=ax.transAxes)
            ax.text(0.5, 0.25, detail, ha="center", va="center",
                    fontsize=9, color="#8a8a8a", transform=ax.transAxes, linespacing=1.6)
            ax.set_title("%s | %s" % (label, metric), fontsize=10)
            ax.set_xticks([]), ax.set_yticks([])
            tiles.append({"task": task, "status": "low_signal", "peak": float(peak)})
            continue
        if usable < 2:
            ax.text(0.5, 0.55, "待补", ha="center", va="center", fontsize=15,
                    color="#8a8a8a", transform=ax.transAxes)
            ax.text(0.5, 0.28, "同档 ≥3 seeds 才出点", ha="center", va="center",
                    fontsize=9, color="#8a8a8a", transform=ax.transAxes)
            ax.set_title("%s | %s" % (label, metric), fontsize=10)
            ax.set_xticks([]), ax.set_yticks([])
            tiles.append({"task": task, "status": "pending",
                          "curves": [len(g) for _c, g in curves]})
            continue
        for (model, strat, cname, col, mk), (c, g) in zip(ARMS, curves):
            if not len(g):
                continue
            ax.errorbar(g.requested_n_train, g["mean"], yerr=g["ci"], fmt=mk + "-",
                        color=col, lw=1.6, ms=4.5, capsize=2.5, label=cname)
        task_caps = df[(df.task == task) & (df.split == split) &
                       (df.requested_n_train != df.actual_n_train)]
        if not task_caps.empty:
            minimum = int(task_caps.requested_n_train.min())
            actual = "/".join(str(int(x)) for x in sorted(task_caps.actual_n_train.unique()))
            ax.text(0.98, 0.03, f"requested≥{minimum}: actual n={actual}",
                    ha="right", va="bottom", fontsize=7.2, color="#A6543D",
                    transform=ax.transAxes)
        ax.set_title("%s | %s" % (label, metric), fontsize=10)
        ax.grid(alpha=0.25, lw=0.6)
        ax.tick_params(labelsize=8)
        tiles.append({"task": task, "status": "plotted",
                      "curves": [len(g) for _c, g in curves]})
    handles, labels = axes.flat[0].get_legend_handles_labels()
    if handles:
        fig.legend(handles, labels, loc="upper center", ncol=3, frameon=False,
                   fontsize=9.5, bbox_to_anchor=(0.5, 0.965))
    fig.suptitle("Data-volume effect by task | official RiNALMo family | %s split | " % split +
                 "33M full@1e-5 / 33M LoRA@3e-4 / 148M LoRA@3e-4 | 3-seed mean ± 95% CI",
                 fontsize=10.5, y=1.02)
    caps = df[df.requested_n_train != df.actual_n_train][[
        "run_id", "task", "split", "model", "strategy",
        "requested_n_train", "actual_n_train",
    ]].to_dict("records")
    fig.text(0.01, 0.005,
             "source: %s | only >=3 formal seeds per cell; requested tiers 1000/1500/2000/2500/3000; "
             "empty tile = tiers pending; capped actual n is recorded in metadata; "
             "650M excluded (32.7 GiB single-card limit)" % path.name,
             fontsize=7.4, color="#555555")
    fig.tight_layout(rect=(0, 0.02, 1, 0.94))
    stem = "data_volume_8task" + ("_family" if split == "family" else "")
    png = OUT / (stem + ".png")
    fig.savefig(png, bbox_inches="tight")
    fig.savefig(OUT / (stem + ".pdf"), bbox_inches="tight")
    plotted = sum(1 for t in tiles if t["status"] == "plotted")
    (OUT / (stem + "_meta.json")).write_text(json.dumps({
        "figure": stem, "source": path.name, "split": split,
        "panels_plotted": plotted, "panels_total": len(tiles), "tiles": tiles,
        "requested_vs_actual": caps,
    }, ensure_ascii=False, indent=1))
    print("plotted", plotted, "/", len(tiles), "->", png)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", choices=("random", "family"), default="random")
    args = parser.parse_args()
    main(args.split)
