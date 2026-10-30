"""⑤b 八任务时间×性能 与 ⑤d 大模型覆盖热图（数据全部来自 best-val 台账与权威聚合表）。"""
from pathlib import Path
import csv
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import font_manager

ROOT = Path(__file__).resolve().parents[3] / "交接文档"
WORK = ROOT / "绘图数据" / "current" / "figure_source_data_20261028"
OUT = Path(__file__).resolve().parent

FONT = Path.home() / "Library/Fonts/msyh.ttc"
font_manager.fontManager.addfont(str(FONT))
YAHEI = font_manager.FontProperties(fname=str(FONT)).get_name()
plt.rcParams.update({
    "font.family": [YAHEI, "DejaVu Sans"],
    "axes.unicode_minus": False,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.linewidth": 1.0,
    "legend.frameon": False,
    "pdf.fonttype": 42,
})

SIX_COLORS = {
    "frozen_random": "#6BAED6", "frozen_family": "#C6DBEF",
    "lora_random": "#FD8D3C", "lora_family": "#D94801",
    "full_random": "#3B3B3B", "full_family": "#A6A6A6",
}
STRAT_COLORS = {"frozen": "#6BAED6", "lora": "#FD8D3C", "full": "#3B3B3B"}
MODELS = ["RiNALMo-micro", "RiNALMo-mega", "RiNALMo-650M", "ERNIE-RNA", "RNA-FM"]
MODEL_SHORT = {"RiNALMo-micro": "33M", "RiNALMo-mega": "148M", "RiNALMo-650M": "650M",
               "ERNIE-RNA": "ERNIE", "RNA-FM": "RNA-FM"}
MARKERS = {"RiNALMo-micro": "o", "RiNALMo-mega": "s", "RiNALMo-650M": "D",
           "ERNIE-RNA": "^", "RNA-FM": "v"}
TASKS = [
    ("noncoding-rna-family", "ncRNA 家族分类", "ACC"),
    ("crispr-off-target", "CRISPR 脱靶", "PR-AUC"),
    ("modification", "modification", "m6A AUC"),
    ("mrl", "MRL", "Pearson r"),
    ("spliceai", "SpliceAI", "macro-F1"),
    ("secondary-structure", "SSP", "pair-F1"),
    ("degradation", "mRNA 降解", "PCC"),
    ("ssi", "SSI", "PCC"),
]
CELL_KEYS = list(SIX_COLORS)
TABLE_MODEL = {"rinalmomicro": "RiNALMo-micro", "rinalmomega": "RiNALMo-mega",
               "rinalmo650m": "RiNALMo-650M", "ernierna": "ERNIE-RNA",
               "rnafm": "RNA-FM", "nucleicbert": "NucleicBERT"}


def load_ledger():
    rows = list(csv.DictReader(open(WORK / "current_results/bestval_ledger_export_20261030.csv")))
    keep = [r for r in rows if "_noshuffle" not in r["run_id"]]
    keep = [r for r in keep if not (r["task"] == "noncoding-rna-family" and int(r["n_train"]) < 5000)]
    df = pd.DataFrame(keep)
    df["value"] = pd.to_numeric(df["value"])
    df["wall_sec"] = pd.to_numeric(df["wall_sec"])
    df["peak_mem_mb"] = pd.to_numeric(df["peak_mem_mb"])
    df["seed"] = df["seed"].astype(int)
    return df


def time_perf(df):
    out = []
    for task, label, metric in TASKS:
        q = df[(df.task == task) & (df.split == "random")]
        for model in MODELS:
            for strat in ("frozen", "lora", "full"):
                c = q[(q.model == model) & (q.strategy == strat)]
                if len(c) == 0:
                    continue
                out.append({"task": task, "model": model, "strategy": strat,
                            "n": len(c), "metric": float(c.value.mean()),
                            "wall_min": float(c.wall_sec.median()) / 60,
                            "peak_gb": float(c.peak_mem_mb.max()) / 1024,
                            "rids": ";".join(c.run_id.astype(str))})
    return pd.DataFrame(out)


