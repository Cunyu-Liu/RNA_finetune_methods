#!/usr/bin/env python3
"""复用 best-val checkpoint 的 SSP B20 pair 机制诊断，禁止 CPU 正式运行。"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import random
import sys

import numpy as np
import torch

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "scripts"))

import expansion_jobs
import mechanism_ncrna as common
from mechanism_mrl import restore_post, save_npz
from rnafteval import finetune_ssp, ledger, valplateau as vp
from rnafteval.splits import prepare_convergence_splits
from rnafteval.strategies import apply_strategy
from rnafteval.tasks import ssp as ssp_task

MODEL = "RiNALMo-micro"
TASK = "secondary-structure"
STATES = ("pre", "lora", "full")
MAX_LEN = 192
N_TRAIN = 2000
N_TEST = 400
THRESHOLDS = (0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9)
PRE_SOURCE = "pre_official_rinalmomicro"
PAIR_ALIGNMENT = "b20_single_base_token_positions_v1"
METRIC_SCOPE = "pooled_pair_F1_precision_recall_only_on_full_test"
DATA_ROOT = Path(os.environ.get("RNAFT_DATA_ROOT", "/root/rna-ft-eval/data"))
FAMILY_PARQUET = Path(os.environ.get(
    "RNAFT_SSP_FAMILY_PARQUET",
    str(DATA_ROOT / "family_splits" / "secondary-structure.parquet")))
ARTIFACT_ROOT = Path(os.environ.get(
    "RNAFT_MECHANISM_SSP_ROOT", str(common.TEAMS_ROOT / "artifacts" / "mechanism_ssp")))


def run_id(strategy, split, seed, suffix="_ckpt_v1"):
    return "mech_rinalmomicro_ssp_%s_%s_s%d%s" % (
        strategy, split, seed, suffix)


def source_run_id(strategy, split, seed):
    if strategy not in ("lora", "full"):
        raise ValueError("只有 post LoRA/full 有源 checkpoint")
    return expansion_jobs.job_for(
        TASK, MODEL, strategy, split, seed, protocol=vp.BESTVAL_PROTOCOL,
        n_train=N_TRAIN, n_test=N_TEST, max_len=MAX_LEN)["rid"]


def load_source_parts(split, seed, evidence_path=""):
    """Repeat finetune_ssp's formal bestval data path, including its test draw."""
    meta = ssp_task.load_metadata()
    if not meta:
        raise ValueError("SSP metadata 缺失: " + ssp_task.BPRNA)
    if split == "random":
        train = ssp_task.load_split("TR0", meta, max_len=MAX_LEN)
        val = ssp_task.load_split("VL0", meta, max_len=MAX_LEN)
        test = ssp_task.load_split("TS0", meta, max_len=MAX_LEN)
    elif split == "family":
        if not FAMILY_PARQUET.is_file():
            raise FileNotFoundError(FAMILY_PARQUET)
        import pyarrow.parquet as pq
        table = pq.read_table(FAMILY_PARQUET).to_pydict()
        side_of = dict(zip(table["id"], table["split"]))
        cluster_of = dict(zip(table["id"], table["cluster_id"]))
        union = []
        for split_name in ("TR0", "VL0", "TS0"):
            union += ssp_task.load_split(split_name, meta, max_len=MAX_LEN)
        seen = set()
        unique = [row for row in union
                  if not (row["id"] in seen or seen.add(row["id"]))]
        train = [dict(row, cluster=cluster_of[row["id"]]) for row in unique
                 if side_of.get(row["id"]) == "train"]
        val = [dict(row, cluster=cluster_of[row["id"]]) for row in unique
               if side_of.get(row["id"]) == "val"]
        test = [dict(row, cluster=cluster_of[row["id"]]) for row in unique
                if side_of.get(row["id"]) == "test"]
    else:
        raise ValueError(split)
    train, val, test, evidence = prepare_convergence_splits(
        train, val, test, n_train=N_TRAIN, sample_seed=seed,
        family=split == "family",
        validation_source=("official_validation" if split == "random"
                           else "family_validation"),
        evidence_path=evidence_path, protocol=vp.BESTVAL_PROTOCOL)
    test = random.Random(seed).sample(test, min(N_TEST, len(test)))
    return {"train": train, "val": val, "test": test}, evidence


def validate_source_result(result, parts, evidence, strategy, split, seed, source_rid):
    expected_identity = {
        "run_id": source_rid, "model": MODEL, "task": TASK,
        "strategy": strategy, "split": split, "seed": seed,
        "metric": "F1", "max_len": MAX_LEN,
        "pair_alignment": PAIR_ALIGNMENT,
    }
    for key, expected in expected_identity.items():
        if result.get(key) != expected:
            raise ValueError("源 result 身份不一致: %s=%r, expected %r" % (
                key, result.get(key), expected))
    for side in ("train", "val", "test"):
        key = "n_" + side
        if result.get(key) != len(parts[side]):
            raise ValueError("源 result %s 与重建数据不一致: %r vs %d" % (
                key, result.get(key), len(parts[side])))
    if result.get("data_evidence") != evidence:
        raise ValueError("源 result 与重建 data_evidence 不一致")
    return True


