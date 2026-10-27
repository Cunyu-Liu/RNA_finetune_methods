#!/usr/bin/env python3
"""绘制 degradation/SSI per-base regression 三状态联合投影。"""
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
TARGETS = {"degradation": "deg_Mg_pH10", "ssi": "struct_true"}
PRE_SOURCE = "pre_official_rinalmomicro_reference_head_seed201"
METRIC_SCOPE = "full_test_only_not_CLS_or_sampled_tokens"
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


def _source_run_id(task, state, split, seed):
    extra = ("_b20fix_bestval_v1" if state == "lora" else
             "_b20fix_lr1e-05_bestval_v1")
    return "ft_rinalmomicro_%s_%s_s%d_%s%s" % (
        task, state, seed, split, extra)


def _aligned_vector(data, name, n_total):
    values = np.asarray(data[name])
    if values.ndim != 1 or len(values) != n_total:
        raise ValueError("逐 token 数组未对齐: " + name)
    return values


def load_projection(path, task=None):
    if task is not None and task not in TARGETS:
        raise ValueError("未知 per-base regression task: %s" % task)
    with np.load(path, allow_pickle=False) as data:
        required = {
            "tsne", "token_embedding", "token_ids", "sequence_ids",
            "base_positions", "token_positions", "state", "y_true",
            "prediction", "residual", "full_pcc", "full_mcrmse",
            "source_run_ids", "color_mode", "task", "split", "seed",
            "n_full_tokens", "n_sample_tokens", "full_test_sha256",
            "test_manifest_sha256", "tsne_perplexity", "tsne_random_state",
        }
        missing = required - set(data.files)
        if missing:
            raise ValueError("aligned regbase 数据缺失: " + ",".join(sorted(missing)))
        aligned_task = str(_shared_scalar(data, "task"))
        if aligned_task not in TARGETS:
            raise ValueError("未知 per-base regression task: %s" % aligned_task)
        if task is not None and aligned_task != task:
            raise ValueError("请求 task 与 aligned 数据不一致")
        split = str(_shared_scalar(data, "split"))
        if split not in ("random", "family"):
            raise ValueError("未知 split: %s" % split)
        seed = _integer(_shared_scalar(data, "seed"), "seed")
        if str(_shared_scalar(data, "color_mode")) != "y_true_continuous":
            raise ValueError("regbase 图必须使用 continuous unbinned y_true 标签")

        states = _aligned_vector(data, "state", len(np.asarray(data["state"]))).astype(str)
        counts = [int(np.sum(states == state)) for state in STATES]
        if not counts[0] or len(set(counts)) != 1:
            raise ValueError("三状态样本数必须相同且非零")
        n = counts[0]
        n_total = 3 * n
        expected_states = [state for state in STATES for _ in range(n)]
        if states.tolist() != expected_states:
            raise ValueError("投影必须按 pre/lora/full 分块排列")

        token_ids = _aligned_vector(data, "token_ids", n_total).astype(str)
        sequence_ids = _aligned_vector(data, "sequence_ids", n_total).astype(str)
        positions = {}
        for key in ("base_positions", "token_positions"):
            values = _aligned_vector(data, key, n_total)
            if (not np.issubdtype(values.dtype, np.integer)
                    or (values < 0).any()):
                raise ValueError(key + " 必须为非负整数")
            positions[key] = values.astype(np.int64)
        continuous = {}
        for key in ("y_true", "prediction", "residual"):
            try:
                values = _aligned_vector(data, key, n_total).astype(np.float64)
            except (TypeError, ValueError) as error:
                raise ValueError(key + " 必须为连续数值") from error
            if not np.isfinite(values).all():
                raise ValueError(key + " 含非有限值")
            continuous[key] = values
        y_true = continuous["y_true"]
        prediction = continuous["prediction"]
        residual = continuous["residual"]
        if not np.allclose(residual, prediction - y_true, rtol=0, atol=1e-6):
            raise ValueError("residual 与 prediction-y_true 不一致")

        expected_ids = ["%s:%04d" % (sequence_id, base) for sequence_id, base in zip(
            sequence_ids, positions["base_positions"])]
        if token_ids.tolist() != expected_ids:
            raise ValueError("token_id 与 sequence_id/base_position 不一致")
        alignment = {
            "token_ids": token_ids,
            "sequence_ids": sequence_ids,
            **positions,
            "y_true": y_true,
        }
        reference = states == STATES[0]
        for state in STATES[1:]:
            selected = states == state
            for key, values in alignment.items():
                if not np.array_equal(values[selected], values[reference]):
                    raise ValueError("三状态对齐不一致: " + key)

        coordinates = np.asarray(data["tsne"], dtype=np.float64)
        if coordinates.shape != (n_total, 2) or not np.isfinite(coordinates).all():
            raise ValueError("联合 coordinates 无效或含非有限值")
        embedding = np.asarray(data["token_embedding"], dtype=np.float64)
        if (embedding.ndim != 2 or embedding.shape[0] != n_total
                or not embedding.shape[1] or not np.isfinite(embedding).all()):
            raise ValueError("token_embedding 无效或含非有限值")

        metrics = {}
        for key in ("full_pcc", "full_mcrmse"):
            values = np.asarray(data[key], dtype=np.float64)
            if values.shape != (3,) or not np.isfinite(values).all():
                raise ValueError(key + " 必须为长度为3的有限数组")
            metrics[key] = values
        source_run_ids = np.asarray(data["source_run_ids"]).astype(str)
        expected_sources = [
            PRE_SOURCE,
            _source_run_id(aligned_task, "lora", split, seed),
            _source_run_id(aligned_task, "full", split, seed),
        ]
        if source_run_ids.shape != (3,) or source_run_ids.tolist() != expected_sources:
            raise ValueError("source_run_ids 与 task/split/seed 或 pre seed-201 身份不一致")

        n_full_tokens = _integer(
            _shared_scalar(data, "n_full_tokens"), "n_full_tokens")
        n_sample_tokens = _integer(
            _shared_scalar(data, "n_sample_tokens"), "n_sample_tokens")
        if n_sample_tokens != n:
            raise ValueError("n_sample_tokens 与每状态坐标数不一致")
        if n_full_tokens < n_sample_tokens:
            raise ValueError("full-test token 数不能小于 sample token 数")
        full_test_sha256 = str(_shared_scalar(data, "full_test_sha256"))
        manifest = str(_shared_scalar(data, "test_manifest_sha256"))
        if not full_test_sha256 or not manifest:
            raise ValueError("full-test/manifest hash 不能为空")
        perplexity = _integer(
            _shared_scalar(data, "tsne_perplexity"), "tsne_perplexity")
        random_state = _integer(
            _shared_scalar(data, "tsne_random_state"), "tsne_random_state")
        return {
            "coordinates": coordinates,
            "token_embedding": embedding,
            "states": states,
            **alignment,
            "prediction": prediction,
            "residual": residual,
            "n": n,
            "task": aligned_task,
            "target": TARGETS[aligned_task],
            "split": split,
            "seed": seed,
            "n_full_tokens": n_full_tokens,
            "n_sample_tokens": n_sample_tokens,
            "perplexity": perplexity,
            "random_state": random_state,
            "full_test_sha256": full_test_sha256,
            "manifest": manifest,
            **metrics,
            "source_run_ids": source_run_ids,
            "metric_scope": METRIC_SCOPE,
        }


