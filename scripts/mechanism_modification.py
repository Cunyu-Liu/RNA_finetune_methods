#!/usr/bin/env python3
"""复用 best-val checkpoint 的 modification 多标签机制诊断。"""
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
from rnafteval.finetune_base import batches, encode_seqs
from rnafteval.splits import prepare_convergence_splits
from rnafteval.strategies import apply_strategy, make_head
from rnafteval.tasks import modification as mod_task

MODEL = "RiNALMo-micro"
TASK = "modification"
STATES = ("pre", "lora", "full")
MAX_LEN = 128
N_LABELS = 12
M6A_INDEX = 7
DATA_ROOT = Path(os.environ.get("RNAFT_DATA_ROOT", "/root/rna-ft-eval/data"))
ARTIFACT_ROOT = Path(os.environ.get(
    "RNAFT_MECHANISM_MOD_ROOT", str(common.TEAMS_ROOT / "artifacts" / "mechanism_modification")))


def source_run_id(strategy, split, seed):
    if strategy == "lora":
        extra = "_bestval_v1_seqmlfix"
    elif strategy == "full":
        extra = "_lr1e-05_bestval_v1_seqmlfix"
    else:
        raise ValueError("只有 post LoRA/full 有源 checkpoint")
    return ledger.run_id(MODEL, TASK, strategy, seed, split, extra)


def load_test_rows(split, seed, n_train=20000):
    if split == "family":
        import pyarrow.parquet as pq
        path = DATA_ROOT / "family_splits" / "modification.parquet"
        if not path.is_file():
            raise FileNotFoundError(path)
        table = pq.read_table(path).to_pydict()
        by_side = {}
        for seq, labels, side, cluster in zip(
                table["seq"], table["labels"], table["split"], table["cluster_id"]):
            if side in ("train", "val", "test"):
                by_side.setdefault(side, []).append({
                    "seq": seq,
                    "labels": [int(x) for x in str(labels).split()],
                    "subset": "family_" + side,
                    "cluster": cluster,
                })
        train, val, test = by_side["train"], by_side["val"], by_side["test"]
    elif split == "random":
        parts = mod_task.load_official_split(str(
            DATA_ROOT / "beacon_raw" / "modification" / "data"))
        train, val, test = parts["train"], parts["validation"], parts["test"]
    else:
        raise ValueError(split)
    train, val, test, evidence = prepare_convergence_splits(
        train, val, test, n_train=n_train, sample_seed=seed,
        family=split == "family",
        validation_source="official_validation" if split == "random" else "family_validation",
        evidence_path="", protocol="bestval_v1")
    return test, evidence


def sequence_gc(sequence):
    sequence = sequence.upper()
    return (sequence.count("G") + sequence.count("C")) / max(1, len(sequence))