def _pair_id(sequence_id, base_i, base_j):
    return "%s:%04d:%04d" % (sequence_id, base_i, base_j)


def _scalar(arrays, key):
    if key not in arrays:
        raise ValueError("pair metadata 缺失: " + key)
    return arrays[key].item()


def _manifest_digest(manifest):
    payload = {key: value for key, value in manifest.items()
               if key != "manifest_sha256"}
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False,
                         separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def make_pair_manifest(rows, tokenizer, split, seed, pair_cap=512,
                       split_evidence=None, batch_size=32, max_len=MAX_LEN):
    """Tokenize before prediction and freeze full-test and sampled pair identity."""
    if isinstance(pair_cap, bool) or not isinstance(pair_cap, int) or pair_cap <= 0:
        raise ValueError("pair_cap 必须为正整数")
    if batch_size <= 0 or max_len <= 0:
        raise ValueError("batch_size 和 max_len 必须为正数")
    ordered = sorted(rows, key=lambda row: (
        common.sequence_hash(row["seq"]), str(row.get("id", ""))))
    sequence_ids = [common.sequence_hash(row["seq"]) for row in ordered]
    if len(sequence_ids) != len(set(sequence_ids)):
        raise ValueError("test 中仍有重复 sequence hash")
    selected_by_class = {0: [], 1: []}
    sequences = []
    full_hash = hashlib.sha256()
    n_full_pairs = 0
    n_full_positive = 0
    for start in range(0, len(ordered), batch_size):
        batch = ordered[start:start + batch_size]
        enc = finetune_ssp.encode_one(
            tokenizer, [row["seq"] for row in batch], "cpu", max_len)
        positions_batch = finetune_ssp.aligned_base_positions(
            tokenizer, enc, batch, max_len)
        for offset, (row, positions) in enumerate(zip(batch, positions_batch)):
            seq_index = start + offset
            sequence_id = sequence_ids[seq_index]
            positions = positions.detach().cpu()
            n_bases = len(positions)
            if n_bases < 2:
                raise ValueError("SSP 序列在 B20 对齐后不足两个 base")
            gold = set(finetune_ssp.effective_pairs(row, n_bases))
            source_id = str(row.get("id", ""))
            cluster = row.get("cluster")
            sequence_payload = {
                "sequence_id": sequence_id, "source_id": source_id,
                "base_positions": positions.tolist(), "pairs": [],
            }
            for base_i in range(n_bases - 1):
                token_i = int(positions[base_i])
                for base_j in range(base_i + 1, n_bases):
                    token_j = int(positions[base_j])
                    label = int((base_i, base_j) in gold)
                    pair_id = _pair_id(sequence_id, base_i, base_j)
                    record = {
                        "pair_id": pair_id, "seq_index": seq_index,
                        "sequence_id": sequence_id, "source_id": source_id,
                        "base_i": base_i, "base_j": base_j,
                        "token_i": token_i, "token_j": token_j,
                        "label": label, "cluster": (
                            None if cluster is None else str(cluster)),
                    }
                    if len(selected_by_class[label]) < pair_cap:
                        selected_by_class[label].append(record)
                    sequence_payload["pairs"].append([
                        base_i, base_j, token_i, token_j, label])
                    n_full_pairs += 1
                    n_full_positive += label
            full_hash.update(json.dumps(
                sequence_payload, sort_keys=True, ensure_ascii=False,
                separators=(",", ":")).encode() + b"\n")
            sequences.append({
                "seq_index": seq_index, "sequence_id": sequence_id,
                "source_id": source_id, "cluster": (
                    None if cluster is None else str(cluster)),
                "length": len(row["seq"]), "n_bases": n_bases,
                "base_token_positions": positions.tolist(),
                "n_pairs": n_bases * (n_bases - 1) // 2,
                "n_positive_pairs": len(gold),
            })
    selected = selected_by_class[0] + selected_by_class[1]
    selected.sort(key=lambda record: (
        record["seq_index"], record["base_i"], record["base_j"]))
    evidence = dict(split_evidence or {})
    evidence["test_sampling"] = {
        "method": "random.Random(seed).sample_after_prepare_convergence_splits",
        "seed": seed, "n_test": N_TEST, "rows_after": len(ordered),
    }
    manifest = {
        "artifact_type": "ssp_pair_test_manifest",
        "model": MODEL, "task": TASK, "split": split, "seed": seed,
        "max_len": max_len,
        "pair_alignment": PAIR_ALIGNMENT,
        "selection": "pair_id_lexicographic_per_class_cap_%d_before_prediction" % pair_cap,
        "pair_cap": pair_cap, "class_balanced_visualization": True,
        "n_full_sequences": len(ordered), "n_full_pairs": n_full_pairs,
        "n_full_positive_pairs": n_full_positive,
        "n_full_negative_pairs": n_full_pairs - n_full_positive,
        "n": len(selected), "pair_ids": [row["pair_id"] for row in selected],
        "records": selected, "sequences": sequences,
        "full_pair_id_schema": "sequence_id:base_i_04d:base_j_04d",
        "full_test_sha256": full_hash.hexdigest(),
        "full_test_hash_algorithm": "sha256_sorted_sequence_ndjson_v1",
        "full_class_support": {
            "0": n_full_pairs - n_full_positive, "1": n_full_positive},
        "sample_class_support": {
            str(label): len(selected_by_class[label]) for label in (0, 1)},
        "sample_support": {
            "pairs": len(selected),
            "positive_pairs": len(selected_by_class[1]),
            "negative_pairs": len(selected_by_class[0]),
        },
        "split_evidence": evidence,
        "metric_scope": METRIC_SCOPE,
    }
    manifest["manifest_sha256"] = _manifest_digest(manifest)
    return ordered, manifest, selected


