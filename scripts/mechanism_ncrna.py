#!/usr/bin/env python3
"""Same-sample ncRNA embedding/prediction diagnostics; never CPU-run formally."""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
import os
from pathlib import Path
import random
import re
import subprocess
import sys

import numpy as np
import torch

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from rnafteval import valplateau as vp
from rnafteval.finetune_one import batches, encode_seqs
from rnafteval.splits import (assert_cluster_no_overlap, assert_no_overlap,
                              prepare_convergence_splits, random_split)
from rnafteval.strategies import apply_strategy, make_head
from rnafteval.tasks.dedup import dedup
from rnafteval.tasks.ncrna import load_ncrna

MODEL = "RiNALMo-micro"
TASK = "noncoding-rna-family"
STATES = ("pre", "lora", "full")
TEAMS_ROOT = Path(os.environ.get(
    "RNAFT_TEAMS_ROOT", "/teams/HoulabData_1788502323/liucunyu/rna-ft-eval"))
ARTIFACT_ROOT = Path(os.environ.get(
    "RNAFT_MECHANISM_ROOT", str(TEAMS_ROOT / "artifacts" / "mechanism")))
DATA_ROOT = Path(os.environ.get("RNAFT_DATA_ROOT", str(TEAMS_ROOT / "data")))
LOCAL_DATA_ROOT = Path("/root/rna-ft-eval/data")
MAX_LEN = 512
N_CLASSES = 13


def run_id(strategy, split, seed, suffix="_mech_v1"):
    return "mech_rinalmomicro_ncrna_%s_%s_s%d%s" % (
        strategy, split, seed, suffix)


def require_cuda(device=0):
    if isinstance(device, torch.device):
        device = device.index
    if isinstance(device, str):
        if not device.startswith("cuda:"):
            raise RuntimeError("formal mechanism runner requires a CUDA device")
        device = int(device.split(":", 1)[1])
    if not isinstance(device, int) or device < 0:
        raise ValueError("device must be a non-negative CUDA index")
    if not torch.cuda.is_available():
        raise RuntimeError("formal mechanism runner requires real CUDA; no CPU fallback")
    count = torch.cuda.device_count()
    if device >= count:
        raise RuntimeError("CUDA device %d is unavailable; device_count=%d" %
                           (device, count))
    torch.cuda.set_device(device)
    return "cuda:%d" % device


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def sequence_hash(sequence):
    canonical = sequence.strip().upper().replace("U", "T")
    return hashlib.sha256(canonical.encode()).hexdigest()


def sequence_stats(sequence):
    sequence = sequence.strip().upper().replace("T", "U")
    length = len(sequence)
    gc = sum(base in "GC" for base in sequence) / length if length else 0.0
    return length, gc


def family_id(row):
    if row.get("cluster") is not None:
        return str(row["cluster"])
    # No clustering is inferred for random-split records.
    return sequence_hash(row["seq"])


def sample_rows(rows, split, seed=17, n_test=0, max_per_family=60):
    if max_per_family <= 0 or n_test < 0:
        raise ValueError("max_per_family must be positive and n_test non-negative")
    eligible = sorted(rows, key=lambda row: sequence_hash(row["seq"]))
    if n_test:
        indices = sorted(random.Random(17).sample(
            range(len(eligible)), min(n_test, len(eligible))))
        eligible = [eligible[index] for index in indices]
    groups = defaultdict(list)
    for row in eligible:
        key = row["label"] if split == "random" else family_id(row)
        groups[key].append(row)
    sampled = []
    for key in sorted(groups, key=str):
        group = groups[key]
        if len(group) > max_per_family:
            group = random.Random(seed).sample(group, max_per_family)
        sampled.extend(group)
    sampled.sort(key=lambda row: sequence_hash(row["seq"]))
    return sampled


