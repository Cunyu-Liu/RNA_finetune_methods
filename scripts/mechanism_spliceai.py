#!/usr/bin/env python3
"""复用 best-val checkpoint 的 SpliceAI per-base token 机制诊断。"""
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
import pyarrow.parquet as pq
import torch

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "scripts"))

import mechanism_ncrna as common
from mechanism_mrl import restore_post, save_npz
from rnafteval import ledger, valplateau as vp
from rnafteval.base_alignment import align_base_labels
from rnafteval.finetune_spl import encode_seqs
from rnafteval.splits import (
    assert_cluster_no_overlap, assert_no_overlap, seq_hash, split_train_validation)
from rnafteval.strategies import apply_strategy, make_head
from rnafteval.tasks import spliceai as spl_task
from rnafteval.tasks.dedup import dedup

MODEL = "RiNALMo-micro"
TASK = "spliceai"
STATES = ("pre", "lora", "full")
CLASS_NAMES = ("negative", "acceptor", "donor")
MAX_LEN = 128
N_TRAIN = 0
DATA_SPLIT_SEED = 17
B20_VERSION = "b20_single_base_token_positions_v1"
METRIC_REL_TOL = 2e-5
METRIC_ABS_TOL = 2e-6
ROC_AUC_ROLE = "auxiliary_full_test_only_not_source_reconciliation"
METRIC_SCOPE = "full_test_macro_F1_and_MICRO_F1_source_reconciliation__ROC_AUC_auxiliary"
PRE_SOURCE = "pre_official_rinalmomicro"
DATA_ROOT = Path(os.environ.get("RNAFT_DATA_ROOT", "/root/rna-ft-eval/data"))
ARTIFACT_ROOT = Path(os.environ.get(
    "RNAFT_MECHANISM_SPLICEAI_ROOT", str(common.TEAMS_ROOT / "artifacts" / "mechanism_spliceai")))


def flat_metric(y, logits):
    from sklearn.metrics import f1_score, recall_score, roc_auc_score
    y = np.asarray(y, dtype=np.int64)
    logits = np.asarray(logits)
    predictions = np.argmax(logits, axis=-1)
    probabilities = torch.softmax(torch.as_tensor(logits), dim=-1).numpy()
    return {
        "macro_f1": float(f1_score(y, predictions, average="macro")),
        "micro_f1": float(f1_score(y, predictions, average="micro")),
        "roc_auc": float(roc_auc_score(
            y, probabilities, multi_class="ovr", average="macro")),
        "recalls": recall_score(
            y, predictions, average=None, labels=[0, 1, 2], zero_division=0).tolist(),
    }


def source_run_id(strategy, split, seed):
    if strategy == "lora":
        extra = "_b20fix_bestval_v1"
    elif strategy == "full":
        extra = "_b20fix_lr1e-05_bestval_v1"
    else:
        raise ValueError("只有 post LoRA/full 有源 checkpoint")
    return ledger.run_id(MODEL, TASK, strategy, seed, split, extra)


def diagnostic_run_id(strategy, split, seed, suffix="_ckpt_v1"):
    return f"mech_rinalmomicro_spliceai_{strategy}_{split}_s{seed}{suffix}"


def build_split_evidence(parts, split, seed=17, n_train=N_TRAIN,
                         input_rows=None, rows_before_sampling=None,
                         ignored_validation=0, family_path=None,
                         random_dedup=None):
    evidence = {
        "protocol": "bestval_v1",
        "task": TASK,
        "validation_source": "train_holdout",
        "split": split,
        "seed": int(seed),
        "holdout_seed": DATA_SPLIT_SEED,
        "canonical_n_train": N_TRAIN,
        "max_len": MAX_LEN,
        "ignored_source_validation_rows": int(ignored_validation),
        "input_rows": dict(input_rows or {}),
        "random_dedup": dict(random_dedup or {}),
        "train_sampling": {
            "method": "random.Random(seed).sample_if_n_train_gt_0",
            "n_train": int(n_train),
            "seed": int(seed),
            "rows_before": (len(parts["train"]) if rows_before_sampling is None
                            else int(rows_before_sampling)),
            "rows_after": len(parts["train"]),
        },
        "n_train": len(parts["train"]),
        "n_val": len(parts["val"]),
        "n_test": len(parts["test"]),
        "output_rows": {side: len(parts[side]) for side in parts},
        "source_data_evidence_present": False,
        "status": "CHECKING",
    }
    if family_path is not None:
        evidence["family_parquet"] = str(family_path)
        evidence["family_parquet_sha256"] = common.sha256_file(family_path)
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
        if any(row.get("cluster") in (None, "") for rows in parts.values()
               for row in rows):
            raise ValueError("family split requires cluster on every row")
        cluster_sides = {side: {str(row["cluster"]) for row in rows}
                         for side, rows in parts.items()}
        cluster_overlaps = {
            "%s_%s" % (a, b): sorted(cluster_sides[a] & cluster_sides[b])
            for a, b in (("train", "val"), ("train", "test"), ("val", "test"))}
        evidence["cluster_cross_split_overlap"] = {
            pair: len(clusters) for pair, clusters in cluster_overlaps.items()}
        evidence["cluster_cross_split_examples"] = {
            pair: clusters[:20] for pair, clusters in cluster_overlaps.items()}
    assert_no_overlap(parts["train"], parts["val"] + parts["test"], unit="seq")
    assert_no_overlap(parts["val"], parts["test"], unit="seq")
    if split == "family":
        assert_cluster_no_overlap(parts["train"], parts["val"] + parts["test"])
        assert_cluster_no_overlap(parts["val"], parts["test"])
    evidence["label_support"] = {
        side: {str(label): int(sum(
            np.sum(np.asarray(row["labels"]) == label) for row in parts[side]))
            for label in range(3)}
        for side in ("train", "val", "test")}
    evidence["status"] = "OK"
    return evidence


