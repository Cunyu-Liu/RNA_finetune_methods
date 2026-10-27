#!/usr/bin/env python3
"""绘制 MRL 三状态联合投影并导出全部显示坐标。"""
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
        required = {coordinate_key, "sample_ids", "state", "y_true", "prediction",
                    "residual", "full_pearson", "source_run_ids", "color_mode",
                    "test_manifest_sha256", "tsne_perplexity", "tsne_random_state"}
        missing = required - set(data.files)
        if missing:
            raise ValueError("aligned MRL 数据缺失: " + ",".join(sorted(missing)))
        if str(scalar(data, "color_mode", "")) != "true_mrl_continuous":
            raise ValueError("MRL 图必须使用 continuous true_mrl 标签")
        states = data["state"].astype(str)
        if list(dict.fromkeys(states)) != list(STATES):
            raise ValueError("投影必须按 pre/lora/full 排列")
        ids = data["sample_ids"].astype(str)
        y_true = data["y_true"].astype(np.float64)
        prediction = data["prediction"].astype(np.float64)
        residual = data["residual"].astype(np.float64)
        counts = [int(np.sum(states == state)) for state in STATES]
        if not counts[0] or len(set(counts)) != 1:
            raise ValueError("三状态样本数必须相同且非零")
        for state in STATES[1:]:
            if not np.array_equal(ids[states == state], ids[states == STATES[0]]):
                raise ValueError("三状态 sample_id 顺序不一致")
            if not np.array_equal(y_true[states == state], y_true[states == STATES[0]]):
                raise ValueError("三状态 MRL 标签不一致")
        coordinates = data[coordinate_key].astype(np.float64)
        if coordinates.shape != (len(states), 2) or not np.isfinite(coordinates).all():
            raise ValueError("联合坐标无效")
        if not np.isfinite(residual).all() or not np.allclose(
                residual, prediction - y_true, rtol=0, atol=1e-6):
            raise ValueError("residual 与 prediction-y_true 不一致")
        return {
            "coordinates": coordinates, "states": states, "ids": ids,
            "y_true": y_true, "prediction": prediction, "residual": residual,
            "n": counts[0], "split": str(scalar(data, "split", "unknown")),
            "seed": int(scalar(data, "seed", -1)),
            "perplexity": int(data["tsne_perplexity"]),
            "random_state": int(data["tsne_random_state"]),
            "manifest": str(data["test_manifest_sha256"].item()),
            "full_pearson": data["full_pearson"].astype(np.float64),
            "source_run_ids": data["source_run_ids"].astype(str),
        }


def plot_projection(projection, output, representation):
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    coordinates = projection["coordinates"]
    states = projection["states"]
    y_true = projection["y_true"]
    fig, axes = plt.subplots(1, 3, figsize=(13.2, 4.5), sharex=True, sharey=True)
    scatter = None
    for index, (axis, state) in enumerate(zip(axes, STATES)):
        selected = states == state
        scatter = axis.scatter(coordinates[selected, 0], coordinates[selected, 1],
                               c=y_true[selected], cmap="viridis", s=8,
                               alpha=0.76, linewidths=0)
        title = TITLES[state]
        if state != "pre":
            title += "\nfull-test Pearson r=%.3f" % projection["full_pearson"][index]
        axis.set_title(title, fontsize=11, pad=9)
        axis.set_xticks([])
        axis.set_yticks([])
        axis.set_xlabel("t-SNE 1")
        if index == 0:
            axis.set_ylabel("t-SNE 2")
    colorbar_axis = fig.add_axes([0.92, 0.22, 0.018, 0.56])
    colorbar = fig.colorbar(scatter, cax=colorbar_axis)
    colorbar.set_label("True MRL")
    fig.suptitle("RiNALMo-micro | %s | %s split | n=%d/state | seed=%d" % (
        LABELS[representation], projection["split"], projection["n"],
        projection["seed"]), fontsize=13, y=0.99)
    fig.text(0.5, 0.015,
             "Joint fit across states | perplexity=%d | random_state=%d | post r uses full test; no classification silhouette"
             % (projection["perplexity"], projection["random_state"]),
             ha="center", fontsize=8.5, color="#4D4D4D")
    fig.subplots_adjust(left=0.06, right=0.90, bottom=0.16, top=0.80, wspace=0.18)
    fig.savefig(str(output) + ".png", bbox_inches="tight")
    fig.savefig(str(output) + ".pdf", bbox_inches="tight")
    plt.close(fig)

    coordinate_path = str(output) + "_coordinates.csv"
    with open(coordinate_path + ".tmp", "w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "representation", "split", "seed", "state", "sample_id", "y_true",
            "prediction", "residual", "tsne_1", "tsne_2", "full_test_pearson",
            "source_run_id", "perplexity", "random_state", "test_manifest_sha256"])
        for index, state in enumerate(STATES):
            for row_index in np.where(states == state)[0]:
                writer.writerow([
                    representation, projection["split"], projection["seed"], state,
                    projection["ids"][row_index], "%.10g" % y_true[row_index],
                    "%.10g" % projection["prediction"][row_index],
                    "%.10g" % projection["residual"][row_index],
                    "%.10g" % coordinates[row_index, 0],
                    "%.10g" % coordinates[row_index, 1],
                    "%.10g" % projection["full_pearson"][index],
                    projection["source_run_ids"][index], projection["perplexity"],
                    projection["random_state"], projection["manifest"]])
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(coordinate_path + ".tmp", coordinate_path)
    metadata = {
        "model": "RiNALMo-micro",
        "task": "mrl",
        "representation": representation,
        "split": projection["split"],
        "seed": projection["seed"],
        "n_per_state": projection["n"],
        "perplexity": projection["perplexity"],
        "random_state": projection["random_state"],
        "color_mode": "true_mrl_continuous",
        "classification_silhouette": None,
        "full_test_pearson": dict(zip(STATES, projection["full_pearson"].tolist())),
        "source_run_ids": dict(zip(STATES, projection["source_run_ids"].tolist())),
        "pre_prediction_head": "fresh_reference_head_seed_201_not_zero_shot",
        "test_manifest_sha256": projection["manifest"],
        "coordinate_csv": coordinate_path,
        "interpretation": "descriptive_only_no_classification_silhouette",
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
