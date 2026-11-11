"""Independently diagnose a converged external MRL checkpoint with constant output."""
import argparse
import hashlib
import json
from pathlib import Path
import random
import sys
import time

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from evaluate_mrl_checkpoint import load_split, pearson
from rnafteval import valplateau as vp
from rnafteval.finetune_mrl import batches, encode_seqs
from rnafteval.models import load_model
from rnafteval.strategies import apply_strategy, make_head


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job-json", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--device", type=int, default=0)
    parser.add_argument("--batch-size", type=int, required=True)
    parser.add_argument("--wait-free-gb", type=float, default=10)
    args = parser.parse_args()
    job = json.loads(args.job_json.read_text())
    if job["model"] not in ("NucleicBERT", "AIDO.RNA-1.6B") or job["strategy"] != "full":
        raise ValueError("external full-FT MRL job required")
    if job["task"] != "mrl" or job["protocol"] != "bestval_v1":
        raise ValueError("external bestval MRL job required")
    rid = job["rid"]
    if not rid.endswith("_reval20261111"):
        raise ValueError("new external retest RID required")
    artifact = Path(job["result_dir"])
    plateau = json.loads((artifact / "plateau.json").read_text())
    if plateau["run_id"] != rid or plateau["status"] != "CONVERGED":
        raise ValueError("converged source checkpoint required")
    if plateau.get("stop_reason") != "validation_no_improvement_patience":
        raise ValueError("unexpected stopping reason")
    error = vp.checkpoint_proof_error(artifact, plateau)
    if error:
        raise ValueError(error)
    if not str(args.output_dir).startswith("/teams/HoulabData_1788502323/liucunyu/"):
        raise ValueError("diagnostics must be written to teams")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    assert torch.cuda.is_available(), "CUDA_UNAVAILABLE_ABORT"
    torch.cuda.set_device(args.device)
    device = f"cuda:{args.device}"
    seed = job["seed"]
    torch.manual_seed(seed)
    random.seed(seed)
    train, val, test, evidence = load_split(job["split"], seed, job["n_train"], args.output_dir)
    if evidence != json.loads((artifact / "split_evidence.json").read_text()):
        raise ValueError("source split evidence mismatch")
    del train, val
    while torch.cuda.mem_get_info(args.device)[0] < args.wait_free_gb * 1024**3:
        print("WAIT_CUDA_MEMORY", flush=True)
        time.sleep(120)
    started = time.time()
    spec, tokenizer, backbone = load_model(job["model"], device)
    with torch.no_grad():
        probe = encode_seqs(tokenizer, [test[0]["seq"]], device, 64)
        width = backbone(**probe).last_hidden_state.shape[-1]
    backbone, _ = apply_strategy(backbone, "full", lora_rank=8)
    head = make_head("per-seq", width, 1).to(device)
    checkpoint = artifact / "best.ckpt"
    state = torch.load(checkpoint, map_location=device, weights_only=True)
    if state["best_epoch"] != plateau["best_epoch"]:
        raise ValueError("best checkpoint epoch mismatch")
    vp.load_backbone_state_dict(backbone, state["backbone"])
    head.load_state_dict(state["head"])
    for name, current in (("backbone", vp.backbone_state_dict(backbone)), ("head", head.state_dict())):
        if current.keys() != state[name].keys():
            raise ValueError(name + " tensor keys differ")
        for key in current:
            if not torch.equal(current[key].detach().cpu(), state[name][key].detach().cpu()):
                raise ValueError(name + " tensor mismatch: " + key)
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
            prediction = head(hidden, pad).squeeze(-1)
            ys.append(y.cpu().numpy())
            ps.append(prediction.cpu().numpy())
    y_true, y_pred = np.concatenate(ys), np.concatenate(ps)
    if not np.isfinite(y_pred).all():
        raise ValueError("nonfinite predictions need a different failure diagnosis")
    value = pearson(y_true, y_pred)
    pred_std = float(y_pred.std())
    if value is not None or pred_std >= 1e-6:
        raise ValueError("not a constant-output candidate; do not exclude")
    summary = {
        "run_id": rid, "model": job["model"], "task": "mrl", "strategy": "full",
        "seed": seed, "split": job["split"], "protocol": "bestval_v1",
        "n_train": job["n_train"], "n_test": len(test),
        "revalidated_pearson_r": None, "revalidated_mse": float(np.mean((y_true-y_pred)**2)),
        "nonfinite_reason": "constant_prediction", "candidate_eligible": False,
        "y_true_mean": float(y_true.mean()), "y_true_std": float(y_true.std()),
        "y_pred_mean": float(y_pred.mean()), "y_pred_std": pred_std,
        "checkpoint_best_epoch": plateau["best_epoch"],
        "plateau_status": plateau["status"], "stop_reason": plateau["stop_reason"],
        "split_evidence_match": True, "restored_tensor_match": True,
        "source_checkpoint_sha256": hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
        "cuda_available": True, "cuda_device": device,
        "cuda_device_name": torch.cuda.get_device_name(args.device),
        "cuda_runtime": torch.version.cuda, "batch_size": args.batch_size,
        "evaluation_peak_mem_mb": torch.cuda.max_memory_allocated(args.device)/1024**2,
        "wall_sec": time.time()-started,
    }
    predictions = args.output_dir / f"{rid}_predictions.npz"
    np.savez_compressed(predictions, y_true=y_true, y_pred=y_pred)
    summary["predictions"] = str(predictions)
    summary["predictions_sha256"] = hashlib.sha256(predictions.read_bytes()).hexdigest()
    (args.output_dir / f"{rid}_revalidation.json").write_text(json.dumps(summary, indent=2, allow_nan=False)+"\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