def _read_family_source(data_root):
    path = Path(data_root) / "family_splits" / "spliceai.parquet"
    if not path.is_file():
        raise FileNotFoundError(path)
    table = pq.read_table(path).to_pydict()
    train, test = [], []
    ignored_validation = 0
    for seq, labels, side, cluster in zip(
            table["seq"], table["labels"], table["split"], table["cluster_id"]):
        row = {"seq": seq, "labels": [int(value) for value in labels],
               "cluster": cluster}
        if side == "train":
            train.append(row)
        elif side == "test":
            test.append(row)
        elif side in ("val", "validation"):
            ignored_validation += 1
        else:
            raise ValueError("unknown family parquet side: %s" % side)
    return train, test, ignored_validation, path


def _read_random_source(data_root):
    data_dir = Path(data_root) / "beacon_raw" / "spliceai" / "data"
    source = spl_task.load_official_split(str(data_dir))
    train = dedup(source["train"])
    official_val = dedup(source["validation"])
    test = dedup(source["test"])
    seen_train = {row["seq"] for row in train}
    official_val = [row for row in official_val if row["seq"] not in seen_train]
    seen_train.update(row["seq"] for row in official_val)
    test = [row for row in test if row["seq"] not in seen_train]
    assert_no_overlap(train, official_val + test, unit="seq")
    assert_no_overlap(official_val, test, unit="seq")
    dedup_evidence = {
        "train_after_within_dedup": len(train),
        "official_validation_after_train_dedup": len(official_val),
        "test_after_train_and_official_validation_dedup": len(test),
        "priority": ["train", "official_validation", "test"],
    }
    return train, test, source, official_val, dedup_evidence


def load_task_parts(split, seed=17, n_train=N_TRAIN, data_root=DATA_ROOT):
    if split not in ("random", "family"):
        raise ValueError(split)
    if n_train < 0:
        raise ValueError("n_train must be non-negative")
    if split == "family":
        raw_train, test, ignored, family_path = _read_family_source(data_root)
        input_rows = {"train": len(raw_train), "test": len(test),
                      "validation_ignored": ignored}
        random_dedup = None
    else:
        raw_train, test, source, official_val, random_dedup = _read_random_source(data_root)
        ignored = len(official_val)
        family_path = None
        input_rows = {"train": len(source["train"]),
                      "official_validation": len(source["validation"]),
                      "test": len(source["test"])}
    train, val = split_train_validation(raw_train, seed=DATA_SPLIT_SEED)
    rows_before_sampling = len(train)
    if n_train > 0:
        train = random.Random(seed).sample(train, min(n_train, len(train)))
    parts = {"train": train, "val": val, "test": test}
    evidence = build_split_evidence(
        parts, split, seed=seed, n_train=n_train, input_rows=input_rows,
        rows_before_sampling=rows_before_sampling, ignored_validation=ignored,
        family_path=family_path, random_dedup=random_dedup)
    return parts, evidence


def validate_source_result(result, ledger_row, source_rid, strategy, split, seed, parts):
    expected = {"run_id": source_rid, "model": MODEL, "task": TASK,
                "strategy": strategy, "split": split, "seed": seed}
    if not isinstance(result, dict) or not isinstance(ledger_row, dict):
        raise ValueError("source result and ledger row are required")
    for key, value in expected.items():
        if result.get(key) != value:
            raise ValueError("source result identity mismatch: %s" % key)
        if key in ledger_row and ledger_row[key] != value:
            raise ValueError("source ledger identity mismatch: %s" % key)
    if result.get("metric") != "MACRO_F1" or result.get("metric2") != "MICRO_F1":
        raise ValueError("source result must contain MACRO_F1/value and MICRO_F1/value2")
    counts = {"n_train": len(parts["train"]), "n_val": len(parts["val"]),
              "n_test": len(parts["test"])}
    for key, value in counts.items():
        if result.get(key) != value:
            raise ValueError("source result %s differs from reconstruction" % key)
        if key in ledger_row and ledger_row[key] != value:
            raise ValueError("source ledger %s differs from reconstruction" % key)
    return counts