def _pooled_counts(labels, probabilities, threshold):
    labels = np.asarray(labels, dtype=np.int64)
    probabilities = np.asarray(probabilities, dtype=np.float64)
    if labels.ndim != 1 or probabilities.shape != labels.shape or not len(labels):
        raise ValueError("pooled pair metric 需要非空一维对齐 labels/probabilities")
    if not np.isin(labels, (0, 1)).all() or not np.isfinite(probabilities).all():
        raise ValueError("pair labels/probabilities 非法")
    predicted = probabilities > threshold
    positive = labels == 1
    return {
        "tp": int(np.sum(predicted & positive)),
        "fp": int(np.sum(predicted & ~positive)),
        "fn": int(np.sum(~predicted & positive)),
    }


def _f1_from_counts(counts):
    tp, fp, fn = counts["tp"], counts["fp"], counts["fn"]
    precision = tp / max(1, tp + fp)
    recall = tp / max(1, tp + fn)
    return 2 * precision * recall / max(1e-9, precision + recall)


def pooled_pair_metrics(labels, probabilities, threshold):
    counts = _pooled_counts(labels, probabilities, threshold)
    tp, fp, fn = counts["tp"], counts["fp"], counts["fn"]
    precision = tp / max(1, tp + fp)
    recall = tp / max(1, tp + fn)
    return {
        "precision": round(precision, 4), "recall": round(recall, 4),
        "f1": round(_f1_from_counts(counts), 4), **counts,
    }


def select_threshold(labels, probabilities, thresholds=THRESHOLDS):
    if not thresholds:
        raise ValueError("threshold grid 不能为空")
    best_threshold = None
    best_f1 = -1.0
    for threshold in thresholds:
        counts = _pooled_counts(labels, probabilities, threshold)
        value = _f1_from_counts(counts)
        if value > best_f1:
            best_threshold = float(threshold)
            best_f1 = value
    return best_threshold, best_f1


def reconcile_source_metrics(metrics, source_result):
    checks = {
        "threshold": math.isclose(
            metrics["threshold"], source_result["threshold"], rel_tol=0, abs_tol=1e-12),
        "val_f1": math.isclose(
            metrics["val_f1"], source_result["val_f1"], rel_tol=2e-5, abs_tol=2e-6),
        "f1": math.isclose(
            metrics["f1"], source_result["value"], rel_tol=2e-5, abs_tol=2e-6),
        "precision": math.isclose(
            metrics["precision"], source_result["precision"], rel_tol=2e-5, abs_tol=2e-6),
        "recall": math.isclose(
            metrics["recall"], source_result["recall"], rel_tol=2e-5, abs_tol=2e-6),
    }
    if not all(checks.values()):
        raise ValueError("完整 source test 指标/阈值对账失败: %s" % checks)
    return checks


def pair_features(head, hidden, token_i, token_j):
    """Return the exact pw input for selected endpoints of one hidden sequence."""
    if hidden.ndim != 2:
        raise ValueError("pair_features 需要 (T, D) hidden")
    token_i = torch.as_tensor(token_i, dtype=torch.long, device=hidden.device)
    token_j = torch.as_tensor(token_j, dtype=torch.long, device=hidden.device)
    if token_i.ndim != 1 or token_i.shape != token_j.shape:
        raise ValueError("token_i/token_j 必须是一维等长位置")
    z = torch.nn.functional.gelu(head.proj(hidden))
    zi = z.index_select(0, token_i)
    zj = z.index_select(0, token_j)
    lo = torch.minimum(zi, zj)
    hi = torch.maximum(zi, zj)
    return torch.cat([lo, hi, zi * zj, hi - lo], dim=-1)


def pair_logits(head, features):
    return head.pw(finetune_ssp.feeds_core(features)).squeeze(-1)


