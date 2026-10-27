#!/usr/bin/env python3
"""复用 best-val checkpoint 的 MRL 同样本机制诊断，禁止 CPU 正式运行。"""
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
from rnafteval import ledger, valplateau as vp
from rnafteval.finetune_mrl import batches, encode_seqs
from rnafteval.splits import prepare_convergence_splits
from rnafteval.strategies import apply_strategy, make_head
from rnafteval.tasks import mrl as mrl_task

MODEL = "RiNALMo-micro"
TASK = "mrl"
STATES = ("pre", "lora", "full")
MAX_LEN = 64
DATA_ROOT = Path(os.environ.get("RNAFT_DATA_ROOT", "/root/rna-ft-eval/data"))
ARTIFACT_ROOT = Path(os.environ.get(
    "RNAFT_MECHANISM_MRL_ROOT", str(common.TEAMS_ROOT / "artifacts" / "mechanism_mrl")))


def source_run_id(strategy, split, seed):
    if strategy == "lora":
        extra = "_bestval_v1"
    elif strategy == "full":
        extra = "_lr1e-05_bestval_v1"
    else:
        raise ValueError("只有 post LoRA/full 有源 checkpoint")
    return ledger.run_id(MODEL, TASK, strategy, seed, split, extra)


def load_test_rows(split, seed, n_train=20000):
    if split == "family":
        import pyarrow.parquet as pq
        path = DATA_ROOT / "family_splits" / "mrl.parquet"
        if not path.is_file():
            raise FileNotFoundError(path)
        table = pq.read_table(path).to_pydict()
        records = [{"seq": seq, "label": float(label), "cluster": cluster}
                   for seq, label, cluster in zip(
                       table["seq"], table["label"], table["cluster_id"])]
        train = [row for row, side in zip(records, table["split"]) if side == "train"]
        val = [row for row, side in zip(records, table["split"]) if side == "val"]
        test = [row for row, side in zip(records, table["split"]) if side == "test"]
    elif split == "random":
        parts = mrl_task.load_official_split(str(
            DATA_ROOT / "beacon_raw" / "mean-ribosome-loading" / "data"))
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
    full_payload = [[sample_id, float(row["label"])]
                    for sample_id, row in zip(ids, ordered)]
    full_hash = hashlib.sha256(json.dumps(
        full_payload, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
    selected = ordered[:min(n_samples, len(ordered))]
    records = [{
        "sample_id": common.sequence_hash(row["seq"]),
        "label": float(row["label"]),
        "cluster": row.get("cluster"),
        "length": len(row["seq"]),
        "gc": sequence_gc(row["seq"]),
    } for row in selected]
    manifest = {
        "artifact_type": "mrl_test_manifest",
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
    }
    payload = json.dumps(manifest, sort_keys=True, ensure_ascii=False).encode()
    manifest["manifest_sha256"] = hashlib.sha256(payload).hexdigest()
    return ordered, manifest


def regression_metrics(y_true, prediction):
    y_true = np.asarray(y_true, dtype=np.float64)
    prediction = np.asarray(prediction, dtype=np.float64)
    pearson = float(np.corrcoef(y_true, prediction)[0, 1])
    mse = float(np.mean((y_true - prediction) ** 2))
    return {"pearson_r": pearson, "mse": mse}


def restore_post(backbone, head, result_dir, result, ledger_row, device):
    if not result.get("acceptance_eligible") or result.get("smoke"):
        raise ValueError("源格不是正式 acceptance_eligible 结果")
    if ledger_row is None or ledger_row.get("status") != "done":
        raise ValueError("源格缺少 ledger done 记录")
    error = vp.checkpoint_proof_error(result_dir, result, ledger_row)
    if error:
        raise ValueError("源 checkpoint proof 失败: " + error)
    state = torch.load(Path(result_dir) / "best.ckpt",
                       map_location=device, weights_only=True)
    vp.load_backbone_state_dict(backbone, state["backbone"])
    head.load_state_dict(state["head"])
    for name, current in (("backbone", vp.backbone_state_dict(backbone)),
                          ("head", head.state_dict())):
        expected = state[name]
        if set(current) != set(expected):
            raise ValueError(name + " tensor keys 与源 checkpoint 不一致")
        for key in current:
            if not torch.equal(current[key].detach().cpu(), expected[key].detach().cpu()):
                raise ValueError(name + " 恢复后 tensor 不一致: " + key)
    return {
        "source_checkpoint": str(Path(result_dir) / "best.ckpt"),
        "source_checkpoint_sha256": common.sha256_file(Path(result_dir) / "best.ckpt"),
        "best_epoch": result["best_epoch"],
        "best_val": result["best_val"],
        "restored_tensor_match": True,
        "checkpoint_proof": "ok",
    }


def extract(backbone, head, tokenizer, rows, device, n_samples, batch_size=64):
    backbone.eval()
    head.eval()
    full_ids, full_y, full_pred = [], [], []
    sample_cls, sample_head = [], []
    with torch.no_grad():
        for start in range(0, len(rows), batch_size):
            batch = rows[start:start + batch_size]
            enc = encode_seqs(tokenizer, [row["seq"] for row in batch], device, MAX_LEN)
            hidden = backbone(**enc).last_hidden_state
            pad = enc["attention_mask"] == 0
            pooled = head.pool(hidden, pad)
            prediction = head.fc2(torch.nn.functional.gelu(head.fc1(pooled))).squeeze(-1)
            full_ids.extend(common.sequence_hash(row["seq"]) for row in batch)
            full_y.extend(float(row["label"]) for row in batch)
            full_pred.extend(prediction.detach().cpu().numpy().tolist())
            keep = min(len(batch), max(0, n_samples - start))
            if keep:
                sample_cls.append(hidden[:keep, 0].detach().cpu().numpy())
                sample_head.append(pooled[:keep].detach().cpu().numpy())
    full_y = np.asarray(full_y, dtype=np.float32)
    full_pred = np.asarray(full_pred, dtype=np.float32)
    if not full_y.size or not np.isfinite(full_pred).all():
        raise ValueError("完整 test 预测为空或非有限值")
    n = min(n_samples, len(rows))
    cls = np.concatenate(sample_cls).astype(np.float32)
    head_embedding = np.concatenate(sample_head).astype(np.float32)
    if len(cls) != n or len(head_embedding) != n:
        raise ValueError("抽样 embedding 数量不一致")
    sample = {
        "sample_ids": np.asarray(full_ids[:n]),
        "y_true": full_y[:n],
        "prediction": full_pred[:n],
        "residual": full_pred[:n] - full_y[:n],
        "cls": cls,
        "head_embedding": head_embedding,
    }
    full = {
        "sample_ids": np.asarray(full_ids),
        "y_true": full_y,
        "prediction": full_pred,
        "residual": full_pred - full_y,
    }
    return full, sample


def save_npz(path, **arrays):
    path = Path(path)
    temporary = path.with_name(path.name + ".tmp.npz")
    np.savez(temporary, **arrays)
    os.replace(temporary, path)


def load_aligned_states(split, seed, suffix="_ckpt_v1"):
    ready = []
    for strategy in STATES:
        out_dir = ARTIFACT_ROOT / (
            f"mech_rinalmomicro_mrl_{strategy}_{split}_s{seed}{suffix}")
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
                      source_reference, diagnostic["metrics_full"]["pearson_r"]))
    return ready