def source_data_evidence(source_result):
    if source_result is None:
        return {"source_data_evidence_present": None,
                "source_data_evidence_note": "not_applicable_pre_reference"}
    if "data_evidence" not in source_result:
        return {
            "source_data_evidence_present": False,
            "source_data_evidence_note": (
                "missing_in_source_result_reconstructed_evidence_is_not_claimed_"
                "as_source_evidence"),
        }
    return {"source_data_evidence_present": True,
            "source_data_evidence_note": "present_in_source_result"}


def reconcile_source_metrics(metrics, source_result):
    checks = {
        "macro_f1": math.isclose(
            metrics["macro_f1"], source_result["value"],
            rel_tol=METRIC_REL_TOL, abs_tol=METRIC_ABS_TOL),
        "micro_f1": math.isclose(
            metrics["micro_f1"], source_result["value2"],
            rel_tol=METRIC_REL_TOL, abs_tol=METRIC_ABS_TOL),
    }
    if not all(checks.values()):
        raise ValueError("完整 test MACRO_F1/MICRO_F1 与源 result 不一致: %s" % checks)
    return checks


def sequence_gc(sequence):
    sequence = sequence.upper()
    return (sequence.count("G") + sequence.count("C")) / max(1, len(sequence))


def _token_id(sequence_id, base_position):
    return "%s:%04d" % (sequence_id, base_position)


def _manifest_digest(manifest):
    payload = {key: value for key, value in manifest.items()
               if key != "manifest_sha256"}
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False,
                         separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(encoded).hexdigest()