def make_test_manifest(rows, split, seed=17, n_test=0, max_per_family=60,
                       family_path=None):
    records = []
    for row in sample_rows(rows, split, seed, n_test, max_per_family):
        length, gc = sequence_stats(row["seq"])
        records.append({
            "sample_id": sequence_hash(row["seq"]),
            "seq_hash": sequence_hash(row["seq"]),
            "label": int(row["label"]),
            "family_id": family_id(row),
            "length": length,
            "gc": gc,
        })
    manifest = {
        "schema_version": 1, "split": split, "seed": seed,
        "data_split_seed": 17, "test_sampling_seed": 17,
        "family_cap_seed": seed, "n_test_requested": n_test,
        "max_per_family": max_per_family,
        "cap_unit": "label" if split == "random" else "family_id",
        "family_id_source": "cluster_id" if split == "family" else "seq_hash_not_clustered",
        "n": len(records), "records": records,
        "sample_ids": [record["sample_id"] for record in records],
        "seq_hashes": [record["seq_hash"] for record in records],
    }
    if split == "family":
        if family_path is None:
            raise ValueError("family manifest requires the cluster parquet fingerprint")
        manifest["family_parquet"] = str(family_path)
        manifest["family_parquet_sha256"] = sha256_file(family_path)
    payload = json.dumps(manifest, sort_keys=True, separators=(",", ":"))
    manifest["manifest_sha256"] = hashlib.sha256(payload.encode()).hexdigest()
    return manifest


def load_data(split, seed=17, converge=True, out_dir=None, data_root=DATA_ROOT):
    data_root = Path(data_root)
    family_path = None
    if split == "family":
        family_path = data_root / "family_splits" / "noncoding-rna-family.parquet"
        if not family_path.is_file():
            alternate = LOCAL_DATA_ROOT / "family_splits" / family_path.name
            if alternate.is_file():
                family_path = alternate
        import pyarrow.parquet as pq
        columns = pq.read_table(family_path).to_pydict()
        recs = [{"seq": seq, "label": int(label), "cluster": cluster}
                for seq, label, cluster in zip(
                    columns["seq"], columns["label"], columns["cluster_id"])]
        parts = {side: [row for row, assigned in zip(recs, columns["split"])
                        if assigned == side]
                 for side in ("train", "val", "test")}
    else:
        source = data_root / "beacon_raw" / "noncoding-rna-family" / "data"
        if not source.is_dir():
            source = LOCAL_DATA_ROOT / "beacon_raw" / "noncoding-rna-family" / "data"
        recs = dedup(load_ncrna(str(source)))
        parts = random_split(recs, seed=17)
    labels = sorted({int(row["label"]) for row in recs})
    if labels != list(range(N_CLASSES)):
        raise ValueError("ncRNA requires exactly labels 0..12; got %s" % labels)
    evidence = None
    if converge:
        evidence_path = Path(out_dir) / "split_evidence.json" if out_dir else None
        (parts["train"], parts["val"], parts["test"], evidence) = \
            prepare_convergence_splits(
                parts["train"], parts["val"], parts["test"],
                sample_seed=seed, family=split == "family",
                validation_source=("family_validation" if split == "family"
                                   else "random_split_validation"),
                evidence_path=str(evidence_path) if evidence_path else "")
    for side in parts:
        for row in parts[side]:
            row["label_id"] = int(row["label"])
    assert_no_overlap(parts["train"], parts["val"] + parts["test"], unit="seq")
    assert_no_overlap(parts["val"], parts["test"], unit="seq")
    if split == "family":
        assert_cluster_no_overlap(parts["train"], parts["val"] + parts["test"])
        assert_cluster_no_overlap(parts["val"], parts["test"])
    return recs, parts, labels, evidence, family_path


def prediction_metrics(logits, labels):
    logits = np.asarray(logits, dtype=np.float64)
    labels = np.asarray(labels, dtype=np.int64)
    if logits.ndim != 2 or logits.shape[0] != labels.shape[0] or not len(labels):
        raise ValueError("metrics require non-empty aligned logits and labels")
    shifted = logits - logits.max(axis=1, keepdims=True)
    probabilities = np.exp(shifted)
    probabilities /= probabilities.sum(axis=1, keepdims=True)
    entropy = -(probabilities * np.log(np.maximum(probabilities, 1e-300))).sum(axis=1)
    predictions = probabilities.argmax(axis=1)
    ordered = np.sort(probabilities, axis=1)
    margin = ordered[:, -1] - ordered[:, -2]
    n_classes = logits.shape[1]
    confusion = np.zeros((n_classes, n_classes), dtype=np.int64)
    np.add.at(confusion, (labels, predictions), 1)
    return {
        "metrics": {
            "ACC": float(np.mean(predictions == labels)),
            "prediction_entropy_median": float(np.median(entropy)),
            "max_class_prediction_fraction": float(
                np.bincount(predictions, minlength=n_classes).max() / len(labels)),
            "confusion_matrix": confusion.tolist(),
        },
        "probabilities": probabilities.astype(np.float32),
        "predictions": predictions.astype(np.int64),
        "entropy": entropy.astype(np.float32),
        "margin": margin.astype(np.float32),
        "confusion": confusion,
    }


