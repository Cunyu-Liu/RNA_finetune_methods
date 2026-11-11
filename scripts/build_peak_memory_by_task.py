from pathlib import Path
import csv
import hashlib
import json
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import font_manager

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "交接文档").is_dir() and (p / "ppt").is_dir())
SOURCE = ROOT / "交接文档/绘图数据/current/figure_source_data_20261030_eight_task_v14/data/bestval_ledger_export_20261101_v209.csv"
OUT = ROOT / "ppt/work/review_20261111"
TASKS = [
    ("noncoding-rna-family", "ncRNA"),
    ("crispr-off-target", "CRISPR"),
    ("modification", "modification"),
    ("mrl", "MRL"),
    ("spliceai", "SpliceAI"),
    ("secondary-structure", "SSP"),
    ("degradation", "degradation"),
    ("ssi", "SSI"),
]
MODELS = ["RiNALMo-micro", "RiNALMo-mega", "RiNALMo-650M", "ERNIE-RNA", "RNA-FM"]
MODEL_SHORT = dict(zip(MODELS, ["33M", "148M", "650M", "ERNIE", "RNA-FM"]))
STRATEGIES = ["frozen", "lora", "full"]
COLORS = {"frozen": "#6BAED6", "lora": "#FD8D3C", "full": "#3B3B3B"}
FONT = Path.home() / "Library/Fonts/msyh.ttc"
font_manager.fontManager.addfont(str(FONT))
plt.rcParams.update({
    "font.family": [font_manager.FontProperties(fname=str(FONT)).get_name(), "DejaVu Sans"],
    "axes.unicode_minus": False,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "pdf.fonttype": 42,
})


def keep_row(row):
    rid = row["run_id"]
    if any(tag in rid for tag in ("_noshuffle", "_smoke", "_diag", "_seqmlfix")):
        return False
    if re.search(r"_r(?:4|16)_", rid) or int(row["seed"]) not in (17, 29, 43):
        return False
    if re.search(r"_e3\d+_", rid):
        return False
    for key in ("artifact_dir", "resolved_artifact_dir"):
        if "/home/cunyuliu/rna-ft-eval/artifacts" in str(row.get(key, "")):
            return False
    return True


def main():
    raw = list(csv.DictReader(SOURCE.open()))
    rows = [r for r in raw if keep_row(r)]
    out = []
    for task, _ in TASKS:
        for model in MODELS:
            for strategy in STRATEGIES:
                selected = [r for r in rows if r["task"] == task and r["model"] == model and r["strategy"] == strategy]
                if not selected:
                    continue
                peaks = np.array([float(r["peak_mem_mb"]) / 1024 for r in selected])
                out.append({
                    "task": task,
                    "model": model,
                    "strategy": strategy,
                    "n": len(selected),
                    "median_gb": float(np.median(peaks)),
                    "min_gb": float(peaks.min()),
                    "max_gb": float(peaks.max()),
                    "rids": ";".join(r["run_id"] for r in selected),
                })
    frame = pd.DataFrame(out)
    frame.to_csv(OUT / "peak_memory_by_task_data.csv", index=False)

    fig, axes = plt.subplots(2, 4, figsize=(12.4, 5.05), constrained_layout=True)
    x = np.arange(len(MODELS))
    width = 0.24
    for ax, (task, label) in zip(axes.flat, TASKS):
        for j, strategy in enumerate(STRATEGIES):
            sub = frame[(frame.task == task) & (frame.strategy == strategy)]
            vals = [float(sub[sub.model == model].median_gb.iloc[0]) if not sub[sub.model == model].empty else np.nan for model in MODELS]
            ax.bar(x + (j - 1) * width, vals, width=width, color=COLORS[strategy], label=strategy)
        ax.set_title(label, fontsize=10, fontweight="bold", color="#1F3A5F")
        ax.set_yscale("log")
        ax.set_ylim(0.25, 30)
        ax.set_xticks(x)
        ax.set_xticklabels([MODEL_SHORT[m] for m in MODELS], fontsize=7)
        ax.tick_params(axis="y", labelsize=7)
        ax.grid(axis="y", color="#E7E7E7", linewidth=0.55)
        ax.set_axisbelow(True)
    for ax in axes[1, :]:
        ax.set_xlabel("model", fontsize=8)
    for ax in axes[:, 0]:
        ax.set_ylabel("peak GPU memory (GB, log)", fontsize=8)
    handles = [plt.Rectangle((0, 0), 1, 1, color=COLORS[s]) for s in STRATEGIES]
    fig.legend(handles, ["Frozen", "LoRA", "Full-FT"], ncol=3, loc="upper center", bbox_to_anchor=(0.5, 1.055), fontsize=8, frameon=False)
    fig.text(0.995, -0.035,
             "source: bestval_ledger_export_20261101_v209 · formal seeds 17/29/43 · bar = per-task median of measured CUDA peaks\n"
             "Different task runner/max_len/output granularity; do not interpret cross-task min–max as a model fault",
             transform=fig.transFigure, ha="right", va="top", fontsize=6.6, color="#666666")
    fig.savefig(OUT / "peak_memory_by_task.png", dpi=300, bbox_inches="tight", facecolor="white")
    fig.savefig(OUT / "peak_memory_by_task.pdf", bbox_inches="tight", facecolor="white")

    def sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()
    micro = frame[(frame.model == "RiNALMo-micro") & (frame.strategy == "lora")]
    manifest = {
        "revision": "20261111_peak_memory_by_task_v1",
        "input": str(SOURCE.relative_to(ROOT)),
        "input_sha256": sha(SOURCE),
        "rows": len(frame),
        "micro_lora": micro[["task", "n", "median_gb", "min_gb", "max_gb"]].to_dict("records"),
        "outputs": {},
    }
    for name in ["peak_memory_by_task_data.csv", "peak_memory_by_task.png", "peak_memory_by_task.pdf", "build_peak_memory_by_task.py"]:
        manifest["outputs"][name] = sha(OUT / name)
    (OUT / "peak_memory_by_task_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"rows": len(frame), "micro_lora": manifest["micro_lora"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
