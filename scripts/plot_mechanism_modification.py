#!/usr/bin/env python3
"""绘制 modification 的 m6A 三状态联合投影并导出全部显示点。"""
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
M6A_INDEX = 7
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
        required = {coordinate_key, "sample_ids", "state", "labels", "m6a_label",
                    "probabilities", "logits", "full_m6a_auc", "full_mean_auc",
                    "source_run_ids", "color_mode", "test_manifest_sha256",
                    "tsne_perplexity", "tsne_random_state"}
        missing = required - set(data.files)
        if missing:
            raise ValueError("aligned modification 数据缺失: " + ",".join(sorted(missing)))
        if str(scalar(data, "color_mode", "")) != "m6a_label_index_7":
            raise ValueError("只能使用 m6A index 7 标签视图")
        states = data["state"].astype(str)
        if list(dict.fromkeys(states)) != list(STATES):
            raise ValueError("投影必须按 pre/lora/full 排列")
        ids = data["sample_ids"].astype(str)
        labels = data["labels"].astype(np.float32)
        m6a_label = data["m6a_label"].astype(int)
        probabilities = data["probabilities"].astype(np.float32)
        logits = data["logits"].astype(np.float32)
        if labels.ndim != 2 or labels.shape[1] != 12:
            raise ValueError("labels 必须为 [N,12]")
        if probabilities.shape != labels.shape or logits.shape != labels.shape:
            raise ValueError("logits/probabilities 形状不一致")
        if not np.array_equal(m6a_label, labels[:, M6A_INDEX].astype(int)):
            raise ValueError("m6a_label 与 labels[:,7] 不一致")
        if not np.isfinite(logits).all() or not np.isfinite(probabilities).all():
            raise ValueError("logits/probabilities 非有限值")
        if not np.allclose(1 / (1 + np.exp(-logits)), probabilities, rtol=1e-4, atol=1e-5):
            raise ValueError("probabilities 不是逐标签独立 sigmoid")
        counts = [int(np.sum(states == state)) for state in STATES]
        if not counts[0] or len(set(counts)) != 1:
            raise ValueError("三状态样本数必须相同且非零")
        for state in STATES[1:]:
            if not np.array_equal(ids[states == state], ids[states == STATES[0]]):
                raise ValueError("三状态 sample_id 顺序不一致")
            if not np.array_equal(labels[states == state], labels[states == STATES[0]]):
                raise ValueError("三状态 12 维标签不一致")
        coordinates = data[coordinate_key].astype(np.float64)
        if coordinates.shape != (len(states), 2) or not np.isfinite(coordinates).all():
            raise ValueError("联合坐标无效")
        return {
            "coordinates": coordinates, "states": states, "ids": ids,
            "labels": labels, "m6a_label": m6a_label,
            "probabilities": probabilities, "logits": logits,
            "n": counts[0], "split": str(scalar(data, "split", "unknown")),
            "seed": int(scalar(data, "seed", -1)),
            "perplexity": int(data["tsne_perplexity"]),
            "random_state": int(data["tsne_random_state"]),
            "manifest": str(data["test_manifest_sha256"].item()),
            "full_m6a_auc": data["full_m6a_auc"].astype(np.float64),
            "full_mean_auc": data["full_mean_auc"].astype(np.float64),
            "source_run_ids": data["source_run_ids"].astype(str),
        }