def train_model(backbone, head, parts, args, out_dir, rid, runtime):
    out_dir = Path(out_dir)
    device = args.device if isinstance(args.device, str) else "cuda:%d" % args.device
    if torch.device(device).type != "cuda" or not torch.cuda.is_available():
        raise RuntimeError("post training requires real CUDA")
    lr = 1e-5 if args.strategy == "full" else 3e-4
    parameters = [p for p in head.parameters() if p.requires_grad]
    parameters += [p for p in backbone.parameters() if p.requires_grad]
    optimizer = torch.optim.AdamW(parameters, lr=lr)
    loss_function = torch.nn.CrossEntropyLoss()

    def save_best(epoch, val_loss):
        vp.save_best_checkpoint(
            out_dir / "best.ckpt", backbone, head,
            epoch=epoch, best_epoch=epoch, best_val=val_loss)

    tracker = vp.make_tracker(out_dir, args, rid, save_best)
    for epoch in vp.training_epochs(args):
        rows = list(parts["train"])
        random.Random(args.seed * 1000 + epoch).shuffle(rows)
        backbone.train()
        head.train()
        total, count = 0.0, 0
        for batch in batches(rows, args.batch_size):
            encoded = encode_seqs(
                args.tokenizer, [row["seq"] for row in batch], device, MAX_LEN)
            target = torch.tensor([row["label_id"] for row in batch],
                                  device=device)
            hidden = backbone(**encoded).last_hidden_state
            pad = encoded["attention_mask"] == 0
            loss = loss_function(head(hidden, pad), target)
            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(parameters, 1.0)
            optimizer.step()
            total += loss.item()
            count += 1
        train_loss = total / max(count, 1)
        backbone.eval()
        head.eval()
        val_total, val_count = 0.0, 0
        with torch.no_grad():
            for batch in batches(parts["val"], args.batch_size * 2):
                encoded = encode_seqs(args.tokenizer, [row["seq"] for row in batch],
                                      device, MAX_LEN)
                target = torch.tensor([row["label_id"] for row in batch],
                                      device=device)
                hidden = backbone(**encoded).last_hidden_state
                pad = encoded["attention_mask"] == 0
                val_loss = loss_function(head(hidden, pad), target)
                val_total += val_loss.item()
                val_count += 1
        val_epoch_loss = val_total / max(val_count, 1)
        print("epoch %d train_loss %.6f val_loss %.6f" %
              (epoch, train_loss, val_epoch_loss), flush=True)
        converged = tracker.record(epoch, train_loss, val_epoch_loss)
        write_json(Path(out_dir) / "job.json", {
            "run_id": rid, "artifact_type": "job", "status": "running",
            "strategy": args.strategy, "split": args.split, "seed": args.seed,
            "out_dir": str(out_dir), "updated_epoch": epoch,
            "convergence": tracker.result_fields(), "cuda": runtime,
        })
        if converged:
            break
    if tracker.status != "CONVERGED":
        raise RuntimeError(
            "validation did not reach CONVERGED; diagnostic is not complete (%s)"
            % tracker.status)
    restored = vp.restore_best_checkpoint(tracker, backbone, head, device)
    proof = dict(tracker.result_fields())
    proof_error = vp.checkpoint_proof_error(out_dir, proof)
    if proof_error:
        raise RuntimeError("best checkpoint proof is invalid: %s" % proof_error)
    if restored["best_epoch"] != proof["best_epoch"]:
        raise RuntimeError("restored checkpoint differs from best validation epoch")
    restored_pairs = (
        ("backbone", vp.backbone_state_dict(backbone), restored["backbone"]),
        ("head", head.state_dict(), restored["head"]),
    )
    for name, current, expected in restored_pairs:
        if current.keys() != expected.keys():
            raise RuntimeError("restored %s keys differ from best checkpoint" % name)
        if any(not torch.equal(current[key].detach().cpu(),
                               expected[key].detach().cpu()) for key in current):
            raise RuntimeError("best %s weights were not restored in memory" % name)
    proof["restored_tensor_match"] = True
    proof["best_checkpoint_sha256"] = sha256_file(out_dir / "best.ckpt")
    proof["restored_before_diagnostic"] = True
    proof["checkpoint_proof"] = "ok"
    write_json(out_dir / "checkpoint_proof.json", {
        "run_id": rid, "protocol": vp.BESTVAL_PROTOCOL,
        "best_epoch": proof["best_epoch"], "best_val": proof["best_val"],
        "best_checkpoint": "best.ckpt",
        "best_checkpoint_sha256": proof["best_checkpoint_sha256"],
        "restored_before_diagnostic": True, "restored_tensor_match": True,
        "checkpoint_proof": "ok",
    })
    return proof, runtime, lr


