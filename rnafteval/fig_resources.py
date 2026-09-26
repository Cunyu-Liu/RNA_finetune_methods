"""T4.1.2 cost-benefit figure (Schmirler Fig.5 style): x=GPU wall (min, log),
y=task metric, one panel per task, colour=strategy. Data: status/resources_costbenefit.csv.
"""
from __future__ import annotations
import csv, os, collections
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = "/mnt/cunyuliu/rna-ft-eval"
CSV = os.path.join(ROOT, "status", "resources_costbenefit.csv")
OUTDIR = os.path.join(ROOT, "status", "figs")
TASKS = [("noncoding-rna-family", "ncRNA family (ACC)"),
         ("secondary-structure", "secondary structure (F1)"),
         ("modification", "m6A modification (AUC)")]
COL = {"frozen": "#4C72B0", "lora": "#DD8452", "full": "#55A868",
       "dora": "#8172B3", "ia3": "#937860", "head-only": "#DA8BC3"}

def main():
    rows = list(csv.DictReader(open(CSV)))
    for r in rows:
        r["wall"] = float(r["wall_med_min"]); r["val"] = float(r["value_mean"])
    os.makedirs(OUTDIR, exist_ok=True)
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.4))
    for ax, (task, label) in zip(axes, TASKS):
        sub = [r for r in rows if r["task"] == task]
        for strat in ["frozen", "lora", "full", "dora", "ia3", "head-only"]:
            pts = [r for r in sub if r["strategy"] == strat]
            if not pts: continue
            ax.scatter([p["wall"] for p in pts], [p["val"] for p in pts],
                       s=42, c=COL.get(strat, "gray"), label=strat, alpha=0.85,
                       edgecolors="white", linewidths=0.5)
        for r in sub:
            if r["model"] in ("RiNALMo-650M", "RiNALMo-micro", "RNA-Sc-650M",
                              "ERNIE-RNA", "UTR-LM"):
                ax.annotate(r["model"], (r["wall"], r["val"]), fontsize=5.5,
                            xytext=(3, 3), textcoords="offset points")
        ax.set_xscale("log"); ax.set_title(label, fontsize=10)
        ax.set_xlabel("wall-clock median (min, GPU)"); ax.grid(alpha=0.25)
    axes[0].set_ylabel("task metric (test, 3-seed mean)")
    axes[0].legend(fontsize=7, loc="lower right")
    fig.suptitle("E5 cost-benefit: performance vs measured GPU wall-clock (formal seeds)", fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(OUTDIR, "fig_resources_costbenefit." + ext), dpi=200)
    print("written", OUTDIR + "/fig_resources_costbenefit.{png,pdf}")

if __name__ == "__main__":
    raise SystemExit(main())
