"""Measure fixed-mask S0 forgetting from a formal downstream checkpoint."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import time

import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from rnafteval import valplateau as vp
from rnafteval.e6_forget import _LM_CLASS, _official_encoder, seed_training
from rnafteval.e6_forget_task import nll_eval, s0_heldout_seqs
from rnafteval.models import MODEL_SPECS, hf_path
from rnafteval.strategies import apply_strategy


def load_lm(model, device):
    import multimolecule
    from multimolecule import RnaTokenizer
    path = hf_path(MODEL_SPECS[model].repo)
    tokenizer = RnaTokenizer.from_pretrained(path)
    cls = getattr(multimolecule, _LM_CLASS[model])
    backbone = cls.from_pretrained(path, trust_remote_code=True)
    if hasattr(backbone, "lm_head") and hasattr(backbone.lm_head, "decoder"):
        decoder = backbone.lm_head.decoder
        if decoder is not None and hasattr(decoder, "bias") and decoder.bias is not None:
            with torch.no_grad():
                decoder.bias.zero_()
    return tokenizer, backbone.to(device)


def restore_lm_backbone(backbone, state, strategy):
    target = _official_encoder(backbone) if strategy == "full" else backbone
    core = target.m if hasattr(target, "m") else target
    if strategy == "full":
        incompatible = core.load_state_dict(state, strict=False)
        allowed = {"pooler.dense.weight", "pooler.dense.bias"}
        if incompatible.missing_keys or set(incompatible.unexpected_keys) - allowed:
            raise ValueError(f"MaskedLM encoder mismatch: {incompatible}")
        auxiliary = sorted(set(incompatible.unexpected_keys) & allowed)
        expected = state
    else:
        target_keys = set(vp.backbone_state_dict(target))
        expected = {}
        auxiliary = []
        for key, value in state.items():
            mapped = key
            if mapped not in target_keys and key.startswith("base_model.model."):
                mapped = "base_model.model.model." + key[len("base_model.model."):]
            if mapped not in target_keys:
                if key.startswith("base_model.model.pooler."):
                    auxiliary.append(key)
                    continue
                raise ValueError("unrecognized LoRA checkpoint key: " + key)
            expected[mapped] = value
        incompatible = core.load_state_dict(expected, strict=False)
        if incompatible.unexpected_keys or any(
                not key.startswith(("lm_head.", "base_model.model.lm_head."))
                for key in incompatible.missing_keys):
            raise ValueError(f"LoRA MaskedLM mismatch: {incompatible}")
    restored = vp.backbone_state_dict(target)
    for key, value in expected.items():
        if key in auxiliary:
            continue
        if key not in restored or not torch.equal(restored[key].detach().cpu(), value.detach().cpu()):
            raise ValueError("restored MaskedLM tensor mismatch: " + key)
    return auxiliary


def validate_source(result, plateau):
    if result["model"] not in _LM_CLASS:
        raise ValueError("only official RiNALMo models are supported")
    if result["task"] not in ("noncoding-rna-family", "mrl", "modification"):
        raise ValueError("unsupported task origin")
    if result["task"] == "noncoding-rna-family" and (
            result["model"] != "RiNALMo-650M" or result["strategy"] != "lora"):
        raise ValueError("preregistered ncRNA arm is 650M LoRA only")
    if result["split"] != "random" or result["seed"] not in (17, 29, 43):
        raise ValueError("formal random-split seed required")
    if result["strategy"] not in ("lora", "full"):
        raise ValueError("only LoRA/full forgetting comparisons are supported")
    expected_lr = 3e-4 if result["strategy"] == "lora" else 1e-5
    if not math.isclose(result["lr"], expected_lr, rel_tol=0, abs_tol=1e-12):
        raise ValueError("source does not use the preregistered default LR")
    if result.get("protocol") != "bestval_v1" or result.get("smoke"):
        raise ValueError("formal bestval source required")
    if plateau["run_id"] != result["run_id"] or plateau["status"] != "CONVERGED":
        raise ValueError("source convergence proof mismatch")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-rid", required=True)
    parser.add_argument("--source-result-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--device", type=int, default=0)
    parser.add_argument("--batch-size", type=int, required=True)
    parser.add_argument("--n-holdout", type=int, default=2000)
    parser.add_argument("--mask-rate", type=float, default=0.15)
    args = parser.parse_args()
    if args.batch_size <= 0 or args.n_holdout <= 0 or not 0 < args.mask_rate <= 1:
        raise ValueError("invalid evaluation configuration")
    if not str(args.output_dir).startswith("/teams/HoulabData_1788502323/liucunyu/"):
        raise ValueError("new artifacts must be written to teams")
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA_UNAVAILABLE_ABORT")
    torch.cuda.set_device(args.device)
    device = f"cuda:{args.device}"
    started = time.time()
    result_path = args.source_result_dir / "result.json"
    result = json.loads(result_path.read_text())
    plateau = json.loads((args.source_result_dir / "plateau.json").read_text())
    if result["run_id"] != args.source_rid:
        raise ValueError("source RID mismatch")
    validate_source(result, plateau)
    error = vp.checkpoint_proof_error(args.source_result_dir, result)
    if error:
        raise ValueError(error)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output = args.output_dir / "result.json"
    if output.exists():
        raise FileExistsError(output)
    seed_training(201)
    torch.cuda.reset_peak_memory_stats(args.device)
    holdout = s0_heldout_seqs(args.n_holdout)
    holdout_sha = hashlib.sha256(json.dumps(holdout, ensure_ascii=False).encode()).hexdigest()
    tokenizer, backbone = load_lm(result["model"], device)
    runtime = vp.runtime_evidence(tokenizer, device)
    pre_a = nll_eval(backbone, tokenizer, holdout, device, bs=args.batch_size,
                     shuffle_seed=201, eval_seed=201, mask_rate=args.mask_rate)
    pre_b = nll_eval(backbone, tokenizer, holdout, device, bs=args.batch_size,
                     shuffle_seed=707, eval_seed=707, mask_rate=args.mask_rate)
    del backbone
    torch.cuda.empty_cache()
    tokenizer, backbone = load_lm(result["model"], device)
    backbone, _ = apply_strategy(backbone, result["strategy"], lora_rank=8)
    checkpoint = args.source_result_dir / "best.ckpt"
    state = torch.load(checkpoint, map_location=device, weights_only=True)
    if state["best_epoch"] != plateau["best_epoch"]:
        raise ValueError("source checkpoint epoch mismatch")
    auxiliary_keys = restore_lm_backbone(backbone, state["backbone"], result["strategy"])
    if result["strategy"] == "lora" and hasattr(backbone, "merge_and_unload"):
        backbone = backbone.merge_and_unload()
    backbone.eval()
    post = nll_eval(backbone, tokenizer, holdout, device, bs=args.batch_size,
                    shuffle_seed=201, eval_seed=201, mask_rate=args.mask_rate)
    noise = abs(pre_b - pre_a)
    values = {"pre_nll_a": pre_a, "pre_nll_b": pre_b, "noise_band": noise,
              "post_nll": post, "delta_nll": post - pre_a}
    if not all(math.isfinite(value) for value in values.values()):
        raise FloatingPointError("nonfinite forgetting metric")
    summary = {
        "run_id": f"e6ckpt_{args.source_rid}_fixedmlm15",
        "source_rid": args.source_rid,
        "source_result": str(result_path),
        "source_checkpoint": str(checkpoint),
        "source_checkpoint_sha256": hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
        "source_protocol": result["protocol"],
        "source_best_epoch": plateau["best_epoch"],
        "source_convergence": plateau["status"],
        "source_runtime": result["runtime"],
        "model": result["model"], "task_origin": result["task"],
        "strategy": result["strategy"], "seed": result["seed"],
        "source_split": result["split"], "split": "s0-heldout",
        "lr": result["lr"], "n_holdout": len(holdout),
        "holdout_sha256": holdout_sha,
        "mask_rate": args.mask_rate, "mask_seed_pre_post": 201,
        "mask_seed_noise": 707, "batch_size": args.batch_size,
        **values, "forgot": (post - pre_a) > max(noise, 1e-6),
        "protocol": "E6-checkpoint-fixed-mask-mlm-v1",
        "non_mlm_auxiliary_keys_not_required": auxiliary_keys,
        "restored_tensor_match": True, "cuda": runtime,
        "evaluation_peak_mem_mb": torch.cuda.max_memory_allocated(args.device)/1024**2,
        "wall_sec": time.time()-started,
        "acceptance_eligible": True,
        "interpretation": "checkpoint-only S0 forgetting; task origins and default LR fixed; not a causal global law",
    }
    temporary = output.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(summary, indent=2, allow_nan=False)+"\n")
    temporary.replace(output)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