def save_state(backbone, head, config, out_dir):
    out_dir = Path(out_dir)
    torch.save({key: value.detach().cpu() for key, value in
                vp.backbone_state_dict(backbone).items()},
               out_dir / "backbone_state.pt")
    torch.save({key: value.detach().cpu() for key, value in
                head.state_dict().items()}, out_dir / "head_state.pt")
    write_json(out_dir / "config.json", config)


def extract_diagnostics(backbone, head, tokenizer, rows, device, batch_size=32,
                        split="random", seed=17):
    device = torch.device(device)
    if device.type != "cuda" or not torch.cuda.is_available():
        raise RuntimeError("formal diagnostic extraction requires real CUDA")
    return extract_tensors(backbone, head, tokenizer, rows, device,
                           batch_size, split, seed)


def extract_tensors(backbone, head, tokenizer, rows, device, batch_size=32,
                    split="random", seed=17):
    backbone.eval()
    head.eval()
    output = defaultdict(list)
    with torch.no_grad():
        for batch in batches(rows, batch_size * 2):
            encoded = encode_seqs(tokenizer, [row["seq"] for row in batch],
                                  device, MAX_LEN)
            hidden = backbone(**encoded).last_hidden_state
            pad = encoded["attention_mask"] == 0
            output["cls"].append(hidden[:, 0, :].detach().cpu().numpy())
            # Direct head.pool output: prediction-head input, not backbone pooling.
            output["head_embedding"].append(
                head.pool(hidden, pad).detach().cpu().numpy())
            output["logits"].append(head(hidden, pad).detach().cpu().numpy())
    arrays = {key: np.concatenate(value).astype(np.float32)
              for key, value in output.items()}
    labels = np.asarray([int(row["label"]) for row in rows], dtype=np.int64)
    details = prediction_metrics(arrays["logits"], labels)
    arrays.update({key: details[key] for key in
                   ("probabilities", "predictions", "entropy", "margin")})
    arrays["labels"] = labels
    arrays["sample_ids"] = np.asarray([sequence_hash(row["seq"]) for row in rows])
    arrays["seq_hash"] = arrays["sample_ids"].copy()
    arrays["family_id"] = np.asarray([family_id(row) for row in rows])
    stats = [sequence_stats(row["seq"]) for row in rows]
    arrays["length"] = np.asarray([item[0] for item in stats], dtype=np.int64)
    arrays["gc"] = np.asarray([item[1] for item in stats], dtype=np.float32)
    arrays["split"] = np.asarray(split)
    arrays["seed"] = np.asarray(seed, dtype=np.int64)
    arrays["state"] = np.asarray(getattr(head, "_mechanism_state", "unknown"))
    if arrays["head_embedding"].shape[1] != arrays["cls"].shape[1]:
        raise ValueError("CLS and head pooling must share backbone hidden width")
    return arrays, details["metrics"]


