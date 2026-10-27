#!/usr/bin/env python3
"""绘制 SSP B20 pair 三状态联合投影并导出全部显示坐标。"""
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
from scipy.special import expit

STATES = ("pre", "lora", "full")
TITLES = {"pre": "Pre-finetuning", "lora": "Post-LoRA", "full": "Post-full finetuning"}
CLASS_NAMES = {0: "unpaired", 1: "paired"}
COLORS = {0: "#6F6F6F", 1: "#3775BA"}
TASK = "secondary-structure"
MAX_LEN = 192
PAIR_ALIGNMENT = "b20_single_base_token_positions_v1"
METRIC_SCOPE = "pooled_pair_F1_precision_recall_only_on_full_test"
PRE_SOURCE = "pre_official_rinalmomicro"
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


def _shared_scalar(data, name):
    values = np.asarray(data[name])
    if values.shape == ():
        return values.item()
    if values.shape == (3,):
        items = values.tolist()
        if any(value != items[0] for value in items[1:]):
            raise ValueError("三状态 metadata 不一致: " + name)
        return items[0]
    raise ValueError("metadata 必须为标量或三状态一致数组: " + name)


def _integer(value, name):
    if isinstance(value, (bool, np.bool_)):
        raise ValueError(name + " 必须为整数")
    try:
        converted = int(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError(name + " 必须为整数") from error
    if converted != value:
        raise ValueError(name + " 必须为整数")
    return converted


def _source_run_id(state, split, seed):
    extra = ("_pairalign_bestval_v1" if state == "lora" else
             "_lr1e-05_pairalign_bestval_v1")
    return "ft_rinalmomicro_secondarystructure_%s_s%d_%s%s" % (
        state, seed, split, extra)


def _aligned_vector(data, name, n_total):
    values = np.asarray(data[name])
    if values.ndim != 1 or len(values) != n_total:
        raise ValueError("逐 pair 数组未对齐: " + name)
    return values


def _class_support(data):
    raw = _shared_scalar(data, "full_class_support")
    try:
        support = json.loads(raw)
    except (TypeError, json.JSONDecodeError) as error:
        raise ValueError("full_class_support 必须为 JSON object") from error
    if not isinstance(support, dict) or set(support) != {"0", "1"}:
        raise ValueError("full_class_support 必须仅含 0/1 两类")
    if any(type(support[key]) is not int or support[key] < 0 for key in ("0", "1")):
        raise ValueError("full_class_support 必须为非负整数")
    return support


def load_projection(path):
    with np.load(path, allow_pickle=False) as data:
        required = {
            "tsne", "head_input", "pair_ids", "sequence_ids", "base_i", "base_j",
            "token_i", "token_j", "state", "labels", "logits", "probabilities",
            "task", "split", "seed", "max_len", "pair_alignment",
            "full_test_sha256", "test_manifest_sha256", "sampling", "metric_scope",
            "full_class_support", "source_run_ids", "full_f1", "full_precision",
            "full_recall", "full_threshold", "full_val_f1", "color_mode",
            "tsne_perplexity", "tsne_random_state",
        }
        missing = required - set(data.files)
        if missing:
            raise ValueError("aligned SSP 数据缺失: " + ",".join(sorted(missing)))
        task = str(_shared_scalar(data, "task"))
        if task != TASK:
            raise ValueError("aligned SSP task 身份不一致")
        split = str(_shared_scalar(data, "split"))
        if split not in ("random", "family"):
            raise ValueError("未知 split: %s" % split)
        seed = _integer(_shared_scalar(data, "seed"), "seed")
        max_len = _integer(_shared_scalar(data, "max_len"), "max_len")
        if max_len != MAX_LEN:
            raise ValueError("SSP max_len 必须为 192")
        if str(_shared_scalar(data, "pair_alignment")) != PAIR_ALIGNMENT:
            raise ValueError("SSP pair_alignment 身份不一致")
        if str(_shared_scalar(data, "metric_scope")) != METRIC_SCOPE:
            raise ValueError("SSP 指标只能来自 full reconstructed test")
        if str(_shared_scalar(data, "color_mode")) != "ssp_pair_gold_label":
            raise ValueError("SSP 图必须使用 pair gold label")
        sampling = str(_shared_scalar(data, "sampling"))
        if not sampling:
            raise ValueError("sampling 不能为空")
        full_test_sha256 = str(_shared_scalar(data, "full_test_sha256"))
        manifest = str(_shared_scalar(data, "test_manifest_sha256"))
        if not full_test_sha256 or not manifest:
            raise ValueError("full-test/manifest hash 不能为空")

        states = np.asarray(data["state"])
        if states.ndim != 1:
            raise ValueError("state 必须为一维数组")
        states = states.astype(str)
        counts = [int(np.sum(states == state)) for state in STATES]
        if not counts[0] or len(set(counts)) != 1:
            raise ValueError("三状态样本数必须相同且非零")
        n = counts[0]
        n_total = 3 * n
        expected_states = [state for state in STATES for _ in range(n)]
        if states.tolist() != expected_states:
            raise ValueError("投影必须按 pre/lora/full 分块排列")

        pair_ids = _aligned_vector(data, "pair_ids", n_total).astype(str)
        sequence_ids = _aligned_vector(data, "sequence_ids", n_total).astype(str)
        positions = {}
        for key in ("base_i", "base_j", "token_i", "token_j"):
            values = _aligned_vector(data, key, n_total)
            if (not np.issubdtype(values.dtype, np.integer)
                    or (values < 0).any() or (values >= max_len).any()):
                raise ValueError(key + " 必须为 [0,max_len) 内整数")
            positions[key] = values.astype(np.int64)
        if (positions["base_i"] >= positions["base_j"]).any():
            raise ValueError("pair 必须满足 base_i < base_j")
        if (positions["token_i"] >= positions["token_j"]).any():
            raise ValueError("pair 必须满足 token_i < token_j")
        labels = _aligned_vector(data, "labels", n_total)
        if (not np.issubdtype(labels.dtype, np.integer)
                or not np.isin(labels, (0, 1)).all()):
            raise ValueError("SSP pair 标签必须为 0=unpaired 或 1=paired")
        labels = labels.astype(np.int64)
        expected_ids = ["%s:%04d:%04d" % (sequence_id, base_i, base_j)
                        for sequence_id, base_i, base_j in zip(
                            sequence_ids, positions["base_i"], positions["base_j"])]
        if pair_ids.tolist() != expected_ids:
            raise ValueError("pair_id 与 sequence_id/base_i/base_j 不一致")

        alignment = {
            "pair_ids": pair_ids, "sequence_ids": sequence_ids,
            **positions, "labels": labels,
        }
        reference = states == STATES[0]
        for state in STATES[1:]:
            selected = states == state
            for key, values in alignment.items():
                if not np.array_equal(values[selected], values[reference]):
                    raise ValueError("三状态 pair 对齐不一致: " + key)

        continuous = {}
        for key in ("logits", "probabilities"):
            try:
                values = _aligned_vector(data, key, n_total).astype(np.float64)
            except (TypeError, ValueError) as error:
                raise ValueError(key + " 必须为连续数值") from error
            if not np.isfinite(values).all():
                raise ValueError(key + " 含非有限值")
            continuous[key] = values
        if not np.allclose(expit(continuous["logits"]), continuous["probabilities"],
                           rtol=1e-5, atol=1e-6):
            raise ValueError("pair probability 不是 sigmoid(logit)")

        coordinates = np.asarray(data["tsne"], dtype=np.float64)
        if coordinates.shape != (n_total, 2) or not np.isfinite(coordinates).all():
            raise ValueError("联合 coordinates 无效或含非有限值")
        embedding = np.asarray(data["head_input"], dtype=np.float64)
        if (embedding.ndim != 2 or embedding.shape[0] != n_total
                or not embedding.shape[1] or not np.isfinite(embedding).all()):
            raise ValueError("head_input 无效或含非有限值")

        metrics = {}
        for key in ("full_f1", "full_precision", "full_recall",
                    "full_threshold", "full_val_f1"):
            values = np.asarray(data[key], dtype=np.float64)
            if values.shape != (3,) or not np.isfinite(values).all():
                raise ValueError(key + " 必须为长度为3的有限数组")
            metrics[key] = values
        source_run_ids = np.asarray(data["source_run_ids"]).astype(str)
        expected_sources = [PRE_SOURCE, _source_run_id("lora", split, seed),
                            _source_run_id("full", split, seed)]
        if source_run_ids.shape != (3,) or source_run_ids.tolist() != expected_sources:
            raise ValueError("source_run_ids 与 split/seed 或 pre seed-201 身份不一致")

        full_class_support = _class_support(data)
        sample_class_support = {
            str(label): int(np.sum(labels[reference] == label)) for label in (0, 1)
        }
        if sum(full_class_support.values()) < n:
            raise ValueError("full-test pair 数不能小于 sample pair 数")
        for label in ("0", "1"):
            if full_class_support[label] < sample_class_support[label]:
                raise ValueError("full-test class support 不能小于 sample class support")
        perplexity = _integer(
            _shared_scalar(data, "tsne_perplexity"), "tsne_perplexity")
        random_state = _integer(
            _shared_scalar(data, "tsne_random_state"), "tsne_random_state")
        return {
            "coordinates": coordinates, "head_input": embedding, "states": states,
            **alignment, **continuous, **metrics,
            "n": n, "task": task, "split": split, "seed": seed, "max_len": max_len,
            "perplexity": perplexity, "random_state": random_state,
            "full_test_sha256": full_test_sha256, "manifest": manifest,
            "source_run_ids": source_run_ids, "sampling": sampling,
            "full_class_support": full_class_support,
            "sample_class_support": sample_class_support,
        }


def _support_summary(class_support):
    return {
        "pairs": int(sum(class_support.values())),
        "positive_pairs": int(class_support["1"]),
        "negative_pairs": int(class_support["0"]),
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
        for label in (0, 1):
            choose = selected & (labels == label)
            axis.scatter(coordinates[choose, 0], coordinates[choose, 1], s=8,
                         color=COLORS[label], alpha=0.72, linewidths=0,
                         label=CLASS_NAMES[label])
        title = TITLES[state]
        if state != "pre":
            title += "\nfull-test pair-F1=%.3f" % projection["full_f1"][index]
        axis.set_title(title, fontsize=11, pad=9)
        axis.set_xticks([])
        axis.set_yticks([])
        axis.set_xlabel("t-SNE 1")
        if index == 0:
            axis.set_ylabel("t-SNE 2")
    handles, legend_labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, legend_labels, loc="center left", bbox_to_anchor=(0.94, 0.5),
               fontsize=8.5, title="Pair label", title_fontsize=9)
    fig.suptitle("RiNALMo-micro | SSP pair | %s split | n=%d/state | seed=%d" % (
        projection["split"], projection["n"], projection["seed"]), fontsize=13, y=0.99)
    fig.text(
        0.5, 0.015,
        "Balanced pair view | metrics only on full reconstructed test | "
        "not CLS or sampled prevalence | no classification silhouette",
        ha="center", fontsize=8.5, color="#4D4D4D")
    fig.subplots_adjust(left=0.055, right=0.86, bottom=0.16, top=0.80, wspace=0.18)
    fig.savefig(str(output) + ".png", bbox_inches="tight", dpi=300)
    fig.savefig(str(output) + ".pdf", bbox_inches="tight")
    plt.close(fig)

    coordinate_path = str(output) + "_coordinates.csv"
    with open(coordinate_path + ".tmp", "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "representation", "task", "split", "seed", "state", "pair_id",
            "sequence_id", "base_i", "base_j", "token_i", "token_j", "label",
            "class_name", "logit", "probability", "tsne_1", "tsne_2", "full_f1",
            "full_precision", "full_recall", "full_threshold", "full_val_f1",
            "metric_scope", "max_len", "pair_alignment", "n_full_pairs",
            "n_sample_pairs", "source_run_id", "sampling", "perplexity",
            "random_state", "full_test_sha256", "test_manifest_sha256",
        ])
        for index, state in enumerate(STATES):
            for row_index in np.where(states == state)[0]:
                label = int(labels[row_index])
                writer.writerow([
                    "pair", projection["task"], projection["split"],
                    projection["seed"], state, projection["pair_ids"][row_index],
                    projection["sequence_ids"][row_index],
                    int(projection["base_i"][row_index]),
                    int(projection["base_j"][row_index]),
                    int(projection["token_i"][row_index]),
                    int(projection["token_j"][row_index]), label, CLASS_NAMES[label],
                    "%.10g" % projection["logits"][row_index],
                    "%.10g" % projection["probabilities"][row_index],
                    "%.10g" % coordinates[row_index, 0],
                    "%.10g" % coordinates[row_index, 1],
                    "%.10g" % projection["full_f1"][index],
                    "%.10g" % projection["full_precision"][index],
                    "%.10g" % projection["full_recall"][index],
                    "%.10g" % projection["full_threshold"][index],
                    "%.10g" % projection["full_val_f1"][index], METRIC_SCOPE,
                    projection["max_len"], PAIR_ALIGNMENT,
                    sum(projection["full_class_support"].values()), projection["n"],
                    projection["source_run_ids"][index], projection["sampling"],
                    projection["perplexity"], projection["random_state"],
                    projection["full_test_sha256"], projection["manifest"],
                ])
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(coordinate_path + ".tmp", coordinate_path)

    source_run_ids = dict(zip(STATES, projection["source_run_ids"].tolist()))
    metadata = {
        "model": "RiNALMo-micro",
        "task": projection["task"],
        "representation": "pair",
        "split": projection["split"],
        "seed": projection["seed"],
        "max_len": projection["max_len"],
        "pair_alignment": PAIR_ALIGNMENT,
        "n_per_state": projection["n"],
        "n_full_pairs": sum(projection["full_class_support"].values()),
        "n_sample_pairs": projection["n"],
        "full_support": _support_summary(projection["full_class_support"]),
        "sample_support": _support_summary(projection["sample_class_support"]),
        "full_class_support": projection["full_class_support"],
        "sample_class_support": projection["sample_class_support"],
        "perplexity": projection["perplexity"],
        "random_state": projection["random_state"],
        "color_mode": "ssp_pair_gold_label",
        "sampling": projection["sampling"],
        "class_balanced_visualization": True,
        "class_names": {str(label): CLASS_NAMES[label] for label in (0, 1)},
        "label_support": {
            state: {CLASS_NAMES[label]: int(np.sum(labels[states == state] == label))
                    for label in (0, 1)} for state in STATES
        },
        "metric_scope": METRIC_SCOPE,
        "source_reconciliation_metrics": [
            "f1", "precision", "recall", "threshold", "val_f1"],
        "classification_silhouette": None,
        "full_f1": dict(zip(STATES, projection["full_f1"].tolist())),
        "full_precision": dict(zip(STATES, projection["full_precision"].tolist())),
        "full_recall": dict(zip(STATES, projection["full_recall"].tolist())),
        "full_threshold": dict(zip(STATES, projection["full_threshold"].tolist())),
        "full_val_f1": dict(zip(STATES, projection["full_val_f1"].tolist())),
        "source_run_ids": source_run_ids,
        "source_proof": {
            "pre": "official_backbone_fresh_reference_pairhead_seed201:" + source_run_ids["pre"],
            "lora": "restored_bestval_checkpoint:" + source_run_ids["lora"],
            "full": "restored_bestval_checkpoint:" + source_run_ids["full"],
        },
        "pre_prediction_head": "fresh_reference_pairhead_seed_201_not_zero_shot",
        "pre_reference_head_seed": 201,
        "pre_non_zero_shot": True,
        "full_test_sha256": projection["full_test_sha256"],
        "test_manifest_sha256": projection["manifest"],
        "coordinate_csv": coordinate_path,
        "interpretation": "descriptive_balanced_pairs_full_reconstructed_test_metrics_only",
    }
    metadata_path = str(output) + "_metadata.json"
    with open(metadata_path + ".tmp", "w", encoding="utf-8") as handle:
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