def validate_pair_arrays(arrays, manifest=None):
    required = ("pair_ids", "sequence_ids", "base_i", "base_j",
                "token_i", "token_j", "labels", "logits", "probabilities")
    n = len(arrays["pair_ids"])
    for key in required:
        if key not in arrays or len(arrays[key]) != n:
            raise ValueError("pair 数组缺失或长度不一致: " + key)
    if "head_input" in arrays and len(arrays["head_input"]) != n:
        raise ValueError("pair head_input 数量不一致")
    if not n:
        raise ValueError("pair 数组为空")
    if np.any(arrays["base_i"] >= arrays["base_j"]):
        raise ValueError("pair 不是上三角 base_i < base_j")
    if not np.isin(arrays["labels"], (0, 1)).all():
        raise ValueError("pair labels 非二值")
    if not np.isfinite(arrays["logits"]).all() or \
            not np.isfinite(arrays["probabilities"]).all():
        raise ValueError("pair logits/probabilities 非有限值")
    expected_probability = torch.sigmoid(torch.as_tensor(arrays["logits"])).numpy()
    if not np.allclose(arrays["probabilities"], expected_probability,
                       rtol=1e-5, atol=1e-6):
        raise ValueError("pair probability 不是 sigmoid(logit)")
    if manifest is not None:
        if arrays["pair_ids"].tolist() != manifest["pair_ids"]:
            raise ValueError("pair_id 顺序与 manifest 不一致")
        by_id = {record["pair_id"]: record for record in manifest["records"]}
        for index, pair_id in enumerate(arrays["pair_ids"].tolist()):
            record = by_id[pair_id]
            for key in ("sequence_id", "base_i", "base_j", "token_i", "token_j", "label"):
                array_key = "labels" if key == "label" else key + "s" if key == "sequence_id" else key
                actual = arrays[array_key][index].item()
                if actual != record[key]:
                    raise ValueError("pair 与 manifest 不一致: %s %s" % (pair_id, key))
    return True


def extract(backbone, head, tokenizer, rows, device, selected=None,
            batch_size=8, max_len=MAX_LEN):
    """Extract every pair for metrics and only manifest pairs for visualization."""
    backbone.eval()
    head.eval()
    selected_by_sequence = {}
    if selected is not None:
        for item in selected:
            selected_by_sequence.setdefault(item["seq_index"], []).append(item)
    full = {key: [] for key in (
        "sequence_index", "base_i", "base_j", "token_i", "token_j",
        "labels", "logits", "probabilities")}
    sample = {key: [] for key in (
        "pair_ids", "sequence_ids", "base_i", "base_j", "token_i", "token_j",
        "labels", "logits", "probabilities", "head_input")}
    with torch.no_grad():
        for start in range(0, len(rows), batch_size):
            batch = rows[start:start + batch_size]
            enc = finetune_ssp.encode_one(
                tokenizer, [row["seq"] for row in batch], device, max_len)
            positions_batch = finetune_ssp.aligned_base_positions(
                tokenizer, enc, batch, max_len)
            hidden = backbone(**enc).last_hidden_state
            scores = head(hidden, enc["attention_mask"] == 0)
            for offset, (row, positions) in enumerate(zip(batch, positions_batch)):
                seq_index = start + offset
                n_bases = len(positions)
                base_i_np, base_j_np = np.triu_indices(n_bases, 1)
                base_i = torch.as_tensor(base_i_np, dtype=torch.long, device=scores.device)
                base_j = torch.as_tensor(base_j_np, dtype=torch.long, device=scores.device)
                aligned = finetune_ssp.aligned_pair_scores(scores[offset], positions)
                logits = aligned[base_i, base_j]
                probabilities = torch.sigmoid(logits)
                token_i = positions[base_i]
                token_j = positions[base_j]
                gold = set(finetune_ssp.effective_pairs(row, n_bases))
                labels_np = np.asarray([
                    int((int(i), int(j)) in gold)
                    for i, j in zip(base_i_np, base_j_np)], dtype=np.int64)
                n_pairs = len(base_i_np)
                full["sequence_index"].append(np.full(n_pairs, seq_index, dtype=np.int32))
                full["base_i"].append(base_i_np.astype(np.int32))
                full["base_j"].append(base_j_np.astype(np.int32))
                full["token_i"].append(token_i.detach().cpu().numpy().astype(np.int32))
                full["token_j"].append(token_j.detach().cpu().numpy().astype(np.int32))
                full["labels"].append(labels_np)
                full["logits"].append(logits.detach().cpu().numpy())
                full["probabilities"].append(probabilities.detach().cpu().numpy())
                chosen = selected_by_sequence.get(seq_index, [])
                if not chosen:
                    continue
                sequence_id = common.sequence_hash(row["seq"])
                chosen_i_np = np.asarray([item["base_i"] for item in chosen], dtype=np.int64)
                chosen_j_np = np.asarray([item["base_j"] for item in chosen], dtype=np.int64)
                chosen_i = torch.as_tensor(chosen_i_np, dtype=torch.long, device=scores.device)
                chosen_j = torch.as_tensor(chosen_j_np, dtype=torch.long, device=scores.device)
                chosen_token_i = positions[chosen_i]
                chosen_token_j = positions[chosen_j]
                for item, token_i_value, token_j_value in zip(
                        chosen, chosen_token_i, chosen_token_j):
                    if item["sequence_id"] != sequence_id or \
                            item["pair_id"] != _pair_id(
                                sequence_id, item["base_i"], item["base_j"]) or \
                            item["token_i"] != int(token_i_value) or \
                            item["token_j"] != int(token_j_value) or \
                            item["label"] != int((item["base_i"], item["base_j"]) in gold):
                        raise ValueError("抽样 pair 与 B20 对齐或 gold 不一致")
                features = pair_features(
                    head, hidden[offset], chosen_token_i, chosen_token_j)
                feature_logits = pair_logits(head, features)
                chosen_logits = aligned[chosen_i, chosen_j]
                if not torch.allclose(feature_logits, chosen_logits,
                                      rtol=1e-5, atol=1e-6):
                    raise ValueError("pair head-input 与 PairHead logits 不一致")
                sample["pair_ids"].extend(item["pair_id"] for item in chosen)
                sample["sequence_ids"].extend(sequence_id for _ in chosen)
                sample["base_i"].append(chosen_i_np.astype(np.int32))
                sample["base_j"].append(chosen_j_np.astype(np.int32))
                sample["token_i"].append(chosen_token_i.detach().cpu().numpy().astype(np.int32))
                sample["token_j"].append(chosen_token_j.detach().cpu().numpy().astype(np.int32))
                sample["labels"].append(np.asarray(
                    [item["label"] for item in chosen], dtype=np.int64))
                sample["logits"].append(chosen_logits.detach().cpu().numpy())
                sample["probabilities"].append(torch.sigmoid(
                    chosen_logits).detach().cpu().numpy())
                sample["head_input"].append(features.detach().cpu().numpy())
    full = {key: np.concatenate(value) for key, value in full.items()}
    full["logits"] = full["logits"].astype(np.float32)
    full["probabilities"] = full["probabilities"].astype(np.float32)
    if not len(full["labels"]) or not np.isfinite(full["logits"]).all() or \
            not np.isfinite(full["probabilities"]).all():
        raise ValueError("完整 pair 预测为空或非有限值")
    if selected is None:
        return full, None
    for key in ("base_i", "base_j", "token_i", "token_j", "labels",
                "logits", "probabilities", "head_input"):
        sample[key] = np.concatenate(sample[key])
    sample["pair_ids"] = np.asarray(sample["pair_ids"])
    sample["sequence_ids"] = np.asarray(sample["sequence_ids"])
    sample["logits"] = sample["logits"].astype(np.float32)
    sample["probabilities"] = sample["probabilities"].astype(np.float32)
    sample["head_input"] = sample["head_input"].astype(np.float32)
    if len(sample["pair_ids"]) != len(selected):
        raise ValueError("抽样 pair embedding 数量不一致")
    return full, sample


