#!/usr/bin/env python3
"""绘制 CRISPR 三状态联合投影，性能只使用完整 test。"""
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
COLORS = {0: "#3775BA", 1: "#B64342"}
plt.rcParams.update({
    "font.family": ["Microsoft YaHei", "Arial", "DejaVu Sans"],
    "font.size": 10,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "savefig.dpi": 300,
    "legend.frameon": False,
})


def scalar(data, name, default):
    if name not in data:
        return default
    return data[name].item()


def load_projection(path, representation):
    if representation not in LABELS:
        raise ValueError(representation)
    with np.load(path, allow_pickle=False) as data:
        coordinate_key = "tsne_cls" if representation == "cls" else "tsne_head"
        required = {coordinate_key, "sample_ids", "state", "labels", "probabilities",
                    "logits", "full_pr_auc", "full_roc_auc", "source_run_ids",
                    "color_mode", "sampling", "test_manifest_sha256",
                    "tsne_perplexity", "tsne_random_state"}
        missing = required - set(data.files)
        if missing:
            raise ValueError("aligned CRISPR 数据缺失: " + ",".join(sorted(missing)))
        if str(scalar(data, "color_mode", "")) != "crispr_off_target_label":
            raise ValueError("只能使用 CRISPR off-target 标签")
        states = data["state"].astype(str)
        if list(dict.fromkeys(states)) != list(STATES):
            raise ValueError("投影必须按 pre/lora/full 排列")
        ids = data["sample_ids"].astype(str)
        labels = data["labels"].astype(int)
        probabilities = data["probabilities"].astype(np.float32)
        logits = data["logits"].astype(np.float32)
        if not set(np.unique(labels)).issubset({0, 1}):
            raise ValueError("CRISPR 标签必须为 0/1")
        if probabilities.shape != (len(labels), 2) or logits.shape != (len(labels), 2):
            raise ValueError("CRISPR logits/probabilities 必须为 [N,2]")
        if not np.isfinite(logits).all() or not np.isfinite(probabilities).all():
            raise ValueError("logits/probabilities 非有限值")
        if not np.allclose(1 / (1 + np.exp(-logits)), probabilities, rtol=1e-4, atol=1e-5):
            raise ValueError("probabilities 不是二分类 softmax")
        counts = [int(np.sum(states == state)) for state in STATES]
        if not counts[0] or len(set(counts)) != 1:
            raise ValueError("三状态样本数必须相同且非零")
        for state in STATES[1:]:
            if not np.array_equal(ids[states == state], ids[states == STATES[0]]):
                raise ValueError("三状态 sample_id 顺序不一致")
            if not np.array_equal(labels[states == state], labels[states == STATES[0]]):
                raise ValueError("三状态二分类标签不一致")
        coordinates = data[coordinate_key].astype(np.float64)
        if coordinates.shape != (len(states), 2) or not np.isfinite(coordinates).all():
            raise ValueError("联合坐标无效")
        return {
            "coordinates": coordinates, "states": states, "ids": ids,
            "labels": labels, "probabilities": probabilities, "logits": logits,
            "n": counts[0], "split": str(scalar(data, "split", "unknown")),
            "seed": int(scalar(data, "seed", -1)),
            "perplexity": int(data["tsne_perplexity"]),
            "random_state": int(data["tsne_random_state"]),
            "manifest": str(data["test_manifest_sha256"].item()),
            "full_pr_auc": data["full_pr_auc"].astype(np.float64),
            "full_roc_auc": data["full_roc_auc"].astype(np.float64),
            "source_run_ids": data["source_run_ids"].astype(str),
            "sampling": str(scalar(data, "sampling", "unknown")),
        }


