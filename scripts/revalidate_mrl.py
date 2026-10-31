import argparse
import json
import random
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import numpy as np
import torch

from rnafteval import valplateau as vp
from rnafteval.finetune_mrl import batches, encode_seqs
from rnafteval.models import load_model
from rnafteval.splits import prepare_convergence_splits
from rnafteval.strategies import apply_strategy, make_head
from rnafteval.tasks import mrl as mrl_task


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--device", type=int, default=0)
    args = parser.parse_args()
    assert torch.cuda.is_available(), "CUDA_UNAVAILABLE_ABORT"
    torch.cuda.set_device(args.device)
    device = f"cuda:{args.device}"
    args.output_dir.mkdir(parents=True, exist_ok=True)

    result = json.loads((args.artifact_dir / "result.json").read_text())
    assert result["run_id"] == "ft_rinalmomicro_mrl_full_s101_random_bestval_v1"
    assert result["strategy"] == "full" and result["seed"] == 101
    assert result["split"] == "random" and result["n_test"] == 7600
    torch.manual_seed(result["seed"])
    random.seed(result["seed"])

    split = mrl_task.load_official_split("/root/rna-ft-eval/data/beacon_raw/mean-ribosome-loading/data")
    train, test = split["train"], split["test"]
    train, val, test, evidence = prepare_convergence_splits(
        train, split.get("validation"), test, n_train=result["n_train"],
        sample_seed=result["seed"], family=False,
        validation_source="official_validation",
        evidence_path=str(args.output_dir / "reconstructed_split_evidence.json"),
        protocol=result["protocol"])
    assert len(test) == result["n_test"]
    assert evidence == result["data_evidence"], "split evidence mismatch"

    spec, tokenizer, backbone = load_model(result["model"], device)
    with torch.no_grad():
        probe = encode_seqs(tokenizer, [train[0]["seq"]], device, 64)
        width = backbone(**probe).last_hidden_state.shape[-1]
    backbone, _ = apply_strategy(backbone, "full", lora_rank=8)
    head = make_head("per-seq", width, 1).to(device)
    state = torch.load(args.artifact_dir / "best.ckpt", map_location=device,
                       weights_only=True)
    assert state["best_epoch"] == result["best_epoch"]
    vp.load_backbone_state_dict(backbone, state["backbone"])
    head.load_state_dict(state["head"])
    backbone.eval()
    head.eval()

    ys, ps = [], []
    with torch.no_grad():
        for batch in batches(test, 64):
            encoded = encode_seqs(tokenizer, [row["seq"] for row in batch], device, 64)
            y = torch.tensor([row["label"] for row in batch], dtype=torch.float32,
                             device=device)
            hidden = backbone(**encoded).last_hidden_state
            pad = encoded["attention_mask"] == 0
            pred = head(hidden, pad).squeeze(-1)
            ys.append(y.cpu().numpy())
            ps.append(pred.cpu().numpy())
    y_true = np.concatenate(ys)
    y_pred = np.concatenate(ps)
    pearson = float(np.corrcoef(y_true, y_pred)[0, 1])
    mse = float(np.mean((y_true - y_pred) ** 2))
    summary = {
        "run_id": result["run_id"], "n_test": len(test),
        "source_pearson_r": result["value"], "revalidated_pearson_r": pearson,
        "source_mse": result["mse"], "revalidated_mse": mse,
        "y_true_mean": float(y_true.mean()), "y_true_std": float(y_true.std()),
        "y_pred_mean": float(y_pred.mean()), "y_pred_std": float(y_pred.std()),
        "cuda_device": torch.cuda.get_device_name(args.device),
        "cuda_runtime": torch.version.cuda,
        "checkpoint_best_epoch": state["best_epoch"],
        "split_evidence_match": True,
    }
    np.savez_compressed(args.output_dir / "mrl_negative_predictions.npz",
                        y_true=y_true, y_pred=y_pred)
    (args.output_dir / "mrl_negative_revalidation.json").write_text(
        json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    assert abs(pearson - result["value"]) < 1e-6, "Pearson mismatch"
    assert abs(mse - result["mse"]) < 1e-6, "MSE mismatch"


if __name__ == "__main__":
    main()