def plot_projection(projection, output):
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    coordinates = projection["coordinates"]
    states = projection["states"]
    y_true = projection["y_true"]
    color_limits = (float(np.min(y_true)), float(np.max(y_true)))
    norm = matplotlib.colors.Normalize(*color_limits)
    fig, axes = plt.subplots(1, 3, figsize=(13.2, 4.5), sharex=True, sharey=True)
    scatter = None
    for index, (axis, state) in enumerate(zip(axes, STATES)):
        selected = states == state
        scatter = axis.scatter(
            coordinates[selected, 0], coordinates[selected, 1],
            c=y_true[selected], cmap="viridis", norm=norm, s=8,
            alpha=0.76, linewidths=0)
        title = TITLES[state]
        if state != "pre":
            title += "\nfull-test PCC=%.3f | MCRMSE=%.3f" % (
                projection["full_pcc"][index], projection["full_mcrmse"][index])
        axis.set_title(title, fontsize=11, pad=9)
        axis.set_xticks([])
        axis.set_yticks([])
        axis.set_xlabel("t-SNE 1")
        if index == 0:
            axis.set_ylabel("t-SNE 2")
    colorbar_axis = fig.add_axes([0.92, 0.22, 0.018, 0.56])
    colorbar = fig.colorbar(scatter, cax=colorbar_axis)
    colorbar.set_label(projection["target"])
    fig.suptitle(
        "RiNALMo-micro | %s per-base token | %s split | n=%d/state | seed=%d" % (
            projection["task"], projection["split"], projection["n"],
            projection["seed"]), fontsize=13, y=0.99)
    fig.text(
        0.5, 0.015,
        "Joint fit across states | perplexity=%d | random_state=%d | "
        "metrics only on full test; not CLS or sampled tokens | no classification silhouette" % (
            projection["perplexity"], projection["random_state"]),
        ha="center", fontsize=8.5, color="#4D4D4D")
    fig.subplots_adjust(left=0.06, right=0.90, bottom=0.16, top=0.80, wspace=0.18)
    fig.savefig(str(output) + ".png", bbox_inches="tight", dpi=300)
    fig.savefig(str(output) + ".pdf", bbox_inches="tight")
    plt.close(fig)

    coordinate_path = str(output) + "_coordinates.csv"
    with open(coordinate_path + ".tmp", "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "representation", "task", "target", "split", "seed", "state",
            "token_id", "sequence_id", "base_position", "token_position",
            "y_true", "prediction", "residual", "tsne_1", "tsne_2",
            "full_pcc", "full_mcrmse", "metric_scope", "n_full_tokens",
            "n_sample_tokens", "source_run_id", "perplexity", "random_state",
            "full_test_sha256", "test_manifest_sha256",
        ])
        for index, state in enumerate(STATES):
            for row_index in np.where(states == state)[0]:
                writer.writerow([
                    "per_base_token", projection["task"], projection["target"],
                    projection["split"], projection["seed"], state,
                    projection["token_ids"][row_index],
                    projection["sequence_ids"][row_index],
                    int(projection["base_positions"][row_index]),
                    int(projection["token_positions"][row_index]),
                    "%.10g" % y_true[row_index],
                    "%.10g" % projection["prediction"][row_index],
                    "%.10g" % projection["residual"][row_index],
                    "%.10g" % coordinates[row_index, 0],
                    "%.10g" % coordinates[row_index, 1],
                    "%.10g" % projection["full_pcc"][index],
                    "%.10g" % projection["full_mcrmse"][index],
                    METRIC_SCOPE, projection["n_full_tokens"],
                    projection["n_sample_tokens"],
                    projection["source_run_ids"][index], projection["perplexity"],
                    projection["random_state"], projection["full_test_sha256"],
                    projection["manifest"],
                ])
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(coordinate_path + ".tmp", coordinate_path)

    source_run_ids = dict(zip(STATES, projection["source_run_ids"].tolist()))
    metadata = {
        "model": "RiNALMo-micro",
        "task": projection["task"],
        "representation": "per_base_token",
        "target": projection["target"],
        "split": projection["split"],
        "seed": projection["seed"],
        "n_per_state": projection["n"],
        "n_full_tokens": projection["n_full_tokens"],
        "n_sample_tokens": projection["n_sample_tokens"],
        "perplexity": projection["perplexity"],
        "random_state": projection["random_state"],
        "label_scope": "sampled_valid_per_base_tokens_only_not_CLS",
        "metric_scope": METRIC_SCOPE,
        "color_mode": "y_true_continuous",
        "continuous_unbinned": True,
        "colorbar_label": projection["target"],
        "color_limits": list(color_limits),
        "classification_silhouette": None,
        "full_pcc": dict(zip(STATES, projection["full_pcc"].tolist())),
        "full_mcrmse": dict(zip(STATES, projection["full_mcrmse"].tolist())),
        "source_run_ids": source_run_ids,
        "source_proof": {
            "pre": "official_backbone_fresh_reference_head_seed201:" + source_run_ids["pre"],
            "lora": "restored_bestval_checkpoint:" + source_run_ids["lora"],
            "full": "restored_bestval_checkpoint:" + source_run_ids["full"],
        },
        "pre_prediction_head": "fresh_reference_head_seed_201_not_zero_shot",
        "pre_reference_head_seed": 201,
        "full_test_sha256": projection["full_test_sha256"],
        "test_manifest_sha256": projection["manifest"],
        "coordinate_csv": coordinate_path,
        "interpretation": "descriptive_only_continuous_unbinned_no_classification_silhouette",
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
    parser.add_argument("--task", choices=tuple(TARGETS))
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    projection = load_projection(args.aligned_npz, task=args.task)
    metadata = plot_projection(projection, args.output)
    print(json.dumps(metadata, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
