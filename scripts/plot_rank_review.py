#!/usr/bin/env python3
"""Export legacy rank sweeps and plot an explicit legacy/best-val review."""
from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
import statistics

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from rnafteval import ledger

MODELS = ("RiNALMo-micro", "SpliceBERT", "ERNIE-RNA", "RNA-FM")
TASKS = ("noncoding-rna-family", "secondary-structure", "mrl")
RANKS = (4, 8, 16)
MODEL_LABEL = {"RiNALMo-micro": "RiNALMo-33M", "SpliceBERT": "SpliceBERT-19M",
               "ERNIE-RNA": "ERNIE-86M", "RNA-FM": "RNA-FM-96M"}
FIELDS = ("run_id", "model", "task", "split", "seed", "rank", "metric",
          "value", "out_dir", "protocol", "evidence_scope")
plt.rcParams.update({"font.family": ["Microsoft YaHei", "Arial", "DejaVu Sans"],
                     "font.size": 9, "pdf.fonttype": 42, "ps.fonttype": 42})


def collect_legacy(rows=None):
    output = []
    for row in ledger.summary() if rows is None else rows:
        extra = row.get("extra", "")
        rank = 4 if extra == "_r4" else 16 if extra == "_r16" else 8 if extra in ("", None) else None
        if (row.get("model") not in MODELS or row.get("task") not in TASKS
                or row.get("strategy") != "lora" or row.get("split") != "random"
                or row.get("status") != "done" or row.get("smoke", False) is not False
                or row.get("protocol") is not None or rank is None
                or row.get("seed") not in (17, 29, 43)):
            continue
        expected_rid = ledger.run_id(row["model"], row["task"], "lora",
                                     row["seed"], "random", extra)
        if row["run_id"] != expected_rid:
            continue
        output.append({key: row.get(key) for key in
                       ("run_id", "model", "task", "split", "seed", "metric",
                        "value", "out_dir")} | {
            "rank": rank, "protocol": "legacy_fixed_epoch",
            "evidence_scope": "historical_rank_sweep_not_mixed_with_bestval",
        })
    output.sort(key=lambda row: (row["task"], row["model"], row["rank"], row["seed"]))
    return output


def grouped(rows, task, model, rank):
    values = [float(row["value"]) for row in rows
              if row["task"] == task and row["model"] == model and int(row["rank"]) == rank]
    if len(values) != 3:
        raise ValueError("legacy group requires 3 seeds: %s/%s/r%d" % (task, model, rank))
    return statistics.mean(values), statistics.stdev(values)


