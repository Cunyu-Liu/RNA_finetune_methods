"""构建 8 任务 × 5 官方模型 × 6 柱（frozen/LoRA/full × random/family）总览图。

数据源（只读）：
  - current_results/bestval_ledger_export_20261030.csv        主矩阵 best-val 台账
  - figures/mrl_bestval_official_sixbar_20261030_data.csv     MRL 权威聚合（含 650M n=2）
  - figures/modification_bestval_official_sixbar_data.csv     modification 权威聚合
  - figures/extension_three_task_sixbar_data.csv              SpliceAI/degradation/SSI 阶段表

输出：
  eight_task_sixbar_data.csv   逐格 n / mean / sd / 数据来源
  eight_task_sixbar.png/.pdf   2×4 面板（上排序列级、下排碱基级）
"""
from pathlib import Path
import csv
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import font_manager

ROOT = Path(__file__).resolve().parents[3] / "交接文档"  # 交接文档/
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
    "frozen_random": "#6BAED6",
    "frozen_family": "#C6DBEF",
    "lora_random": "#FD8D3C",
    "lora_family": "#D94801",
    "full_random": "#3B3B3B",
    "full_family": "#A6A6A6",
}
SIX_LABELS = {
    "frozen_random": "Frozen (R)",
    "frozen_family": "Frozen (F)",
    "lora_random": "LoRA (R)",
    "lora_family": "LoRA (F)",
    "full_random": "Full-FT (R)",
    "full_family": "Full-FT (F)",
}
MODELS = ["RiNALMo-micro", "RiNALMo-mega", "RiNALMo-650M", "ERNIE-RNA", "RNA-FM"]
MODEL_SHORT = {
    "RiNALMo-micro": "33M",
    "RiNALMo-mega": "148M",
    "RiNALMo-650M": "650M",
    "ERNIE-RNA": "ERNIE",
    "RNA-FM": "RNA-FM",
}
TASKS = [
    ("noncoding-rna-family", "ncRNA 家族分类", "ACC", "序列级分类"),
    ("crispr-off-target", "CRISPR 脱靶", "PR-AUC", "序列级分类"),
    ("modification", "modification", "m6A AUC", "序列级分类"),
    ("mrl", "MRL", "Pearson r", "序列级回归"),
    ("spliceai", "SpliceAI", "macro-F1", "碱基级分类"),
    ("secondary-structure", "SSP", "pair-F1", "碱基级分类"),
    ("degradation", "mRNA 降解", "PCC", "碱基级回归"),
    ("ssi", "SSI", "PCC", "碱基级回归"),
]
CELL_KEYS = list(SIX_COLORS)


def load_ledger():
    rows = list(csv.DictReader(open(WORK / "current_results/bestval_ledger_export_20261030.csv")))
    keep = []
    for r in rows:
        # 训练顺序 A/B 诊断不计入任何正式均值
        if "_noshuffle" in r["run_id"]:
            continue
        # 排除 C5c 低数据档（ncRNA 1000–3000），其余任务的全量 n 即为本矩阵口径
        if r["task"] == "noncoding-rna-family" and int(r["n_train"]) < 5000:
            continue
        keep.append(r)
    return pd.DataFrame(keep)


def ledger_cell(df, task, model, strategy, split):
    q = df[(df.task == task) & (df.model == model) & (df.strategy == strategy) & (df.split == split)]
    assert q["seed"].astype(int).nunique() == len(q), (task, model, strategy, split, "duplicate seed")
    vals = pd.to_numeric(q["value"], errors="coerce").dropna().to_numpy(float)
    return len(vals), float(vals.mean()) if len(vals) else np.nan, \
        float(vals.std(ddof=1)) if len(vals) > 1 else 0.0


def aggregate_table(df, task):
    out = []
    for model in MODELS:
        row = {"model": model}
        for key in CELL_KEYS:
            strategy, split = key.rsplit("_", 1)
            n, mean, sd = ledger_cell(df, task, model, strategy, split)
            row[f"{key}_n"], row[key], row[f"{key}_sd"] = n, mean, sd
        row["source"] = "bestval_ledger_export_20261030"
        out.append(row)
    return pd.DataFrame(out)


def merge_sixbar_table(task, path):
    src = pd.read_csv(path)
    out = []
    for model in MODELS:
        row = {"model": model}
        if model in set(src.model):
            s = src[src.model == model].iloc[0]
            for key in CELL_KEYS:
                row[f"{key}_n"] = int(s[f"{key}_n"]) if pd.notna(s[f"{key}_n"]) else 0
                row[key] = float(s[key]) if pd.notna(s[key]) else np.nan
                row[f"{key}_sd"] = 0.0
        else:
            for key in CELL_KEYS:
                row[f"{key}_n"], row[key], row[f"{key}_sd"] = 0, np.nan, 0.0
        row["source"] = path.name
        out.append(row)
    return pd.DataFrame(out)