def draw_time_perf(df, path_png, path_pdf):
    tp = time_perf(df)
    tp.to_csv(OUT / "eight_task_time_perf_data.csv", index=False)
    fig, axes = plt.subplots(2, 4, figsize=(12.4, 5.05), constrained_layout=True)
    for i, (task, label, metric) in enumerate(TASKS):
        ax = axes[i // 4, i % 4]
        sub = tp[tp.task == task]
        if sub.empty:
            ax.text(0.5, 0.5, "no completed run", ha="center", va="center", transform=ax.transAxes,
                    fontsize=9, color="#999999")
            ax.set_title(f"{label}｜{metric}", fontsize=9, fontweight="bold", color="#1F3A5F")
            ax.set_xticks([]); ax.set_yticks([])
            continue
        xmax = max(6, sub.wall_min.max() * 1.18)
        for _, row in sub.iterrows():
            ax.scatter(row.wall_min, row.metric, s=52, marker=MARKERS[row.model],
                       color=STRAT_COLORS[row.strategy], alpha=0.9,
                       edgecolor="white", linewidth=0.8, zorder=3)
        ax.set_title(f"{label}｜{metric}", fontsize=9, fontweight="bold", color="#1F3A5F")
        ax.set_xlabel("median wall time (min, random split)", fontsize=7.4)
        ax.set_ylabel(metric, fontsize=7.4)
        ax.set_xlim(0, xmax)
        lo = max(0, sub.metric.min() - (sub.metric.max() - sub.metric.min()) * 0.35 - 0.05)
        ax.set_ylim(lo, min(1.05, sub.metric.max() * 1.15 + 0.03))
        ax.tick_params(labelsize=6.4, length=2)
        ax.grid(color="#EDEDED", lw=0.5)
        ax.set_axisbelow(True)
    handles = [plt.Line2D([], [], marker="o", ls="", color=STRAT_COLORS[k], markersize=7,
                          label={"frozen": "Frozen", "lora": "LoRA", "full": "Full-FT"}[k])
               for k in STRAT_COLORS]
    handles += [plt.Line2D([], [], marker=MARKERS[m], ls="", color="#777777", markersize=6,
                           label=MODEL_SHORT[m]) for m in MODELS]
    fig.legend(handles=handles, ncol=8, loc="upper center", bbox_to_anchor=(0.5, 1.08), fontsize=7.4)
    fig.text(0.995, -0.04,
             "source: bestval ledger export 20261030 · random split only · full-data cells (n_train = task full set) · "
             "median wall of completed seeds (shared GPU, so wall time is not a benchmark claim)\n"
             "marker = model, colour = strategy; missing points mean the cell is not closed, never plotted as 0",
             transform=fig.transFigure, ha="right", va="top", fontsize=6.4, color="#777777")
    fig.savefig(path_png, dpi=300, bbox_inches="tight", facecolor="white")
    fig.savefig(path_pdf, bbox_inches="tight", facecolor="white")
    return tp


def coverage_matrix(df):
    """8 任务 × 5 模型 × 6 臂：已闭合种子数（>=1 记为已有点，=3 记为三种子闭合）。"""
    out = []
    for task, _l, _m in TASKS:
        for model in MODELS:
            row = {"task": task, "model": model}
            for key in CELL_KEYS:
                strat, split = key.rsplit("_", 1)
                q = df[(df.task == task) & (df.model == model) &
                       (df.strategy == strat) & (df.split == split)]
                row[key] = int(q.seed.nunique())
            out.append(row)
    return pd.DataFrame(out)


def draw_coverage(cov, path_png, path_pdf):
    fig, axes = plt.subplots(1, 2, figsize=(12.4, 3.6), constrained_layout=True,
                             gridspec_kw={"wspace": 0.06})
    titles = {"RiNALMo-mega": "RiNALMo 148M（official mega）", "RiNALMo-650M": "RiNALMo 650M（official giga）"}
    for ax, model in zip(axes, titles):
        sub = cov[cov.model == model].set_index("task").reindex([t[0] for t in TASKS])
        mat = sub[CELL_KEYS].to_numpy(int)
        im = ax.imshow(np.clip(mat, 0, 3), cmap="YlGnBu", vmin=0, vmax=3, aspect="auto")
        for i in range(mat.shape[0]):
            for j in range(mat.shape[1]):
                v = mat[i, j]
                ax.text(j, i, str(v) if v else "0", ha="center", va="center",
                        fontsize=8.2, color="#1B1B1B" if v < 3 else "white", fontweight="bold")
        ax.set_xticks(range(len(CELL_KEYS)))
        ax.set_xticklabels(["Frozen (R)", "Frozen (F)", "LoRA (R)", "LoRA (F)", "Full (R)", "Full (F)"],
                           fontsize=8.0, rotation=18, ha="right")
        ax.set_yticks(range(len(TASKS)))
        ax.set_yticklabels([f"{l}｜{m}" for _t, l, m in TASKS], fontsize=8.2)
        ax.set_title(titles[model], fontsize=11, fontweight="bold", color="#1F3A5F", pad=8)
        ax.tick_params(length=0)
        for s in ax.spines.values():
            s.set_visible(False)
    cb = fig.colorbar(im, ax=axes, fraction=0.018, pad=0.012, ticks=[0, 1, 2, 3])
    cb.set_label("completed seeds (0 = no closed cell)", fontsize=7.2)
    cb.ax.tick_params(labelsize=7)
    fig.text(0.995, -0.06,
             "source: bestval ledger export 20261030 + MRL/modification tables · cell value = number of completed formal seeds (17/29/43)\n"
             "0 = 该格未闭合（不是 0 分）；3 = 三种子齐；凡 <3 的格在 ①a-2/①a-3/①a-4 中一律斜线标注，不做插值或旧值回填",
             transform=fig.transFigure, ha="right", va="top", fontsize=6.6, color="#777777")
    fig.savefig(path_png, dpi=300, bbox_inches="tight", facecolor="white")
    fig.savefig(path_pdf, bbox_inches="tight", facecolor="white")


def main():
    df = load_ledger()
    tp = draw_time_perf(df, OUT / "eight_task_time_perf.png", OUT / "eight_task_time_perf.pdf")
    cov = coverage_matrix(df)
    cov.to_csv(OUT / "bigmodel_coverage_data.csv", index=False)
    draw_coverage(cov, OUT / "bigmodel_coverage.png", OUT / "bigmodel_coverage.pdf")
    mem = draw_memory(df, OUT / "peak_memory.png", OUT / "peak_memory.pdf")
    print(mem.to_string(index=False))
    # 断言：MRL micro LoRA random 的中位 wall 与均值须与已有表一致口径
    m = tp[(tp.task == "mrl") & (tp.model == "RiNALMo-micro") & (tp.strategy == "lora")].iloc[0]
    assert abs(m.metric - 0.8039) < 0.003, m.metric
    print(tp.groupby("task").size().to_string())
    print(cov.groupby("model")[CELL_KEYS].sum().to_string())
    (OUT / "time_perf_coverage_meta.json").write_text(json.dumps({
        "revision": "20261030_2030_work",
        "source": "bestval_ledger_export_20261030.csv",
        "notes": "wall time = median of completed seeds on shared RTX5090; not a controlled benchmark",
    }, ensure_ascii=False, indent=2))




def draw_memory(df, path_png, path_pdf):
    """5 官方模型 × 3 策略：跨 8 任务的中位峰值显存（须与任务配对，故附 min-max）。"""
    rows = []
    for model in MODELS:
        for strat in ("frozen", "lora", "full"):
            q = df[(df.model == model) & (df.strategy == strat)]
            if len(q) == 0:
                continue
            per_task = q.groupby("task").peak_mem_mb.median()
            rows.append({"model": model, "strategy": strat, "n_runs": len(q),
                         "median_gb": per_task.median() / 1024,
                         "min_gb": per_task.min() / 1024, "max_gb": per_task.max() / 1024,
                         "n_tasks": int(per_task.size)})
    m = pd.DataFrame(rows)
    m.to_csv(OUT / "peak_memory_data.csv", index=False)
    fig, ax = plt.subplots(figsize=(11.6, 3.95), constrained_layout=True)
    models_present = [x for x in MODELS if x in set(m.model)]
    x = np.arange(len(models_present))
    width = 0.25
    for j, strat in enumerate(("frozen", "lora", "full")):
        for i, model in enumerate(models_present):
            r = m[(m.model == model) & (m.strategy == strat)]
            if r.empty:
                continue
            r = r.iloc[0]
            ax.bar(x[i] + (j - 1) * width, r.median_gb, width=width * 0.92,
                   color=STRAT_COLORS[strat], edgecolor="white", linewidth=0.5,
                   yerr=[[r.median_gb - r.min_gb], [r.max_gb - r.median_gb]], capsize=3,
                   label={"frozen": "Frozen", "lora": "LoRA", "full": "Full-FT"}[strat] if i == 0 else None)
            ax.text(x[i] + (j - 1) * width, r.median_gb + 0.6, f"{r.median_gb:.1f}",
                    ha="center", va="bottom", fontsize=8, color="#333333")
    ax.axhline(24, color="#B03A2E", ls="--", lw=1.0, alpha=0.8)
    ax.text(len(models_present) - 0.55, 24.5, "24 GB 单卡参考线", color="#B03A2E", fontsize=8.2, ha="right")
    ax.set_xticks(x)
    ax.set_xticklabels([MODEL_SHORT[mm] for mm in models_present], fontsize=10)
    ax.set_ylabel("peak GPU memory (GB, median per task)", fontsize=9.6)
    ax.grid(axis="y", color="#E8E8E8", lw=0.6)
    ax.set_axisbelow(True)
    ax.legend(ncol=3, loc="upper left", fontsize=9)
    ax.set_ylim(0, max(30, float(m.max_gb.max()) * 1.12))
    fig.text(0.995, -0.03,
             "source: bestval ledger export 20261030 (peak_mem_mb of completed runs) · bar = median of per-task medians; whisker = min–max across the 8 tasks\n"
             "显存与标签顺序无关，可用于成本判断；但绝对值随 batch/序列长度变化，跨任务比较须同时看 min–max",
             transform=fig.transFigure, ha="right", va="top", fontsize=6.6, color="#777777")
    fig.savefig(path_png, dpi=300, bbox_inches="tight", facecolor="white")
    fig.savefig(path_pdf, bbox_inches="tight", facecolor="white")
    return m


if __name__ == "__main__":
    main()
