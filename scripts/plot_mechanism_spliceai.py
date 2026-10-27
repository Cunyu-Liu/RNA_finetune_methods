#!/usr/bin/env python3
"""绘制 SpliceAI per-base token 三状态联合投影。"""
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
from scipy.special import softmax

STATES = ("pre", "lora", "full")
TITLES = {"pre": "Pre-finetuning", "lora": "Post-LoRA", "full": "Post-full finetuning"}
CLASS_NAMES = {0: "negative", 1: "acceptor", 2: "donor"}
COLORS = {0: "#6F6F6F", 1: "#3775BA", 2: "#B64342"}
ROC_AUC_ROLE = "auxiliary_full_test_only_not_source_reconciliation"
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


def load_projection(path):
    with np.load(path, allow_pickle=False) as data:
        required = {"tsne", "token_ids", "sequence_ids", "base_positions",
                    "token_positions", "state", "labels", "probabilities", "logits",
                    "full_macro_f1", "full_micro_f1", "full_roc_auc", "roc_auc_role",
                    "metric_scope", "source_run_ids", "color_mode", "sampling",
                    "full_test_sha256", "test_manifest_sha256", "tsne_perplexity",
                    "tsne_random_state"}
        missing = required - set(data.files)
        if missing:
            raise ValueError("aligned SpliceAI 数据缺失: " + ",".join(sorted(missing)))
        if str(scalar(data, "color_mode", "")) != "spliceai_token_class":
            raise ValueError("只能使用 SpliceAI token class")
        if str(scalar(data, "roc_auc_role", "")) != ROC_AUC_ROLE:
            raise ValueError("ROC-AUC 只能作为 full-test auxiliary 诊断")
        states = data["state"].astype(str)
        if list(dict.fromkeys(states)) != list(STATES):
            raise ValueError("投影必须按 pre/lora/full 排列")
        token_ids = data["token_ids"].astype(str)
        sequence_ids = data["sequence_ids"].astype(str)
        base_positions = data["base_positions"].astype(int)
        token_positions = data["token_positions"].astype(int)
        labels = data["labels"].astype(int)
        probabilities = data["probabilities"].astype(np.float32)
        logits = data["logits"].astype(np.float32)
        if not set(np.unique(labels)).issubset({0, 1, 2}):
            raise ValueError("SpliceAI 标签必须为 0/1/2")
        if probabilities.shape != (len(labels), 3) or logits.shape != (len(labels), 3):
            raise ValueError("SpliceAI logits/probabilities 必须为 [N,3]")
        if not np.isfinite(logits).all() or not np.isfinite(probabilities).all():
            raise ValueError("logits/probabilities 非有限值")
        if not np.allclose(softmax(logits, axis=-1), probabilities, rtol=1e-4, atol=1e-5):
            raise ValueError("probabilities 不是三分类 softmax")
        expected_ids = [f"{sequence_id}:{base:04d}" for sequence_id, base in zip(
            sequence_ids, base_positions)]
        if token_ids.tolist() != expected_ids:
            raise ValueError("token_id 与 sequence_id/base_position 不一致")
        counts = [int(np.sum(states == state)) for state in STATES]
        if not counts[0] or len(set(counts)) != 1:
            raise ValueError("三状态样本数必须相同且非零")
        alignment = {"token_ids": token_ids, "sequence_ids": sequence_ids,
                     "base_positions": base_positions, "token_positions": token_positions,
                     "labels": labels}
        for state in STATES[1:]:
            for key, values in alignment.items():
                if not np.array_equal(values[states == state], values[states == STATES[0]]):
                    raise ValueError("三状态对齐不一致: " + key)
        coordinates = data["tsne"].astype(np.float64)
        if coordinates.shape != (len(states), 2) or not np.isfinite(coordinates).all():
            raise ValueError("联合坐标无效")
        metrics = {key: data[key].astype(np.float64) for key in
                   ("full_macro_f1", "full_micro_f1", "full_roc_auc")}
        if any(values.shape != (3,) or not np.isfinite(values).all()
               for values in metrics.values()):
            raise ValueError("full-test macro/micro/ROC-AUC 数组无效")
        return {
            "coordinates": coordinates, "states": states, **alignment,
            "probabilities": probabilities, "logits": logits,
            "n": counts[0], "split": str(scalar(data, "split", "unknown")),
            "seed": int(scalar(data, "seed", -1)),
            "perplexity": int(data["tsne_perplexity"]),
            "random_state": int(data["tsne_random_state"]),
            "manifest": str(data["test_manifest_sha256"].item()),
            "full_test_sha256": str(data["full_test_sha256"].item()),
            **metrics,
            "roc_auc_role": ROC_AUC_ROLE,
            "metric_scope": str(scalar(data, "metric_scope", "")),
            "source_run_ids": data["source_run_ids"].astype(str),
            "sampling": str(scalar(data, "sampling", "unknown")),
        }


