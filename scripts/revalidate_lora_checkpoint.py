"""Evaluate the formal ncRNA LoRA checkpoint on full test, with CUDA peak proof."""
import argparse
import hashlib
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import mechanism_ncrna as common
from mechanism_mrl import restore_post
from rnafteval import ledger, valplateau as vp
from rnafteval.finetune_one import batches, encode_seqs
from rnafteval.models import load_model
from rnafteval.splits import prepare_convergence_splits
from rnafteval.strategies import apply_strategy, make_head


def source_run_id(seed):
    if seed not in (17, 29, 43):
        raise ValueError("formal seeds are 17, 29, 43")
    return ledger.run_id(common.MODEL, common.TASK, "lora", seed, "random",
                         "_bestval_v1_fixedsplit")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--device", type=int, default=0)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.batch_size <= 0:
        raise ValueError("batch-size must be positive")
    device = common.require_cuda(args.device)
    started = time.time()
    rid = source_run_id(args.seed)
    row = ledger.by_run_id(rid)
    if row is None:
        raise ValueError("source ledger row is missing")
    source_dir = Path(row["out_dir"])
    result = json.loads((source_dir / "result.json").read_text())
    if result["run_id"] != rid or result["metric"] != "ACC":
        raise ValueError("source identity or metric mismatch")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output = args.output_dir / f"ncrna_lora_s{args.seed}_random_checkpoint.json"
    if output.exists():
        raise FileExistsError(output)
    _, parts, labels, _, _ = common.load_data(
        "random", args.seed, False, args.output_dir)
    parts["train"], parts["val"], parts["test"], evidence = prepare_convergence_splits(
        parts["train"], parts["val"], parts["test"], sample_seed=args.seed,
        family=False, validation_source="random_split_validation",
        evidence_path=str(args.output_dir / f"ncrna_lora_s{args.seed}_split_evidence.json"),
        protocol=result["protocol"])
    if evidence != result["data_evidence"]:
        raise ValueError("source split evidence differs from reconstruction")
    spec, tokenizer, backbone = load_model(common.MODEL, device)
    with torch.no_grad():
        probe = encode_seqs(tokenizer, [parts["test"][0]["seq"]], device, common.MAX_LEN)
        width = backbone(**probe).last_hidden_state.shape[-1]
    backbone, _ = apply_strategy(backbone, "lora", lora_rank=8)
    head = make_head("per-seq", width, len(labels)).to(device)
    checkpoint = restore_post(backbone, head, source_dir, result, row, device)
    runtime = vp.runtime_evidence(tokenizer, device)
    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats(args.device)
    backbone.eval()
    head.eval()
    ys, logits = [], []
    with torch.no_grad():
        for batch in batches(parts["test"], args.batch_size * 2):
            encoded = encode_seqs(tokenizer, [row["seq"] for row in batch],
                                  device, common.MAX_LEN)
            hidden = backbone(**encoded).last_hidden_state
            pad = encoded["attention_mask"] == 0
            logits.append(head(hidden, pad).cpu().numpy())
            ys.extend(int(row["label_id"]) for row in batch)
    logits = np.concatenate(logits)
    accuracy = float(np.mean(logits.argmax(axis=1) == np.asarray(ys)))
    if not math.isclose(accuracy, result["value"], rel_tol=0, abs_tol=1e-12):
        raise ValueError(f"full-test accuracy mismatch: {accuracy} vs {result['value']}")
    summary = {
        "source_rid": rid,
        "source_artifact_dir": str(source_dir),
        "source_checkpoint_sha256": hashlib.sha256(
            (source_dir / "best.ckpt").read_bytes()).hexdigest(),
        "source_peak_mem_mb": float(row["peak_mem_mb"]),
        "source_full_test_accuracy": result["value"],
        "revalidated_full_test_accuracy": accuracy,
        "full_test_metric_match": True,
        "evaluation_peak_mem_mb": torch.cuda.max_memory_allocated(args.device) / 1024**2,
        "peak_scope": "checkpoint_evaluation_only_not_training_peak",
        "task": common.TASK,
        "model": common.MODEL,
        "strategy": "lora",
        "split": "random",
        "seed": args.seed,
        "n_train": result["n_train"],
        "n_val": result["n_val"],
        "n_test": result["n_test"],
        "max_len": common.MAX_LEN,
        "train_batch_size": args.batch_size,
        "evaluation_batch_size": args.batch_size * 2,
        "protocol": result["protocol"],
        "best_epoch": result["best_epoch"],
        "split_evidence_match": True,
        "checkpoint": checkpoint,
        "cuda": runtime,
        "wall_sec": time.time() - started,
        "predictions": str(args.output_dir / f"ncrna_lora_s{args.seed}_random_predictions.npz"),
    }
    np.savez_compressed(summary["predictions"], y_true=np.asarray(ys), logits=logits)
    output.write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
