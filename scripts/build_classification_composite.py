from hashlib import sha256
import json
from pathlib import Path
import shutil

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
SOURCE = ROOT / "交接文档/绘图数据/current/figure_source_data_20261028"
LEDGER = ROOT / "交接文档/绘图数据/current/figure_source_data_20261030_eight_task_v14/data/bestval_ledger_export_20261031_v4.csv"
PACKAGE = ROOT / "交接文档/绘图数据/current/figure_source_data_20261101_classification_composite"
FIGURES = PACKAGE / "figures"
DATA = PACKAGE / "data"
COORDINATES = DATA / "coordinates"
STATES = ("pre", "lora", "full")
STRATEGIES = ("frozen", "lora", "full")
COLORS = {"frozen": "#77AADD", "lora": "#EE8866", "full": "#444444"}

CONFIGS = [
    {
        "task": "ncrna", "prefix": "ncrna", "metric": "ACC", "title": "ncRNA family classification",
        "label": "label", "source": {
            "random": {
                "frozen": "ft_rinalmomicro_noncodingrnafamily_frozen_s17_random_bestval_v1",
                "lora": "ft_rinalmomicro_noncodingrnafamily_lora_s17_random_bestval_v1_fixedsplit",
                "full": "ft_rinalmomicro_noncodingrnafamily_full_s17_random_lr1e-05_bestval_v1"},
            "family": {
                "frozen": "ft_rinalmomicro_noncodingrnafamily_frozen_s17_family_bestval_v1",
                "lora": "ft_rinalmomicro_noncodingrnafamily_lora_s17_family_bestval_v1_fixedsplit",
                "full": "ft_rinalmomicro_noncodingrnafamily_full_s17_family_lr1e-05_bestval_v1"}},
    },
    {
        "task": "modification", "prefix": "modification", "metric": "m6A AUC", "title": "Modification | m6A index 7",
        "label": "m6a_label", "source": {
            "random": {
                "frozen": "ft_rinalmomicro_modification_frozen_s17_random_bestval_v1",
                "lora": "ft_rinalmomicro_modification_lora_s17_random_bestval_v1_seqmlfix",
                "full": "ft_rinalmomicro_modification_full_s17_random_lr1e-05_bestval_v1_seqmlfix"},
            "family": {
                "frozen": "ft_rinalmomicro_modification_frozen_s17_family_bestval_v1",
                "lora": "ft_rinalmomicro_modification_lora_s17_family_bestval_v1_seqmlfix",
                "full": "ft_rinalmomicro_modification_full_s17_family_lr1e-05_bestval_v1_seqmlfix"}},
    },
    {
        "task": "crispr", "prefix": "crispr", "metric": "PR-AUC", "title": "CRISPR off-target classification",
        "label": "label", "source": {
            "random": {
                "frozen": "ft_rinalmomicro_crisprofftarget_frozen_s17_random_bestval_v1",
                "lora": "ft_rinalmomicro_crisprofftarget_lora_s17_random_bestval_v1",
                "full": "ft_rinalmomicro_crisprofftarget_full_s17_random_lr1e-05_bestval_v1"},
            "family": {
                "frozen": "ft_rinalmomicro_crisprofftarget_frozen_s17_family_bestval_v1",
                "lora": "ft_rinalmomicro_crisprofftarget_lora_s17_family_bestval_v1",
                "full": "ft_rinalmomicro_crisprofftarget_full_s17_family_lr1e-05_bestval_v1"}},
    },
    {
        "task": "ssp", "prefix": "ssp", "metric": "pair-F1", "title": "SSP | pair-level classification",
        "label": "label", "downloaded": True, "source": {
            "random": {
                "frozen": "ft_rinalmomicro_secondarystructure_frozen_s17_random_pairalign_bestval_v1",
                "lora": "ft_rinalmomicro_secondarystructure_lora_s17_random_pairalign_bestval_v1",
                "full": "ft_rinalmomicro_secondarystructure_full_s17_random_lr1e-05_pairalign_bestval_v1"},
            "family": {
                "frozen": "ft_rinalmomicro_secondarystructure_frozen_s17_family_pairalign_bestval_v1",
                "lora": "ft_rinalmomicro_secondarystructure_lora_s17_family_pairalign_bestval_v1",
                "full": "ft_rinalmomicro_secondarystructure_full_s17_family_lr1e-05_pairalign_bestval_v1"}},
    },
    {
        "task": "spliceai", "prefix": "spliceai", "metric": "macro-F1", "title": "SpliceAI | per-base classification",
        "label": "label", "downloaded": True, "source": {
            "random": {
                "frozen": "ft_rinalmomicro_spliceai_frozen_s17_random_b20fix_bestval_v1",
                "lora": "ft_rinalmomicro_spliceai_lora_s17_random_b20fix_bestval_v1",
                "full": "ft_rinalmomicro_spliceai_full_s17_random_b20fix_lr1e-05_bestval_v1"},
            "family": {
                "frozen": "ft_rinalmomicro_spliceai_frozen_s17_family_b20fix_bestval_v1",
                "lora": "ft_rinalmomicro_spliceai_lora_s17_family_b20fix_bestval_v1",
                "full": "ft_rinalmomicro_spliceai_full_s17_family_b20fix_lr1e-05_bestval_v1"}},
    },
]


