#!/usr/bin/env python3
"""复用 best-val checkpoint 的 SpliceAI per-base token 机制诊断。"""
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
from rnafteval.finetune_spl import batches, encode_seqs
from rnafteval.splits import (
    assert_cluster_no_overlap, assert_no_overlap, seq_hash, split_train_validation)
from rnafteval.strategies import apply_strategy, make_head
from rnafteval.tasks import spliceai as spl_task

MODEL = "RiNALMo-micro"
TASK = "spliceai"
STATES = ("pre", "lora", "full")
CLASS_NAMES = ("negative", "donor", "acceptor")
MAX_LEN = 128
DATA_ROOT = Path(os.environ.get("RNAFT_DATA_ROOT", "/root/rna-ft-eval/data"))
ARTIFACT_ROOT = Path(os.environ.get(
    "RNAFT_MECHANISM_SPLICEAI_ROOT", str(common.TEAMS_ROOT / "artifacts" / "mechanism_spliceai")))


def flat_metric(y, logits):
    from sklearn.metrics import f1_score, recall_score, roc_auc_score
    return {
        "macro_f1": float(f1_score(y, np.argmax(logits, axis=-1), average="macro")),
        "roc_auc": float(roc_auc_score(y, torch.softmax(
            torch.as_tensor(logits), dim=-1).numpy(), multi_class="ovr", average="macro")),
        "recalls": recall_score(y, np.argmax(logits, axis=-1), average=None).tolist(),
    }


def source_run_id(strategy, split, seed):
    if strategy == "lora":
        extra = "_b20fix_bestval_v1"
    elif strategy == "full":
        extra = "_b20fix_lr1e-05_bestval_v1"
    else:
        raise ValueError("只有 post LoRA/full 有源 checkpoint")
    return ledger.run_id(MODEL, TASK, strategy, seed, split, extra)