def diagnostic_is_usable(payload):
    if payload.get("artifact_type") != "diagnostic":
        return False
    if payload.get("status") != "diagnostic":
        return False
    if payload.get("strategy") == "pre":
        return payload.get("pretrained_baseline") is True
    convergence = payload.get("convergence", {})
    if (convergence.get("status") != "CONVERGED"
            or convergence.get("protocol") != vp.BESTVAL_PROTOCOL
            or convergence.get("restored_before_diagnostic") is not True
            or convergence.get("restored_tensor_match") is not True
            or convergence.get("checkpoint_proof") != "ok"):
        return False
    checkpoints = payload.get("checkpoints", {})
    return all(name in checkpoints and Path(checkpoints[name]).is_file()
               for name in ("backbone", "head", "config", "best", "best_proof"))


def resolve_run_dirs(split, seed, suffix, artifact_root=ARTIFACT_ROOT):
    return {state: Path(artifact_root) / run_id(state, split, seed, suffix)
            for state in STATES}


def load_aligned_states(split, seed, suffix="_mech_v1",
                        artifact_root=ARTIFACT_ROOT, required_states=STATES):
    states = []
    for state in required_states:
        directory = resolve_run_dirs(split, seed, suffix, artifact_root)[state]
        diagnostic_path = directory / "diagnostic.json"
        manifest_path = directory / "test_manifest.json"
        if not diagnostic_path.is_file() or not (directory / "embeddings.npz").is_file():
            continue
        diagnostic = json.loads(diagnostic_path.read_text())
        manifest = json.loads(manifest_path.read_text())
        if not diagnostic_is_usable(diagnostic):
            continue
        if (diagnostic.get("split") != split or diagnostic.get("seed") != seed
                or diagnostic.get("strategy") != state):
            continue
        manifest_hash = sha256_file(manifest_path)
        if diagnostic.get("test_manifest_sha256") != manifest_hash:
            continue
        with np.load(directory / "embeddings.npz", allow_pickle=False) as data:
            arrays = {key: data[key].copy() for key in data.files}
        if arrays["sample_ids"].tolist() != manifest["sample_ids"]:
            raise ValueError("embedding order differs from test manifest: %s" % directory)
        states.append((state, arrays, manifest_hash, directory))
    if not states:
        return []
    expected_ids = states[0][1]["sample_ids"].tolist()
    expected_hash = states[0][2]
    for state, arrays, manifest_hash, directory in states[1:]:
        if manifest_hash != expected_hash or arrays["sample_ids"].tolist() != expected_ids:
            raise ValueError("states do not share one test manifest: %s" % directory)
    return states


def aligned_tsne(states, output_path):
    if [state for state, *_ in states] != list(STATES):
        raise ValueError("aligned t-SNE requires pre, lora and full in state order")
    ids = states[0][1]["sample_ids"]
    labels = states[0][1]["labels"]
    for _, arrays, _, _ in states[1:]:
        if not np.array_equal(arrays["sample_ids"], ids):
            raise ValueError("t-SNE sample order is not aligned")
        if not np.array_equal(arrays["labels"], labels):
            raise ValueError("t-SNE labels are not aligned")
    head_embedding = np.concatenate([arrays["head_embedding"] for _, arrays, _, _ in states])
    cls = np.concatenate([arrays["cls"] for _, arrays, _, _ in states])
    if len(head_embedding) < 2:
        raise ValueError("joint t-SNE requires at least two samples")
    from sklearn.manifold import TSNE
    from sklearn.metrics import silhouette_score
    perplexity = min(30, len(head_embedding) - 1)
    coordinates = TSNE(n_components=2, random_state=17,
                       perplexity=perplexity).fit_transform(head_embedding)
    silhouette = {}
    for state, arrays, _, _ in states:
        values = arrays["head_embedding"].astype(np.float64)
        n_labels = len(np.unique(arrays["labels"]))
        if len(np.unique(values, axis=0)) < 2 or not 2 <= n_labels < len(values):
            silhouette[state] = None
        else:
            silhouette[state] = float(silhouette_score(values, arrays["labels"]))
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez(output_path, tsne=coordinates, cls=cls, head_embedding=head_embedding,
             labels=np.tile(labels, len(states)),
             state=np.concatenate([
                 np.full(len(arrays["sample_ids"]), state) for state, arrays, _, _ in states]),
             sample_ids=np.tile(ids, len(states)),
             silhouette=np.asarray(json.dumps(silhouette)),
             tsne_random_state=np.asarray(17), tsne_perplexity=np.asarray(perplexity),
             test_manifest_sha256=np.asarray(states[0][2]),
             interpretation=np.asarray("descriptive_only_no_head_causality"))
    return {"path": str(output_path), "n_per_state": len(ids),
            "n_total": len(head_embedding), "perplexity": perplexity,
            "random_state": 17, "silhouette_head_embedding": silhouette,
            "silhouette_input": "original_head_embedding",
            "interpretation": "descriptive_only_no_head_causality"}