def file_sha(path):
    return sha256(path.read_bytes()).hexdigest()


def build(config, ledger):
    frames = []
    for split in ("random", "family"):
        if config.get("downloaded"):
            coordinate_path = COORDINATES / f"mechanism_{config['prefix']}/mechanism_{config['prefix']}_{split}_s17_coordinates.csv"
        else:
            coordinate_path = SOURCE / f"mechanism/mechanism_{config['prefix']}_{split}_cls_coordinates.csv"
        frame = pd.read_csv(coordinate_path)
        assert set(frame["state"]) == set(STATES)
        assert set(frame["seed"]) == {17} and set(frame["split"]) == {split}
        assert np.isfinite(frame[["tsne_1", "tsne_2"]].to_numpy()).all()
        frames.append(frame)
        shutil.copy2(coordinate_path, COORDINATES / f"{config['task']}_{split}_cls_coordinates.csv")
    coordinates = pd.concat(frames, ignore_index=True)
    performance = []
    for split in ("random", "family"):
        for strategy in STRATEGIES:
            rid = config["source"][split][strategy]
            rows = ledger[ledger["run_id"] == rid]
            assert len(rows) == 1, (config["task"], split, strategy, len(rows))
            row = rows.iloc[0]
            assert row["seed"] == 17 and row["split"] == split and row["strategy"] == strategy
            performance.append({"task": config["task"], "split": split, "seed": 17,
                                "strategy": strategy, "metric": config["metric"],
                                "value": row["value"], "run_id": rid,
                                "result_path": row["result_path"]})
            if strategy != "frozen" and "source_run_id" in coordinates:
                source_values = coordinates[(coordinates["split"] == split) &
                                            (coordinates["state"] == strategy)]
                assert set(source_values["source_run_id"]) == {rid}
                metric_column = {"modification": "full_m6a_auc",
                                 "crispr": "full_pr_auc", "ssp": "full_f1",
                                 "spliceai": "full_macro_f1"}.get(config["task"])
                if metric_column:
                    source_metric = source_values[metric_column].unique()
                    assert len(source_metric) == 1
                    assert abs(source_metric[0] - row["value"]) < 2e-6
    performance = pd.DataFrame(performance)
    performance.to_csv(DATA / f"{config['task']}_performance_seed17.csv", index=False)

    fig = plt.figure(figsize=(16, 6.2), constrained_layout=True)
    grid = fig.add_gridspec(2, 4, width_ratios=(1, 1, 1, 1.22))
    for row_index, split in enumerate(("random", "family")):
        for col, state in enumerate(STATES):
            ax = fig.add_subplot(grid[row_index, col])
            subset = coordinates[(coordinates["split"] == split) &
                                 (coordinates["state"] == state)]
            labels = subset[config["label"]].to_numpy()
            if config["task"] == "ncrna":
                scatter = ax.scatter(subset["tsne_1"], subset["tsne_2"], c=labels,
                                     cmap="tab20", s=4, alpha=0.65, linewidths=0)
            else:
                if config["task"] == "spliceai":
                    palette = np.choose(labels, ["#8A9BA8", "#D1495B", "#4C78A8"])
                else:
                    palette = np.where(labels == 1, "#D1495B", "#8A9BA8")
                scatter = ax.scatter(subset["tsne_1"], subset["tsne_2"], c=palette,
                                     s=5, alpha=0.65, linewidths=0)
            ax.set_title(f"{split} | {state} | n={len(subset)}", fontsize=11,
                         fontweight="bold", color="#1F3A5F")
            ax.set_xticks([])
            ax.set_yticks([])
            for spine in ax.spines.values():
                spine.set_color("#CCCCCC")
        ax = fig.add_subplot(grid[row_index, 3])
        subset = performance[performance["split"] == split].set_index("strategy").loc[list(STRATEGIES)]
        bars = ax.bar(np.arange(3), subset["value"], color=[COLORS[s] for s in STRATEGIES], width=0.65)
        for bar, value in zip(bars, subset["value"]):
            ax.text(bar.get_x() + bar.get_width() / 2, value + 0.018, f"{value:.3f}",
                    ha="center", va="bottom", fontsize=10, fontweight="bold", color="#1F3A5F")
        ax.set_xticks(np.arange(3), ["Frozen", "LoRA", "Full-FT"])
        ax.set_ylim(0, 1.08)
        ax.set_ylabel(config["metric"])
        ax.set_title(f"{split} | full-test performance | seed17", fontsize=11,
                     fontweight="bold", color="#1F3A5F")
        ax.grid(axis="y", color="#E8E8E8", linewidth=0.7)
        ax.set_axisbelow(True)
    fig.suptitle(f"{config['title']} | representation and downstream performance",
                 fontsize=16, fontweight="bold", color="#1F3A5F")
    fig.text(0.5, -0.02,
             "Joint t-SNE within each split (display sample only); bars use the exact same seed17 checkpoints on full test. Pre uses a reference head, not zero-shot.",
             ha="center", va="top", fontsize=9, color="#666666")
    fig.savefig(FIGURES / f"{config['task']}_classification_composite.png", dpi=300,
                bbox_inches="tight", facecolor="white")
    fig.savefig(FIGURES / f"{config['task']}_classification_composite.pdf",
                bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return {
        "task": config["task"], "seed": 17, "model": "RiNALMo-micro",
        "figure": f"figures/{config['task']}_classification_composite.png",
        "performance_data": f"data/{config['task']}_performance_seed17.csv",
        "coordinate_rows": len(coordinates), "performance_rows": len(performance),
        "metric_scope": "full_test_only", "projection_scope": "display_sample_only",
        "interpretation": "descriptive_not_causal",
    }


def main():
    FIGURES.mkdir(parents=True, exist_ok=True)
    COORDINATES.mkdir(parents=True, exist_ok=True)
    ledger = pd.read_csv(LEDGER)
    metadata = [build(config, ledger) for config in CONFIGS]
    (DATA / "composite_metadata.json").write_text(json.dumps(metadata, indent=2))
    files = sorted(path for path in PACKAGE.rglob("*") if path.is_file() and path.name != "manifest.json")
    manifest = {
        "revision": "20261101_classification_composite_v1",
        "source_ledger": str(LEDGER.relative_to(ROOT)),
        "source_ledger_sha256": file_sha(LEDGER),
        "files": [{"path": str(path.relative_to(PACKAGE)), "sha256": file_sha(path)}
                  for path in files],
    }
    (PACKAGE / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps({"figures": len(metadata), "files": len(files)}, indent=2))


if __name__ == "__main__":
    main()