TABLE_MODEL = {
    "rinalmomicro": "RiNALMo-micro",
    "rinalmomega": "RiNALMo-mega",
    "rinalmo650m": "RiNALMo-650M",
    "ernierna": "ERNIE-RNA",
    "rnafm": "RNA-FM",
    "nucleicbert": "NucleicBERT",
}


def merge_extension(task, path):
    src = pd.read_csv(path)
    src = src[src.task == task].copy()
    src["model"] = src["model"].map(lambda x: TABLE_MODEL.get(x, x))
    out = []
    for model in MODELS:
        row = {"model": model, "source": path.name}
        s = src[src.model == model]
        for key in CELL_KEYS:
            ncol = f"{key}_n"
            if len(s) and ncol in s and pd.notna(s.iloc[0][ncol]) and float(s.iloc[0][ncol]) > 0:
                row[f"{key}_n"] = int(s.iloc[0][ncol])
                row[key] = float(s.iloc[0][key])
                row[f"{key}_sd"] = 0.0
            else:
                row[f"{key}_n"], row[key], row[f"{key}_sd"] = 0, np.nan, 0.0
        out.append(row)
    return pd.DataFrame(out)


def panel_ylim(task, table):
    vals = []
    for key in CELL_KEYS:
        v = table[key].to_numpy(float)
        vals.extend(v[np.isfinite(v)])
    if not vals:
        return 1.0
    hi = max(vals)
    step = 0.2 if hi <= 0.8 else 0.25
    return min(1.05, step * (int(np.ceil((hi * 1.12) / step))) + 0.05)


def draw(ax, table, task_label, metric, ylim, label_min_n=3):
    x = np.arange(len(table))
    width = 0.135
    for j, key in enumerate(CELL_KEYS):
        pos = x + (j - 2.5) * width
        for i in range(len(table)):
            n = int(table[f"{key}_n"].iloc[i])
            v = float(table[key].iloc[i])
            sd = float(table[f"{key}_sd"].iloc[i])
            if n == 0 or not np.isfinite(v):
                continue
            ax.bar(pos[i], v, width=width * 0.94, color=SIX_COLORS[key],
                   edgecolor="white", linewidth=0.4,
                   yerr=sd if n > 1 else None, capsize=1.2,
                   hatch="///" if n < 3 else None)
            if n >= label_min_n:
                ax.text(pos[i], min(v + ylim * 0.012, ylim * 0.97), f"{v:.2f}",
                        ha="center", va="bottom", fontsize=6.2, color="#333333", rotation=90)
    ax.set_title(f"{task_label}｜{metric}", fontsize=8.4, fontweight="bold",
                 color="#1F3A5F", pad=4)
    ax.set_xticks(x)
    ax.set_xticklabels([MODEL_SHORT[m] for m in table.model], fontsize=6.6)
    ax.set_ylim(0, ylim)
    ax.tick_params(axis="y", labelsize=6.4, length=2, pad=1)
    ax.tick_params(axis="x", length=0, pad=1.5)
    ax.grid(axis="y", color="#E8E8E8", lw=0.5)
    ax.set_axisbelow(True)


EXT_TASKS = ["crispr-off-target", "spliceai", "secondary-structure", "degradation", "ssi"]