def git_sha():
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"],
                                       cwd=REPO_ROOT, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def build_parser():
    parser = argparse.ArgumentParser(
        description="RiNALMo-micro ncRNA same-sample mechanism diagnostics")
    parser.add_argument("--split", choices=("random", "family"), required=True)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--strategy", choices=STATES, required=True)
    parser.add_argument("--device", type=int, required=True)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--epochs", type=int, default=10,
                        help="legacy fixed-epoch setting; does not cap --converge")
    parser.add_argument("--out-suffix", default="_mech_v1")
    parser.add_argument("--n-test", type=int, default=0)
    parser.add_argument("--max-per-family", type=int, default=60)
    vp.add_convergence_args(parser)
    parser.set_defaults(convergence_mode="bestval")
    return parser


def validate_args(args):
    if not re.fullmatch(r"_[A-Za-z0-9_-]+", args.out_suffix):
        raise ValueError("out-suffix must begin with _ and contain no path separators")
    if args.batch_size <= 0 or args.epochs <= 0:
        raise ValueError("batch-size and epochs must be positive")
    if args.strategy != "pre" and not args.converge:
        raise ValueError("post diagnostic requires --converge and held-out validation")
    if args.strategy != "pre" and getattr(args, "convergence_mode", "bestval") != "bestval":
        raise ValueError("post diagnostic requires --convergence-mode bestval (bestval_v1)")


