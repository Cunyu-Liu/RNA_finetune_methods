#!/usr/bin/env python3
"""degradation/SSI per-base regression checkpoint mechanism diagnostics."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
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
from rnafteval.finetune_regbase import batches, encode_seqs
from rnafteval.splits import (
    assert_cluster_no_overlap, assert_no_overlap, seeded_sample,
    split_train_validation)
from rnafteval.strategies import TokenHead, apply_strategy
from rnafteval.tasks import degradation as deg_task
from rnafteval.tasks import ssi as ssi_task

MODEL = "RiNALMo-micro"
TASKS = ("degradation", "ssi")
STATES = ("pre", "lora", "full")
MAX_LEN = 192
N_TRAIN = 0
DATA_SPLIT_SEED = 17
PRE_HEAD_SEED = 201
METRIC_REL_TOL = 2e-5
METRIC_ABS_TOL = 2e-6
PRE_SOURCE = "pre_official_rinalmomicro_reference_head_seed201"
DATA_ROOT = Path(os.environ.get("RNAFT_DATA_ROOT", "/root/rna-ft-eval/data"))
ARTIFACT_ROOT = Path(os.environ.get(
    "RNAFT_MECHANISM_REGBASE_ROOT",
    str(common.TEAMS_ROOT / "artifacts" / "mechanism_regbase")))


def _validate_task_split(task, split):
    if task not in TASKS:
        raise ValueError("unknown per-base regression task: %s" % task)
    if split not in ("random", "family"):
        raise ValueError("unknown split: %s" % split)


def diagnostic_run_id(task, strategy, split, seed, suffix="_ckpt_v1"):
    _validate_task_split(task, split)
    if strategy not in STATES:
        raise ValueError("unknown state: %s" % strategy)
    return "mech_rinalmomicro_%s_%s_%s_s%d%s" % (
        task, strategy, split, seed, suffix)


def source_run_id(task, strategy, split, seed):
    _validate_task_split(task, split)
    if strategy == "lora":
        extra = "_b20fix_bestval_v1"
    elif strategy == "full":
        extra = "_b20fix_lr1e-05_bestval_v1"
    else:
        raise ValueError("only post LoRA/full states have source checkpoints")
    return ledger.run_id(MODEL, task, strategy, seed, split, extra)


def _read_family_source(task, data_root):
    path = Path(data_root) / "family_splits" / (task + ".parquet")
    if not path.is_file():
        raise FileNotFoundError(path)
    table = pq.read_table(path).to_pydict()
    train, test = [], []
    ignored_validation = 0
    for seq, labels, side, cluster in zip(
            table["seq"], table["labels"], table["split"], table["cluster_id"]):
        row = {"seq": seq, "labels": np.asarray(labels, dtype=np.float32),
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


def _read_random_source(task, data_root):
    if task == "degradation":
        data_dir = Path(data_root) / "beacon_raw" / "degradation" / "data"
        source = deg_task.load_official_split(str(data_dir))
    else:
        data_dir = (Path(data_root) / "beacon_raw" /
                    "structural-score-imputation" / "data")
        source = ssi_task.load_official_split(str(data_dir))
    return (source["train"], source["test"], len(source["validation"]), None)


def build_split_evidence(parts, task, split, seed=17, n_train=N_TRAIN,
                         input_rows=None, rows_before_sampling=None,
                         ignored_validation=0, family_path=None):
    _validate_task_split(task, split)
    evidence = {
        "protocol": "bestval_v1",
        "task": task,
        "split": split,
        "seed": int(seed),
        "holdout_seed": DATA_SPLIT_SEED,
        "validation_source": "train_holdout",
        "ignored_source_validation_rows": int(ignored_validation),
        "canonical_n_train": N_TRAIN,
        "max_len": MAX_LEN,
        "input_rows": dict(input_rows or {}),
        "train_sampling": {
            "method": "seeded_sample",
            "n_train": int(n_train),
            "seed": int(seed),
            "rows_before": (len(parts["train"]) if rows_before_sampling is None
                            else int(rows_before_sampling)),
            "rows_after": len(parts["train"]),
        },
        "n_train": len(parts["train"]),
        "n_val": len(parts["val"]),
        "n_test": len(parts["test"]),
        "output_rows": {side: len(parts[side])
                        for side in ("train", "val", "test")},
        "status": "CHECKING",
    }
    if family_path is not None:
        evidence["family_parquet"] = str(family_path)
        evidence["family_parquet_sha256"] = common.sha256_file(family_path)
    sides = {side: {common.sequence_hash(row["seq"]) for row in rows}
             for side, rows in parts.items()}
    overlaps = {"%s_%s" % (left, right): sorted(sides[left] & sides[right])
                for left, right in (("train", "val"), ("train", "test"),
                                    ("val", "test"))}
    evidence["sequence_cross_split_overlap"] = {
        pair: len(values) for pair, values in overlaps.items()}
    evidence["sequence_cross_split_examples"] = {
        pair: values[:20] for pair, values in overlaps.items()}
    if split == "family":
        if any(row.get("cluster") in (None, "") for rows in parts.values()
               for row in rows):
            raise ValueError("family split requires cluster on every row")
        cluster_sides = {side: {str(row["cluster"]) for row in rows}
                         for side, rows in parts.items()}
        cluster_overlaps = {
            "%s_%s" % (left, right): sorted(
                cluster_sides[left] & cluster_sides[right])
            for left, right in (("train", "val"), ("train", "test"),
                                ("val", "test"))}
        evidence["cluster_cross_split_overlap"] = {
            pair: len(values) for pair, values in cluster_overlaps.items()}
        evidence["cluster_cross_split_examples"] = {
            pair: values[:20] for pair, values in cluster_overlaps.items()}
    assert_no_overlap(parts["train"], parts["val"] + parts["test"], unit="seq")
    assert_no_overlap(parts["val"], parts["test"], unit="seq")
    if split == "family":
        assert_cluster_no_overlap(parts["train"], parts["val"] + parts["test"])
        assert_cluster_no_overlap(parts["val"], parts["test"])
    evidence["status"] = "OK"
    return evidence


def load_task_parts(task, split, seed=17, n_train=N_TRAIN, data_root=DATA_ROOT):
    _validate_task_split(task, split)
    if n_train < 0:
        raise ValueError("n_train must be non-negative")
    if split == "family":
        raw_train, test, ignored, family_path = _read_family_source(task, data_root)
    else:
        raw_train, test, ignored, family_path = _read_random_source(task, data_root)
    input_rows = {"train": len(raw_train), "test": len(test),
                  "validation_ignored": ignored}
    if task == "ssi" and split == "random":
        train, val = ssi_task.split_train_validation_by_sequence(
            raw_train, seed=DATA_SPLIT_SEED)
    else:
        train, val = split_train_validation(raw_train, seed=DATA_SPLIT_SEED)
    rows_before_sampling = len(train)
    train = seeded_sample(train, n_train, seed)
    parts = {"train": train, "val": val, "test": test}
    evidence = build_split_evidence(
        parts, task, split, seed=seed, n_train=n_train, input_rows=input_rows,
        rows_before_sampling=rows_before_sampling, ignored_validation=ignored,
        family_path=family_path)
    if task == "ssi" and split == "random":
        evidence.update({
            "validation_grouping": ssi_task.RANDOM_GROUPING,
            "same_sequence_records_preserved": True,
            "requested_n_train": int(n_train),
            "input_same_sequence_rows": {
                "train": ssi_task.same_sequence_record_counts(raw_train),
                "test": ssi_task.same_sequence_record_counts(test)},
        })
    return parts, evidence


def validate_source(source_result, source_row, source_rid, task, strategy,
                    split, seed, parts):
    expected = {"run_id": source_rid, "model": MODEL, "task": task,
                "strategy": strategy, "split": split, "seed": seed}
    if not isinstance(source_result, dict) or not isinstance(source_row, dict):
        raise ValueError("source result and ledger row are required")
    for key, value in expected.items():
        if source_result.get(key) != value:
            raise ValueError("source result identity mismatch: %s" % key)
        if key in source_row and source_row[key] != value:
            raise ValueError("source ledger identity mismatch: %s" % key)
    if source_result.get("metric") != "PCC":
        raise ValueError("source result is not a per-base PCC result")
    expected_lr = 1e-5 if strategy == "full" else 3e-4
    if not math.isclose(float(source_result.get("lr", float("nan"))),
                        expected_lr, rel_tol=0.0, abs_tol=1e-12):
        raise ValueError("source learning rate does not match the canonical run")
    if source_result.get("rank") != 8:
        raise ValueError("source LoRA rank is not the canonical rank 8")
    counts = {"n_train": len(parts["train"]), "n_val": len(parts["val"]),
              "n_test": len(parts["test"])}
    for key, value in counts.items():
        if source_result.get(key) != value:
            raise ValueError("source result %s differs from reconstruction" % key)
        if key in source_row and source_row[key] != value:
            raise ValueError("source ledger %s differs from reconstruction" % key)
    return counts


def load_source(task, strategy, split, seed, parts):
    source_rid = source_run_id(task, strategy, split, seed)
    source_row = ledger.by_run_id(source_rid)
    if source_row is None:
        raise ValueError("source cell is missing from ledger: " + source_rid)
    source_dir = Path(source_row.get("out_dir") or
                      Path(ledger.ARTIFACT_ROOT) / source_rid)
    source_result = json.loads((source_dir / "result.json").read_text())
    validate_source(source_result, source_row, source_rid, task, strategy,
                    split, seed, parts)
    return source_dir, source_result, source_row


def source_data_evidence(source_result, reconstructed=None):
    if source_result is None:
        return {"source_data_evidence_present": None,
                "source_data_evidence_note": "not_applicable_pre_reference"}
    is_ssi_random = (source_result.get("task") == "ssi"
                     and source_result.get("split") == "random")
    if is_ssi_random and reconstructed is None:
        raise ValueError("SSI random source requires reconstructed split evidence")
    if "data_evidence" not in source_result:
        if is_ssi_random:
            raise ValueError(
                "SSI random source is missing required sequence-grouped data_evidence")
        return {
            "source_data_evidence_present": False,
            "source_data_evidence_note": (
                "missing_in_source_result_reconstructed_evidence_is_not_claimed_"
                "as_source_evidence"),
        }
    source = source_result["data_evidence"]
    if not isinstance(source, dict):
        raise ValueError("source data_evidence must be an object")
    note = "present_in_source_result"
    if (reconstructed is not None and source_result.get("task") == "ssi"
            and source_result.get("split") == "random"):
        keys = (
            "protocol", "task", "split", "seed", "holdout_seed",
            "validation_source", "validation_grouping",
            "same_sequence_records_preserved", "ignored_source_validation_rows",
            "input_rows", "input_same_sequence_rows", "canonical_n_train",
            "requested_n_train", "max_len", "train_sampling", "n_train",
            "n_val", "n_test", "output_rows", "status",
        )
        mismatches = {
            key: {"source": source.get(key), "reconstructed": reconstructed.get(key)}
            for key in keys if source.get(key) != reconstructed.get(key)
        }
        if mismatches:
            raise ValueError("source/reconstructed SSI data evidence differs: %s"
                             % json.dumps(mismatches, sort_keys=True))
        note = "matched_reconstructed_sequence_grouped_split"
    return {"source_data_evidence_present": True,
            "source_data_evidence_note": note}


def regression_metrics(y_true, prediction, sequence_ids):
    y_true = np.asarray(y_true)
    prediction = np.asarray(prediction)
    sequence_ids = np.asarray(sequence_ids)
    if (y_true.ndim != 1 or prediction.ndim != 1 or sequence_ids.ndim != 1
            or not len(y_true) or len(y_true) != len(prediction)
            or len(y_true) != len(sequence_ids)):
        raise ValueError("metrics require aligned non-empty token arrays")
    if not np.isfinite(y_true).all() or not np.isfinite(prediction).all():
        raise FloatingPointError("non-finite per-base regression values")
    pcc = float(np.corrcoef(prediction, y_true)[0, 1])
    sequence_mse = []
    for sequence_id in dict.fromkeys(sequence_ids.tolist()):
        keep = sequence_ids == sequence_id
        p = prediction[keep]
        t = y_true[keep]
        sequence_mse.append(float(((p - t) ** 2).mean()))
    mcrmse = float(np.sqrt(np.mean(sequence_mse)))
    if not math.isfinite(pcc) or not math.isfinite(mcrmse):
        raise FloatingPointError("non-finite full-test PCC/MCRMSE")
    return {"pcc": pcc, "mcrmse": mcrmse}


def source_metrics_match(metrics, source_result):
    values = (metrics.get("pcc"), metrics.get("mcrmse"),
              source_result.get("value"), source_result.get("mcrmse"))
    if any(not isinstance(value, (int, float)) or isinstance(value, bool)
           or not math.isfinite(value) for value in values):
        return False
    return (math.isclose(metrics["pcc"], source_result["value"],
                         rel_tol=METRIC_REL_TOL, abs_tol=METRIC_ABS_TOL)
            and math.isclose(metrics["mcrmse"], source_result["mcrmse"],
                             rel_tol=METRIC_REL_TOL, abs_tol=METRIC_ABS_TOL))


def reconcile_source_metrics(metrics, source_result):
    if not source_metrics_match(metrics, source_result):
        raise ValueError(
            "full-test PCC/MCRMSE do not match source result: "
            "pcc=%r source=%r mcrmse=%r source=%r" % (
                metrics.get("pcc"), source_result.get("value"),
                metrics.get("mcrmse"), source_result.get("mcrmse")))
    return True


def _token_id(sequence_id, base_position):
    return "%s:%04d" % (sequence_id, base_position)


def compute_full_test_hash(task, max_len, sequence_ids, token_ids,
                           token_sequence_ids, base_positions, token_positions,
                           y_true):
    lengths = (len(token_ids), len(token_sequence_ids), len(base_positions),
               len(token_positions), len(y_true))
    if len(set(lengths)) != 1:
        raise ValueError("full-test hash fields are not aligned")
    tokens = [[str(token_id), str(sequence_id), int(base), int(token), float(label)]
              for token_id, sequence_id, base, token, label in zip(
                  token_ids, token_sequence_ids, base_positions, token_positions,
                  y_true)]
    payload = {"task": task, "max_len": int(max_len),
               "sequences": [str(value) for value in sequence_ids],
               "tokens": tokens}
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(encoded).hexdigest()


def manifest_digest(manifest):
    payload = {key: value for key, value in manifest.items()
               if key != "manifest_sha256"}
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False,
                         separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(encoded).hexdigest()


def ordered_record_ids(rows, task, split):
    ordered = sorted(rows, key=lambda row: common.sequence_hash(row["seq"]))
    if not (task == "ssi" and split == "random"):
        return ordered, [common.sequence_hash(row["seq"]) for row in ordered]
    occurrences = {}
    record_ids = []
    for row in ordered:
        sequence_hash = common.sequence_hash(row["seq"])
        occurrence = occurrences.get(sequence_hash, 0)
        occurrences[sequence_hash] = occurrence + 1
        record_ids.append("%s:%04d" % (sequence_hash, occurrence))
    if len(record_ids) != len(set(record_ids)):
        raise ValueError("record-level SSI identities are not unique")
    return ordered, record_ids


def make_token_manifest(tokenizer, rows, task, split, seed, token_cap,
                        split_evidence, max_len=MAX_LEN, batch_size=32):
    _validate_task_split(task, split)
    if isinstance(token_cap, bool) or not isinstance(token_cap, int) or token_cap <= 0:
        raise ValueError("token_cap must be a positive integer")
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")
    ordered, sequence_ids = ordered_record_ids(rows, task, split)
    if not (task == "ssi" and split == "random") \
            and len(sequence_ids) != len(set(sequence_ids)):
        raise ValueError("test contains duplicate sequence hashes")
    records = []
    for start in range(0, len(ordered), batch_size):
        batch = ordered[start:start + batch_size]
        enc = encode_seqs(tokenizer, [row["seq"] for row in batch],
                          "cpu", max_len)
        labels, mask = align_base_labels(
            tokenizer, enc, batch, max_len,
            allow_short_labels=(task == "degradation"))
        for offset in range(len(batch)):
            token_positions = mask[offset].nonzero().flatten().cpu().numpy()
            valid_labels = labels[offset][mask[offset]].float().cpu().numpy()
            if not np.isfinite(valid_labels).all():
                raise FloatingPointError("non-finite label in test manifest")
            sequence_id = sequence_ids[start + offset]
            for base_position, (token_position, label) in enumerate(
                    zip(token_positions, valid_labels)):
                records.append({
                    "seq_index": start + offset,
                    "sequence_id": sequence_id,
                    "base_position": int(base_position),
                    "token_position": int(token_position),
                    "token_id": _token_id(sequence_id, base_position),
                    "y_true": float(label),
                })
    if not records:
        raise ValueError("full test has no valid per-base labels")
    records.sort(key=lambda record: record["token_id"])
    full_hash = compute_full_test_hash(
        task, max_len, sequence_ids,
        [record["token_id"] for record in records],
        [record["sequence_id"] for record in records],
        [record["base_position"] for record in records],
        [record["token_position"] for record in records],
        [record["y_true"] for record in records])
    selected = [dict(record) for record in records[:min(token_cap, len(records))]]
    manifest = {
        "artifact_type": "regbase_continuous_token_test_manifest",
        "model": MODEL,
        "task": task,
        "split": split,
        "seed": int(seed),
        "max_len": int(max_len),
        "selection": "sequence_hash_token_id_lexicographic_before_prediction",
        "label_sampling": "continuous_unbinned_unstratified",
        "token_cap": int(token_cap),
        "n_full_sequences": len(ordered),
        "n_full_tokens": len(records),
        "n_sample_tokens": len(selected),
        "n": len(selected),
        "token_ids": [record["token_id"] for record in selected],
        "records": selected,
        "full_test_sha256": full_hash,
        "split_evidence": split_evidence,
        "metric_scope": "full_test_global_pcc_and_sequence_equal_weight_mcrmse",
    }
    if task == "ssi" and split == "random":
        manifest.update({
            "record_ids": sequence_ids,
            "n_full_records": len(ordered),
            "n_unique_sequences": len({common.sequence_hash(row["seq"]) for row in ordered}),
            "record_identity_scope": "sequence_hash_occurrence_within_official_test",
            "metric_scope": "full_test_global_pcc_and_record_equal_weight_mcrmse",
        })
    manifest["manifest_sha256"] = manifest_digest(manifest)
    return ordered, manifest, selected


def _finite_array(name, values):
    values = np.asarray(values)
    if not np.isfinite(values).all():
        raise FloatingPointError(name + " contains non-finite values")
    return values


def extract(backbone, head, tokenizer, rows, device, task, manifest, selected,
            batch_size=32, max_len=MAX_LEN):
    if task != manifest["task"] or max_len != manifest["max_len"]:
        raise ValueError("extraction task/max_len differs from manifest")
    if len(rows) != manifest["n_full_sequences"]:
        raise ValueError("extraction rows differ from manifest")
    if task == "ssi" and manifest["split"] == "random":
        record_ids = manifest["record_ids"]
    else:
        record_ids = [common.sequence_hash(row["seq"]) for row in rows]
    if len(record_ids) != len(rows):
        raise ValueError("record identities differ from extraction rows")
    backbone.eval()
    head.eval()
    selected_by_sequence = {}
    for record in selected:
        selected_by_sequence.setdefault(record["seq_index"], []).append(record)
    full = {key: [] for key in ("token_ids", "sequence_ids", "base_positions",
                                "token_positions", "y_true", "prediction")}
    sample = {key: [] for key in ("token_ids", "sequence_ids", "base_positions",
                                  "token_positions", "y_true", "prediction")}
    sample_embeddings = []
    with torch.no_grad():
        for start in range(0, len(rows), batch_size):
            batch = rows[start:start + batch_size]
            enc = encode_seqs(tokenizer, [row["seq"] for row in batch],
                              device, max_len)
            labels, mask = align_base_labels(
                tokenizer, enc, batch, max_len,
                allow_short_labels=(task == "degradation"))
            hidden = backbone(**enc).last_hidden_state
            pad = enc.get("attention_mask")
            pad = None if pad is None else pad == 0
            prediction = head(hidden, pad).squeeze(-1)
            for offset, row in enumerate(batch):
                seq_index = start + offset
                sequence_id = record_ids[seq_index]
                valid_token_positions = mask[offset].nonzero().flatten()
                hidden_valid = hidden[offset][mask[offset]]
                prediction_valid = prediction[offset][mask[offset]]
                labels_valid = labels[offset][mask[offset]]
                token_positions = valid_token_positions.detach().cpu().numpy()
                p = prediction_valid.float().detach().cpu().numpy()
                y = labels_valid.float().detach().cpu().numpy()
                n_valid = len(y)
                full["token_ids"].extend(
                    _token_id(sequence_id, base) for base in range(n_valid))
                full["sequence_ids"].extend([sequence_id] * n_valid)
                full["base_positions"].extend(range(n_valid))
                full["token_positions"].extend(int(value) for value in token_positions)
                full["y_true"].extend(y.tolist())
                full["prediction"].extend(p.tolist())
                for record in selected_by_sequence.get(seq_index, []):
                    base = record["base_position"]
                    if base >= n_valid or int(token_positions[base]) != \
                            record["token_position"]:
                        raise ValueError("selected token position differs from B20 mask")
                    token_id = _token_id(sequence_id, base)
                    if (record["sequence_id"] != sequence_id
                            or record["token_id"] != token_id
                            or record["y_true"] != float(y[base])):
                        raise ValueError("selected token identity/label differs from B20")
                    sample["token_ids"].append(token_id)
                    sample["sequence_ids"].append(sequence_id)
                    sample["base_positions"].append(base)
                    sample["token_positions"].append(int(token_positions[base]))
                    sample["y_true"].append(float(y[base]))
                    sample["prediction"].append(float(p[base]))
                    sample_embeddings.append(
                        hidden_valid[base].float().detach().cpu().numpy())
    for arrays in (full, sample):
        for key in ("token_ids", "sequence_ids"):
            arrays[key] = np.asarray(arrays[key])
        for key in ("base_positions", "token_positions"):
            arrays[key] = np.asarray(arrays[key], dtype=np.int64)
        for key in ("y_true", "prediction"):
            arrays[key] = np.asarray(arrays[key], dtype=np.float32)
        arrays["residual"] = arrays["prediction"] - arrays["y_true"]
    if not len(full["y_true"]) or not sample_embeddings:
        raise ValueError("full/sample token extraction is empty")
    sample["token_embedding"] = np.stack(sample_embeddings).astype(np.float32)
    for name, arrays in (("full", full), ("sample", sample)):
        for key in ("y_true", "prediction", "residual"):
            _finite_array(name + " " + key, arrays[key])
    _finite_array("sample token_embedding", sample["token_embedding"])
    full_hash = compute_full_test_hash(
        task, max_len, record_ids, full["token_ids"], full["sequence_ids"],
        full["base_positions"], full["token_positions"], full["y_true"])
    if full_hash != manifest["full_test_sha256"]:
        raise ValueError("full-test hash changed during prediction")
    if len(full["y_true"]) != manifest["n_full_tokens"]:
        raise ValueError("full-test token count differs from manifest")
    if sample["token_ids"].tolist() != manifest["token_ids"]:
        raise ValueError("sample token order differs from manifest")
    if len(sample["y_true"]) != manifest["n_sample_tokens"]:
        raise ValueError("sample token count differs from manifest")
    return full, sample


def fresh_reference_head(d_model, device):
    torch.manual_seed(PRE_HEAD_SEED)
    return TokenHead(d_model, 1, hidden=32).to(device)


def _artifact_metadata(manifest):
    return {
        "task": np.asarray(manifest["task"]),
        "split": np.asarray(manifest["split"]),
        "seed": np.asarray(manifest["seed"], dtype=np.int64),
        "n_full_tokens": np.asarray(manifest["n_full_tokens"], dtype=np.int64),
        "n_sample_tokens": np.asarray(manifest["n_sample_tokens"], dtype=np.int64),
        "full_test_sha256": np.asarray(manifest["full_test_sha256"]),
        "test_manifest_sha256": np.asarray(manifest["manifest_sha256"]),
        "split_evidence": np.asarray(json.dumps(
            manifest["split_evidence"], sort_keys=True, allow_nan=False)),
        "selection": np.asarray(manifest["selection"]),
    }


def _scalar(arrays, key):
    if key not in arrays or np.asarray(arrays[key]).shape != ():
        raise ValueError("state is missing scalar alignment field: " + key)
    return np.asarray(arrays[key]).item()


def validate_state_arrays(strategy, arrays, manifest_hash):
    required = ("token_ids", "sequence_ids", "base_positions", "token_positions",
                "y_true", "prediction", "residual", "token_embedding")
    if any(key not in arrays for key in required):
        raise ValueError("state %s is missing token arrays" % strategy)
    n = len(arrays["token_ids"])
    if n == 0:
        raise ValueError("state has no sample tokens")
    for key in required[:-1]:
        if np.asarray(arrays[key]).ndim != 1 or len(arrays[key]) != n:
            raise ValueError("state token arrays are not aligned: " + key)
    embedding = np.asarray(arrays["token_embedding"])
    if embedding.ndim != 2 or embedding.shape[0] != n:
        raise ValueError("state token_embedding shape is invalid")
    for key in ("base_positions", "token_positions"):
        values = np.asarray(arrays[key])
        if not np.issubdtype(values.dtype, np.integer) or (values < 0).any():
            raise ValueError("state positions must be non-negative integers")
    for key in ("y_true", "prediction", "residual"):
        _finite_array(strategy + " " + key, arrays[key])
    _finite_array(strategy + " token_embedding", embedding)
    if not np.array_equal(np.asarray(arrays["residual"]),
                          np.asarray(arrays["prediction"]) - np.asarray(arrays["y_true"])):
        raise ValueError("state residual is not prediction minus y_true")
    expected_ids = [_token_id(sequence_id, base) for sequence_id, base in zip(
        arrays["sequence_ids"], arrays["base_positions"])]
    if arrays["token_ids"].tolist() != expected_ids:
        raise ValueError("state token_id does not match sequence/base position")
    metadata = {key: _scalar(arrays, key) for key in (
        "task", "split", "seed", "n_full_tokens", "n_sample_tokens",
        "full_test_sha256", "test_manifest_sha256", "split_evidence")}
    if metadata["task"] not in TASKS or metadata["split"] not in ("random", "family"):
        raise ValueError("state has invalid task/split metadata")
    if isinstance(metadata["seed"], bool) or int(metadata["seed"]) != metadata["seed"]:
        raise ValueError("state seed is not an integer")
    if int(metadata["n_sample_tokens"]) != n:
        raise ValueError("state sample token count is inconsistent")
    if int(metadata["n_full_tokens"]) < n:
        raise ValueError("state full token count is smaller than sample")
    if metadata["test_manifest_sha256"] != manifest_hash:
        raise ValueError("state arrays and diagnostic manifest hash differ")
    return metadata


def validate_state_proof(strategy, diagnostic, task, split, seed):
    expected = {"model": MODEL, "task": task, "split": split, "seed": seed,
                "strategy": strategy}
    for key, value in expected.items():
        if diagnostic.get(key) != value:
            raise ValueError("diagnostic identity mismatch: %s (%s)" % (key, strategy))
    if strategy == "pre":
        if diagnostic.get("reference_head_seed") != PRE_HEAD_SEED:
            raise ValueError("pre state lacks the seed-201 reference-head proof")
        if diagnostic.get("source_run_id") is not None:
            raise ValueError("pre state must not reference a post checkpoint")
        return
    checkpoint = diagnostic.get("checkpoint") or {}
    if (diagnostic.get("full_test_metric_match") is not True
            or checkpoint.get("restored_tensor_match") is not True
            or checkpoint.get("checkpoint_proof") != "ok"
            or diagnostic.get("source_proof", {}).get("state") != "complete"):
        raise ValueError("post diagnostic lacks full-test/checkpoint/registry proof: " + strategy)
    expected_rid = source_run_id(task, strategy, split, seed)
    if diagnostic.get("source_run_id") != expected_rid:
        raise ValueError("post diagnostic source RID is not task isolated")
    if task == "ssi" and split == "random":
        if (diagnostic.get("source_data_evidence_present") is not True
                or diagnostic.get("source_data_evidence_note") !=
                "matched_reconstructed_sequence_grouped_split"):
            raise ValueError("SSI random post lacks matched sequence-grouped data evidence")
        if (diagnostic.get("n_full_test_records") != diagnostic.get("n_test")
                or diagnostic.get("record_identity_scope") !=
                "sequence_hash_occurrence_within_official_test"):
            raise ValueError("SSI random post lacks record-level identity proof")


def load_aligned_states(task, split, seed, suffix="_ckpt_v1", artifact_root=None):
    _validate_task_split(task, split)
    root = Path(ARTIFACT_ROOT if artifact_root is None else artifact_root)
    ready = []
    for strategy in STATES:
        out_dir = root / diagnostic_run_id(task, strategy, split, seed, suffix)
        diagnostic_path = out_dir / "diagnostic.json"
        embedding_path = out_dir / "embeddings.npz"
        if not diagnostic_path.is_file() or not embedding_path.is_file():
            continue
        diagnostic = json.loads(diagnostic_path.read_text())
        if diagnostic.get("status") != "diagnostic":
            continue
        validate_state_proof(strategy, diagnostic, task, split, seed)
        manifest_path = out_dir / "test_manifest.json"
        if not manifest_path.is_file():
            raise ValueError("diagnostic is missing its test manifest")
        manifest = json.loads(manifest_path.read_text())
        if (manifest.get("task") != task or manifest.get("split") != split
                or manifest.get("seed") != seed):
            raise ValueError("manifest identity differs from requested state")
        manifest_hash = manifest.get("manifest_sha256")
        if (manifest_hash != manifest_digest(manifest)
                or diagnostic.get("test_manifest_sha256") != manifest_hash):
            raise ValueError("manifest hash proof is invalid")
        with np.load(embedding_path, allow_pickle=False) as data:
            arrays = {key: data[key].copy() for key in data.files}
        metadata = validate_state_arrays(strategy, arrays, manifest_hash)
        split_evidence = json.dumps(
            manifest["split_evidence"], sort_keys=True, allow_nan=False)
        if (metadata["full_test_sha256"] != manifest["full_test_sha256"]
                or int(metadata["n_full_tokens"]) != manifest["n_full_tokens"]
                or int(metadata["n_sample_tokens"]) != manifest["n_sample_tokens"]
                or metadata["split_evidence"] != split_evidence):
            raise ValueError("embedding metadata differs from the saved token manifest")
        records = manifest["records"]
        expected = {
            "token_ids": [record["token_id"] for record in records],
            "sequence_ids": [record["sequence_id"] for record in records],
            "base_positions": [record["base_position"] for record in records],
            "token_positions": [record["token_position"] for record in records],
            "y_true": [record["y_true"] for record in records],
        }
        for key, values in expected.items():
            if not np.array_equal(arrays[key], np.asarray(values)):
                raise ValueError("embedding %s differs from the saved token manifest" % key)
        source_reference = diagnostic["source_run_id"] or PRE_SOURCE
        ready.append((strategy, arrays, manifest_hash, source_reference,
                      diagnostic["metrics_full"], diagnostic))
    return ready


def aligned_regression(states, output_path, task=None, perplexity=30,
                       random_state=17):
    if len(states) != 3 or {item[0] for item in states} != set(STATES):
        raise ValueError("aligned regression requires pre, lora and full")
    if perplexity <= 0:
        raise ValueError("perplexity must be positive")
    states = sorted(states, key=lambda item: STATES.index(item[0]))
    reference = states[0][1]
    reference_metadata = validate_state_arrays(states[0][0], reference, states[0][2])
    aligned_task = task or reference_metadata["task"]
    _validate_task_split(aligned_task, reference_metadata["split"])
    split = reference_metadata["split"]
    seed = int(reference_metadata["seed"])
    manifest_hashes = {item[2] for item in states}
    if len(manifest_hashes) != 1:
        raise ValueError("three states do not share one test manifest")
    for strategy, arrays, manifest_hash, source, metrics, diagnostic in states:
        metadata = validate_state_arrays(strategy, arrays, manifest_hash)
        validate_state_proof(strategy, diagnostic, aligned_task, split, seed)
        expected_source = (PRE_SOURCE if strategy == "pre" else
                           source_run_id(aligned_task, strategy, split, seed))
        if source != expected_source:
            raise ValueError("state source RID is not aligned with task/split/seed")
        if any(not isinstance(metrics.get(key), (int, float))
               or isinstance(metrics.get(key), bool)
               or not math.isfinite(metrics[key]) for key in ("pcc", "mcrmse")):
            raise FloatingPointError("non-finite or missing full-test metrics")
        for key in ("task", "split", "seed", "n_full_tokens",
                    "full_test_sha256", "split_evidence"):
            if metadata[key] != reference_metadata[key]:
                raise ValueError("three-state metadata mismatch: " + key)
        if metadata["task"] != aligned_task:
            raise ValueError("cross-task alignment is forbidden")
        for key in ("token_ids", "sequence_ids", "base_positions", "token_positions"):
            if not np.array_equal(reference[key], arrays[key]):
                raise ValueError("three-state token/position mismatch: " + key)
        if not np.array_equal(reference["y_true"], arrays["y_true"]):
            raise ValueError("three-state continuous labels differ")
        if (arrays["token_embedding"].shape[1]
                != reference["token_embedding"].shape[1]):
            raise ValueError("three-state embedding widths differ")
    token = np.concatenate([item[1]["token_embedding"] for item in states]).astype(
        np.float64)
    n = len(reference["token_ids"])
    effective_perplexity = min(perplexity, max(1, (len(token) - 1) // 3))
    from sklearn.manifold import TSNE
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
        base_positions=np.tile(reference["base_positions"], 3),
        token_positions=np.tile(reference["token_positions"], 3),
        state=np.concatenate([np.full(n, item[0]) for item in states]),
        y_true=np.tile(reference["y_true"], 3),
        prediction=np.concatenate([item[1]["prediction"] for item in states]),
        residual=np.concatenate([item[1]["residual"] for item in states]),
        task=np.asarray(aligned_task),
        split=np.asarray(split),
        seed=np.asarray(seed, dtype=np.int64),
        source_run_ids=np.asarray([item[3] for item in states]),
        full_pcc=np.asarray([item[4]["pcc"] for item in states], dtype=np.float64),
        full_mcrmse=np.asarray([item[4]["mcrmse"] for item in states],
                               dtype=np.float64),
        n_full_tokens=np.asarray(reference_metadata["n_full_tokens"], dtype=np.int64),
        n_sample_tokens=np.asarray(n, dtype=np.int64),
        full_test_sha256=np.asarray(reference_metadata["full_test_sha256"]),
        test_manifest_sha256=np.asarray(states[0][2]),
        split_evidence=np.asarray(reference_metadata["split_evidence"]),
        tsne_perplexity=np.asarray(effective_perplexity),
        tsne_random_state=np.asarray(random_state),
        color_mode=np.asarray("y_true_continuous"),
        interpretation=np.asarray("descriptive_only_no_classification_silhouette"),
    )
    return {
        "path": str(output_path), "task": aligned_task, "split": split, "seed": seed,
        "n_per_state": n, "n_total": len(token),
        "n_full_tokens": int(reference_metadata["n_full_tokens"]),
        "perplexity": effective_perplexity, "random_state": random_state,
        "color_mode": "y_true_continuous",
        "classification_silhouette": None,
        "interpretation": "descriptive_only_no_classification_silhouette",
    }


def validate_args(args):
    if args.token_cap <= 0 or args.batch_size <= 0:
        raise ValueError("token-cap and batch-size must be positive integers")
    if args.wait_free_gb < 0 or args.memory_poll_s <= 0:
        raise ValueError("wait-free-gb must be nonnegative and memory-poll-s positive")


def run(args):
    validate_args(args)
    _validate_task_split(args.task, args.split)
    device = common.require_cuda(args.device)
    memory_evidence = common.wait_for_cuda_memory(
        device, args.wait_free_gb, args.memory_poll_s)
    parts, split_evidence = load_task_parts(
        args.task, args.split, args.seed, n_train=N_TRAIN, data_root=DATA_ROOT)
    source_dir = source_result = source_row = source_proof = None
    if args.strategy != "pre":
        source_dir, source_result, source_row = load_source(
            args.task, args.strategy, args.split, args.seed, parts)
        source_proof = common.require_complete_source(
            source_result["run_id"], source_row)
    out_dir = ARTIFACT_ROOT / diagnostic_run_id(
        args.task, args.strategy, args.split, args.seed)
    out_dir.mkdir(parents=True, exist_ok=True)
    if any((out_dir / name).exists() for name in
           ("diagnostic.json", "predictions.npz", "embeddings.npz")):
        raise FileExistsError("refusing to overwrite existing diagnostic: %s" % out_dir)
    common.write_json(out_dir / "job.json", {
        "run_id": out_dir.name, "status": "running", "task": args.task,
        "split": args.split, "seed": args.seed, "strategy": args.strategy,
        "out_dir": str(out_dir), "git_sha": common.git_sha(),
        "memory_evidence": memory_evidence,
    })
    aligned_cleanup_path = None
    try:
        from rnafteval.models import load_model
        spec, tokenizer, backbone = load_model(MODEL, device)
        with torch.no_grad():
            probe = encode_seqs(tokenizer, [parts["train"][0]["seq"]],
                                device, MAX_LEN)
            d_model = backbone(**probe).last_hidden_state.shape[-1]
        ordered, manifest, selected = make_token_manifest(
            tokenizer, parts["test"], args.task, args.split, args.seed,
            args.token_cap, split_evidence, max_len=MAX_LEN,
            batch_size=args.batch_size)
        common.write_json(out_dir / "test_manifest.json", manifest)
        checkpoint_evidence = None
        if args.strategy == "pre":
            backbone.eval()
            head = fresh_reference_head(d_model, device)
        else:
            backbone, _n_trainable = apply_strategy(
                backbone, args.strategy, lora_rank=8)
            head = TokenHead(d_model, 1, hidden=32).to(device)
            checkpoint_evidence = dict(restore_post(
                backbone, head, source_dir, source_result, source_row, device))
            checkpoint_evidence["restored_before_full_test_recomputation"] = True
        head.eval()
        runtime = vp.runtime_evidence(tokenizer, device)
        full, sample = extract(
            backbone, head, tokenizer, ordered, device, args.task, manifest,
            selected, batch_size=args.batch_size, max_len=MAX_LEN)
        metrics = regression_metrics(
            full["y_true"], full["prediction"], full["sequence_ids"])
        metric_match = None
        if source_result is not None:
            metric_match = reconcile_source_metrics(metrics, source_result)
        metadata = _artifact_metadata(manifest)
        full.update(metadata)
        sample.update(metadata)
        save_npz(out_dir / "predictions.npz", **full)
        save_npz(out_dir / "embeddings.npz", **sample)
        source_evidence = source_data_evidence(source_result, split_evidence)
        diagnostic = {
            "artifact_type": "regbase_diagnostic",
            "status": "diagnostic",
            "model": MODEL,
            "task": args.task,
            "model_repo": spec.repo,
            "strategy": args.strategy,
            "split": args.split,
            "seed": args.seed,
            "max_len": MAX_LEN,
            "canonical_n_train": N_TRAIN,
            "n_train": len(parts["train"]),
            "n_val": len(parts["val"]),
            "n_test": len(parts["test"]),
            "n_full_test_sequences": len(ordered),
            "n_full_test_tokens": len(full["y_true"]),
            "n_sample_tokens": len(sample["y_true"]),
            "metrics_full": metrics,
            "metric_definition": {
                "pcc": "global_corrcoef_over_concatenated_valid_tokens",
                "mcrmse": ("sqrt_mean_of_per_record_mse_equal_record_weight"
                           if args.task == "ssi" and args.split == "random" else
                           "sqrt_mean_of_per_sequence_mse_equal_sequence_weight"),
            },
            "source_run_id": None if source_result is None else source_result["run_id"],
            "source_metrics": None if source_result is None else {
                "pcc": source_result["value"], "mcrmse": source_result["mcrmse"]},
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
            "prediction_head": ("fresh_reference_head_seed_201_not_zero_shot"
                                if args.strategy == "pre" else "restored_bestval_head"),
            "reference_head_seed": PRE_HEAD_SEED if args.strategy == "pre" else None,
            "interpretation": "descriptive_only_no_mechanism_conclusion",
        }
        if args.task == "ssi" and args.split == "random":
            diagnostic.update({
                "n_full_test_records": len(ordered),
                "n_unique_test_sequences": len({
                    common.sequence_hash(row["seq"]) for row in ordered}),
                "record_identity_scope": manifest["record_identity_scope"],
            })
        diagnostic.update(source_evidence)
        ready = load_aligned_states(args.task, args.split, args.seed)
        source_reference = PRE_SOURCE if source_result is None else source_result["run_id"]
        ready.append((args.strategy, sample, manifest["manifest_sha256"],
                      source_reference, metrics, diagnostic))
        diagnostic["aligned_tsne"] = None
        diagnostic["available_states"] = [item[0] for item in ready]
        if len(ready) == 3:
            aligned_path = ARTIFACT_ROOT / (
                "mech_rinalmomicro_%s_aligned_%s_s%d_ckpt_v1.npz" % (
                    args.task, args.split, args.seed))
            if aligned_path.exists():
                raise FileExistsError("refusing to overwrite aligned diagnostic: %s" % aligned_path)
            aligned_cleanup_path = aligned_path
            diagnostic["aligned_tsne"] = aligned_regression(
                ready, aligned_path, task=args.task)
        common.write_json(out_dir / "diagnostic.json", diagnostic)
        common.write_json(out_dir / "job.json", {
            "run_id": out_dir.name, "status": "diagnostic", "out_dir": str(out_dir),
            "diagnostic": str(out_dir / "diagnostic.json"),
            "git_sha": diagnostic["git_sha"],
            "full_test_metric_match": metric_match,
        })
        print(json.dumps({
            "run_id": out_dir.name, "status": "diagnostic", "task": args.task,
            "n_full_test_tokens": len(full["y_true"]),
            "n_sample_tokens": len(sample["y_true"]), "metrics_full": metrics,
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
    parser.add_argument("--task", choices=TASKS, required=True)
    parser.add_argument("--split", choices=("random", "family"), required=True)
    parser.add_argument("--strategy", choices=STATES, required=True)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--device", type=int, required=True)
    parser.add_argument("--token-cap", type=int, required=True)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--wait-free-gb", type=float, default=3.0)
    parser.add_argument("--memory-poll-s", type=float, default=60.0)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        return run(args)
    except Exception as error:
        print(json.dumps({"event": "REGBASE_MECHANISM_ABORT",
                          "error": "%s: %s" % (type(error).__name__, error)}),
              flush=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
