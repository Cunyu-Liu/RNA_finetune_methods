"""结论④ 8 任务等价线：小模型全参 @n 与大模型 LoRA @m 的等价对。

Each panel = one task (random split primary, family fallback). Two curves share the
same labelled-sequence axis: RiNALMo-micro full-FT @1e-5 and RiNALMo-mega LoRA @3e-4.
For every full budget n we draw a dotted guide to the LoRA curve and label the
smallest m whose mean is >= full(n) mean; only cells with >=3 formal seeds qualify.
Panels without both arms on >=3 tiers are left as an explicit "pending" tile, never
interpolated and never filled with zeros.
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
COL_FULL = "#1f4e79"
COL_LORA = "#e07b39"
# CRISPR 正例率 0.59%：1000–3000 档只含 ~6–18 个正例，PR-AUC 停在基线附近，
# 该档位不可用于等价线判断；低于阈值直接标“正例过少”，不画误导性曲线。
MIN_SIGNAL = {"crispr-off-target": 0.05}


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
    df = df[~df.run_id.str.contains("_smoke|_diag|_noshuffle|_r4_|_r16_")]
    df = df[~df.run_id.str.endswith("_seqmlfix")]
    df = df[~df.artifact_dir.astype(str).str.contains("/home/cunyuliu/rna-ft-eval/artifacts")]
    return df


def arm(df, task, split, model, strategy):
    sub = df[(df.task == task) & (df.split == split) & (df.model == model) &
             (df.strategy == strategy)]
    g = sub.groupby("n_train").value.agg(["mean", "std", "count"]).reset_index()
    return g[g["count"] >= 3].sort_values("n_train")


def equivalence(full, lora):
    pairs = []
    for n in sorted(full.n_train.unique()):
        full_seed = full[full.n_train == n].set_index("seed").value
        candidates = []
        for m in sorted(lora.n_train.unique()):
            lora_seed = lora[lora.n_train == m].set_index("seed").value
            common = full_seed.index.intersection(lora_seed.index)
            if len(common) < 3:
                continue
            differences = lora_seed.loc[common] - full_seed.loc[common]
            mean = float(differences.mean())
            ci = float(1.96 * differences.std(ddof=1) / len(common) ** 0.5)
            candidates.append({"full_n": int(n), "lora_n": int(m),
                               "delta": mean, "ci95": ci,
                               "equivalent": abs(mean) <= 0.02 and mean - ci <= 0 <= mean + ci})
        if not candidates:
            continue
        closest = min(candidates, key=lambda row: (abs(row["delta"]), row["lora_n"]))
        equivalent = [row for row in candidates if row["equivalent"]]
        chosen = min(equivalent, key=lambda row: (abs(row["delta"]), row["lora_n"])) \
            if equivalent else closest
        pairs.append(chosen)
    return pairs


def main():
    path = latest_export()
    df = load(path)
    fig, axes = plt.subplots(2, 4, figsize=(13.4, 6.4), dpi=200)
    tiles = []
    for ax, (task, label, metric) in zip(axes.flat, TASKS):
        split = "random"
        full = arm(df, task, split, "RiNALMo-micro", "full")
        lora = arm(df, task, split, "RiNALMo-mega", "lora")
        if full.empty or lora.empty or len(full) < 2 or len(lora) < 2:
            ax.text(0.5, 0.55, "待补", ha="center", va="center",
                    fontsize=15, color="#8a8a8a", transform=ax.transAxes)
            ax.text(0.5, 0.28, "两臂同档 ≥3 seeds 才出点", ha="center",
                    va="center", fontsize=9, color="#8a8a8a",
                    transform=ax.transAxes)
            ax.set_title("%s | %s" % (label, metric), fontsize=10)
            ax.set_xticks([]), ax.set_yticks([])
            tiles.append({"task": task, "split": split, "status": "pending",
                          "full_points": int(len(full)), "lora_points": int(len(lora))})
            continue
        floor = MIN_SIGNAL.get(task)
        peak = max(full["mean"].max(), lora["mean"].max())
        if floor is not None and peak < 4 * floor:
            ax.text(0.5, 0.55, "正例过少", ha="center", va="center",
                    fontsize=14, color="#8a8a8a", transform=ax.transAxes)
            ax.text(0.5, 0.28, "1000–3000 档 PR-AUC≈基线\n需 ≥6000 档再判等价",
                    ha="center", va="center", fontsize=9, color="#8a8a8a",
                    transform=ax.transAxes, linespacing=1.6)
            ax.set_title("%s | %s" % (label, metric), fontsize=10)
            ax.set_xticks([]), ax.set_yticks([])
            tiles.append({"task": task, "split": split, "status": "low_signal",
                          "peak": float(peak), "floor": floor})
            continue
        ax.plot(full.n_train, full["mean"], "o-", color=COL_FULL, lw=1.6,
                ms=4.5, label="33M full-FT")
        ax.plot(lora.n_train, lora["mean"], "s-", color=COL_LORA, lw=1.6,
                ms=4.5, label="148M LoRA")
        raw_full = df[(df.task == task) & (df.split == split) &
                      (df.model == "RiNALMo-micro") & (df.strategy == "full")]
        raw_lora = df[(df.task == task) & (df.split == split) &
                      (df.model == "RiNALMo-mega") & (df.strategy == "lora")]
        pairs = equivalence(raw_full, raw_lora)
        for pair in pairs:
            if not pair["equivalent"]:
                continue
            n, m = pair["full_n"], pair["lora_n"]
            target = float(full[full.n_train == n]["mean"].iloc[0])
            ax.plot([n, m], [target, target], ":", color="#6b6b6b", lw=1.1)
            ax.annotate("≈LoRA@%d" % m, (m, target), textcoords="offset points",
                        xytext=(2, 4), fontsize=7.5, color="#333333")
        if not any(pair["equivalent"] for pair in pairs):
            ax.text(0.5, 0.04, "当前范围未观测到等价候选", ha="center", va="bottom",
                    fontsize=7.8, color="#777777", transform=ax.transAxes)
        ax.set_title("%s | %s" % (label, metric), fontsize=10)
        ax.grid(alpha=0.25, lw=0.6)
        ax.tick_params(labelsize=8)
        tiles.append({"task": task, "split": split, "status": "plotted",
                      "equivalence": pairs,
                      "full_points": int(len(full)), "lora_points": int(len(lora))})
    handles, labels = axes.flat[0].get_legend_handles_labels()
    if handles:
        fig.legend(handles, labels, loc="upper center", ncol=2, frameon=False,
                   fontsize=10, bbox_to_anchor=(0.5, 0.965))
    fig.suptitle("Data-budget equivalence | official same-family models | "
                 "33M full-FT @1e-5 vs 148M LoRA @3e-4 | random split | "
                 "bars = 3-seed mean", fontsize=11, y=1.02)
    fig.text(0.01, 0.005,
             "source: %s | dotted guide = |paired delta|<=0.02 and 95%% CI covers 0; "
             "only 3 formal seeds per cell; no interpolation; empty tile = pending"
             % path.name, fontsize=7.4, color="#555555")
    fig.tight_layout(rect=(0, 0.02, 1, 0.94))
    png = OUT / "equivalence_8task.png"
    fig.savefig(png, bbox_inches="tight")
    fig.savefig(OUT / "equivalence_8task.pdf", bbox_inches="tight")
    plotted = sum(1 for t in tiles if t["status"] == "plotted")
    (OUT / "equivalence_8task_meta.json").write_text(json.dumps({
        "figure": "equivalence_8task", "source": path.name,
        "panels_plotted": plotted, "panels_total": len(tiles), "tiles": tiles,
    }, ensure_ascii=False, indent=1))
    print("plotted panels", plotted, "/", len(tiles), "->", png)


if __name__ == "__main__":
    main()
