import argparse
from hashlib import sha256
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
PACKAGE = ROOT / "交接文档/绘图数据/current/figure_source_data_20261101_classification_composite"
COORDINATES = PACKAGE / "data/coordinates/mechanism_spliceai"
LEDGER = ROOT / "交接文档/绘图数据/current/figure_source_data_20261030_eight_task_v14/data/bestval_ledger_export_20261031_v4.csv"
STATES = ("pre", "lora", "full")
STRATEGIES = ("frozen", "lora", "full")
COLORS = {"frozen": "#77AADD", "lora": "#EE8866", "full": "#444444"}


def rid(strategy, seed, split):
    if strategy == "frozen":
        return f"ft_rinalmomicro_spliceai_frozen_s{seed}_{split}_b20fix_bestval_v1"
    if strategy == "lora":
        return f"ft_rinalmomicro_spliceai_lora_s{seed}_{split}_b20fix_bestval_v1"
    return f"ft_rinalmomicro_spliceai_full_s{seed}_{split}_b20fix_lr1e-05_bestval_v1"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=("random", "family"), required=True)
    args = parser.parse_args()
    split = args.split
    ledger = pd.read_csv(LEDGER)
    all_coordinates = []
    performance = []
    for seed in (17, 29, 43):
        path = COORDINATES / f"mechanism_spliceai_{split}_s{seed}_coordinates.csv"
        assert path.is_file(), path
        frame = pd.read_csv(path)
        assert set(frame["state"]) == set(STATES)
        assert set(frame["seed"]) == {seed} and set(frame["split"]) == {split}
        assert np.isfinite(frame[["tsne_1", "tsne_2"]].to_numpy()).all()
        all_coordinates.append(frame)
        for strategy in STRATEGIES:
            source_rid = rid(strategy, seed, split)
            rows = ledger[ledger["run_id"] == source_rid]
            assert len(rows) == 1, (seed, split, strategy, len(rows))
            value = rows.iloc[0]["value"]
            performance.append({"split": split, "seed": seed, "strategy": strategy,
                                "metric": "macro-F1", "value": value,
                                "run_id": source_rid,
                                "result_path": rows.iloc[0]["result_path"]})
            if strategy != "frozen":
                source = frame[frame["state"] == strategy]
                assert set(source["source_run_id"]) == {source_rid}
                metric = source["full_macro_f1"].unique()
                assert len(metric) == 1 and abs(metric[0] - value) < 2e-6
    coordinates = pd.concat(all_coordinates, ignore_index=True)
    performance = pd.DataFrame(performance)
    performance.to_csv(PACKAGE / f"data/spliceai_{split}_multiseed_performance.csv", index=False)

    fig = plt.figure(figsize=(16, 7.2), constrained_layout=True)
    grid = fig.add_gridspec(3, 4, width_ratios=(1, 1, 1, 1.22))
    for row_index, seed in enumerate((17, 29, 43)):
        for col, state in enumerate(STATES):
            ax = fig.add_subplot(grid[row_index, col])
            subset = coordinates[(coordinates["seed"] == seed) &
                                 (coordinates["state"] == state)]
            palette = np.choose(subset["label"].to_numpy(),
                                ["#8A9BA8", "#D1495B", "#4C78A8"])
            ax.scatter(subset["tsne_1"], subset["tsne_2"], c=palette,
                       s=5, alpha=0.65, linewidths=0)
            ax.set_title(f"seed{seed} | {state} | n={len(subset)}", fontsize=11,
                         fontweight="bold", color="#1F3A5F")
            ax.set_xticks([])
            ax.set_yticks([])
            for spine in ax.spines.values():
                spine.set_color("#CCCCCC")
        ax = fig.add_subplot(grid[row_index, 3])
        subset = performance[performance["seed"] == seed].set_index("strategy").loc[list(STRATEGIES)]
        bars = ax.bar(np.arange(3), subset["value"],
                      color=[COLORS[strategy] for strategy in STRATEGIES], width=0.65)
        for bar, value in zip(bars, subset["value"]):
            ax.text(bar.get_x() + bar.get_width() / 2, value + 0.018, f"{value:.3f}",
                    ha="center", va="bottom", fontsize=10, fontweight="bold", color="#1F3A5F")
        ax.set_xticks(np.arange(3), ["Frozen", "LoRA", "Full-FT"])
        ax.set_ylim(0, 1.08)
        ax.set_ylabel("macro-F1")
        ax.set_title(f"seed{seed} | full-test performance", fontsize=11,
                     fontweight="bold", color="#1F3A5F")
        ax.grid(axis="y", color="#E8E8E8", linewidth=0.7)
        ax.set_axisbelow(True)
    fig.suptitle(f"SpliceAI {split} | three seeds | representation and full-test performance",
                 fontsize=16, fontweight="bold", color="#1F3A5F")
    fig.text(0.5, -0.015,
             "Each seed/split has an independent joint t-SNE (display sample only). Bars use exact checkpoints on full test; gray/red/blue = negative/acceptor/donor.",
             ha="center", va="top", fontsize=9, color="#666666")
    stem = PACKAGE / f"figures/spliceai_{split}_multiseed_composite"
    fig.savefig(stem.with_suffix(".png"), dpi=300, bbox_inches="tight", facecolor="white")
    fig.savefig(stem.with_suffix(".pdf"), bbox_inches="tight", facecolor="white")
    plt.close(fig)
    metadata = {
        "task": "spliceai", "split": split, "seeds": [17, 29, 43],
        "coordinate_rows": len(coordinates), "performance_rows": len(performance),
        "coordinate_sha256": {str(seed): sha256((COORDINATES / f"mechanism_spliceai_{split}_s{seed}_coordinates.csv").read_bytes()).hexdigest()
                              for seed in (17, 29, 43)},
        "metric_scope": "full_test_only", "projection_scope": "display_sample_only",
        "figure": stem.with_suffix(".png").name,
    }
    (PACKAGE / f"data/spliceai_{split}_multiseed_metadata.json").write_text(json.dumps(metadata, indent=2))
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
