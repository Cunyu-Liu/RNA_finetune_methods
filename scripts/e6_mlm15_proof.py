"""Verify one corrected E6 cell: ledger done + protocol/result consistency."""
import argparse
import json
import math
from pathlib import Path

from rnafteval import ledger
from rnafteval.e6_forget import TRAINING_SEED_PROTOCOL


def verify(result_dir, model, strategy, seed, ledger_task="e6-forgetting",
           extra="_mlm15fix_seedfix", result_task=None,
           protocol_prefix="E6-v1-fixed-mask-mlm"):
    rid = ledger.run_id(model, ledger_task, strategy, seed, "s0-heldout",
                        extra=extra)
    row = ledger.by_run_id(rid)
    if not row or row.get("status") != "done":
        raise SystemExit("ledger is not done: " + rid)
    path = Path(result_dir) / "result.json"
    with path.open() as fh:
        result = json.load(fh)
    expected = {"run_id": rid, "model": model,
                "strategy": strategy, "seed": seed, "split": "s0-heldout"}
    if result_task is not None:
        expected["task"] = result_task
    for key, value in expected.items():
        if result.get(key) != value:
            raise SystemExit("result mismatch: " + key)
    if not str(result.get("protocol", "")).startswith(protocol_prefix):
        raise SystemExit("wrong E6 protocol")
    if result.get("training_seed_protocol") != TRAINING_SEED_PROTOCOL:
        raise SystemExit("wrong training seed protocol")
    if result.get("mask_rate") != 0.15:
        raise SystemExit("wrong mask rate")
    if not isinstance(result.get("batch_size"), int) or result["batch_size"] < 1:
        raise SystemExit("invalid batch size")
    for key in ("pre_nll_a", "pre_nll_b", "noise_band", "post_nll", "delta_nll",
                "peak_mem_mb"):
        if not isinstance(result.get(key), (int, float)) or not math.isfinite(result[key]):
            raise SystemExit("non-finite metric: " + key)
    return rid


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("result_dir")
    parser.add_argument("model")
    parser.add_argument("strategy")
    parser.add_argument("seed", type=int)
    parser.add_argument("--ledger-task", default="e6-forgetting")
    parser.add_argument("--extra", default="_mlm15fix_seedfix")
    parser.add_argument("--result-task")
    parser.add_argument("--protocol-prefix", default="E6-v1-fixed-mask-mlm")
    args = parser.parse_args(argv)
    rid = verify(args.result_dir, args.model, args.strategy, args.seed,
                 ledger_task=args.ledger_task, extra=args.extra,
                 result_task=args.result_task,
                 protocol_prefix=args.protocol_prefix)
    print("E6_PROOF_OK", rid)


if __name__ == "__main__":
    main()
