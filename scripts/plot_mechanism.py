#!/usr/bin/env python3
"""Plot same-sample three-state diagnostics and export every displayed coordinate."""
from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

STATES = ("pre", "lora", "full")
TITLES = {"pre": "Pre-finetuning", "lora": "Post-LoRA", "full": "Post-full finetuning"}
LABELS = {"cls": "CLS embedding", "head": "Prediction-head input"}
COLORS = ("#0F4D92", "#3775BA", "#42949E", "#8BCF8B", "#D9A441",
          "#B64342", "#E9A6A1", "#9A4D8E", "#EA84DD", "#767676",
          "#4D4D4D", "#6B8E23", "#CFCECE")
plt.rcParams.update({
    "font.family": ["Microsoft YaHei", "Arial", "DejaVu Sans"],
    "font.size": 10, "pdf.fonttype": 42, "ps.fonttype": 42,
    "savefig.dpi": 300, "legend.frameon": False,
})


def scalar(data, name, default):
    if name not in data:
        return default
    return data[name].item()


def silhouette_by_state(values, labels, states):
    from sklearn.metrics import silhouette_score
    result = {}
    for state in STATES:
        selected = states == state
        x = values[selected].astype(np.float64)
        y = labels[selected]
        if len(np.unique(x, axis=0)) < 2 or not 2 <= len(np.unique(y)) < len(x):
            result[state] = None
        else:
            result[state] = float(silhouette_score(x, y))
    return result


def load_projection(path, representation):
    with np.load(path, allow_pickle=False) as data:
        required = {"sample_ids", "labels", "state", "head_embedding", "cls",
                    "tsne_perplexity", "tsne_random_state"}
        missing = required - set(data.files)
        if missing:
            raise ValueError("aligned data is missing: " + ",".join(sorted(missing)))
        states = data["state"].astype(str)
        if list(dict.fromkeys(states)) != list(STATES):
            raise ValueError("projection must contain pre, lora and full in order")
        ids = data["sample_ids"].astype(str)
        labels = data["labels"]
        counts = [int(np.sum(states == state)) for state in STATES]
        if not counts[0] or len(set(counts)) != 1:
            raise ValueError("states must have the same nonzero sample count")
        for state in STATES[1:]:
            if not np.array_equal(ids[states == state], ids[states == STATES[0]]):
                raise ValueError("sample order differs across states")
            if not np.array_equal(labels[states == state], labels[states == STATES[0]]):
                raise ValueError("labels differ across states")
        values = data["cls" if representation == "cls" else "head_embedding"]
        if representation == "cls":
            if "tsne" not in data:
                raise ValueError("head coordinates are missing")
            from sklearn.manifold import TSNE
            coordinates = TSNE(
                n_components=2, random_state=int(data["tsne_random_state"]),
                perplexity=int(data["tsne_perplexity"])).fit_transform(values)
        else:
            coordinates = data["tsne"]
        if coordinates.shape != (len(states), 2) or not np.isfinite(coordinates).all():
            raise ValueError("invalid joint coordinates")
        return {
            "coordinates": coordinates, "values": values, "labels": labels,
            "states": states, "ids": ids, "n": counts[0],
            "split": str(scalar(data, "split", "unknown")),
            "seed": int(scalar(data, "seed", -1)),
            "perplexity": int(data["tsne_perplexity"]),
            "random_state": int(data["tsne_random_state"]),
            "manifest": str(scalar(data, "test_manifest_sha256", "unknown")),
        }


def plot_projection(projection, output, representation):
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    coordinates = projection["coordinates"]
    labels = projection["labels"]
    states = projection["states"]
    silhouettes = silhouette_by_state(projection["values"], labels, states)
    fig, axes = plt.subplots(1, 3, figsize=(13.2, 4.5), sharex=True, sharey=True)
    unique_labels = sorted(np.unique(labels).tolist())
    colors = {label: COLORS[index % len(COLORS)] for index, label in enumerate(unique_labels)}
    for axis, state in zip(axes, STATES):
        selected = states == state
        for label in unique_labels:
            choose = selected & (labels == label)
            axis.scatter(coordinates[choose, 0], coordinates[choose, 1], s=8,
                         color=colors[label], alpha=0.74, linewidths=0,
                         label="Family %s" % label)
        score = silhouettes[state]
        axis.set_title("%s\nhigh-dim silhouette: %s" %
                       (TITLES[state], "NA" if score is None else "%.3f" % score),
                       fontsize=11, pad=9)
        axis.set_xticks([])
        axis.set_yticks([])
        for spine in axis.spines.values():
            spine.set_color("#CFCECE")
            spine.set_linewidth(0.8)
    for axis in axes:
        axis.set_xlabel("t-SNE 1")
        axis.set_ylabel("t-SNE 2")
    axes[0].set_ylabel("t-SNE 2")
    handles, legend_labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, legend_labels, loc="center left", bbox_to_anchor=(0.99, 0.5),
               fontsize=8, title="ncRNA family", title_fontsize=9)
    fig.suptitle("RiNALMo-micro | %s | %s split | n=%d/state | seed=%d" %
                 (LABELS[representation], projection["split"], projection["n"],
                  projection["seed"]), fontsize=13, y=0.99)
    fig.text(0.5, 0.015,
             "Joint fit across states | perplexity=%d | random_state=%d | color=true family label; descriptive only"
             % (projection["perplexity"], projection["random_state"]),
             ha="center", fontsize=8.5, color="#4D4D4D")
    fig.tight_layout(rect=(0, 0.055, 0.88, 0.93), pad=1.2)
    fig.savefig(str(output) + ".png", bbox_inches="tight")
    fig.savefig(str(output) + ".pdf", bbox_inches="tight")
    plt.close(fig)

    coordinate_path = str(output) + "_coordinates.csv"
    with open(coordinate_path + ".tmp", "w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["representation", "split", "seed", "state", "sample_id",
                         "label", "tsne_1", "tsne_2", "silhouette_high_dim",
                         "perplexity", "random_state", "test_manifest_sha256"])
        for state in STATES:
            for index in np.where(states == state)[0]:
                writer.writerow([representation, projection["split"], projection["seed"],
                                 state, projection["ids"][index], labels[index],
                                 "%.10g" % coordinates[index, 0],
                                 "%.10g" % coordinates[index, 1], silhouettes[state],
                                 projection["perplexity"], projection["random_state"],
                                 projection["manifest"]])
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(coordinate_path + ".tmp", coordinate_path)
    metadata = {
        "representation": representation, "split": projection["split"],
        "seed": projection["seed"], "n_per_state": projection["n"],
        "perplexity": projection["perplexity"], "random_state": projection["random_state"],
        "silhouette_input": "original_high_dimensional_" + representation,
        "silhouette": silhouettes, "test_manifest_sha256": projection["manifest"],
        "coordinate_csv": coordinate_path,
        "interpretation": "descriptive_only_no_head_causality",
    }
    metadata_path = str(output) + "_metadata.json"
    with open(metadata_path + ".tmp", "w") as handle:
        json.dump(metadata, handle, indent=2)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(metadata_path + ".tmp", metadata_path)
    return metadata


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("aligned_npz")
    parser.add_argument("--representation", choices=("cls", "head"), required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    projection = load_projection(args.aligned_npz, args.representation)
    metadata = plot_projection(projection, args.output, args.representation)
    print(json.dumps(metadata, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
