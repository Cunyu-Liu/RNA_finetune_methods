"""E6 灾难性遗忘谱线图（C6）：受控 RNA-Sc 家族 ΔNLL vs 模型规模。

仅受控系（因果 NLL，基线 ~4.5）。官方 RiNALMo-micro 为 MLM 全上下文
口径、绝对 NLL 跨系不可比，故不入本图（其行见 status/e6_table.md）。

x = 参数量（log 轴），y = ΔNLL（post − pre；正 = 遗忘）；两线 = LoRA /
full-FT，逐种子散点 + 均值折线，0 线参考。1M→650M 非单调谱线 = C6 主发现。

用法: python -m rnafteval.fig_e6 [--out status/figs]
"""
from __future__ import annotations

import argparse
import os

from rnafteval.export_e6 import collect

ROOT = "/mnt/cunyuliu/rna-ft-eval"
SCALE = {"RNA-Sc-1M": 1e6, "RNA-Sc-10M": 1e7, "RNA-Sc-30M": 3e7,
         "RNA-Sc-100M": 1e8, "RNA-Sc-650M": 6.5e8}
ORDER = ["RNA-Sc-1M", "RNA-Sc-10M", "RNA-Sc-30M", "RNA-Sc-100M",
         "RNA-Sc-650M"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "status", "figs"))
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    data = collect()

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    colors = {"lora": "#2166ac", "full": "#b2182b"}
    labels = {"lora": "LoRA", "full": "full-FT"}
    plotted = 0
    for strat in ("lora", "full"):
        xs, means, seedsets = [], [], []
        for m in ORDER:
            d = data.get((m, strat), {})
            if not d:
                continue
            vals = [r["delta_nll"] for r in d.values()]
            xs.append(SCALE[m])
            means.append(sum(vals) / len(vals))
            seedsets.append(vals)
        if not xs:
            continue
        plotted += len(xs)
        ax.plot(xs, means, "-o", color=colors[strat], label=labels[strat],
                lw=1.8, ms=5, zorder=3)
        for x, vals in zip(xs, seedsets):
            ax.scatter([x] * len(vals), vals, color=colors[strat], s=14,
                       alpha=0.55, zorder=2)

    ax.axhline(0, color="#555555", ls="--", lw=1)
    ax.set_xscale("log")
    ax.set_xticks([1e6, 1e7, 3e7, 1e8, 6.5e8])
    ax.set_xticklabels(["1M", "10M", "30M", "100M", "650M"])
    ax.set_xlabel("controlled family size (params, log scale)")
    ax.set_ylabel(u"\u0394 pretraining NLL  (post \u2212 pre;  + = forgetting)")
    ax.set_title("C6: catastrophic forgetting is non-monotone across scale\n"
                 "(RNA-Sc controlled family; causal NLL)")
    ax.legend(frameon=False)
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(args.out, "fig_e6_spectrum.%s" % ext),
                    dpi=200, bbox_inches="tight")
    print("fig_e6_spectrum: %d scale points -> %s" % (plotted, args.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())