def write_legacy_csv(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def plot_review(legacy, rank8, output):
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    rank_rows = rank8["rows"]
    if len(rank_rows) != 6 or not all(row["proof"] == "ledger_result_curve_checkpoint_3_pass"
                                      for row in rank_rows):
        raise ValueError("rank8 panel requires six three-pass results")
    fig, axes = plt.subplots(1, 4, figsize=(14.5, 4.0),
                             gridspec_kw={"width_ratios": [0.9, 1.6, 1.6, 0.9]})
    colors = {4: "#AADCA9", 8: "#D9A441", 16: "#0F4D92"}
    split_colors = {"random": "#3775BA", "family": "#B64342"}
    ax = axes[0]
    for index, split in enumerate(("random", "family")):
        values = [float(row["ACC"]) for row in rank_rows if row["split"] == split]
        ax.bar(index, statistics.mean(values), yerr=statistics.stdev(values),
               capsize=4, color=split_colors[split], width=0.58,
               edgecolor="#4D4D4D", linewidth=0.6)
        ax.text(index, statistics.mean(values) + 0.004,
                "%.3f" % statistics.mean(values), ha="center", fontsize=8)
    ax.set_xticks([0, 1], ["random", "family"])
    ax.set_ylim(0.85, 0.95)
    ax.set_title("ncRNA | rank8 best-val\nmean ± SD, n=3/split", fontsize=10)
    ax.set_ylabel("ACC")
    ax.grid(axis="y", alpha=0.18, linewidth=0.6)

    for ax, task, title, metric in (
            (axes[1], "secondary-structure", "SSP | legacy rank sweep", "F1"),
            (axes[2], "mrl", "MRL | legacy rank sweep", "Pearson r")):
        x = np.arange(len(MODELS))
        width = 0.24
        rank_series = RANKS
        for offset, rank in enumerate(rank_series):
            summaries = [grouped(legacy, task, model, rank) for model in MODELS]
            means = [item[0] for item in summaries]
            errors = [item[1] for item in summaries]
            ax.bar(x + (offset - (len(rank_series) - 1) / 2) * width,
                   means, width, yerr=errors,
                   capsize=2, color=colors[rank], label="r=%d" % rank,
                   edgecolor="#4D4D4D", linewidth=0.4)
        ax.set_xticks(x, [MODEL_LABEL[model] for model in MODELS], rotation=16,
                      ha="right", fontsize=7.5)
        ax.set_title(title + "\nfixed epoch, mean ± SD, n=3", fontsize=10)
        ax.set_ylabel(metric)
        ax.grid(axis="y", alpha=0.18, linewidth=0.6)
        ax.legend(fontsize=7, loc="best")
    for ax in axes[:3]:
        ax.spines[["top", "right"]].set_visible(False)

    ax = axes[3]
    ax.set_axis_off()
    ax.set_title("modification | protocol review", fontsize=10)
    ax.text(0.5, 0.60, "Legacy per-base implementation\nquarantined", ha="center", va="center",
            fontsize=10, color="#B03A2E", weight="bold",
            bbox={"boxstyle": "round,pad=0.5", "facecolor": "#F4F7FA",
                  "edgecolor": "#CFCECE"})
    ax.text(0.5, 0.32, "Pending _seqmlfix formal runs\nHistorical invalid values not shown", ha="center", va="center",
            fontsize=8.5, color="#4D4D4D")
    fig.suptitle("Rank review | new rank8 protocol check + legacy sweeps", fontsize=13, y=0.99)
    fig.text(0.5, 0.01,
             "Legacy panels are not mixed with best-val. rank8 uses fixed split and checkpoint proof; old m6A values are quarantined.",
             ha="center", fontsize=8, color="#4D4D4D")
    fig.tight_layout(rect=(0, 0.055, 1, 0.91), pad=1.0)
    fig.savefig(str(output) + ".png", dpi=300, bbox_inches="tight")
    fig.savefig(str(output) + ".pdf", bbox_inches="tight")
    plt.close(fig)
    metadata = {
        "legacy_groups": len(legacy) // 3,
        "mrl_rank8_legacy": "complete_n3",
        "legacy_protocol": "fixed_epoch_n3",
        "rank8_protocol": rank8["protocol"],
        "rank8_random_mean": statistics.mean(
            row["ACC"] for row in rank_rows if row["split"] == "random"),
        "rank8_family_mean": statistics.mean(
            row["ACC"] for row in rank_rows if row["split"] == "family"),
        "modification": "legacy_per_base_quarantined_pending_seqmlfix",
        "source": "ledger + rank8_bestval_summary.json",
        "interpretation": "old low value not reproduced; not proof of cause",
    }
    with open(str(output) + "_metadata.json.tmp", "w") as handle:
        json.dump(metadata, handle, indent=2)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(str(output) + "_metadata.json.tmp", str(output) + "_metadata.json")
    return metadata


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export-legacy")
    parser.add_argument("--legacy-csv")
    parser.add_argument("--rank8-json")
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    if args.export_legacy:
        rows = collect_legacy()
        expected = 108
        if len(rows) != expected:
            raise ValueError("legacy source is incomplete: %d != %d" % (len(rows), expected))
        write_legacy_csv(args.export_legacy, rows)
        missing_path = args.export_legacy + ".missing.json"
        with open(missing_path + ".tmp", "w") as handle:
            json.dump({"missing_groups": []}, handle, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(missing_path + ".tmp", missing_path)
        print(json.dumps({"rows": len(rows), "groups": len(rows) // 3,
                          "mrl_rank8_legacy": "complete_n3",
                          "output": args.export_legacy}, indent=2))
        return 0
    if not (args.legacy_csv and args.rank8_json and args.output):
        parser.error("plot requires --legacy-csv, --rank8-json and --output")
    with open(args.legacy_csv, newline="") as handle:
        legacy = list(csv.DictReader(handle))
    rank8 = json.loads(Path(args.rank8_json).read_text())
    metadata = plot_review(legacy, rank8, args.output)
    print(json.dumps(metadata, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