def build_split_evidence(parts, split):
    evidence = {
        "protocol": "bestval_v1",
        "validation_source": "train_holdout",
        "split": split,
        "n_train": len(parts["train"]),
        "n_val": len(parts["val"]),
        "n_test": len(parts["test"]),
        "source_data_evidence_present": False,
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
    evidence["label_support"] = {
        side: {str(label): int(sum(
            np.sum(np.asarray(row["labels"]) == label) for row in parts[side]))
            for label in range(3)}
        for side in ("train", "val", "test")}
    evidence["n_train"] = len(parts["train"])
    evidence["n_val"] = len(parts["val"])
    evidence["n_test"] = len(parts["test"])
    evidence["status"] = "OK"
    return evidence


def load_task_parts(split):
    if split == "family":
        train, test = spl_task.load_family_splits(str(DATA_ROOT / "family_splits"))
        train, val = split_train_validation(train)
    elif split == "random":
        train, val, test = spl_task.load_all(str(DATA_ROOT / "spliceai"))
        train, val = split_train_validation(train)
    else:
        raise ValueError(split)
    return {"train": train, "val": val, "test": test}


def sequence_gc(sequence):
    sequence = sequence.upper()
    return (sequence.count("G") + sequence.count("C")) / max(1, len(sequence))


def make_token_manifest(rows, split, seed, per_class_cap=512):
    if per_class_cap <= 0:
        raise ValueError("per_class_cap 必须为正数")
    ordered = sorted(rows, key=lambda row: common.sequence_hash(row["seq"]))
    candidates = {label: [] for label in range(3)}
    full_support = {label: 0 for label in range(3)}
    full_payload = []
    total_tokens = 0
    for seq_index, row in enumerate(ordered):
        sequence_id = common.sequence_hash(row["seq"])
        labels = np.asarray(row["labels"], dtype=np.int64)
        if len(labels) != len(row["seq"]):
            raise ValueError("SpliceAI labels 与序列长度不一致")
        full_payload.append([sequence_id, labels.tolist()])
        for position, label in enumerate(labels):
            if label < 0:
                continue
            record = {
                "seq_index": seq_index,
                "sequence_id": sequence_id,
                "position": int(position),
                "token_id": f"{sequence_id}:{position:04d}",
                "label": int(label),
            }
            candidates[int(label)].append(record)
            full_support[int(label)] += 1
            total_tokens += 1
    selected = []
    for label in range(3):
        candidates[label].sort(key=lambda record: record["token_id"])
        selected.extend(candidates[label][:per_class_cap])
    selected.sort(key=lambda record: (record["seq_index"], record["position"]))
    records = []
    for item in selected:
        row = ordered[item["seq_index"]]
        records.append({
            "token_id": item["token_id"],
            "sequence_id": item["sequence_id"],
            "position": item["position"],
            "label": item["label"],
            "cluster": row.get("cluster"),
            "length": len(row["seq"]),
            "gc": sequence_gc(row["seq"]),
        })
    full_hash = hashlib.sha256(json.dumps(
        full_payload, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
    manifest = {
        "artifact_type": "spliceai_token_test_manifest",
        "model": MODEL,
        "task": TASK,
        "split": split,
        "seed": seed,
        "selection": f"token_id_lexicographic_per_class_cap_{per_class_cap}_before_prediction",
        "per_class_cap": per_class_cap,
        "class_balanced_visualization": True,
        "n_full_sequences": len(ordered),
        "n_full_tokens": total_tokens,
        "n": len(selected),
        "token_ids": [record["token_id"] for record in records],
        "records": records,
        "full_test_sha256": full_hash,
        "full_class_support": {str(key): value for key, value in full_support.items()},
        "sample_class_support": {str(label): sum(
            record["label"] == label for record in records) for label in range(3)},
        "class_names": list(CLASS_NAMES),
        "metric_scope": "macro_F1_and_ROC_AUC_only_on_full_test",
    }
    payload = json.dumps(manifest, sort_keys=True, ensure_ascii=False).encode()
    manifest["manifest_sha256"] = hashlib.sha256(payload).hexdigest()
    return ordered, manifest, selected


def extract(backbone, head, tokenizer, rows, device, selected, batch_size=16):
    backbone.eval()
    head.eval()
    selected_by_sequence = {}
    for item in selected:
        selected_by_sequence.setdefault(item["seq_index"], []).append(item)
    full_token_ids, full_sequence_ids, full_positions = [], [], []
    full_labels, full_logits, full_probabilities = [], [], []
    sample_embeddings, sample_logits, sample_probabilities = [], [], []
    sample_token_ids = []
    with torch.no_grad():
        for start in range(0, len(rows), batch_size):
            batch = rows[start:start + batch_size]
            enc = encode_seqs(tokenizer, [row["seq"] for row in batch], device, MAX_LEN)
            hidden = backbone(**enc).last_hidden_state
            pad = enc["attention_mask"] == 0
            logits = head(hidden, pad)
            probabilities = torch.softmax(logits, dim=-1)
            for offset, row in enumerate(batch):
                seq_index = start + offset
                sequence_id = common.sequence_hash(row["seq"])
                labels = np.asarray(row["labels"], dtype=np.int64)
                positions = np.where(labels >= 0)[0]
                if len(positions) == 0:
                    continue
                full_token_ids.extend(f"{sequence_id}:{position:04d}" for position in positions)
                full_sequence_ids.extend([sequence_id] * len(positions))
                full_positions.extend(int(position) for position in positions)
                full_labels.extend(int(labels[position]) for position in positions)
                full_logits.append(logits[offset, positions].detach().cpu().numpy())
                full_probabilities.append(probabilities[offset, positions].detach().cpu().numpy())
                chosen = selected_by_sequence.get(seq_index, [])
                if chosen:
                    chosen_positions = torch.tensor(
                        [item["position"] for item in chosen], device=hidden.device)
                    sample_embeddings.append(hidden[offset, chosen_positions].detach().cpu().numpy())
                    sample_logits.append(logits[offset, chosen_positions].detach().cpu().numpy())
                    sample_probabilities.append(probabilities[offset, chosen_positions].detach().cpu().numpy())
                    sample_token_ids.extend(item["token_id"] for item in chosen)
    full = {
        "token_ids": np.asarray(full_token_ids),
        "sequence_ids": np.asarray(full_sequence_ids),
        "positions": np.asarray(full_positions, dtype=np.int64),
        "labels": np.asarray(full_labels, dtype=np.int64),
        "logits": np.concatenate(full_logits).astype(np.float32),
        "probabilities": np.concatenate(full_probabilities).astype(np.float32),
    }
    sample = {
        "token_ids": np.asarray(sample_token_ids),
        "sequence_ids": np.asarray([item["sequence_id"] for item in selected]),
        "positions": np.asarray([item["position"] for item in selected], dtype=np.int64),
        "labels": np.asarray([item["label"] for item in selected], dtype=np.int64),
        "logits": np.concatenate(sample_logits).astype(np.float32),
        "probabilities": np.concatenate(sample_probabilities).astype(np.float32),
        "token_embedding": np.concatenate(sample_embeddings).astype(np.float32),
    }
    if len(sample["token_ids"]) != len(selected) or \
            sample["token_embedding"].shape[0] != len(selected):
        raise ValueError("抽样 token embedding 数量不一致")
    if full["logits"].shape != (len(full["labels"]), 3):
        raise ValueError("完整 test token logits 形状不一致")
    if not np.isfinite(full["logits"]).all() or not np.isfinite(full["probabilities"]).all():
        raise ValueError("完整 test logits/probabilities 非有限值")
    return full, sample


def load_aligned_states(split, seed, suffix="_ckpt_v1"):
    ready = []
    for strategy in STATES:
        out_dir = ARTIFACT_ROOT / (
            f"mech_rinalmomicro_spliceai_{strategy}_{split}_s{seed}{suffix}")
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


def aligned_spliceai(states, output_path, perplexity=30, random_state=17):
    if len(states) != 3 or {item[0] for item in states} != set(STATES):
        raise ValueError("需要 pre/lora/full 三状态")
    states = sorted(states, key=lambda item: STATES.index(item[0]))
    if len({item[2] for item in states}) != 1:
        raise ValueError("三状态 test manifest 不一致")
    reference = states[0][1]
    for _strategy, arrays, _manifest, _source, _metrics in states[1:]:
        if not np.array_equal(reference["token_ids"], arrays["token_ids"]):
            raise ValueError("三状态 token_id 顺序不一致")
        if not np.array_equal(reference["labels"], arrays["labels"]):
            raise ValueError("三状态 token 标签不一致")
    from sklearn.manifold import TSNE
    token = np.concatenate([item[1]["token_embedding"] for item in states]).astype(np.float64)
    n = len(reference["token_ids"])
    effective_perplexity = min(perplexity, max(1, (len(token) - 1) // 3))
    coordinates = TSNE(n_components=2, random_state=random_state,
                       perplexity=effective_perplexity).fit_transform(token)
    output_path = Path(output_path)
    if output_path.suffix != ".npz":
        output_path = output_path.with_suffix(".npz")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    save_npz(
        output_path,
        tsne=coordinates,
        token_embedding=token,
        token_ids=np.tile(reference["token_ids"], 3),
        sequence_ids=np.tile(reference["sequence_ids"], 3),
        positions=np.tile(reference["positions"], 3),
        state=np.concatenate([np.full(n, item[0]) for item in states]),
        labels=np.tile(reference["labels"], 3),
        probabilities=np.concatenate([item[1]["probabilities"] for item in states]),
        logits=np.concatenate([item[1]["logits"] for item in states]),
        split=np.asarray(reference.get("split", "unknown")),
        seed=np.asarray(reference.get("seed", -1)),
        source_run_ids=np.asarray([item[3] for item in states]),
        full_macro_f1=np.asarray([item[4]["macro_f1"] for item in states], dtype=np.float64),
        full_roc_auc=np.asarray([item[4]["roc_auc"] for item in states], dtype=np.float64),
        test_manifest_sha256=np.asarray(states[0][2]),
        tsne_perplexity=np.asarray(effective_perplexity),
        tsne_random_state=np.asarray(random_state),
        color_mode=np.asarray("spliceai_token_class"),
        sampling=np.asarray("per_class_cap_512_before_prediction"),
        interpretation=np.asarray("descriptive_balanced_tokens_full_test_metrics_only"),
    )
    return {
        "path": str(output_path), "n_per_state": n, "n_total": len(token),
        "perplexity": effective_perplexity, "random_state": random_state,
        "color_mode": "spliceai_token_class",
        "classification_silhouette": None,
        "interpretation": "descriptive_balanced_tokens_full_test_metrics_only",
    }


def run(args):
    if args.per_class_cap <= 0 or args.batch_size <= 0:
        raise ValueError("per_class_cap 和 batch_size 必须为正数")
    if args.wait_free_gb < 0 or args.memory_poll_s <= 0:
        raise ValueError("wait_free_gb 不能为负，memory_poll_s 必须为正数")
    device = common.require_cuda(args.device)
    memory_evidence = common.wait_for_cuda_memory(
        device, args.wait_free_gb, args.memory_poll_s)
    parts = load_task_parts(args.split)
    split_evidence = build_split_evidence(parts, args.split)
    ordered, manifest, selected = make_token_manifest(
        parts["test"], args.split, args.seed, args.per_class_cap)
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
        if source_result.get("metric") != "MACRO_F1" or source_result.get("metric2") != "AUC":
            raise ValueError("源格不是 SpliceAI macro-F1/AUC 结果")
        if source_result["n_test"] != len(ordered):
            raise ValueError("源 result n_test 与重建 test 不一致")
    out_dir = ARTIFACT_ROOT / (
        f"mech_rinalmomicro_spliceai_{args.strategy}_{args.split}_s{args.seed}_ckpt_v1")
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
            head = make_head("per-base", d_model, 3).to(device)
        else:
            backbone, _n_trainable = apply_strategy(backbone, args.strategy, lora_rank=8)
            head = make_head("per-base", d_model, 3).to(device)
            checkpoint_evidence = restore_post(
                backbone, head, source_dir, source_result, source_row, device)
        head.eval()
        runtime = vp.runtime_evidence(tokenizer, device)
        full, sample = extract(backbone, head, tokenizer, ordered, device,
                               selected, args.batch_size)
        metrics = flat_metric(full["labels"], full["logits"])
        metric_match = None
        if source_result is not None:
            metric_match = (
                math.isclose(metrics["macro_f1"], source_result["value"],
                             rel_tol=2e-5, abs_tol=2e-6)
                and math.isclose(metrics["roc_auc"], source_result["value2"],
                                 rel_tol=2e-5, abs_tol=2e-6))
            if not metric_match:
                raise ValueError("完整 test macro-F1/ROC-AUC 与源 result 不一致")
        sample["split"] = np.asarray(args.split)
        sample["seed"] = np.asarray(args.seed)
        save_npz(out_dir / "predictions.npz", **full)
        save_npz(out_dir / "embeddings.npz", **sample)
        diagnostic = {
            "artifact_type": "spliceai_diagnostic",
            "status": "diagnostic",
            "model": MODEL,
            "task": TASK,
            "model_repo": spec.repo,
            "strategy": args.strategy,
            "split": args.split,
            "seed": args.seed,
            "n_full_test_sequences": len(ordered),
            "n_full_test_tokens": len(full["labels"]),
            "n_sample": len(sample["token_ids"]),
            "metrics_full": metrics,
            "source_run_id": None if source_result is None else source_result["run_id"],
            "source_metrics": None if source_result is None else {
                "macro_f1": source_result["value"], "roc_auc": source_result["value2"]},
            "full_test_metric_match": metric_match,
            "split_evidence": split_evidence,
            "source_data_evidence_present": False if source_result is None else (
                "data_evidence" in source_result),
            "test_manifest": str(out_dir / "test_manifest.json"),
            "test_manifest_sha256": manifest["manifest_sha256"],
            "predictions": str(out_dir / "predictions.npz"),
            "embeddings": str(out_dir / "embeddings.npz"),
            "checkpoint": checkpoint_evidence,
            "cuda": runtime,
            "git_sha": common.git_sha(),
            "prediction_head": ("fresh_reference_head_seed_201_not_zero_shot"
                                if args.strategy == "pre" else "restored_bestval_head"),
            "interpretation": "descriptive_balanced_tokens_full_test_metrics_only",
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
                f"mech_rinalmomicro_spliceai_aligned_{args.split}_s{args.seed}_ckpt_v1.npz")
            diagnostic["aligned_tsne"] = aligned_spliceai(ready, aligned_path)
        common.write_json(out_dir / "diagnostic.json", diagnostic)
        common.write_json(out_dir / "job.json", {
            "run_id": out_dir.name, "status": "diagnostic", "out_dir": str(out_dir),
            "diagnostic": str(out_dir / "diagnostic.json"), "git_sha": diagnostic["git_sha"],
            "full_test_metric_match": metric_match,
        })
        print(json.dumps({
            "run_id": out_dir.name, "status": "diagnostic",
            "n_full_test_sequences": len(ordered),
            "n_full_test_tokens": len(full["labels"]),
            "n_sample": len(sample["token_ids"]),
            "macro_f1": metrics["macro_f1"], "roc_auc": metrics["roc_auc"],
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
    parser.add_argument("--per-class-cap", type=int, default=512)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--wait-free-gb", type=float, default=3.0)
    parser.add_argument("--memory-poll-s", type=float, default=60.0)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        return run(args)
    except Exception as error:
        print(json.dumps({"event": "SPLICEAI_MECHANISM_ABORT",
                          "error": "%s: %s" % (type(error).__name__, error)}), flush=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
