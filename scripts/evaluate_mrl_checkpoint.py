"""Re-evaluate an external MRL best checkpoint and preserve per-sample predictions."""
import argparse
import hashlib
import json
import math
import random
import sys
import time
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from rnafteval import valplateau as vp
from rnafteval.finetune_mrl import batches, encode_seqs
from rnafteval.models import load_model
from rnafteval.splits import prepare_convergence_splits
from rnafteval.strategies import apply_strategy, make_head
from rnafteval.tasks import mrl as mrl_task


def pearson(y_true, y_pred):
    if float(np.std(y_pred)) < 1e-12:
        return None
    value = float(np.corrcoef(y_true, y_pred)[0, 1])
    return value if math.isfinite(value) else None


def load_split(split_name, seed, n_train, output_dir):
    if split_name == "family":
        import pyarrow.parquet as pq
        table = pq.read_table("/root/rna-ft-eval/data/family_splits/mrl.parquet").to_pydict()
        records = [{"seq": s, "label": float(label), "cluster": cluster}
                   for s, label, cluster in zip(table["seq"], table["label"], table["cluster_id"])]
        train = [row for row, part in zip(records, table["split"]) if part == "train"]
        test = [row for row, part in zip(records, table["split"]) if part == "test"]
        val = [row for row, part in zip(records, table["split"]) if part == "val"] or None
    elif split_name == "random":
        split = mrl_task.load_official_split("/root/rna-ft-eval/data/beacon_raw/mean-ribosome-loading/data")
        train, test, val = split["train"], split["test"], split.get("validation")
    else:
        raise ValueError(split_name)
    return prepare_convergence_splits(
        train, val, test, n_train=n_train, sample_seed=seed,
        family=split_name == "family",
        validation_source="family_validation" if split_name == "family" else "official_validation",
        evidence_path=str(output_dir / "split_evidence.json"), protocol="bestval_v1")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--reference-result", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--device", type=int, default=0)
    parser.add_argument("--batch-size", type=int, required=True)
    parser.add_argument("--wait-free-gb", type=float, default=10.0)
    args = parser.parse_args()
    if args.batch_size <= 0 or args.wait_free_gb < 0:
        raise ValueError("batch-size must be positive and memory gate nonnegative")
    if not str(args.output_dir).startswith("/teams/HoulabData_1788502323/liucunyu/"):
        raise ValueError("prediction artifacts must remain on teams")
    assert torch.cuda.is_available(), "CUDA_UNAVAILABLE_ABORT"
    torch.cuda.set_device(args.device)
    device = f"cuda:{args.device}"
    args.output_dir.mkdir(parents=True, exist_ok=True)
    started = time.time()
    result = json.loads(args.reference_result.read_text())
    rid = result["run_id"]
    if not rid.endswith("_reval20261111") or rid != args.artifact_dir.name:
        raise ValueError("external retest RID and artifact directory differ")
    if result.get("model") not in ("NucleicBERT", "AIDO.RNA-1.6B"):
        raise ValueError("only external MRL retest models are supported")
    if result.get("task") != "mrl" or result.get("strategy") != "full":
        raise ValueError("only full-FT MRL checkpoints are supported")
    if result.get("protocol") != "bestval_v1":
        raise ValueError("bestval_v1 is required")
    proof_error = vp.checkpoint_proof_error(args.artifact_dir, result)
    if proof_error:
        raise ValueError(proof_error)
    plateau = json.loads((args.artifact_dir / "plateau.json").read_text())
    if plateau["run_id"] != rid or plateau["status"] != "CONVERGED":
        raise ValueError("convergence identity or status mismatch")
    seed, split_name = result["seed"], result["split"]
    torch.manual_seed(seed)
    random.seed(seed)
    train, val, test, evidence = load_split(split_name, seed, result["n_train"], args.output_dir)
    if evidence != result["data_evidence"] or len(test) != result["n_test"]:
        raise ValueError("split evidence or full-test size mismatch")
    del train, val
    while torch.cuda.mem_get_info(args.device)[0] < args.wait_free_gb * 1024**3:
        print("WAIT_CUDA_MEMORY", flush=True)
        time.sleep(120)
    spec, tokenizer, backbone = load_model(result["model"], device)
    with torch.no_grad():
        probe = encode_seqs(tokenizer, [test[0]["seq"]], device, 64)
        width = backbone(**probe).last_hidden_state.shape[-1]
    backbone, _ = apply_strategy(backbone, "full", lora_rank=8)
    head = make_head("per-seq", width, 1).to(device)
    state = torch.load(args.artifact_dir / "best.ckpt", map_location=device, weights_only=True)
    if state["best_epoch"] != plateau["best_epoch"]:
        raise ValueError("best checkpoint epoch mismatch")
    vp.load_backbone_state_dict(backbone, state["backbone"])
    head.load_state_dict(state["head"])
    for name, current in (("backbone", vp.backbone_state_dict(backbone)), ("head", head.state_dict())):
        if current.keys() != state[name].keys():
            raise ValueError(name + " tensor keys differ")
        for key in current:
            if not torch.equal(current[key].detach().cpu(), state[name][key].detach().cpu()):
                raise ValueError(name + " restored tensor differs: " + key)
    backbone.eval()
    head.eval()
    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats(args.device)
    ys, ps = [], []
    with torch.no_grad():
        for batch in batches(test, args.batch_size):
            encoded = encode_seqs(tokenizer, [row["seq"] for row in batch], device, 64)
            y = torch.tensor([row["label"] for row in batch], dtype=torch.float32, device=device)
            hidden = backbone(**encoded).last_hidden_state
            pad = encoded["attention_mask"] == 0
            pred = head(hidden, pad).squeeze(-1)
            ys.append(y.cpu().numpy())
            ps.append(pred.cpu().numpy())
    y_true, y_pred = np.concatenate(ys), np.concatenate(ps)
    if not np.isfinite(y_pred).all():
        raise ValueError("nonfinite predictions require separate failure diagnosis")
    value = pearson(y_true, y_pred)
    source_value = result.get("value")
    source_mse = result.get("mse")
    if not isinstance(source_mse, (int, float)) or not math.isfinite(source_mse):
        raise ValueError("finite source MSE is required")
    mse = float(np.mean((y_true-y_pred)**2))
    mse_match = math.isclose(mse, source_mse, rel_tol=2e-5, abs_tol=2e-7)
    if isinstance(source_value, (int, float)) and math.isfinite(source_value):
        metric_match = value is not None and math.isclose(value, source_value, rel_tol=2e-5, abs_tol=2e-7)
    else:
        metric_match = value is None and float(y_pred.std()) < 1e-6
    metric_match = metric_match and mse_match
    summary = {
        "run_id": rid, "model": result["model"], "task": "mrl", "strategy": "full",
        "seed": seed, "split": split_name, "protocol": "bestval_v1",
        "n_train": result["n_train"], "n_test": len(test),
        "source_pearson_r": source_value, "revalidated_pearson_r": value,
        "source_mse": source_mse, "revalidated_mse": mse, "full_test_mse_match": mse_match,
        "full_test_metric_match": metric_match,
        "nonfinite_reason": "constant_prediction" if value is None else None,
        "y_true_mean": float(y_true.mean()), "y_true_std": float(y_true.std()),
        "y_pred_mean": float(y_pred.mean()), "y_pred_std": float(y_pred.std()),
        "best_epoch": plateau["best_epoch"], "plateau_status": plateau["status"],
        "split_evidence_match": True, "restored_tensor_match": True,
        "source_checkpoint_sha256": hashlib.sha256((args.artifact_dir/"best.ckpt").read_bytes()).hexdigest(),
        "cuda_available": True, "cuda_device": device,
        "cuda_device_name": torch.cuda.get_device_name(args.device), "cuda_runtime": torch.version.cuda,
        "max_len": 64, "train_batch_size": args.batch_size // 2,
        "evaluation_batch_size": args.batch_size,
        "evaluation_peak_mem_mb": torch.cuda.max_memory_allocated(args.device)/1024**2,
        "peak_scope": "checkpoint_evaluation_only_not_training_peak",
        "wall_sec": time.time()-started,
    }
    predictions = args.output_dir / f"{rid}_predictions.npz"
    summary["predictions"] = str(predictions)
    np.savez_compressed(predictions, y_true=y_true, y_pred=y_pred)
    summary["predictions_sha256"] = hashlib.sha256(predictions.read_bytes()).hexdigest()
    (args.output_dir / f"{rid}_evaluation.json").write_text(json.dumps(summary, indent=2, allow_nan=False)+"\n")
    print(json.dumps(summary, indent=2))
    if not metric_match:
        raise ValueError("revalidated full-test differs from source; evidence preserved")


if __name__ == "__main__":
    main()