def main():
    ledger = load_ledger()
    tables, notes = {}, {}
    for task, label, metric, family in TASKS:
        if task == "mrl":
            t = merge_sixbar_table(task, WORK / "figures/mrl_bestval_official_sixbar_20261030_data.csv")
            t["source"] = "mrl_bestval_official_sixbar_20261030"
        elif task == "modification":
            t = merge_sixbar_table(task, WORK / "figures/modification_bestval_official_sixbar_data.csv")
            t["source"] = "modification_bestval_official_sixbar"
        elif task in ("spliceai", "degradation", "ssi"):
            t = merge_extension(task, WORK / "figures/extension_three_task_sixbar_data.csv")
            # 台账中同一格的正式 best-val 结果优先覆盖阶段表
            for i, model in enumerate(MODELS):
                for key in CELL_KEYS:
                    strategy, split = key.rsplit("_", 1)
                    n, mean, sd = ledger_cell(ledger, task, model, strategy, split)
                    if n > 0:
                        t.loc[i, f"{key}_n"], t.loc[i, key], t.loc[i, f"{key}_sd"] = n, mean, sd
                        t.loc[i, "source"] = t.loc[i, "source"] + "+ledger"
        else:
            t = aggregate_table(ledger, task)
        tables[task] = t
        notes[task] = (label, metric, family)

    combined = []
    for task, _label, _metric, _fam in TASKS:
        t = tables[task].copy()
        t.insert(0, "task", task)
        combined.append(t)
    allt = pd.concat(combined, ignore_index=True)
    allt.to_csv(OUT / "eight_task_sixbar_data.csv", index=False)

    # 数值断言：核心已知值必须命中
    def cell(task, model, key):
        t = tables[task]
        return float(t[t.model == model].iloc[0][key])
    checks = [
        ("mrl", "RiNALMo-micro", "frozen_random", 0.7299, 0.002),
        ("mrl", "RiNALMo-micro", "lora_random", 0.8039, 0.002),
        ("modification", "RiNALMo-micro", "frozen_random", 0.6498, 0.004),
        ("noncoding-rna-family", "RiNALMo-micro", "lora_random", None, None),
    ]
    for task, model, key, expected, tol in checks:
        got = cell(task, model, key)
        if expected is not None:
            assert abs(got - expected) <= tol, (task, model, key, got, expected)
    lo = [c for c in ("noncoding-rna-family", "crispr-off-target", "modification", "mrl",
                      "spliceai", "secondary-structure", "degradation", "ssi")
          if np.isfinite(tables[c][CELL_KEYS].to_numpy(float)).sum() > 0]
    assert len(lo) == 8, lo
    print("assertions ok; ncRNA micro lora_random =", round(cell("noncoding-rna-family", "RiNALMo-micro", "lora_random"), 4))

    fig, axes = plt.subplots(2, 3, figsize=(12.4, 4.25), constrained_layout=True)
    ext = [t for t in TASKS if t[0] in EXT_TASKS]
    for idx, (task, label, metric, family) in enumerate(ext):
        ax = axes[idx // 3, idx % 3]
        draw(ax, tables[task], label, metric, panel_ylim(task, tables[task]))
        ax.text(0.985, 0.965, family, transform=ax.transAxes, ha="right", va="top",
                fontsize=6.0, color="#8A8A8A")
    ax_note = axes[1, 2]
    ax_note.axis("off")
    handles = [plt.Rectangle((0, 0), 1, 1, color=SIX_COLORS[k]) for k in CELL_KEYS]
    ax_note.legend(handles, [SIX_LABELS[k] for k in CELL_KEYS], ncol=2, loc="upper left",
                   fontsize=7.6, handlelength=1.4, columnspacing=1.0, labelspacing=0.6)
    ax_note.text(0.0, 0.42,
                 "读图：本页补齐 ①a 的其余 5 个任务，\n"
                 "与前 3 页（ncRNA / modification / MRL）合并为 8 任务。\n"
                 "六柱 = frozen / LoRA / full-FT × random(R) / family(F)。\n"
                 "斜线 = n<3；空白 = 该格未完成（不画 0）。\n"
                 "纵轴按任务独立，不跨指标比较。",
                 transform=ax_note.transAxes, ha="left", va="top", fontsize=7.4, color="#333333",
                 linespacing=1.6)
    fig.text(0.995, -0.035,
             "source: bestval ledger export 20261030 (main matrix) + B20 stage table for SpliceAI/degradation/SSI · "
             "bars = mean, whisker = SD when n>1 · value labels shown when n>=3 · no cross-task score pooling",
             transform=fig.transFigure, ha="right", va="top", fontsize=6.4, color="#777777")
    fig.savefig(OUT / "eight_task_sixbar.png", dpi=300, bbox_inches="tight", facecolor="white")
    fig.savefig(OUT / "eight_task_sixbar.pdf", bbox_inches="tight", facecolor="white")

    # 覆盖度摘要
    summary = []
    for task, label, metric, family in TASKS:
        t = tables[task]
        filled = int(sum(int(t[f"{k}_n"].sum()) for k in CELL_KEYS))
        complete = sum(1 for k in CELL_KEYS for i in range(len(t)) if int(t[f"{k}_n"].iloc[i]) >= 3)
        summary.append({"task": task, "family": family, "metric": metric,
                        "runs_plotted": filled, "cells_ge3seed": complete, "cells_total": 30})
    pd.DataFrame(summary).to_csv(OUT / "eight_task_sixbar_coverage.csv", index=False)
    (OUT / "eight_task_sixbar_meta.json").write_text(json.dumps({
        "figure": "eight_task_sixbar",
        "revision": "20261030_2030_work",
        "sources": ["current_results/bestval_ledger_export_20261030.csv",
                    "figures/mrl_bestval_official_sixbar_20261030_data.csv",
                    "figures/modification_bestval_official_sixbar_data.csv",
                    "figures/extension_three_task_sixbar_data.csv"],
        "coverage": summary,
        "notes": "hatched=n<3; NA=not complete; 每任务只用本任务主指标，不跨指标汇总",
    }, ensure_ascii=False, indent=2))
    print(pd.DataFrame(summary).to_string(index=False))


if __name__ == "__main__":
    main()