def plot_projection(projection, output):
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    coordinates = projection["coordinates"]
    states = projection["states"]
    labels = projection["labels"]
    fig, axes = plt.subplots(1, 3, figsize=(13.2, 4.5), sharex=True, sharey=True)
    for index, (axis, state) in enumerate(zip(axes, STATES)):
        selected = states == state
        for label in (0, 1, 2):
            choose = selected & (labels == label)
            axis.scatter(coordinates[choose, 0], coordinates[choose, 1], s=8,
                         color=COLORS[label], alpha=0.72, linewidths=0,
                         label=CLASS_NAMES[label])
        title = TITLES[state]
        if state != "pre":
            title += "\nfull-test macro-F1=%.3f | micro-F1=%.3f" % (
                projection["full_macro_f1"][index], projection["full_micro_f1"][index])
        axis.set_title(title, fontsize=11, pad=9)
        axis.set_xticks([])
        axis.set_yticks([])
        axis.set_xlabel("t-SNE 1")
        if index == 0:
            axis.set_ylabel("t-SNE 2")
    handles, legend_labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, legend_labels, loc="center left", bbox_to_anchor=(0.94, 0.5),
               fontsize=8.5, title="Token class", title_fontsize=9)
    fig.suptitle("RiNALMo-micro | per-base token | %s split | n=%d/state | seed=%d" % (
        projection["split"], projection["n"], projection["seed"]), fontsize=13, y=0.99)
    fig.text(0.5, 0.015,
             "Balanced token view | macro/micro: full-test source metrics | ROC-AUC: auxiliary only",
             ha="center", fontsize=8.5, color="#4D4D4D")
    fig.subplots_adjust(left=0.055, right=0.86, bottom=0.16, top=0.80, wspace=0.18)
    fig.savefig(str(output) + ".png", bbox_inches="tight")
    fig.savefig(str(output) + ".pdf", bbox_inches="tight")
    plt.close(fig)

    coordinate_path = str(output) + "_coordinates.csv"
    with open(coordinate_path + ".tmp", "w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "representation", "split", "seed", "state", "token_id", "sequence_id",
            "base_position", "token_position", "label", "class_name", "logits_json",
            "probabilities_json", "tsne_1", "tsne_2", "full_macro_f1", "full_micro_f1",
            "full_roc_auc", "roc_auc_role", "source_run_id", "sampling", "perplexity",
            "random_state", "full_test_sha256", "test_manifest_sha256"])
        for index, state in enumerate(STATES):
            for row_index in np.where(states == state)[0]:
                label = int(labels[row_index])
                writer.writerow([
                    "per_base_token", projection["split"], projection["seed"], state,
                    projection["token_ids"][row_index], projection["sequence_ids"][row_index],
                    int(projection["base_positions"][row_index]),
                    int(projection["token_positions"][row_index]), label, CLASS_NAMES[label],
                    json.dumps(projection["logits"][row_index].tolist(), separators=(",", ":")),
                    json.dumps(projection["probabilities"][row_index].tolist(), separators=(",", ":")),
                    "%.10g" % coordinates[row_index, 0],
                    "%.10g" % coordinates[row_index, 1],
                    "%.10g" % projection["full_macro_f1"][index],
                    "%.10g" % projection["full_micro_f1"][index],
                    "%.10g" % projection["full_roc_auc"][index], ROC_AUC_ROLE,
                    projection["source_run_ids"][index], projection["sampling"],
                    projection["perplexity"], projection["random_state"],
                    projection["full_test_sha256"], projection["manifest"]])
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(coordinate_path + ".tmp", coordinate_path)
    metadata = {
        "model": "RiNALMo-micro",
        "task": "spliceai",
        "representation": "per_base_token",
        "split": projection["split"],
        "seed": projection["seed"],
        "n_per_state": projection["n"],
        "perplexity": projection["perplexity"],
        "random_state": projection["random_state"],
        "color_mode": "spliceai_token_class",
        "sampling": projection["sampling"],
        "class_balanced_visualization": True,
        "class_names": {str(label): CLASS_NAMES[label] for label in range(3)},
        "metric_scope": projection["metric_scope"],
        "source_reconciliation_metrics": ["macro_f1", "micro_f1"],
        "roc_auc_role": ROC_AUC_ROLE,
        "classification_silhouette": None,
        "label_support": {
            state: {CLASS_NAMES[label]: int(np.sum(labels[states == state] == label))
                    for label in range(3)} for state in STATES
        },
        "full_macro_f1": dict(zip(STATES, projection["full_macro_f1"].tolist())),
        "full_micro_f1": dict(zip(STATES, projection["full_micro_f1"].tolist())),
        "full_roc_auc": dict(zip(STATES, projection["full_roc_auc"].tolist())),
        "source_run_ids": dict(zip(STATES, projection["source_run_ids"].tolist())),
        "pre_prediction_head": "fresh_reference_head_seed_201_not_zero_shot",
        "full_test_sha256": projection["full_test_sha256"],
        "test_manifest_sha256": projection["manifest"],
        "coordinate_csv": coordinate_path,
        "interpretation": "descriptive_balanced_tokens_full_test_metrics_only",
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
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    projection = load_projection(args.aligned_npz)
    metadata = plot_projection(projection, args.output)
    print(json.dumps(metadata, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
