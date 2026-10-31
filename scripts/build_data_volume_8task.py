"""结论⑤c 8 任务数据量曲线：同一任务内比较 33M-full / 33M-LoRA / 148M-LoRA。

Only cells with >=3 formal seeds are plotted (mean ± 95% CI over seeds);
tasks without tiers stay as explicit "待补" tiles. No interpolation, no zeros.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[3] / "交接文档"
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
MIN_SIGNAL = {"crispr-off-target": 0.05}
ARMS = [
    ("RiNALMo-micro", "full", "33M full-FT", "#1f4e79", "o"),
    ("RiNALMo-micro", "lora", "33M LoRA", "#4c9f70", "^"),
    ("RiNALMo-mega", "lora", "148M LoRA", "#e07b39", "s"),
]


def latest_export():
    cands = sorted((OUT.parent / "data").glob("bestval_ledger_export_*.csv"))
    assert cands, "no bestval export"
    return cands[-1]


def load(path):
    df = pd.read_csv(path)
    df = df[df.protocol == "bestval_v1"]
    df = df[df.n_train.isin(BUDGETS)]
    df = df[df.seed.isin([17, 29, 43])]
    df = df[df.lr.isin([1e-5, 3e-4, 0.00001, 0.0003])]
    df = df[~df.run_id.str.contains("_smoke|_diag|_noshuffle|_r4_|_r16_|_dense")]
    df = df[~df.run_id.str.endswith("_seqmlfix")]
    df = df[~df.artifact_dir.astype(str).str.contains("/home/cunyuliu/rna-ft-eval/artifacts")]
    return df


def curve(df, task, split, model, strategy):
    sub = df[(df.task == task) & (df.split == split) & (df.model == model) &
             (df.strategy == strategy)]
    g = sub.groupby("n_train").value.agg(["mean", "std", "count"]).reset_index()
    g = g[g["count"] >= 3].sort_values("n_train")
    g["ci"] = 1.96 * g["std"] / g["count"].pow(0.5)
    return g


def main():
    path = latest_export()
    df = load(path)
    fig, axes = plt.subplots(2, 4, figsize=(13.6, 5.1), dpi=200)
    tiles = []
    for ax, (task, label, metric) in zip(axes.flat, TASKS):
        split = "random"
        curves = [(c, curve(df, task, split, m, s)) for m, s, c, _col, _mk in ARMS]
        usable = sum(1 for _c, g in curves if len(g) >= 3)
        floor = MIN_SIGNAL.get(task)
        peak = max((g["mean"].max() for _c, g in curves if len(g)), default=0)
        if floor is not None and peak < 4 * floor:
            ax.text(0.5, 0.55, "正例过少", ha="center", va="center", fontsize=13,
                    color="#8a8a8a", transform=ax.transAxes)
            ax.text(0.5, 0.25, "1000–3000 档 PR-AUC≈基线\n需 ≥6000 档", ha="center",
                    va="center", fontsize=9, color="#8a8a8a", transform=ax.transAxes,
                    linespacing=1.6)
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
            ax.errorbar(g.n_train, g["mean"], yerr=g["ci"], fmt=mk + "-",
                        color=col, lw=1.6, ms=4.5, capsize=2.5, label=cname)
        ax.set_title("%s | %s" % (label, metric), fontsize=10)
        ax.grid(alpha=0.25, lw=0.6)
        ax.tick_params(labelsize=8)
        tiles.append({"task": task, "status": "plotted",
                      "curves": [len(g) for _c, g in curves]})
    handles, labels = axes.flat[0].get_legend_handles_labels()
    if handles:
        fig.legend(handles, labels, loc="upper center", ncol=3, frameon=False,
                   fontsize=9.5, bbox_to_anchor=(0.5, 0.965))
    fig.suptitle("Data-volume effect by task | official RiNALMo family | random split | "
                 "33M full@1e-5 / 33M LoRA@3e-4 / 148M LoRA@3e-4 | 3-seed mean ± 95% CI",
                 fontsize=10.5, y=1.02)
    fig.text(0.01, 0.005,
             "source: %s | only >=3 formal seeds per cell; tiers 1000/1500/2000/2500/3000; "
             "empty tile = tiers pending; 650M excluded (32.7 GiB single-card limit)" % path.name,
             fontsize=7.4, color="#555555")
    fig.tight_layout(rect=(0, 0.02, 1, 0.94))
    fig.savefig(OUT / "data_volume_8task.png", bbox_inches="tight")
    fig.savefig(OUT / "data_volume_8task.pdf", bbox_inches="tight")
    plotted = sum(1 for t in tiles if t["status"] == "plotted")
    (OUT / "data_volume_8task_meta.json").write_text(json.dumps({
        "figure": "data_volume_8task", "source": path.name,
        "panels_plotted": plotted, "panels_total": len(tiles), "tiles": tiles,
    }, ensure_ascii=False, indent=1))
    print("plotted", plotted, "/", len(tiles), "->", OUT / "data_volume_8task.png")


if __name__ == "__main__":
    main()
