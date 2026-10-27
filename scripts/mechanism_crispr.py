#!/usr/bin/env python3
"""复用 best-val checkpoint 的 CRISPR 不平衡二分类机制诊断。"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import sys

import numpy as np
import torch

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "scripts"))

import mechanism_ncrna as common
from mechanism_mrl import restore_post, save_npz
from rnafteval import ledger, valplateau as vp
from rnafteval.finetune_clf import batches, encode_seqs
from rnafteval.splits import (
    assert_cluster_no_overlap, assert_no_overlap, seq_hash)
from rnafteval.strategies import apply_strategy, make_head
from rnafteval.tasks import crispr as cr_task

MODEL = "RiNALMo-micro"
TASK = "crispr-off-target"
STATES = ("pre", "lora", "full")
MAX_LEN = 128
DATA_ROOT = Path(os.environ.get("RNAFT_DATA_ROOT", "/root/rna-ft-eval/data"))
ARTIFACT_ROOT = Path(os.environ.get(
    "RNAFT_MECHANISM_CRISPR_ROOT", str(common.TEAMS_ROOT / "artifacts" / "mechanism_crispr")))


def source_run_id(strategy, split, seed):
    if strategy == "lora":
        extra = "_bestval_v1"
    elif strategy == "full":
        extra = "_lr1e-05_bestval_v1"
    else:
        raise ValueError("只有 post LoRA/full 有源 checkpoint")
    return ledger.run_id(MODEL, TASK, strategy, seed, split, extra)


def int_label(value):
    if isinstance(value, (list, tuple)):
        return int(value[0])
    return int(value)


def build_evidence(parts, split):
    labels = sorted({row["label"] for side in parts.values() for row in side})
    evidence = {
        "protocol": "bestval_v1",
        "split_source": "family_validation" if split == "family" else "official_validation",
        "split": split,
        "n_train": len(parts["train"]),
        "n_val": len(parts["val"]),
        "n_test": len(parts["test"]),
        "status": "CHECKING",
    }
    sides = {side: {seq_hash(row["seq"]) for row in rows}
             for side, rows in parts.items()}
    overlaps = {"%s_%s" % (a, b): sorted(sides[a] & sides[b])
                for a, b in (("train", "val"), ("train", "test"), ("val", "test"))}
    evidence["sequence_cross_split_overlap"] = {
        pair: len(hashes) for pair, hashes in overlaps.items()}
    evidence["sequence_cross_split_examples"] = {
        pair: hashes[:20] for pair, hashes in overlaps.items()}
    evidence["deduplicated"] = all(
        len(hashes) == len(parts[side]) for side, hashes in sides.items())
    if split == "family":
        cluster_sides = {side: {str(row["cluster"]) for row in rows}
                         for side, rows in parts.items()}
        cluster_overlaps = {
            "%s_%s" % (a, b): sorted(cluster_sides[a] & cluster_sides[b])
            for a, b in (("train", "val"), ("train", "test"), ("val", "test"))}
        evidence["cluster_cross_split_overlap"] = {
            pair: len(clusters) for pair, clusters in cluster_overlaps.items()}
        evidence["cluster_cross_split_examples"] = {
            pair: clusters[:20] for pair, clusters in cluster_overlaps.items()}
    assert_no_overlap(parts["train"], parts["val"], unit="seq")
    assert_no_overlap(parts["train"], parts["test"], unit="seq")
    assert_no_overlap(parts["val"], parts["test"], unit="seq")
    if split == "family":
        assert_cluster_no_overlap(parts["train"], parts["val"])
        assert_cluster_no_overlap(parts["train"], parts["test"])
        assert_cluster_no_overlap(parts["val"], parts["test"])
    supported = {row["label"] for row in parts["train"]}
    evidence["label_support"] = {
        side: {str(label): sum(row["label"] == label for row in parts[side])
               for label in labels}
        for side in ("train", "val", "test")}
    evidence["missing_label_support"] = {
        side: sorted(row["label"] for row in parts[side]
                     if row["label"] not in supported)
        for side in ("train", "val", "test")}
    evidence["n_train"] = len(parts["train"])
    evidence["n_val"] = len(parts["val"])
    evidence["n_test"] = len(parts["test"])
    evidence["status"] = "OK"
    return evidence


def load_test_rows(split):
    if split == "family":
        import pyarrow.parquet as pq
        path = DATA_ROOT / "family_splits" / "crispr-off-target.parquet"
        if not path.is_file():
            raise FileNotFoundError(path)
        table = pq.read_table(path).to_pydict()
        label_column = table["label"] if "label" in table else table["labels"]
        records = [{"seq": seq, "label": int_label(label), "cluster": cluster}
                   for seq, label, cluster in zip(
                       table["seq"], label_column, table["cluster_id"])]
        parts = {side: [row for row, value in zip(records, table["split"])
                        if value == side]
                 for side in ("train", "val", "test")}
    elif split == "random":
        official = cr_task.load_official_split(str(
            DATA_ROOT / "beacon_raw" / "crispr-off-target" / "data"))
        parts = {"train": official["train"], "val": official["val"],
                 "test": official["test"]}
        for side in parts:
            for row in parts[side]:
                row["label"] = int(row["label"])
        seen = set()
        for side in ("train", "val", "test"):
            kept = []
            for row in parts[side]:
                if row["seq"] in seen:
                    continue
                seen.add(row["seq"])
                kept.append(row)
            parts[side] = kept
    else:
        raise ValueError(split)
    evidence = build_evidence(parts, split)
    return parts["test"], evidence


def sequence_gc(sequence):
    sequence = sequence.upper()
    return (sequence.count("G") + sequence.count("C")) / max(1, len(sequence))


def make_manifest(rows, split, seed, n_samples, positive_cap=256):
    if n_samples <= 0 or positive_cap <= 0:
        raise ValueError("n_samples 和 positive_cap 必须为正数")
    ordered = sorted(rows, key=lambda row: common.sequence_hash(row["seq"]))
    ids = [common.sequence_hash(row["seq"]) for row in ordered]
    if len(ids) != len(set(ids)):
        raise ValueError("test 中仍有重复 sequence hash")
    positives = [index for index, row in enumerate(ordered) if int(row["label"]) == 1]
    negatives = [index for index, row in enumerate(ordered) if int(row["label"]) == 0]
    target = min(n_samples, len(ordered))
    selected = positives[:positive_cap]
    selected += negatives[:max(0, target - len(selected))]
    if len(selected) < target:
        selected += positives[positive_cap:positive_cap + target - len(selected)]
    selected = sorted(selected)
    records = []
    for index in selected:
        row = ordered[index]
        records.append({
            "sample_id": common.sequence_hash(row["seq"]),
            "label": int(row["label"]),
            "cluster": row.get("cluster"),
            "cleav": row.get("cleav"),
            "length": len(row["seq"]),
            "gc": sequence_gc(row["seq"]),
        })
    full_payload = [[sample_id, int(row["label"])] for sample_id, row in zip(ids, ordered)]
    full_hash = hashlib.sha256(json.dumps(
        full_payload, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
    manifest = {
        "artifact_type": "crispr_test_manifest",
        "model": MODEL,
        "task": TASK,
        "split": split,
        "seed": seed,
        "selection": f"positive_cap_{positive_cap}_then_negative_hash_fill_before_prediction",
        "positive_cap": positive_cap,
        "visualization_enrichment": True,
        "n_full_test": len(ordered),
        "n": len(selected),
        "sample_ids": [record["sample_id"] for record in records],
        "records": records,
        "full_test_sha256": full_hash,
        "full_test_positive": len(positives),
        "full_test_negative": len(negatives),
        "sample_positive": sum(record["label"] == 1 for record in records),
        "sample_negative": sum(record["label"] == 0 for record in records),
        "metric_scope": "PR_AUC_only_on_full_test_not_enriched_sample",
    }
    payload = json.dumps(manifest, sort_keys=True, ensure_ascii=False).encode()
    manifest["manifest_sha256"] = hashlib.sha256(payload).hexdigest()
    return ordered, manifest, selected


def crispr_metrics(y_true, probabilities):
    from sklearn.metrics import average_precision_score, confusion_matrix, roc_auc_score
    y_true = np.asarray(y_true, dtype=int)
    probabilities = np.asarray(probabilities)
    positive = probabilities[:, 1]
    predicted = (positive > 0.5).astype(int)
    clipped = np.clip(probabilities, 1e-12, 1.0)
    entropy = -np.sum(clipped * np.log(clipped), axis=1)
    return {
        "pr_auc": float(average_precision_score(y_true, positive)),
        "roc_auc": float(roc_auc_score(y_true, positive)),
        "confusion_matrix": confusion_matrix(y_true, predicted, labels=[0, 1]).tolist(),
        "positive_support": int(y_true.sum()),
        "negative_support": int(len(y_true) - y_true.sum()),
        "predicted_positive": int(predicted.sum()),
        "max_class_prediction_fraction": float(max(
            np.mean(predicted == 0), np.mean(predicted == 1))),
        "prediction_entropy_median": float(np.median(entropy)),
    }


def extract(backbone, head, tokenizer, rows, device, selected_indices, batch_size=64):
    backbone.eval()
    head.eval()
    selected_set = set(selected_indices)
    full_ids, full_labels, full_logits, full_probabilities = [], [], [], []
    sample_cls, sample_head = [], []
    with torch.no_grad():
        for start in range(0, len(rows), batch_size):
            batch = rows[start:start + batch_size]
            enc = encode_seqs(tokenizer, [row["seq"] for row in batch], device, MAX_LEN)
            hidden = backbone(**enc).last_hidden_state
            pad = enc["attention_mask"] == 0
            pooled = head.pool(hidden, pad)
            logits = head.fc2(torch.nn.functional.gelu(head.fc1(pooled)))
            probabilities = torch.softmax(logits, dim=-1)
            full_ids.extend(common.sequence_hash(row["seq"]) for row in batch)
            full_labels.extend(int(row["label"]) for row in batch)
            full_logits.append(logits.detach().cpu().numpy())
            full_probabilities.append(probabilities.detach().cpu().numpy())
            keep = [index for index in range(start, start + len(batch)) if index in selected_set]
            if keep:
                local = torch.tensor([index - start for index in keep],
                                     device=hidden.device, dtype=torch.long)
                sample_cls.append(hidden[local, 0].detach().cpu().numpy())
                sample_head.append(pooled[local].detach().cpu().numpy())
    labels = np.asarray(full_labels, dtype=np.int64)
    logits = np.concatenate(full_logits).astype(np.float32)
    probabilities = np.concatenate(full_probabilities).astype(np.float32)
    if labels.shape[0] != len(rows) or logits.shape != (len(rows), 2):
        raise ValueError("完整 test 二分类形状不一致")
    if not np.isfinite(logits).all() or not np.isfinite(probabilities).all():
        raise ValueError("完整 test logits/probabilities 非有限值")
    selected = np.asarray(selected_indices, dtype=int)
    sample = {
        "sample_ids": np.asarray(full_ids)[selected],
        "labels": labels[selected],
        "logits": logits[selected],
        "probabilities": probabilities[selected],
        "cls": np.concatenate(sample_cls).astype(np.float32),
        "head_embedding": np.concatenate(sample_head).astype(np.float32),
    }
    if len(sample["sample_ids"]) != len(sample["cls"]) != len(selected_indices):
        raise ValueError("抽样 embedding 数量不一致")
    full = {
        "sample_ids": np.asarray(full_ids),
        "labels": labels,
        "logits": logits,
        "probabilities": probabilities,
    }
    return full, sample


def load_aligned_states(split, seed, suffix="_ckpt_v1"):
    ready = []
    for strategy in STATES:
        out_dir = ARTIFACT_ROOT / (
            f"mech_rinalmomicro_crispr_{strategy}_{split}_s{seed}{suffix}")
        diagnostic_path = out_dir / "diagnostic.json"
        embedding_path = out_dir / "embeddings.npz"
        if not diagnostic_path.is_file() or not embedding_path.is_file():
            continue
        diagnostic = json.loads(diagnostic_path.read_text())
        if diagnostic.get("status") != "diagnostic":
            continue
        if strategy != "pre" and (
                diagnostic.get("full_test_metric_match") is not True
                or not diagnostic.get("checkpoint", {}).get("restored_tensor_match")):
            raise ValueError("post 诊断缺少 full-test 或 checkpoint 证明: " + strategy)
        with np.load(embedding_path, allow_pickle=False) as data:
            arrays = {key: data[key] for key in data.files}
        source_reference = diagnostic["source_run_id"] or "pre_official_rinalmomicro"
        ready.append((strategy, arrays, diagnostic["test_manifest_sha256"],
                      source_reference, diagnostic["metrics_full"]))
    return ready


def aligned_crispr(states, output_path, perplexity=30, random_state=17):
    if len(states) != 3 or {item[0] for item in states} != set(STATES):
        raise ValueError("需要 pre/lora/full 三状态")
    states = sorted(states, key=lambda item: STATES.index(item[0]))
    if len({item[2] for item in states}) != 1:
        raise ValueError("三状态 test manifest 不一致")
    reference = states[0][1]
    for _strategy, arrays, _manifest, _source, _metrics in states[1:]:
        if not np.array_equal(reference["sample_ids"], arrays["sample_ids"]):
            raise ValueError("三状态 sample_id 顺序不一致")
        if not np.array_equal(reference["labels"], arrays["labels"]):
            raise ValueError("三状态二分类标签不一致")
    from sklearn.manifold import TSNE
    cls = np.concatenate([item[1]["cls"] for item in states]).astype(np.float64)
    head = np.concatenate([item[1]["head_embedding"] for item in states]).astype(np.float64)
    n = len(reference["sample_ids"])
    effective_perplexity = min(perplexity, max(1, (len(cls) - 1) // 3))
    coordinates = {}
    for name, values in (("cls", cls), ("head", head)):
        coordinates[name] = TSNE(n_components=2, random_state=random_state,
                                 perplexity=effective_perplexity).fit_transform(values)
    output_path = Path(output_path)
    if output_path.suffix != ".npz":
        output_path = output_path.with_suffix(".npz")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    save_npz(
        output_path,
        tsne_cls=coordinates["cls"], tsne_head=coordinates["head"],
        cls=cls, head_embedding=head,
        sample_ids=np.tile(reference["sample_ids"], 3),
        state=np.concatenate([np.full(n, item[0]) for item in states]),
        labels=np.tile(reference["labels"], 3),
        probabilities=np.concatenate([item[1]["probabilities"] for item in states]),
        logits=np.concatenate([item[1]["logits"] for item in states]),
        split=np.asarray(reference.get("split", "unknown")),
        seed=np.asarray(reference.get("seed", -1)),
        source_run_ids=np.asarray([item[3] for item in states]),
        full_pr_auc=np.asarray([item[4]["pr_auc"] for item in states], dtype=np.float64),
        full_roc_auc=np.asarray([item[4]["roc_auc"] for item in states], dtype=np.float64),
        test_manifest_sha256=np.asarray(states[0][2]),
        tsne_perplexity=np.asarray(effective_perplexity),
        tsne_random_state=np.asarray(random_state),
        color_mode=np.asarray("crispr_off_target_label"),
        sampling=np.asarray("positive_cap_256_then_negative_hash_fill"),
        interpretation=np.asarray("descriptive_enriched_sample_full_test_metrics_only"),
    )
    return {
        "path": str(output_path), "n_per_state": n, "n_total": len(cls),
        "perplexity": effective_perplexity, "random_state": random_state,
        "color_mode": "crispr_off_target_label",
        "classification_silhouette": None,
        "interpretation": "descriptive_enriched_sample_full_test_metrics_only",
    }


def run(args):
    if args.n_samples <= 0 or args.batch_size <= 0 or args.positive_cap <= 0:
        raise ValueError("n_samples、batch_size 和 positive_cap 必须为正数")
    if args.wait_free_gb < 0 or args.memory_poll_s <= 0:
        raise ValueError("wait_free_gb 不能为负，memory_poll_s 必须为正数")
    device = common.require_cuda(args.device)
    memory_evidence = common.wait_for_cuda_memory(
        device, args.wait_free_gb, args.memory_poll_s)
    rows, split_evidence = load_test_rows(args.split)
    ordered, manifest, selected_indices = make_manifest(
        rows, args.split, args.seed, args.n_samples, args.positive_cap)
    source_result = None
    source_dir = None
    source_row = None
    if args.strategy != "pre":
        source_rid = source_run_id(args.strategy, args.split, args.seed)
        source_row = ledger.by_run_id(source_rid)
        if source_row is None:
            raise ValueError("源格缺少 ledger 记录: " + source_rid)
        source_dir = Path(source_row["out_dir"])
        source_result = json.loads((source_dir / "result.json").read_text())
        if source_result.get("metric") != "PRAUC" or source_result.get("metric2") != "AUC":
            raise ValueError("源格不是 CRISPR PRAUC/AUC 结果")
        if source_result["n_test"] != len(ordered):
            raise ValueError("源 result n_test 与重建 test 不一致")
        if source_result.get("data_evidence") != split_evidence:
            raise ValueError("源 result 与重建 split evidence 不一致")
    out_dir = ARTIFACT_ROOT / (
        f"mech_rinalmomicro_crispr_{args.strategy}_{args.split}_s{args.seed}_ckpt_v1")
    out_dir.mkdir(parents=True, exist_ok=True)
    if (out_dir / "diagnostic.json").exists() or (out_dir / "embeddings.npz").exists():
        raise FileExistsError("拒绝覆盖已有诊断: " + str(out_dir))
    common.write_json(out_dir / "test_manifest.json", manifest)
    common.write_json(out_dir / "job.json", {
        "run_id": out_dir.name, "status": "running", "split": args.split,
        "seed": args.seed, "strategy": args.strategy, "out_dir": str(out_dir),
        "git_sha": common.git_sha(), "memory_evidence": memory_evidence,
    })
    try:
        from rnafteval.models import load_model
        spec, tokenizer, backbone = load_model(MODEL, device)
        with torch.no_grad():
            probe = encode_seqs(tokenizer, [ordered[0]["seq"]], device, MAX_LEN)
            d_model = backbone(**probe).last_hidden_state.shape[-1]
        checkpoint_evidence = None
        if args.strategy == "pre":
            backbone.eval()
            torch.manual_seed(201)
            head = make_head("per-seq", d_model, 2).to(device)
        else:
            backbone, _n_trainable = apply_strategy(backbone, args.strategy, lora_rank=8)
            head = make_head("per-seq", d_model, 2).to(device)
            checkpoint_evidence = restore_post(
                backbone, head, source_dir, source_result, source_row, device)
        head.eval()
        runtime = vp.runtime_evidence(tokenizer, device)
        full, sample = extract(backbone, head, tokenizer, ordered, device,
                               selected_indices, args.batch_size)
        metrics = crispr_metrics(full["labels"], full["probabilities"])
        metric_match = None
        if source_result is not None:
            metric_match = (
                math.isclose(metrics["pr_auc"], source_result["value"],
                             rel_tol=2e-5, abs_tol=2e-6)
                and math.isclose(metrics["roc_auc"], source_result["value2"],
                                 rel_tol=2e-5, abs_tol=2e-6))
            if not metric_match:
                raise ValueError("完整 test PR-AUC/ROC-AUC 与源 result 不一致")
        sample["split"] = np.asarray(args.split)
        sample["seed"] = np.asarray(args.seed)
        save_npz(out_dir / "predictions.npz", **full)
        save_npz(out_dir / "embeddings.npz", **sample)
        diagnostic = {
            "artifact_type": "crispr_diagnostic",
            "status": "diagnostic",
            "model": MODEL,
            "task": TASK,
            "model_repo": spec.repo,
            "strategy": args.strategy,
            "split": args.split,
            "seed": args.seed,
            "n_full_test": len(ordered),
            "n_sample": len(sample["sample_ids"]),
            "metrics_full": metrics,
            "source_run_id": None if source_result is None else source_result["run_id"],
            "source_metrics": None if source_result is None else {
                "pr_auc": source_result["value"], "roc_auc": source_result["value2"]},
            "full_test_metric_match": metric_match,
            "split_evidence": split_evidence,
            "test_manifest": str(out_dir / "test_manifest.json"),
            "test_manifest_sha256": manifest["manifest_sha256"],
            "predictions": str(out_dir / "predictions.npz"),
            "embeddings": str(out_dir / "embeddings.npz"),
            "checkpoint": checkpoint_evidence,
            "cuda": runtime,
            "git_sha": common.git_sha(),
            "prediction_head": ("fresh_reference_head_seed_201_not_zero_shot"
                                if args.strategy == "pre" else "restored_bestval_head"),
            "interpretation": "descriptive_enriched_sample_full_test_metrics_only",
        }
        ready = load_aligned_states(args.split, args.seed)
        source_reference = ("pre_official_rinalmomicro" if source_result is None
                            else source_result["run_id"])
        ready.append((args.strategy, sample, manifest["manifest_sha256"],
                      source_reference, metrics))
        diagnostic["aligned_tsne"] = None
        diagnostic["available_states"] = [item[0] for item in ready]
        if len(ready) == 3:
            aligned_path = ARTIFACT_ROOT / (
                f"mech_rinalmomicro_crispr_aligned_{args.split}_s{args.seed}_ckpt_v1.npz")
            diagnostic["aligned_tsne"] = aligned_crispr(ready, aligned_path)
        common.write_json(out_dir / "diagnostic.json", diagnostic)
        common.write_json(out_dir / "job.json", {
            "run_id": out_dir.name, "status": "diagnostic", "out_dir": str(out_dir),
            "diagnostic": str(out_dir / "diagnostic.json"), "git_sha": diagnostic["git_sha"],
            "full_test_metric_match": metric_match,
        })
        print(json.dumps({
            "run_id": out_dir.name, "status": "diagnostic",
            "n_full_test": len(ordered), "n_sample": len(sample["sample_ids"]),
            "pr_auc": metrics["pr_auc"], "roc_auc": metrics["roc_auc"],
            "sample_positive": manifest["sample_positive"],
            "sample_negative": manifest["sample_negative"],
            "full_test_metric_match": metric_match,
            "aligned": diagnostic["aligned_tsne"],
        }, indent=2), flush=True)
        return 0
    except Exception as error:
        common.write_json(out_dir / "job.json", {
            "run_id": out_dir.name, "status": "failed", "out_dir": str(out_dir),
            "error": "%s: %s" % (type(error).__name__, error),
            "git_sha": common.git_sha(),
        })
        raise


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", choices=("random", "family"), required=True)
    parser.add_argument("--strategy", choices=STATES, required=True)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--device", type=int, required=True)
    parser.add_argument("--n-samples", type=int, default=1024)
    parser.add_argument("--positive-cap", type=int, default=256)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--wait-free-gb", type=float, default=3.0)
    parser.add_argument("--memory-poll-s", type=float, default=60.0)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        return run(args)
    except Exception as error:
        print(json.dumps({"event": "CRISPR_MECHANISM_ABORT",
                          "error": "%s: %s" % (type(error).__name__, error)}), flush=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