def make_manifest(rows, split, seed, n_samples):
    if n_samples <= 0:
        raise ValueError("n_samples 必须为正数")
    ordered = sorted(rows, key=lambda row: common.sequence_hash(row["seq"]))
    ids = [common.sequence_hash(row["seq"]) for row in ordered]
    if len(ids) != len(set(ids)):
        raise ValueError("test 中仍有重复 sequence hash")
    if any(len(row["labels"]) != N_LABELS for row in ordered):
        raise ValueError("modification 每行必须有 12 个标签")
    full_payload = [[sample_id, list(map(int, row["labels"]))]
                    for sample_id, row in zip(ids, ordered)]
    full_hash = hashlib.sha256(json.dumps(
        full_payload, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
    selected = ordered[:min(n_samples, len(ordered))]
    records = [{
        "sample_id": common.sequence_hash(row["seq"]),
        "labels": list(map(int, row["labels"])),
        "m6a_label": int(row["labels"][M6A_INDEX]),
        "cluster": row.get("cluster"),
        "length": len(row["seq"]),
        "gc": sequence_gc(row["seq"]),
    } for row in selected]
    manifest = {
        "artifact_type": "modification_test_manifest",
        "model": MODEL,
        "task": TASK,
        "split": split,
        "seed": seed,
        "selection": "sequence_hash_ascending_before_prediction",
        "n_full_test": len(ordered),
        "n": len(selected),
        "sample_ids": [record["sample_id"] for record in records],
        "records": records,
        "full_test_sha256": full_hash,
        "label_semantics": "BEACON sequence-level multi-label; m6A index 7",
    }
    payload = json.dumps(manifest, sort_keys=True, ensure_ascii=False).encode()
    manifest["manifest_sha256"] = hashlib.sha256(payload).hexdigest()
    return ordered, manifest


def modification_metrics(y_true, probabilities):
    from sklearn.metrics import roc_auc_score
    y_true = np.asarray(y_true)
    probabilities = np.asarray(probabilities)
    if y_true.shape != probabilities.shape or y_true.ndim != 2 \
            or y_true.shape[1] != N_LABELS:
        raise ValueError("labels/probabilities 必须为 [N,12]")
    aucs = np.full(N_LABELS, np.nan, dtype=np.float64)
    valid = np.zeros(N_LABELS, dtype=bool)
    for index in range(N_LABELS):
        if len(np.unique(y_true[:, index])) > 1:
            valid[index] = True
            aucs[index] = roc_auc_score(y_true[:, index], probabilities[:, index])
    source_compatible = np.where(valid, aucs, 0.5)
    positive = y_true.sum(axis=0).astype(int)
    return {
        "m6a_auc": None if not valid[M6A_INDEX] else float(aucs[M6A_INDEX]),
        "mean_auc": float(source_compatible.mean()),
        "mean_auc_valid": None if not valid.any() else float(np.nanmean(aucs)),
        "aucs_by_modification": [None if np.isnan(value) else float(value) for value in aucs],
        "aucs_source_compatible": source_compatible.tolist(),
        "valid_label_mask": valid.tolist(),
        "positive_support": positive.tolist(),
        "negative_support": (len(y_true) - positive).tolist(),
        "m6a_index": M6A_INDEX,
    }


def extract(backbone, head, tokenizer, rows, device, n_samples, batch_size=64):
    backbone.eval()
    head.eval()
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
            probabilities = torch.sigmoid(logits)
            full_ids.extend(common.sequence_hash(row["seq"]) for row in batch)
            full_labels.extend(row["labels"] for row in batch)
            full_logits.append(logits.detach().cpu().numpy())
            full_probabilities.append(probabilities.detach().cpu().numpy())
            keep = min(len(batch), max(0, n_samples - start))
            if keep:
                sample_cls.append(hidden[:keep, 0].detach().cpu().numpy())
                sample_head.append(pooled[:keep].detach().cpu().numpy())
    labels = np.asarray(full_labels, dtype=np.float32)
    logits = np.concatenate(full_logits).astype(np.float32)
    probabilities = np.concatenate(full_probabilities).astype(np.float32)
    if labels.shape != logits.shape or labels.shape[1] != N_LABELS:
        raise ValueError("完整 test 多标签形状不一致")
    if not np.isfinite(logits).all() or not np.isfinite(probabilities).all():
        raise ValueError("完整 test logits/probabilities 非有限值")
    n = min(n_samples, len(rows))
    sample = {
        "sample_ids": np.asarray(full_ids[:n]),
        "labels": labels[:n],
        "logits": logits[:n],
        "probabilities": probabilities[:n],
        "cls": np.concatenate(sample_cls).astype(np.float32),
        "head_embedding": np.concatenate(sample_head).astype(np.float32),
    }
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
            f"mech_rinalmomicro_modification_{strategy}_{split}_s{seed}{suffix}")
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


def aligned_modification(states, output_path, perplexity=30, random_state=17):
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
            raise ValueError("三状态 12 维标签不一致")
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
        labels=np.tile(reference["labels"], (3, 1)),
        m6a_label=np.tile(reference["labels"][:, M6A_INDEX], 3),
        probabilities=np.concatenate([item[1]["probabilities"] for item in states]),
        logits=np.concatenate([item[1]["logits"] for item in states]),
        split=np.asarray(reference.get("split", "unknown")),
        seed=np.asarray(reference.get("seed", -1)),
        source_run_ids=np.asarray([item[3] for item in states]),
        full_m6a_auc=np.asarray([item[4]["m6a_auc"] for item in states], dtype=np.float64),
        full_mean_auc=np.asarray([item[4]["mean_auc"] for item in states], dtype=np.float64),
        test_manifest_sha256=np.asarray(states[0][2]),
        tsne_perplexity=np.asarray(effective_perplexity),
        tsne_random_state=np.asarray(random_state),
        color_mode=np.asarray("m6a_label_index_7"),
        label_semantics=np.asarray("BEACON sequence-level multi-label; m6A index 7"),
        interpretation=np.asarray("descriptive_multilabel_m6a_view_not_single_label_task"),
    )
    return {
        "path": str(output_path), "n_per_state": n, "n_total": len(cls),
        "perplexity": effective_perplexity, "random_state": random_state,
        "color_mode": "m6a_label_index_7",
        "classification_silhouette": None,
        "interpretation": "descriptive_multilabel_m6a_view_not_single_label_task",
    }