def plot_projection(projection, output, representation):
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    coordinates = projection["coordinates"]
    states = projection["states"]
    labels = projection["labels"]
    fig, axes = plt.subplots(1, 3, figsize=(13.2, 4.5), sharex=True, sharey=True)
    for index, (axis, state) in enumerate(zip(axes, STATES)):
        selected = states == state
        for label in (0, 1):
            choose = selected & (labels == label)
            axis.scatter(coordinates[choose, 0], coordinates[choose, 1], s=8,
                         color=COLORS[label], alpha=0.74, linewidths=0,
                         label="off-target negative" if label == 0 else "off-target positive")
        title = TITLES[state]
        if state != "pre":
            title += "\nfull-test PR-AUC=%.3f" % projection["full_pr_auc"][index]
        axis.set_title(title, fontsize=11, pad=9)
        axis.set_xticks([])
        axis.set_yticks([])
        axis.set_xlabel("t-SNE 1")
        if index == 0:
            axis.set_ylabel("t-SNE 2")
    handles, legend_labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, legend_labels, loc="center left", bbox_to_anchor=(0.94, 0.5),
               fontsize=8.5, title="True label", title_fontsize=9)
    fig.suptitle("RiNALMo-micro | %s | %s split | n=%d/state | seed=%d" % (
        LABELS[representation], projection["split"], projection["n"],
        projection["seed"]), fontsize=13, y=0.99)
    fig.text(0.5, 0.015,
             "Positive-enriched view | PR-AUC only on full test | no sampled prevalence or silhouette",
             ha="center", fontsize=8.5, color="#4D4D4D")
    fig.subplots_adjust(left=0.055, right=0.86, bottom=0.16, top=0.80, wspace=0.18)
    fig.savefig(str(output) + ".png", bbox_inches="tight")
    fig.savefig(str(output) + ".pdf", bbox_inches="tight")
    plt.close(fig)

    coordinate_path = str(output) + "_coordinates.csv"
    with open(coordinate_path + ".tmp", "w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "representation", "split", "seed", "state", "sample_id", "label",
            "positive_probability", "logits_json", "probabilities_json", "tsne_1",
            "tsne_2", "full_pr_auc", "full_roc_auc", "source_run_id", "sampling",
            "perplexity", "random_state", "test_manifest_sha256"])
        for index, state in enumerate(STATES):
            for row_index in np.where(states == state)[0]:
                writer.writerow([
                    representation, projection["split"], projection["seed"], state,
                    projection["ids"][row_index], int(labels[row_index]),
                    "%.10g" % projection["probabilities"][row_index, 1],
                    json.dumps(projection["logits"][row_index].tolist(), separators=(",", ":")),
                    json.dumps(projection["probabilities"][row_index].tolist(), separators=(",", ":")),
                    "%.10g" % coordinates[row_index, 0],
                    "%.10g" % coordinates[row_index, 1],
                    "%.10g" % projection["full_pr_auc"][index],
                    "%.10g" % projection["full_roc_auc"][index],
                    projection["source_run_ids"][index], projection["sampling"],
                    projection["perplexity"], projection["random_state"],
                    projection["manifest"]])
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(coordinate_path + ".tmp", coordinate_path)
    metadata = {
        "model": "RiNALMo-micro",
        "task": "crispr-off-target",
        "representation": representation,
        "split": projection["split"],
        "seed": projection["seed"],
        "n_per_state": projection["n"],
        "perplexity": projection["perplexity"],
        "random_state": projection["random_state"],
        "color_mode": "crispr_off_target_label",
        "sampling": projection["sampling"],
        "visualization_enrichment": True,
        "metric_scope": "PR_AUC_and_ROC_AUC_only_on_full_test",
        "classification_silhouette": None,
        "label_support": {
            state: {"positive": int(np.sum(labels[states == state] == 1)),
                    "negative": int(np.sum(labels[states == state] == 0))}
            for state in STATES
        },
        "full_pr_auc": dict(zip(STATES, projection["full_pr_auc"].tolist())),
        "full_roc_auc": dict(zip(STATES, projection["full_roc_auc"].tolist())),
        "source_run_ids": dict(zip(STATES, projection["source_run_ids"].tolist())),
        "pre_prediction_head": "fresh_reference_head_seed_201_not_zero_shot",
        "test_manifest_sha256": projection["manifest"],
        "coordinate_csv": coordinate_path,
        "interpretation": "descriptive_enriched_sample_full_test_metrics_only",
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