def compute_full_test_hash(task, max_len, b20_version, sequence_ids, token_ids,
                           token_sequence_ids, base_positions, token_positions, labels):
    lengths = (len(token_ids), len(token_sequence_ids), len(base_positions),
               len(token_positions), len(labels))
    if len(set(lengths)) != 1:
        raise ValueError("full-test hash fields are not aligned")
    tokens = [[str(token_id), str(sequence_id), int(base), int(token), int(label)]
              for token_id, sequence_id, base, token, label in zip(
                  token_ids, token_sequence_ids, base_positions, token_positions, labels)]
    payload = {
        "task": task,
        "max_len": int(max_len),
        "b20_version": b20_version,
        "sequence_ids": [str(value) for value in sequence_ids],
        "tokens": tokens,
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(encoded).hexdigest()


def _aligned_labels(tokenizer, encoded, rows, max_len):
    return align_base_labels(
        tokenizer, encoded, rows, max_len, dtype=torch.long)


def _valid_positions(labels, mask, offset):
    token_positions = mask[offset].nonzero(as_tuple=False).flatten()
    aligned = labels[offset].index_select(0, token_positions)
    keep = aligned >= 0
    base_positions = torch.arange(len(token_positions), device=token_positions.device)[keep]
    token_positions = token_positions[keep]
    aligned = aligned[keep]
    if aligned.numel() and not bool(((aligned >= 0) & (aligned <= 2)).all()):
        raise ValueError("SpliceAI labels must be 0 negative, 1 acceptor, 2 donor or -100")
    return base_positions, token_positions, aligned


def make_token_manifest(tokenizer, rows, split, seed, per_class_cap=512,
                        split_evidence=None, batch_size=16, max_len=MAX_LEN):
    if isinstance(per_class_cap, bool) or not isinstance(per_class_cap, int) \
            or per_class_cap <= 0:
        raise ValueError("per_class_cap 必须为正整数")
    if batch_size <= 0 or max_len <= 0:
        raise ValueError("batch_size 和 max_len 必须为正数")
    ordered = sorted(rows, key=lambda row: common.sequence_hash(row["seq"]))
    sequence_ids = [common.sequence_hash(row["seq"]) for row in ordered]
    if len(sequence_ids) != len(set(sequence_ids)):
        raise ValueError("test 中仍有重复 sequence hash")
    full_records = []
    sequences = []
    for start in range(0, len(ordered), batch_size):
        batch = ordered[start:start + batch_size]
        encoded = encode_seqs(
            tokenizer, [row["seq"] for row in batch], "cpu", max_len)
        labels, mask = _aligned_labels(tokenizer, encoded, batch, max_len)
        for offset, row in enumerate(batch):
            seq_index = start + offset
            sequence_id = sequence_ids[seq_index]
            base_positions, token_positions, valid_labels = _valid_positions(
                labels, mask, offset)
            base_np = base_positions.cpu().numpy()
            token_np = token_positions.cpu().numpy()
            label_np = valid_labels.cpu().numpy()
            cluster = row.get("cluster")
            for base, token, label in zip(base_np, token_np, label_np):
                full_records.append({
                    "seq_index": seq_index,
                    "sequence_id": sequence_id,
                    "base_position": int(base),
                    "token_position": int(token),
                    "token_id": _token_id(sequence_id, int(base)),
                    "label": int(label),
                    "cluster": None if cluster is None else str(cluster),
                    "length": len(row["seq"]),
                    "gc": sequence_gc(row["seq"]),
                })
            sequences.append({
                "seq_index": seq_index,
                "sequence_id": sequence_id,
                "base_token_positions": token_np.tolist(),
                "n_full_tokens": len(label_np),
            })
    if not full_records:
        raise ValueError("full test has no valid SpliceAI labels")
    full_support = np.bincount(
        [record["label"] for record in full_records], minlength=3)
    selected_by_class = {label: [] for label in range(3)}
    for label in range(3):
        candidates = sorted(
            (record for record in full_records if record["label"] == label),
            key=lambda record: record["token_id"])
        selected_by_class[label] = [dict(record) for record in candidates[:per_class_cap]]
    selected = [record for label in range(3) for record in selected_by_class[label]]
    selected.sort(key=lambda record: (record["seq_index"], record["base_position"]))
    full_hash = compute_full_test_hash(
        TASK, max_len, B20_VERSION, sequence_ids,
        [record["token_id"] for record in full_records],
        [record["sequence_id"] for record in full_records],
        [record["base_position"] for record in full_records],
        [record["token_position"] for record in full_records],
        [record["label"] for record in full_records])
    manifest = {
        "artifact_type": "spliceai_token_test_manifest",
        "model": MODEL,
        "task": TASK,
        "split": split,
        "seed": int(seed),
        "max_len": int(max_len),
        "b20_version": B20_VERSION,
        "selection": f"token_id_lexicographic_per_class_cap_{per_class_cap}_before_prediction",
        "per_class_cap": int(per_class_cap),
        "class_balanced_visualization": True,
        "n_full_sequences": len(ordered),
        "n_full_tokens": len(full_records),
        "n_sample_tokens": len(selected),
        "n": len(selected),
        "sequence_ids": sequence_ids,
        "sequences": sequences,
        "token_ids": [record["token_id"] for record in selected],
        "records": selected,
        "full_test_sha256": full_hash,
        "full_test_hash_algorithm": "sha256_task_maxlen_b20_sequence_base_token_labels_v1",
        "full_class_support": {str(label): int(full_support[label]) for label in range(3)},
        "sample_class_support": {
            str(label): len(selected_by_class[label]) for label in range(3)},
        "class_names": list(CLASS_NAMES),
        "split_evidence": dict(split_evidence or {}),
        "metric_scope": METRIC_SCOPE,
        "roc_auc_role": ROC_AUC_ROLE,
    }
    manifest["manifest_sha256"] = _manifest_digest(manifest)
    return ordered, manifest, selected


def validate_token_arrays(arrays, manifest=None, require_embedding=False):
    required = ("token_ids", "sequence_ids", "base_positions", "token_positions",
                "labels", "logits", "probabilities")
    if any(key not in arrays for key in required):
        raise ValueError("token 数组缺失")
    n = len(arrays["token_ids"])
    if not n:
        raise ValueError("token 数组为空")
    for key in ("token_ids", "sequence_ids", "base_positions", "token_positions", "labels"):
        if np.asarray(arrays[key]).ndim != 1 or len(arrays[key]) != n:
            raise ValueError("token 数组长度不一致: " + key)
    if arrays["logits"].shape != (n, 3) or arrays["probabilities"].shape != (n, 3):
        raise ValueError("token logits/probabilities 必须为 [N,3]")
    if not np.isfinite(arrays["logits"]).all() or not np.isfinite(arrays["probabilities"]).all():
        raise ValueError("token logits/probabilities 非有限值")
    expected_probability = torch.softmax(torch.as_tensor(arrays["logits"]), dim=-1).numpy()
    if not np.allclose(arrays["probabilities"], expected_probability, rtol=1e-4, atol=1e-5):
        raise ValueError("token probabilities 不是三分类 softmax")
    if not np.isin(arrays["labels"], (0, 1, 2)).all():
        raise ValueError("SpliceAI 标签必须为 0/1/2")
    expected_ids = [_token_id(sequence_id, int(base)) for sequence_id, base in zip(
        arrays["sequence_ids"], arrays["base_positions"])]
    if arrays["token_ids"].tolist() != expected_ids:
        raise ValueError("token_id 必须由 sequence_id/base_position 生成")
    if require_embedding:
        embedding = np.asarray(arrays.get("token_embedding"))
        if embedding.ndim != 2 or embedding.shape[0] != n or not np.isfinite(embedding).all():
            raise ValueError("token_embedding 形状或数值无效")
    if manifest is not None:
        expected = {
            "token_ids": [record["token_id"] for record in manifest["records"]],
            "sequence_ids": [record["sequence_id"] for record in manifest["records"]],
            "base_positions": [record["base_position"] for record in manifest["records"]],
            "token_positions": [record["token_position"] for record in manifest["records"]],
            "labels": [record["label"] for record in manifest["records"]],
        }
        for key, values in expected.items():
            if not np.array_equal(arrays[key], np.asarray(values)):
                raise ValueError("embedding %s differs from the saved token manifest" % key)
        if arrays["token_ids"].tolist() != manifest["token_ids"]:
            raise ValueError("sample token order differs from manifest")
    return True


def extract(backbone, head, tokenizer, rows, device, manifest, selected,
            batch_size=16, max_len=MAX_LEN):
    if manifest["task"] != TASK or max_len != manifest["max_len"] or \
            manifest["b20_version"] != B20_VERSION:
        raise ValueError("extraction task/max_len/B20 differs from manifest")
    if len(rows) != manifest["n_full_sequences"]:
        raise ValueError("extraction rows differ from manifest")
    sequence_ids = [common.sequence_hash(row["seq"]) for row in rows]
    if sequence_ids != manifest["sequence_ids"]:
        raise ValueError("extraction sequence identity/order differs from manifest")
    backbone.eval()
    head.eval()
    selected_by_sequence = {}
    for record in selected:
        selected_by_sequence.setdefault(record["seq_index"], []).append(record)
    full = {key: [] for key in (
        "token_ids", "sequence_ids", "base_positions", "token_positions",
        "labels", "logits", "probabilities")}
    sample = {key: [] for key in (
        "token_ids", "sequence_ids", "base_positions", "token_positions",
        "labels", "logits", "probabilities", "token_embedding")}
    with torch.no_grad():
        for start in range(0, len(rows), batch_size):
            batch = rows[start:start + batch_size]
            encoded = encode_seqs(
                tokenizer, [row["seq"] for row in batch], device, max_len)
            labels, mask = _aligned_labels(tokenizer, encoded, batch, max_len)
            hidden = backbone(**encoded).last_hidden_state
            logits = head(hidden, encoded["attention_mask"] == 0)
            probabilities = torch.softmax(logits, dim=-1)
            for offset, row in enumerate(batch):
                seq_index = start + offset
                sequence_id = sequence_ids[seq_index]
                base_positions, token_positions, valid_labels = _valid_positions(
                    labels, mask, offset)
                if not len(valid_labels):
                    continue
                hidden_valid = hidden[offset].index_select(0, token_positions)
                logits_valid = logits[offset].index_select(0, token_positions)
                probability_valid = probabilities[offset].index_select(0, token_positions)
                base_np = base_positions.cpu().numpy()
                token_np = token_positions.cpu().numpy()
                label_np = valid_labels.cpu().numpy()
                full["token_ids"].extend(
                    _token_id(sequence_id, int(base)) for base in base_np)
                full["sequence_ids"].extend([sequence_id] * len(label_np))
                full["base_positions"].extend(int(base) for base in base_np)
                full["token_positions"].extend(int(token) for token in token_np)
                full["labels"].extend(int(label) for label in label_np)
                full["logits"].append(logits_valid.detach().cpu().numpy())
                full["probabilities"].append(probability_valid.detach().cpu().numpy())
                index_by_base = {int(base): index for index, base in enumerate(base_np)}
                for record in selected_by_sequence.get(seq_index, []):
                    base = record["base_position"]
                    if base not in index_by_base:
                        raise ValueError("selected base_position differs from B20 mask")
                    index = index_by_base[base]
                    token_id = _token_id(sequence_id, base)
                    if (record["sequence_id"] != sequence_id
                            or record["token_id"] != token_id
                            or record["token_position"] != int(token_np[index])
                            or record["label"] != int(label_np[index])):
                        raise ValueError("selected token identity/position/label differs from B20")
                    sample["token_ids"].append(token_id)
                    sample["sequence_ids"].append(sequence_id)
                    sample["base_positions"].append(base)
                    sample["token_positions"].append(int(token_np[index]))
                    sample["labels"].append(int(label_np[index]))
                    sample["logits"].append(logits_valid[index].detach().cpu().numpy())
                    sample["probabilities"].append(probability_valid[index].detach().cpu().numpy())
                    sample["token_embedding"].append(hidden_valid[index].detach().cpu().numpy())
    for arrays in (full, sample):
        for key in ("token_ids", "sequence_ids"):
            arrays[key] = np.asarray(arrays[key])
        for key in ("base_positions", "token_positions", "labels"):
            arrays[key] = np.asarray(arrays[key], dtype=np.int64)
    for key in ("logits", "probabilities"):
        full[key] = np.concatenate(full[key]).astype(np.float32)
        sample[key] = np.asarray(sample[key], dtype=np.float32)
    sample["token_embedding"] = np.asarray(sample["token_embedding"], dtype=np.float32)
    if not len(full["labels"]) or not len(sample["labels"]):
        raise ValueError("full/sample token extraction is empty")
    full_hash = compute_full_test_hash(
        TASK, max_len, B20_VERSION, sequence_ids,
        full["token_ids"], full["sequence_ids"], full["base_positions"],
        full["token_positions"], full["labels"])
    if full_hash != manifest["full_test_sha256"]:
        raise ValueError("full-test hash changed during prediction")
    if len(full["labels"]) != manifest["n_full_tokens"]:
        raise ValueError("full-test token count differs from manifest")
    full_support = np.bincount(full["labels"], minlength=3)
    expected_support = [manifest["full_class_support"][str(label)] for label in range(3)]
    if full_support.tolist() != expected_support:
        raise ValueError("full-test class support differs from manifest")
    if len(sample["labels"]) != manifest["n_sample_tokens"]:
        raise ValueError("sample token count differs from manifest")
    sample_support = np.bincount(sample["labels"], minlength=3)
    expected_sample = [manifest["sample_class_support"][str(label)] for label in range(3)]
    if sample_support.tolist() != expected_sample:
        raise ValueError("sample class support differs from manifest")
    validate_token_arrays(full)
    validate_token_arrays(sample, manifest, require_embedding=True)
    return full, sample


def _artifact_metadata(manifest):
    return {
        "task": np.asarray(manifest["task"]),
        "split": np.asarray(manifest["split"]),
        "seed": np.asarray(manifest["seed"], dtype=np.int64),
        "max_len": np.asarray(manifest["max_len"], dtype=np.int64),
        "b20_version": np.asarray(manifest["b20_version"]),
        "n_full_tokens": np.asarray(manifest["n_full_tokens"], dtype=np.int64),
        "n_sample_tokens": np.asarray(manifest["n_sample_tokens"], dtype=np.int64),
        "full_test_sha256": np.asarray(manifest["full_test_sha256"]),
        "test_manifest_sha256": np.asarray(manifest["manifest_sha256"]),
        "selection": np.asarray(manifest["selection"]),
    }


def _scalar(arrays, key):
    if key not in arrays or np.asarray(arrays[key]).shape != ():
        raise ValueError("state is missing scalar alignment field: " + key)
    return np.asarray(arrays[key]).item()


def _validate_state_metadata(arrays, manifest):
    validate_token_arrays(arrays, manifest, require_embedding=True)
    expected = {
        "task": TASK,
        "split": manifest["split"],
        "seed": manifest["seed"],
        "max_len": manifest["max_len"],
        "b20_version": B20_VERSION,
        "n_full_tokens": manifest["n_full_tokens"],
        "n_sample_tokens": manifest["n_sample_tokens"],
        "full_test_sha256": manifest["full_test_sha256"],
        "test_manifest_sha256": manifest["manifest_sha256"],
    }
    for key, value in expected.items():
        if _scalar(arrays, key) != value:
            raise ValueError("embedding metadata differs from manifest: " + key)


def load_aligned_states(split, seed, suffix="_ckpt_v1", artifact_root=None):
    root = Path(ARTIFACT_ROOT if artifact_root is None else artifact_root)
    ready = []
    for strategy in STATES:
        out_dir = root / diagnostic_run_id(strategy, split, seed, suffix)
        diagnostic_path = out_dir / "diagnostic.json"
        embedding_path = out_dir / "embeddings.npz"
        manifest_path = out_dir / "test_manifest.json"
        if not diagnostic_path.is_file() or not embedding_path.is_file():
            continue
        if not manifest_path.is_file():
            raise ValueError("diagnostic is missing its test manifest: " + strategy)
        diagnostic = json.loads(diagnostic_path.read_text())
        if diagnostic.get("status") != "diagnostic":
            continue
        expected_identity = {"model": MODEL, "task": TASK, "strategy": strategy,
                             "split": split, "seed": seed}
        for key, value in expected_identity.items():
            if diagnostic.get(key) != value:
                raise ValueError("诊断身份不一致: %s (%s)" % (key, strategy))
        if strategy == "pre":
            if diagnostic.get("source_run_id") is not None or \
                    diagnostic.get("reference_head_seed") != 201:
                raise ValueError("pre 诊断缺少 seed-201 reference-head 身份")
        else:
            checkpoint = diagnostic.get("checkpoint") or {}
            if (diagnostic.get("full_test_metric_match") is not True
                    or checkpoint.get("restored_tensor_match") is not True
                    or checkpoint.get("checkpoint_proof") != "ok"
                    or diagnostic.get("source_proof", {}).get("state") != "complete"):
                raise ValueError("post 诊断缺少 full-test/checkpoint/registry 证明: " + strategy)
            if diagnostic.get("source_run_id") != source_run_id(strategy, split, seed):
                raise ValueError("post 诊断 source RID 身份不一致: " + strategy)
        manifest = json.loads(manifest_path.read_text())
        if (manifest.get("model") != MODEL or manifest.get("task") != TASK
                or manifest.get("split") != split or manifest.get("seed") != seed
                or manifest.get("max_len") != MAX_LEN
                or manifest.get("b20_version") != B20_VERSION):
            raise ValueError("manifest 身份不一致: " + strategy)
        if (manifest.get("manifest_sha256") != _manifest_digest(manifest)
                or diagnostic.get("test_manifest_sha256") != manifest["manifest_sha256"]):
            raise ValueError("诊断 manifest hash 不一致: " + strategy)
        if diagnostic.get("full_test_sha256") != manifest["full_test_sha256"]:
            raise ValueError("诊断 full-test hash 不一致: " + strategy)
        with np.load(embedding_path, allow_pickle=False) as data:
            arrays = {key: data[key].copy() for key in data.files}
        _validate_state_metadata(arrays, manifest)
        source_reference = diagnostic["source_run_id"] or PRE_SOURCE
        ready.append((strategy, arrays, manifest["manifest_sha256"],
                      source_reference, diagnostic["metrics_full"]))
    return ready


def aligned_spliceai(states, output_path, perplexity=30, random_state=17):
    if len(states) != 3 or {item[0] for item in states} != set(STATES):
        raise ValueError("需要 pre/lora/full 三状态")
    states = sorted(states, key=lambda item: STATES.index(item[0]))
    if len({item[2] for item in states}) != 1:
        raise ValueError("三状态 test manifest 不一致")
    reference = states[0][1]
    validate_token_arrays(reference, require_embedding=True)
    reference_metadata = {key: _scalar(reference, key) for key in (
        "task", "split", "seed", "max_len", "b20_version", "n_full_tokens",
        "n_sample_tokens", "full_test_sha256", "test_manifest_sha256", "selection")}
    alignment_keys = ("token_ids", "sequence_ids", "base_positions",
                      "token_positions", "labels")
    for strategy, arrays, manifest_hash, source, metrics in states:
        validate_token_arrays(arrays, require_embedding=True)
        if arrays["token_embedding"].shape[1] != reference["token_embedding"].shape[1]:
            raise ValueError("三状态 token embedding 维度不一致")
        for key in alignment_keys:
            if not np.array_equal(reference[key], arrays[key]):
                raise ValueError("三状态 token 对齐不一致: " + key)
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
               for key in ("macro_f1", "micro_f1", "roc_auc")):
            raise FloatingPointError("full-test metrics 缺失或非有限值")
    from sklearn.manifold import TSNE
    token = np.concatenate([item[1]["token_embedding"] for item in states]).astype(np.float64)
    n = len(reference["token_ids"])
    effective_perplexity = min(perplexity, max(1, (len(token) - 1) // 3))
    coordinates = TSNE(n_components=2, random_state=random_state,
                       perplexity=effective_perplexity).fit_transform(token)
    output_path = Path(output_path)
    if output_path.suffix != ".npz":
        output_path = output_path.with_suffix(".npz")
    if output_path.exists():
        raise FileExistsError("拒绝覆盖已有 aligned 诊断: " + str(output_path))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tiled = {key: np.tile(reference[key], 3) for key in alignment_keys}
    save_npz(
        output_path,
        tsne=coordinates,
        token_embedding=token,
        **tiled,
        state=np.concatenate([np.full(n, item[0]) for item in states]),
        probabilities=np.concatenate([item[1]["probabilities"] for item in states]),
        logits=np.concatenate([item[1]["logits"] for item in states]),
        task=np.asarray(reference_metadata["task"]),
        split=np.asarray(reference_metadata["split"]),
        seed=np.asarray(reference_metadata["seed"], dtype=np.int64),
        max_len=np.asarray(reference_metadata["max_len"], dtype=np.int64),
        b20_version=np.asarray(reference_metadata["b20_version"]),
        n_full_tokens=np.asarray(reference_metadata["n_full_tokens"], dtype=np.int64),
        n_sample_tokens=np.asarray(n, dtype=np.int64),
        full_test_sha256=np.asarray(reference_metadata["full_test_sha256"]),
        source_run_ids=np.asarray([item[3] for item in states]),
        full_macro_f1=np.asarray([item[4]["macro_f1"] for item in states], dtype=np.float64),
        full_micro_f1=np.asarray([item[4]["micro_f1"] for item in states], dtype=np.float64),
        full_roc_auc=np.asarray([item[4]["roc_auc"] for item in states], dtype=np.float64),
        roc_auc_role=np.asarray(ROC_AUC_ROLE),
        metric_scope=np.asarray(METRIC_SCOPE),
        class_names=np.asarray(CLASS_NAMES),
        test_manifest_sha256=np.asarray(states[0][2]),
        tsne_perplexity=np.asarray(effective_perplexity),
        tsne_random_state=np.asarray(random_state),
        color_mode=np.asarray("spliceai_token_class"),
        sampling=np.asarray(reference_metadata["selection"]),
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
    parts, split_evidence = load_task_parts(
        args.split, seed=args.seed, n_train=N_TRAIN, data_root=DATA_ROOT)
    source_result = None
    source_dir = None
    source_row = None
    source_proof = None
    source_rid = None
    if args.strategy != "pre":
        source_rid = source_run_id(args.strategy, args.split, args.seed)
        source_row = ledger.by_run_id(source_rid)
        if source_row is None:
            raise ValueError("源格缺少 ledger 记录: " + source_rid)
        source_dir = Path(source_row["out_dir"])
        source_result = json.loads((source_dir / "result.json").read_text())
        validate_source_result(source_result, source_row, source_rid, args.strategy,
                               args.split, args.seed, parts)
        source_proof = common.require_complete_source(source_rid, source_row)
    out_dir = ARTIFACT_ROOT / diagnostic_run_id(args.strategy, args.split, args.seed)
    out_dir.mkdir(parents=True, exist_ok=True)
    if any((out_dir / name).exists() for name in
           ("diagnostic.json", "predictions.npz", "embeddings.npz")):
        raise FileExistsError("拒绝覆盖已有诊断: " + str(out_dir))
    common.write_json(out_dir / "job.json", {
        "run_id": out_dir.name, "status": "running", "split": args.split,
        "seed": args.seed, "strategy": args.strategy, "out_dir": str(out_dir),
        "model": MODEL, "task": TASK, "max_len": MAX_LEN,
        "n_train": N_TRAIN, "source_run_id": source_rid,
        "git_sha": common.git_sha(), "memory_evidence": memory_evidence,
    })
    aligned_cleanup_path = None
    try:
        from rnafteval.models import load_model
        spec, tokenizer, backbone = load_model(MODEL, device)
        ordered, manifest, selected = make_token_manifest(
            tokenizer, parts["test"], args.split, args.seed, args.per_class_cap,
            split_evidence, batch_size=args.batch_size, max_len=MAX_LEN)
        common.write_json(out_dir / "test_manifest.json", manifest)
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
        full, sample = extract(
            backbone, head, tokenizer, ordered, device, manifest, selected,
            batch_size=args.batch_size, max_len=MAX_LEN)
        metrics = flat_metric(full["labels"], full["logits"])
        metric_match = None
        reconciliation = None
        if source_result is not None:
            reconciliation = reconcile_source_metrics(metrics, source_result)
            metric_match = True
        metadata = _artifact_metadata(manifest)
        full.update(metadata)
        sample.update(metadata)
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
            "max_len": MAX_LEN,
            "b20_version": B20_VERSION,
            "canonical_n_train": N_TRAIN,
            "n_train": len(parts["train"]),
            "n_val": len(parts["val"]),
            "n_test": len(parts["test"]),
            "n_full_test_sequences": len(ordered),
            "n_full_test_tokens": len(full["labels"]),
            "n_sample": len(sample["token_ids"]),
            "metrics_full": metrics,
            "metric_scope": METRIC_SCOPE,
            "roc_auc_role": ROC_AUC_ROLE,
            "source_run_id": None if source_result is None else source_result["run_id"],
            "source_metrics": None if source_result is None else {
                "macro_f1": source_result["value"],
                "micro_f1": source_result["value2"]},
            "source_reconciliation": reconciliation,
            "full_test_metric_match": metric_match,
            "source_proof": source_proof,
            "split_evidence": split_evidence,
            "test_manifest": str(out_dir / "test_manifest.json"),
            "test_manifest_sha256": manifest["manifest_sha256"],
            "full_test_sha256": manifest["full_test_sha256"],
            "predictions": str(out_dir / "predictions.npz"),
            "embeddings": str(out_dir / "embeddings.npz"),
            "checkpoint": checkpoint_evidence,
            "cuda": runtime,
            "git_sha": common.git_sha(),
            "class_names": list(CLASS_NAMES),
            "prediction_head": ("fresh_reference_head_seed_201_not_zero_shot"
                                if args.strategy == "pre" else "restored_bestval_head"),
            "reference_head_seed": 201 if args.strategy == "pre" else None,
            "interpretation": "descriptive_balanced_tokens_full_test_metrics_only",
        }
        diagnostic.update(source_data_evidence(source_result))
        ready = load_aligned_states(args.split, args.seed)
        source_reference = PRE_SOURCE if source_result is None else source_result["run_id"]
        ready.append((args.strategy, sample, manifest["manifest_sha256"],
                      source_reference, metrics))
        diagnostic["aligned_tsne"] = None
        diagnostic["available_states"] = [item[0] for item in ready]
        if len(ready) == 3:
            aligned_path = ARTIFACT_ROOT / (
                f"mech_rinalmomicro_spliceai_aligned_{args.split}_s{args.seed}_ckpt_v1.npz")
            if aligned_path.exists():
                raise FileExistsError("拒绝覆盖已有 aligned 诊断: " + str(aligned_path))
            aligned_cleanup_path = aligned_path
            diagnostic["aligned_tsne"] = aligned_spliceai(ready, aligned_path)
        common.write_json(out_dir / "diagnostic.json", diagnostic)
        common.write_json(out_dir / "job.json", {
            "run_id": out_dir.name, "status": "diagnostic", "out_dir": str(out_dir),
            "diagnostic": str(out_dir / "diagnostic.json"),
            "git_sha": diagnostic["git_sha"],
            "full_test_metric_match": metric_match,
        })
        print(json.dumps({
            "run_id": out_dir.name, "status": "diagnostic",
            "n_full_test_sequences": len(ordered),
            "n_full_test_tokens": len(full["labels"]),
            "n_sample": len(sample["token_ids"]),
            "macro_f1": metrics["macro_f1"], "micro_f1": metrics["micro_f1"],
            "auxiliary_roc_auc": metrics["roc_auc"],
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
