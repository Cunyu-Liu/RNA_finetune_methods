"""C5b 等价线图：双家族 full-FT vs LoRA（random 切分 acc）+ family 侧崩溃注记。

用法: python -m rnafteval.fig_c5b
产物: status/figs/fig_c5b.png
"""
from __future__ import annotations

import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = "/mnt/cunyuliu/rna-ft-eval"
OUT = os.path.join(ROOT, "status", "figs")

FAMILY = {
    "RiNALMo (official)": {
        "full": [("RiNALMo-micro", 33, 0.938), ("RiNALMo-mega", 148, 0.942)],
        "lora": [("RiNALMo-micro", 33, 0.929), ("RiNALMo-650M", 650, 0.969)],
    },
    "RNA-Sc (controlled)": {
        "full": [("RNA-Sc-1M", 1, 0.693), ("RNA-Sc-10M", 10, 0.788),
                 ("RNA-Sc-30M", 30, None)],
        "lora": [("RNA-Sc-10M", 10, 0.740), ("RNA-Sc-30M", 30, None),
                 ("RNA-Sc-100M", 100, 0.795)],
    },
}


def fill_from_ledger():
    """从 ledger 补 None 值（30M 等在跑的档位落账后自动入图）。"""
    vals = {}
    with open(os.path.join(ROOT, "ledger.jsonl")) as f:
        for line in f:
            r = json.loads(line)
            if r.get("task") != "noncoding-rna-family" or r.get("status") != "done":
                continue
            rid = r.get("run_id", "")
            if "_lr" in rid or "_e3" in rid or "_smoke" in rid:
                continue
            key = (r.get("model"), r.get("strategy"), r.get("split"))
            vals.setdefault(key, []).append(r.get("value"))
    for fam, arms in FAMILY.items():
        for arm, pts in arms.items():
            for i, (m, scale, v) in enumerate(pts):
                if v is None:
                    dd = vals.get((m, arm, "random"), [])
                    if dd:
                        pts[i] = (m, scale, sum(dd) / len(dd))
    return vals


def main():
    vals = fill_from_ledger()
    os.makedirs(OUT, exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), sharey=True)
    for ax, (fam, arms) in zip(axes, FAMILY.items()):
        for arm, style in (("full", "o-"), ("lora", "s--")):
            pts = [(s, v) for _, s, v in arms[arm] if v is not None]
            if len(pts) >= 2:
                xs, ys = zip(*pts)
                ax.plot(xs, ys, style, label={"full": "full FT (tuned)",
                                              "lora": "LoRA (r=8)"}[arm])
        ax.set_xscale("log")
        ax.set_xlabel("params (M, log)")
        ax.set_title(fam, fontsize=11)
        ax.grid(alpha=0.3)
        ax.legend(fontsize=9)
    axes[0].set_ylabel("ncRNA accuracy (random split)")
    axes[0].set_ylim(0.6, 1.0)
    fig.suptitle("C5b: small full-FT vs large LoRA — equivalence is family-dependent",
                 fontsize=12)
    fig.text(0.5, 0.01,
             "family splits: 7 scales in 0.06-0.12 band on average; 148M LoRA escapes (0.14-0.33) — "
             "largely scale-invariant, partial LoRA escape at high pretraining sufficiency",
             ha="center", fontsize=9, style="italic")
    fig.tight_layout(rect=(0, 0.04, 1, 0.94))
    out = os.path.join(OUT, "fig_c5b.png")
    fig.savefig(out, dpi=180)
    print("written:", out)


if __name__ == "__main__":
    main()
