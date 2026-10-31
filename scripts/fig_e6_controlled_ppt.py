"""Controlled-only E6 figure for the results deck; official MLM is excluded."""
import argparse
from hashlib import sha256
import json
import math
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

PALETTE = {"blue": "#0F4D92", "red": "#B64342", "gray": "#767676"}
SCALES = {"RNA-Sc-1M": 1, "RNA-Sc-10M": 10, "RNA-Sc-30M": 30,
          "RNA-Sc-100M": 100, "RNA-Sc-650M": 650}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    rows = [json.loads(line) for line in open(args.ledger) if line.strip()]
    grouped = defaultdict(list)
    source_rows = []
    for row in rows:
        if (row.get("task") == "e6-forgetting" and row.get("status") == "done"
                and row.get("model") in SCALES and row.get("strategy") in ("lora", "full")
                and row.get("seed") in (17, 29, 43) and not row.get("smoke")):
            value = row.get("delta_nll")
            if isinstance(value, (int, float)) and math.isfinite(value):
                grouped[(row["model"], row["strategy"])].append(value)
                source_rows.append({key: row.get(key) for key in
                                    ("run_id", "model", "strategy", "seed", "delta_nll",
                                     "out_dir", "protocol", "forgetting_protocol")})
    assert len(grouped) == 10, f"expected 10 controlled groups, got {len(grouped)}"
    assert sum(len(v) for v in grouped.values()) == 30, "expected 30 controlled cells"
    assert all(len(values) == 3 for values in grouped.values())
    assert len({row["run_id"] for row in source_rows}) == 30

    plt.rcParams.update({
        "font.family": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
        "font.size": 11, "axes.linewidth": 1.4,
        "axes.spines.top": False, "axes.spines.right": False,
        "legend.frameon": False, "svg.fonttype": "none",
    })
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(11.2, 4.3),
                                  gridspec_kw={"width_ratios": [2.25, 1]})
    for strategy, color, label in (("lora", PALETTE["blue"], "LoRA"),
                                   ("full", PALETTE["red"], "full-FT")):
        xs = list(SCALES.values())
        means = [np.mean(grouped[(model, strategy)]) for model in SCALES]
        assert all(np.isfinite(means)), (model, strategy, means)
        ax.plot(xs, means, "-o", color=color, lw=2.1, ms=5.5, label=label, zorder=3)
        for model, x in SCALES.items():
            values = grouped[(model, strategy)]
            ax.scatter([x] * len(values), values, s=18, color=color,
                       alpha=0.45, zorder=2)
    ax.axhline(0, color=PALETTE["gray"], lw=1.0, ls="--")
    ax.set_xscale("log")
    ax.set_xticks(list(SCALES.values()), ["1M", "10M", "30M", "100M", "650M"])
    ax.set_xlabel("Controlled model size (log scale)")
    ax.set_ylabel("Δ pretraining NLL (post − pre)")
    ax.set_title("A  Non-monotone forgetting across controlled scale", loc="left", fontweight="bold")
    ax.legend(loc="upper left")
    ax.text(0.02, 0.03, "Positive = forgetting; negative = reverse gain",
            transform=ax.transAxes, color=PALETTE["gray"], fontsize=9)

    worst_full = max(grouped[("RNA-Sc-30M", "full")])
    worst_lora = max(grouped[("RNA-Sc-30M", "lora")])
    bars = ax2.bar([0, 1], [worst_lora, worst_full],
                   color=[PALETTE["blue"], PALETTE["red"]], width=0.58,
                   edgecolor="black", linewidth=1.0)
    ax2.set_xticks([0, 1], ["LoRA", "full-FT"])
    ax2.set_ylabel("Worst-seed ΔNLL (post − pre)")
    ax2.set_title("B  30M worst-seed comparison", loc="left", fontweight="bold")
    for bar, value in zip(bars, [worst_lora, worst_full]):
        ax2.text(bar.get_x() + bar.get_width() / 2, value + 0.7,
                 f"+{value:.1f}", ha="center", va="bottom", fontweight="bold")
    ratio = worst_full / worst_lora
    ax2.annotate(f"≈{ratio:.1f}× tail reduction", xy=(0, worst_lora),
                 xytext=(0.5, worst_full * 0.72), ha="center",
                 arrowprops={"arrowstyle": "->", "color": PALETTE["gray"], "lw": 1.2},
                 color=PALETTE["gray"], fontweight="bold")
    ax2.set_ylim(0, worst_full * 1.2)
    fig.suptitle("Controlled RNA-Sc | causal held-out NLL after ncRNA fine-tuning",
                 x=0.02, ha="left", fontsize=14, fontweight="bold")
    fig.text(0.02, 0.005,
             "Seeds 17/29/43; points = individual runs, lines = means. Official MLM uses a separate fixed-mask protocol and is not mixed into this panel.",
             color=PALETTE["gray"], fontsize=8.5)
    fig.tight_layout(rect=(0, 0.045, 1, 0.92))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=300, bbox_inches="tight")
    fig.savefig(out.with_suffix(".pdf"), bbox_inches="tight")
    import csv
    with out.with_suffix(".csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(source_rows[0]))
        writer.writeheader()
        writer.writerows(source_rows)
    metadata = {
        "source_ledger": str(args.ledger),
        "source_ledger_sha256": sha256(Path(args.ledger).read_bytes()).hexdigest(),
        "cells": 30, "groups": {f"{model}/{strategy}": {
            "n": len(grouped[(model, strategy)]),
            "mean": float(np.mean(grouped[(model, strategy)]))}
            for model in SCALES for strategy in ("lora", "full")},
        "worst_lora_30m": worst_lora, "worst_full_30m": worst_full,
        "tail_ratio": ratio, "y_axis": "delta_nll_post_minus_pre",
        "positive_meaning": "forgetting", "negative_meaning": "reverse_gain",
        "official_mlm": "separate_fixed_mask_protocol_not_mixed",
    }
    out.with_suffix(".json").write_text(json.dumps(metadata, indent=2))
    print("CONTROLLED_E6_FIG_OK", {"cells": 30, "worst_lora": worst_lora,
                                  "worst_full": worst_full, "ratio": ratio,
                                  "out": str(out)})


if __name__ == "__main__":
    main()