def plot_projection(projection, output, representation):
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    coordinates = projection["coordinates"]
    states = projection["states"]
    m6a_label = projection["m6a_label"]
    fig, axes = plt.subplots(1, 3, figsize=(13.2, 4.5), sharex=True, sharey=True)
    for index, (axis, state) in enumerate(zip(axes, STATES)):
        selected = states == state
        for label in (0, 1):
            choose = selected & (m6a_label == label)
            axis.scatter(coordinates[choose, 0], coordinates[choose, 1], s=8,
                         color=COLORS[label], alpha=0.74, linewidths=0,
                         label="m6A negative" if label == 0 else "m6A positive")
        title = TITLES[state]
        if state != "pre":
            title += "\nfull-test m6A AUC=%.3f" % projection["full_m6a_auc"][index]
        axis.set_title(title, fontsize=11, pad=9)
        axis.set_xticks([])
        axis.set_yticks([])
        axis.set_xlabel("t-SNE 1")
        if index == 0:
            axis.set_ylabel("t-SNE 2")
    handles, legend_labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, legend_labels, loc="center left", bbox_to_anchor=(0.94, 0.5),
               fontsize=9, title="Label index 7", title_fontsize=9)
    fig.suptitle("RiNALMo-micro | %s | %s split | n=%d/state | seed=%d" % (
        LABELS[representation], projection["split"], projection["n"],
        projection["seed"]), fontsize=13, y=0.99)
    fig.text(0.5, 0.015,
             "m6A view of 12-label task | post AUC uses full test | no 12-class softmax or silhouette",
             ha="center", fontsize=8.5, color="#4D4D4D")
    fig.subplots_adjust(left=0.055, right=0.86, bottom=0.16, top=0.80, wspace=0.18)
    fig.savefig(str(output) + ".png", bbox_inches="tight")
    fig.savefig(str(output) + ".pdf", bbox_inches="tight")
    plt.close(fig)

    coordinate_path = str(output) + "_coordinates.csv"
    with open(coordinate_path + ".tmp", "w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "representation", "split", "seed", "state", "sample_id", "m6a_label",
            "m6a_probability", "m6a_logit", "labels_json", "probabilities_json",
            "logits_json", "tsne_1", "tsne_2", "full_m6a_auc", "full_mean_auc",
            "source_run_id", "perplexity", "random_state", "test_manifest_sha256"])
        for index, state in enumerate(STATES):
            for row_index in np.where(states == state)[0]:
                labels = projection["labels"][row_index].astype(int).tolist()
                probabilities = projection["probabilities"][row_index].tolist()
                logits = projection["logits"][row_index].tolist()
                writer.writerow([
                    representation, projection["split"], projection["seed"], state,
                    projection["ids"][row_index], int(m6a_label[row_index]),
                    "%.10g" % probabilities[M6A_INDEX], "%.10g" % logits[M6A_INDEX],
                    json.dumps(labels, separators=(",", ":")),
                    json.dumps(probabilities, separators=(",", ":")),
                    json.dumps(logits, separators=(",", ":")),
                    "%.10g" % coordinates[row_index, 0],
                    "%.10g" % coordinates[row_index, 1],
                    "%.10g" % projection["full_m6a_auc"][index],
                    "%.10g" % projection["full_mean_auc"][index],
                    projection["source_run_ids"][index], projection["perplexity"],
                    projection["random_state"], projection["manifest"]])
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(coordinate_path + ".tmp", coordinate_path)
    metadata = {
        "model": "RiNALMo-micro",
        "task": "modification",
        "representation": representation,
        "split": projection["split"],
        "seed": projection["seed"],
        "n_per_state": projection["n"],
        "perplexity": projection["perplexity"],
        "random_state": projection["random_state"],
        "color_mode": "m6a_label_index_7",
        "label_semantics": "BEACON sequence-level multi-label; m6A index 7",
        "classification_silhouette": None,
        "m6a_support": {
            state: {
                "positive": int(np.sum(m6a_label[states == state] == 1)),
                "negative": int(np.sum(m6a_label[states == state] == 0)),
            } for state in STATES
        },
        "full_m6a_auc": dict(zip(STATES, projection["full_m6a_auc"].tolist())),
        "full_mean_auc": dict(zip(STATES, projection["full_mean_auc"].tolist())),
        "source_run_ids": dict(zip(STATES, projection["source_run_ids"].tolist())),
        "pre_prediction_head": "fresh_reference_head_seed_201_not_zero_shot",
        "test_manifest_sha256": projection["manifest"],
        "coordinate_csv": coordinate_path,
        "interpretation": "descriptive_multilabel_m6a_view_not_single_label_task",
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