def load_aligned_states(split, seed, suffix="_ckpt_v1"):
    ready = []
    for strategy in STATES:
        out_dir = ARTIFACT_ROOT / run_id(strategy, split, seed, suffix)
        diagnostic_path = out_dir / "diagnostic.json"
        embedding_path = out_dir / "embeddings.npz"
        manifest_path = out_dir / "test_manifest.json"
        if not diagnostic_path.is_file() or not embedding_path.is_file() or \
                not manifest_path.is_file():
            continue
        diagnostic = json.loads(diagnostic_path.read_text())
        if diagnostic.get("status") != "diagnostic":
            continue
        if (diagnostic.get("strategy") != strategy
                or diagnostic.get("split") != split
                or diagnostic.get("seed") != seed):
            raise ValueError("诊断身份不一致: " + strategy)
        if strategy != "pre" and (
                diagnostic.get("full_test_metric_match") is not True
                or not diagnostic.get("checkpoint", {}).get("restored_tensor_match")
                or diagnostic.get("source_proof", {}).get("state") != "complete"):
            raise ValueError("post 诊断缺少 full-test/checkpoint/registry 证明: " + strategy)
        manifest = json.loads(manifest_path.read_text())
        if manifest.get("manifest_sha256") != _manifest_digest(manifest) or \
                diagnostic.get("test_manifest_sha256") != manifest["manifest_sha256"]:
            raise ValueError("诊断 manifest hash 不一致: " + strategy)
        with np.load(embedding_path, allow_pickle=False) as data:
            arrays = {key: data[key] for key in data.files}
        validate_pair_arrays(arrays, manifest)
        source_reference = diagnostic["source_run_id"] or PRE_SOURCE
        ready.append((strategy, arrays, manifest["manifest_sha256"],
                      source_reference, diagnostic["metrics_full"]))
    return ready