def run(args):
    if args.n_samples <= 0 or args.batch_size <= 0:
        raise ValueError("n_samples 和 batch_size 必须为正数")
    if args.wait_free_gb < 0 or args.memory_poll_s <= 0:
        raise ValueError("wait_free_gb 不能为负，memory_poll_s 必须为正数")
    device = common.require_cuda(args.device)
    memory_evidence = common.wait_for_cuda_memory(
        device, args.wait_free_gb, args.memory_poll_s)
    rows, split_evidence = load_test_rows(args.split, args.seed)
    ordered, manifest = make_manifest(rows, args.split, args.seed, args.n_samples)
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
        if source_result["n_test"] != len(ordered):
            raise ValueError("源 result n_test 与重建 test 不一致")
        if source_result.get("data_evidence") != split_evidence:
            raise ValueError("源 result 与重建 split evidence 不一致")
    out_dir = ARTIFACT_ROOT / (
        f"mech_rinalmomicro_modification_{args.strategy}_{args.split}_s{args.seed}_ckpt_v1")
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
            head = make_head("per-seq", d_model, N_LABELS).to(device)
        else:
            backbone, _n_trainable = apply_strategy(backbone, args.strategy, lora_rank=8)
            head = make_head("per-seq", d_model, N_LABELS).to(device)
            checkpoint_evidence = restore_post(
                backbone, head, source_dir, source_result, source_row, device)
        head.eval()
        runtime = vp.runtime_evidence(tokenizer, device)
        full, sample = extract(backbone, head, tokenizer, ordered, device,
                               args.n_samples, args.batch_size)
        metrics = modification_metrics(full["labels"], full["probabilities"])
        metric_match = None
        if source_result is not None:
            checks = [
                metrics["m6a_auc"] is not None and math.isclose(
                    metrics["m6a_auc"], source_result["value"], rel_tol=2e-5, abs_tol=2e-6),
                math.isclose(metrics["mean_auc"], source_result["metric_mean_auc"],
                             rel_tol=2e-5, abs_tol=2e-6),
                np.allclose(metrics["aucs_source_compatible"],
                            source_result["aucs_by_modification"], rtol=2e-5, atol=2e-6),
            ]
            metric_match = all(checks)
            if not metric_match:
                raise ValueError("完整 test 多标签 AUC 与源 result 不一致")
        sample["split"] = np.asarray(args.split)
        sample["seed"] = np.asarray(args.seed)
        save_npz(out_dir / "predictions.npz", **full)
        save_npz(out_dir / "embeddings.npz", **sample)
        diagnostic = {
            "artifact_type": "modification_diagnostic",
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
                "m6a_auc": source_result["value"],
                "mean_auc": source_result["metric_mean_auc"],
                "aucs_source_compatible": source_result["aucs_by_modification"],
            },
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
            "label_semantics": "BEACON sequence-level multi-label; m6A index 7",
            "interpretation": "descriptive_multilabel_m6a_view_not_single_label_task",
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
                f"mech_rinalmomicro_modification_aligned_{args.split}_s{args.seed}_ckpt_v1.npz")
            diagnostic["aligned_tsne"] = aligned_modification(ready, aligned_path)
        common.write_json(out_dir / "diagnostic.json", diagnostic)
        common.write_json(out_dir / "job.json", {
            "run_id": out_dir.name, "status": "diagnostic", "out_dir": str(out_dir),
            "diagnostic": str(out_dir / "diagnostic.json"), "git_sha": diagnostic["git_sha"],
            "full_test_metric_match": metric_match,
        })
        print(json.dumps({
            "run_id": out_dir.name, "status": "diagnostic",
            "n_full_test": len(ordered), "n_sample": len(sample["sample_ids"]),
            "m6a_auc": metrics["m6a_auc"], "mean_auc": metrics["mean_auc"],
            "mean_auc_valid": metrics["mean_auc_valid"],
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
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--wait-free-gb", type=float, default=3.0)
    parser.add_argument("--memory-poll-s", type=float, default=60.0)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        return run(args)
    except Exception as error:
        print(json.dumps({"event": "MODIFICATION_MECHANISM_ABORT",
                          "error": "%s: %s" % (type(error).__name__, error)}), flush=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