def run(args):
    validate_args(args)
    device = require_cuda(args.device)
    if device != "cuda:%d" % args.device:
        raise RuntimeError("formal diagnostic cannot replace requested GPU with CPU")
    cuda_index = args.device
    args.device = device
    rid = run_id(args.strategy, args.split, args.seed, args.out_suffix)
    out_dir = ARTIFACT_ROOT / rid
    out_dir.mkdir(parents=True, exist_ok=True)
    for name in ("diagnostic.json", "embeddings.npz"):
        if (out_dir / name).exists():
            raise FileExistsError("refusing to overwrite existing diagnostic: %s" % out_dir)
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    torch.cuda.manual_seed_all(args.seed)
    torch.cuda.reset_peak_memory_stats(cuda_index)
    config = {
        "run_id": rid, "model": MODEL, "task": TASK,
        "strategy": args.strategy, "split": args.split, "seed": args.seed,
        "data_split_seed": 17, "batch_size": args.batch_size,
        "max_len": MAX_LEN, "n_test": args.n_test,
        "max_per_family": args.max_per_family, "n_classes": N_CLASSES,
        "out_suffix": args.out_suffix, "converge": bool(args.converge),
        "cuda_device": device, "patience": args.patience, "min_delta": args.min_delta,
        "abs_floor": vp.ABS_FLOOR,
        "convergence_mode": (getattr(args, "convergence_mode", "plateau")
                             if args.strategy == "pre" else "bestval"),
        "convergence_protocol": (None if args.strategy == "pre"
                                 else vp.BESTVAL_PROTOCOL),
        "convergence_epoch_limit": None,
        "epochs": args.epochs,
        "lr": 1e-5 if args.strategy == "full" else 3e-4,
        "optimizer": "AdamW", "gradient_clip_norm": 1.0,
        "lora": {"rank": 8, "alpha": 4, "dropout": 0.0},
        "head": {"type": "per-seq", "hidden": 32,
                 "pool": "attention", "embedding": "head.pool(h,pad)"},
        "artifact_root": str(ARTIFACT_ROOT), "data_root": str(DATA_ROOT),
        "validation": "held_out_validation_not_test",
        "interpretation": "descriptive_diagnostic_only",
    }
    job = dict(config, artifact_type="job", status="running", out_dir=str(out_dir))
    write_json(out_dir / "manifest.json", {
        "run_id": rid, "artifact_type": "run_manifest", "status": "running",
        "config": config, "git_sha": git_sha(), "out_dir": str(out_dir),
    })
    write_json(out_dir / "job.json", job)
    try:
        recs, parts, labels, data_evidence, family_path = load_data(
            args.split, args.seed, True, out_dir)
        manifest = make_test_manifest(
            parts["test"], args.split, args.seed, args.n_test,
            args.max_per_family, family_path)
        if not manifest["records"]:
            raise ValueError("selected test subset is empty")
        by_hash = {sequence_hash(row["seq"]): row for row in parts["test"]}
        rows = [by_hash[sample_id] for sample_id in manifest["sample_ids"]]
        write_json(out_dir / "test_manifest.json", manifest)
        manifest_hash = sha256_file(out_dir / "test_manifest.json")
        from rnafteval.models import load_model
        spec, tokenizer, backbone = load_model(MODEL, device)
        with torch.no_grad():
            probe = encode_seqs(tokenizer, [recs[0]["seq"]], device, MAX_LEN)
            d_model = backbone(**probe).last_hidden_state.shape[-1]
        if d_model != spec.d_model:
            print("d_model corrected: spec %d -> actual %d" % (spec.d_model, d_model))
        runtime = vp.runtime_evidence(tokenizer, device)
        if args.strategy == "pre":
            backbone.eval()
            n_trainable = 0
            convergence = None
        else:
            backbone, n_trainable = apply_strategy(
                backbone, args.strategy, lora_rank=8, lora_alpha=4)
            args.tokenizer = tokenizer
            head = make_head("per-seq", d_model, N_CLASSES).to(device)
            convergence, runtime, lr = train_model(
                backbone, head=head, parts=parts, args=args,
                out_dir=out_dir, rid=rid, runtime=runtime)
            # Keep the exact trained module for both pooling and classification.
            save_state(backbone, head, config, out_dir)
        if args.strategy == "pre":
            # The untrained reference head is reproducible and never a zero-shot classifier.
            torch.manual_seed(201)
            head = make_head("per-seq", d_model, N_CLASSES).to(device)
            head.eval()
        head._mechanism_state = args.strategy
        arrays, metrics = extract_diagnostics(
            backbone, head, tokenizer, rows, device, args.batch_size,
            args.split, args.seed)
        if arrays["sample_ids"].tolist() != manifest["sample_ids"]:
            raise RuntimeError("diagnostic samples differ from saved test manifest")
        np.savez(out_dir / "embeddings.npz", **arrays)
        cluster_evidence = dict(data_evidence or {})
        if args.split == "family":
            split_clusters = {side: {family_id(row) for row in parts[side]}
                              for side in parts}
            cluster_evidence.update({
                "cluster_column": "cluster_id", "source": str(family_path),
                "source_sha256": sha256_file(family_path),
                "n_clusters_by_split": {side: len(value)
                                        for side, value in split_clusters.items()},
                "train_val_test_cluster_disjoint": not (
                    split_clusters["train"] & split_clusters["val"]
                    or split_clusters["train"] & split_clusters["test"]
                    or split_clusters["val"] & split_clusters["test"]),
            })
        diagnostic = {
            "artifact_type": "diagnostic", "status": "diagnostic",
            "run_id": rid, "model": MODEL, "model_repo": spec.repo,
            "model_class": "%s.%s" % (type(backbone).__module__, type(backbone).__name__),
            "head_class": "%s.%s" % (type(head).__module__, type(head).__name__),
            "task": TASK,
            "strategy": args.strategy, "split": args.split, "seed": args.seed,
            "n": len(rows), "n_classes": N_CLASSES,
            "n_train": len(parts["train"]), "n_val": len(parts["val"]),
            "n_test_before_selection": len(parts["test"]),
            "metrics": metrics, "config": config,
            "git_sha": git_sha(), "cuda": runtime,
            "tokenizer": {key: runtime[key] for key in
                          ("tokenizer_class", "tokenizer_name_or_path",
                           "tokenizer_vocab_size")},
            "shape": {key: list(arrays[key].shape) for key in
                      ("cls", "head_embedding", "logits", "probabilities")},
            "cluster_split": cluster_evidence,
            "test_manifest_sha256": manifest_hash,
            "test_manifest": str(out_dir / "test_manifest.json"),
            "embeddings": str(out_dir / "embeddings.npz"),
            "label_values": labels,
            "interpretation": "descriptive_diagnostic_only_no_mechanism_conclusion",
        }
        if args.strategy == "pre":
            diagnostic.update({
                "pretrained_baseline": True, "convergence_required": False,
                "convergence": None,
                "prediction_head": "freshly_initialized_reference_head_not_trained",
                "reference_head_seed": 201,
                "prediction_metrics_reference_only": True,
                "checkpoints": None,
            })
        else:
            diagnostic.update({
                "pretrained_baseline": False, "convergence_required": True,
                "convergence": convergence,
                "prediction_head": "trained_post_%s_head" % args.strategy,
                "backbone_trainable": n_trainable,
                "checkpoints": {
                    "backbone": str(out_dir / "backbone_state.pt"),
                    "head": str(out_dir / "head_state.pt"),
                    "config": str(out_dir / "config.json"),
                    "best": str(out_dir / "best.ckpt"),
                    "best_proof": str(out_dir / "checkpoint_proof.json"),
                },
            })
        ready = load_aligned_states(args.split, args.seed, args.out_suffix)
        ready.append((args.strategy, arrays, manifest_hash, out_dir))
        ready.sort(key=lambda item: STATES.index(item[0]))
        if len(ready) == len(STATES):
            aligned_path = ARTIFACT_ROOT / (
                "mech_rinalmomicro_ncrna_aligned_%s_s%d%s" %
                (args.split, args.seed, args.out_suffix))
            diagnostic["aligned_tsne"] = aligned_tsne(ready, aligned_path)
        else:
            diagnostic["aligned_tsne"] = None
            diagnostic["available_states"] = [item[0] for item in ready]
        write_json(out_dir / "diagnostic.json", diagnostic)
        job["status"] = "diagnostic"
        job["diagnostic"] = str(out_dir / "diagnostic.json")
        job["test_manifest_sha256"] = manifest_hash
        write_json(out_dir / "manifest.json", {
            "run_id": rid, "artifact_type": "run_manifest",
            "status": "diagnostic", "config": config, "git_sha": diagnostic["git_sha"],
            "out_dir": str(out_dir), "diagnostic": str(out_dir / "diagnostic.json"),
            "test_manifest_sha256": manifest_hash,
            "embeddings_sha256": sha256_file(out_dir / "embeddings.npz"),
            "interpretation": diagnostic["interpretation"],
        })
        job["cuda_peak_memory_mb"] = (
            torch.cuda.max_memory_allocated(cuda_index) / (1 << 20))
        write_json(out_dir / "job.json", job)
        print(json.dumps({"run_id": rid, "status": "diagnostic", "n": len(rows),
                          "out_dir": str(out_dir),
                          "aligned_tsne": diagnostic["aligned_tsne"] is not None},
                         indent=2), flush=True)
        return 0
    except Exception as error:
        job["status"] = "failed"
        job["error"] = "%s: %s" % (type(error).__name__, error)
        write_json(out_dir / "job.json", job)
        manifest_path = out_dir / "manifest.json"
        if manifest_path.is_file():
            run_manifest = json.loads(manifest_path.read_text())
            run_manifest["status"] = "failed"
            run_manifest["error"] = job["error"]
            write_json(manifest_path, run_manifest)
        for name in ("diagnostic.json", "embeddings.npz"):
            (out_dir / name).unlink(missing_ok=True)
        raise


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        return run(args)
    except Exception as error:
        print(json.dumps({"event": "MECHANISM_DIAGNOSTIC_ABORT",
                          "error": "%s: %s" % (type(error).__name__, error)}),
              flush=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