def aligned_ssp(states, output_path, perplexity=30, random_state=17):
    if len(states) != 3 or {item[0] for item in states} != set(STATES):
        raise ValueError("需要 pre/lora/full 三状态")
    states = sorted(states, key=lambda item: STATES.index(item[0]))
    if len({item[2] for item in states}) != 1:
        raise ValueError("三状态 test manifest 不一致")
    reference = states[0][1]
    metadata_keys = (
        "task", "split", "seed", "max_len", "pair_alignment",
        "full_test_sha256", "sampling", "metric_scope", "full_class_support")
    reference_metadata = {key: _scalar(reference, key) for key in metadata_keys}
    if (reference_metadata["task"] != TASK
            or reference_metadata["max_len"] != MAX_LEN
            or reference_metadata["pair_alignment"] != PAIR_ALIGNMENT
            or reference_metadata["metric_scope"] != METRIC_SCOPE):
        raise ValueError("SSP aligned 自包含 metadata 身份不一致")
    alignment_keys = ("pair_ids", "sequence_ids", "base_i", "base_j",
                      "token_i", "token_j", "labels")
    for strategy, arrays, _manifest, source, metrics in states:
        validate_pair_arrays(arrays)
        for key, value in reference_metadata.items():
            if _scalar(arrays, key) != value:
                raise ValueError("三状态 metadata 不一致: " + key)
        expected_source = PRE_SOURCE if strategy == "pre" else source_run_id(
            strategy, reference_metadata["split"], reference_metadata["seed"])
        if source != expected_source:
            raise ValueError("三状态 source RID 身份不一致: " + strategy)
        if any(not isinstance(metrics.get(key), (int, float))
               or isinstance(metrics.get(key), bool)
               or not math.isfinite(metrics[key])
               for key in ("f1", "precision", "recall", "threshold", "val_f1")):
            raise FloatingPointError("full-test pair metrics 缺失或非有限值")
    for _strategy, arrays, _manifest, _source, _metrics in states[1:]:
        for key in alignment_keys:
            if not np.array_equal(reference[key], arrays[key]):
                raise ValueError("三状态 pair 对齐不一致: " + key)
        if arrays["head_input"].shape[1] != reference["head_input"].shape[1]:
            raise ValueError("三状态 pair head-input 维度不一致")
    from sklearn.manifold import TSNE
    head_input = np.concatenate([
        item[1]["head_input"] for item in states]).astype(np.float64)
    n = len(reference["pair_ids"])
    effective_perplexity = min(perplexity, max(1, (len(head_input) - 1) // 3))
    coordinates = TSNE(n_components=2, random_state=random_state,
                       perplexity=effective_perplexity).fit_transform(head_input)
    output_path = Path(output_path)
    if output_path.suffix != ".npz":
        output_path = output_path.with_suffix(".npz")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tiled = {key: np.tile(reference[key], 3) for key in alignment_keys}
    save_npz(
        output_path, tsne=coordinates, head_input=head_input, **tiled,
        state=np.concatenate([np.full(n, item[0]) for item in states]),
        logits=np.concatenate([item[1]["logits"] for item in states]),
        probabilities=np.concatenate([item[1]["probabilities"] for item in states]),
        task=np.asarray(reference_metadata["task"]),
        split=np.asarray(reference_metadata["split"]),
        seed=np.asarray(reference_metadata["seed"], dtype=np.int64),
        max_len=np.asarray(reference_metadata["max_len"], dtype=np.int64),
        pair_alignment=np.asarray(reference_metadata["pair_alignment"]),
        full_test_sha256=np.asarray(reference_metadata["full_test_sha256"]),
        metric_scope=np.asarray(reference_metadata["metric_scope"]),
        full_class_support=np.asarray(reference_metadata["full_class_support"]),
        source_run_ids=np.asarray([item[3] for item in states]),
        full_f1=np.asarray([item[4]["f1"] for item in states], dtype=np.float64),
        full_precision=np.asarray([
            item[4]["precision"] for item in states], dtype=np.float64),
        full_recall=np.asarray([item[4]["recall"] for item in states], dtype=np.float64),
        full_threshold=np.asarray([
            item[4]["threshold"] for item in states], dtype=np.float64),
        full_val_f1=np.asarray([item[4]["val_f1"] for item in states], dtype=np.float64),
        test_manifest_sha256=np.asarray(states[0][2]),
        tsne_perplexity=np.asarray(effective_perplexity),
        tsne_random_state=np.asarray(random_state),
        color_mode=np.asarray("ssp_pair_gold_label"),
        sampling=np.asarray(reference_metadata["sampling"]),
        interpretation=np.asarray("descriptive_balanced_pairs_full_test_metrics_only"),
    )
    return {
        "path": str(output_path), "n_per_state": n, "n_total": len(head_input),
        "perplexity": effective_perplexity, "random_state": random_state,
        "color_mode": "ssp_pair_gold_label", "classification_silhouette": None,
        "interpretation": "descriptive_balanced_pairs_full_test_metrics_only",
    }


def run(args):
    if args.pair_cap <= 0 or args.batch_size <= 0:
        raise ValueError("pair_cap 和 batch_size 必须为正数")
    if args.wait_free_gb < 0 or args.memory_poll_s <= 0:
        raise ValueError("wait_free_gb 不能为负，memory_poll_s 必须为正数")
    device = common.require_cuda(args.device)
    memory_evidence = common.wait_for_cuda_memory(
        device, args.wait_free_gb, args.memory_poll_s)
    parts, evidence = load_source_parts(args.split, args.seed)
    source_result = None
    source_dir = None
    source_row = None
    source_rid = None
    source_proof = None
    if args.strategy != "pre":
        source_rid = source_run_id(args.strategy, args.split, args.seed)
        source_row = ledger.by_run_id(source_rid)
        if source_row is None:
            raise ValueError("源格缺少 ledger 记录: " + source_rid)
        source_dir = Path(source_row["out_dir"])
        source_result = json.loads((source_dir / "result.json").read_text())
        validate_source_result(source_result, parts, evidence, args.strategy,
                               args.split, args.seed, source_rid)
        source_proof = common.require_complete_source(source_rid, source_row)
    out_dir = ARTIFACT_ROOT / run_id(args.strategy, args.split, args.seed)
    out_dir.mkdir(parents=True, exist_ok=True)
    if any((out_dir / name).exists() for name in
           ("diagnostic.json", "predictions.npz", "embeddings.npz")):
        raise FileExistsError("拒绝覆盖已有诊断: " + str(out_dir))
    common.write_json(out_dir / "job.json", {
        "run_id": out_dir.name, "status": "running", "split": args.split,
        "seed": args.seed, "strategy": args.strategy, "out_dir": str(out_dir),
        "model": MODEL, "task": TASK, "max_len": MAX_LEN,
        "n_train": N_TRAIN, "n_test": N_TEST, "pair_cap": args.pair_cap,
        "threshold_grid": list(THRESHOLDS), "source_run_id": source_rid,
        "git_sha": common.git_sha(), "memory_evidence": memory_evidence,
    })
    aligned_cleanup_path = None
    try:
        from rnafteval.models import load_model
        spec, tokenizer, backbone = load_model(MODEL, device)
        ordered, manifest, selected = make_pair_manifest(
            parts["test"], tokenizer, args.split, args.seed, args.pair_cap,
            evidence, max_len=MAX_LEN)
        common.write_json(out_dir / "test_manifest.json", manifest)
        common.write_json(out_dir / "split_evidence.json", manifest["split_evidence"])
        with torch.no_grad():
            probe = finetune_ssp.encode_one(
                tokenizer, [ordered[0]["seq"]], device, MAX_LEN)
            d_model = backbone(**probe).last_hidden_state.shape[-1]
        checkpoint_evidence = None
        if args.strategy == "pre":
            backbone.eval()
            torch.manual_seed(201)
            head = finetune_ssp.PairHead(d_model).to(device)
        else:
            backbone, _n_trainable = apply_strategy(
                backbone, args.strategy, lora_rank=8)
            head = finetune_ssp.PairHead(d_model).to(device)
            checkpoint_evidence = restore_post(
                backbone, head, source_dir, source_result, source_row, device)
        head.eval()
        runtime = vp.runtime_evidence(tokenizer, device)
        val_full, _ = extract(
            backbone, head, tokenizer, parts["val"], device,
            batch_size=args.batch_size * 2, max_len=MAX_LEN)
        threshold, val_f1 = select_threshold(
            val_full["labels"], val_full["probabilities"], THRESHOLDS)
        full, sample = extract(
            backbone, head, tokenizer, ordered, device, selected,
            batch_size=args.batch_size * 2, max_len=MAX_LEN)
        if len(full["labels"]) != manifest["n_full_pairs"] or \
                int(full["labels"].sum()) != manifest["n_full_positive_pairs"] or \
                len(ordered) != manifest["n_full_sequences"]:
            raise ValueError("完整 pair 预测与 manifest support 不一致")
        validate_pair_arrays(sample, manifest)
        metrics = pooled_pair_metrics(
            full["labels"], full["probabilities"], threshold)
        metrics.update(threshold=threshold, val_f1=round(val_f1, 4))
        metric_match = None
        reconciliation = None
        if source_result is not None:
            reconciliation = reconcile_source_metrics(metrics, source_result)
            metric_match = True
        full["predictions"] = (
            full["probabilities"] > threshold).astype(np.int64)
        sample["predictions"] = (
            sample["probabilities"] > threshold).astype(np.int64)
        sample["task"] = np.asarray(TASK)
        sample["split"] = np.asarray(args.split)
        sample["seed"] = np.asarray(args.seed)
        sample["max_len"] = np.asarray(MAX_LEN)
        sample["pair_alignment"] = np.asarray(manifest["pair_alignment"])
        sample["full_test_sha256"] = np.asarray(manifest["full_test_sha256"])
        sample["sampling"] = np.asarray(manifest["selection"])
        sample["metric_scope"] = np.asarray(manifest["metric_scope"])
        sample["full_class_support"] = np.asarray(json.dumps(
            manifest["full_class_support"], sort_keys=True, separators=(",", ":")))
        save_npz(out_dir / "predictions.npz", **full)
        save_npz(out_dir / "embeddings.npz", **sample)
        diagnostic = {
            "artifact_type": "ssp_pair_diagnostic", "status": "diagnostic",
            "model": MODEL, "task": TASK, "model_repo": spec.repo,
            "strategy": args.strategy, "split": args.split, "seed": args.seed,
            "max_len": MAX_LEN, "n_train": len(parts["train"]),
            "n_val": len(parts["val"]), "n_test": len(ordered),
            "n_full_test_sequences": len(ordered),
            "n_full_test_pairs": len(full["labels"]),
            "n_full_test_positive_pairs": int(full["labels"].sum()),
            "n_sample": len(sample["pair_ids"]), "pair_cap": args.pair_cap,
            "metrics_full": metrics,
            "metric_scope": METRIC_SCOPE,
            "threshold_evidence": {
                "grid": list(THRESHOLDS), "source": "validation_only",
                "comparison": "strict_greater", "tie_rule": "keep_first",
            },
            "source_run_id": None if source_result is None else source_result["run_id"],
            "source_metrics": None if source_result is None else {
                "f1": source_result["value"],
                "precision": source_result["precision"],
                "recall": source_result["recall"],
                "threshold": source_result["threshold"],
                "val_f1": source_result["val_f1"],
            },
            "source_reconciliation": reconciliation,
            "full_test_metric_match": metric_match,
            "source_proof": source_proof,
            "split_evidence": manifest["split_evidence"],
            "source_data_evidence_present": (
                False if source_result is None else "data_evidence" in source_result),
            "test_manifest": str(out_dir / "test_manifest.json"),
            "test_manifest_sha256": manifest["manifest_sha256"],
            "full_test_sha256": manifest["full_test_sha256"],
            "predictions": str(out_dir / "predictions.npz"),
            "embeddings": str(out_dir / "embeddings.npz"),
            "checkpoint": checkpoint_evidence, "cuda": runtime,
            "git_sha": common.git_sha(),
            "pretrained_baseline": args.strategy == "pre",
            "prediction_head": (
                "fresh_reference_pairhead_seed_201_not_zero_shot"
                if args.strategy == "pre" else "restored_bestval_pairhead"),
            "reference_head_seed": 201 if args.strategy == "pre" else None,
            "prediction_metrics_reference_only": args.strategy == "pre",
            "interpretation": "descriptive_balanced_pairs_full_test_metrics_only",
        }
        ready = load_aligned_states(args.split, args.seed)
        source_reference = (PRE_SOURCE if source_result is None
                            else source_result["run_id"])
        ready.append((args.strategy, sample, manifest["manifest_sha256"],
                      source_reference, metrics))
        diagnostic["aligned_tsne"] = None
        diagnostic["available_states"] = [item[0] for item in ready]
        if len(ready) == 3:
            aligned_path = ARTIFACT_ROOT / (
                "mech_rinalmomicro_ssp_aligned_%s_s%d_ckpt_v1.npz" % (
                    args.split, args.seed))
            if aligned_path.exists():
                raise FileExistsError("拒绝覆盖已有 aligned 诊断: " + str(aligned_path))
            aligned_cleanup_path = aligned_path
            diagnostic["aligned_tsne"] = aligned_ssp(ready, aligned_path)
        common.write_json(out_dir / "diagnostic.json", diagnostic)
        common.write_json(out_dir / "job.json", {
            "run_id": out_dir.name, "status": "diagnostic", "out_dir": str(out_dir),
            "diagnostic": str(out_dir / "diagnostic.json"),
            "git_sha": diagnostic["git_sha"], "pair_cap": args.pair_cap,
            "full_test_metric_match": metric_match,
        })
        print(json.dumps({
            "run_id": out_dir.name, "status": "diagnostic",
            "n_full_test_sequences": len(ordered),
            "n_full_test_pairs": len(full["labels"]),
            "n_sample": len(sample["pair_ids"]), "metrics_full": metrics,
            "full_test_metric_match": metric_match,
            "aligned": diagnostic["aligned_tsne"],
        }, indent=2), flush=True)
        return 0
    except Exception as error:
        common.cleanup_failed_diagnostic(out_dir, aligned_cleanup_path)
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
    parser.add_argument("--pair-cap", type=int, default=512,
                        help="每类可视化 pair 上限；不影响 full-test 指标")
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--wait-free-gb", type=float, default=3.0)
    parser.add_argument("--memory-poll-s", type=float, default=60.0)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        return run(args)
    except Exception as error:
        print(json.dumps({"event": "SSP_MECHANISM_ABORT",
                          "error": "%s: %s" % (type(error).__name__, error)}), flush=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