def aligned_regression(states, output_path, perplexity=30, random_state=17):
    if len(states) != 3 or {item[0] for item in states} != set(STATES):
        raise ValueError("需要 pre/lora/full 三状态")
    states = sorted(states, key=lambda item: STATES.index(item[0]))
    if len({item[2] for item in states}) != 1:
        raise ValueError("三状态 test manifest 不一致")
    reference = states[0][1]
    for _strategy, arrays, _manifest, _out_dir, _pearson in states[1:]:
        if not np.array_equal(reference["sample_ids"], arrays["sample_ids"]):
            raise ValueError("三状态 sample_id 顺序不一致")
        if not np.allclose(reference["y_true"], arrays["y_true"], rtol=0, atol=0):
            raise ValueError("三状态 MRL 标签不一致")
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
        y_true=np.tile(reference["y_true"], 3),
        prediction=np.concatenate([item[1]["prediction"] for item in states]),
        residual=np.concatenate([item[1]["residual"] for item in states]),
        split=np.asarray(states[0][1].get("split", "unknown")),
        seed=np.asarray(states[0][1].get("seed", -1)),
        source_run_ids=np.asarray([item[3] for item in states]),
        full_pearson=np.asarray([item[4] for item in states], dtype=np.float64),
        test_manifest_sha256=np.asarray(states[0][2]),
        tsne_perplexity=np.asarray(effective_perplexity),
        tsne_random_state=np.asarray(random_state),
        color_mode=np.asarray("true_mrl_continuous"),
        interpretation=np.asarray("descriptive_only_no_classification_silhouette"),
    )
    return {
        "path": str(output_path), "n_per_state": n, "n_total": len(cls),
        "perplexity": effective_perplexity, "random_state": random_state,
        "color_mode": "true_mrl_continuous",
        "classification_silhouette": None,
        "interpretation": "descriptive_only_no_classification_silhouette",
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
        source_dir = Path(ledger.ARTIFACT_ROOT) / source_rid
        source_result = json.loads((source_dir / "result.json").read_text())
        source_row = ledger.by_run_id(source_rid)
        if source_result["n_test"] != len(ordered):
            raise ValueError("源 result n_test 与重建 test 不一致")
        if source_result.get("data_evidence") != split_evidence:
            raise ValueError("源 result 与重建 split evidence 不一致")
    out_dir = ARTIFACT_ROOT / (
        f"mech_rinalmomicro_mrl_{args.strategy}_{args.split}_s{args.seed}_ckpt_v1")
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
            head = make_head("per-seq", d_model, 1).to(device)
        else:
            backbone, _n_trainable = apply_strategy(backbone, args.strategy, lora_rank=8)
            head = make_head("per-seq", d_model, 1).to(device)
            checkpoint_evidence = restore_post(
                backbone, head, source_dir, source_result, source_row, device)
        head.eval()
        runtime = vp.runtime_evidence(tokenizer, device)
        full, sample = extract(backbone, head, tokenizer, ordered, device,
                               args.n_samples, args.batch_size)
        metrics = regression_metrics(full["y_true"], full["prediction"])
        if not math.isfinite(metrics["pearson_r"]) or not math.isfinite(metrics["mse"]):
            raise ValueError("完整 test 回归指标非有限值")
        metric_match = None
        if source_result is not None:
            metric_match = math.isclose(
                metrics["pearson_r"], source_result["value"], rel_tol=2e-5, abs_tol=2e-6)
            if not metric_match:
                raise ValueError("完整 test Pearson r 与源 result 不一致: %s vs %s" % (
                    metrics["pearson_r"], source_result["value"]))
            if not math.isclose(metrics["mse"], source_result["mse"],
                                rel_tol=2e-5, abs_tol=1e-6):
                raise ValueError("完整 test MSE 与源 result 不一致")
        sample["split"] = np.asarray(args.split)
        sample["seed"] = np.asarray(args.seed)
        save_npz(out_dir / "predictions.npz", **full)
        save_npz(out_dir / "embeddings.npz", **sample)
        diagnostic = {
            "artifact_type": "mrl_diagnostic",
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
                "pearson_r": source_result["value"], "mse": source_result["mse"]},
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
            "interpretation": "descriptive_only_no_classification_silhouette",
        }
        ready = load_aligned_states(args.split, args.seed)
        source_reference = ("pre_official_rinalmomicro" if source_result is None
                            else source_result["run_id"])
        ready.append((args.strategy, sample, manifest["manifest_sha256"],
                      source_reference, metrics["pearson_r"]))
        diagnostic["aligned_tsne"] = None
        diagnostic["available_states"] = [item[0] for item in ready]
        if len(ready) == 3:
            aligned_path = ARTIFACT_ROOT / (
                f"mech_rinalmomicro_mrl_aligned_{args.split}_s{args.seed}_ckpt_v1.npz")
            diagnostic["aligned_tsne"] = aligned_regression(ready, aligned_path)
        common.write_json(out_dir / "diagnostic.json", diagnostic)
        common.write_json(out_dir / "job.json", {
            "run_id": out_dir.name, "status": "diagnostic", "out_dir": str(out_dir),
            "diagnostic": str(out_dir / "diagnostic.json"), "git_sha": diagnostic["git_sha"],
            "full_test_metric_match": metric_match,
        })
        print(json.dumps({
            "run_id": out_dir.name, "status": "diagnostic",
            "n_full_test": len(ordered), "n_sample": len(sample["sample_ids"]),
            "metrics_full": metrics, "full_test_metric_match": metric_match,
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
        print(json.dumps({"event": "MRL_MECHANISM_ABORT",
                          "error": "%s: %s" % (type(error).__name__, error)}), flush=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
