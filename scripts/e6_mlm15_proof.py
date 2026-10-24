"""Verify one corrected E6 cell: ledger done + protocol/result consistency."""
import argparse
import json
import math
from pathlib import Path

from rnafteval import ledger


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("result_dir")
    parser.add_argument("model")
    parser.add_argument("strategy")
    parser.add_argument("seed", type=int)
    args = parser.parse_args()
    rid = ledger.run_id(args.model, "e6-forgetting", args.strategy,
                        args.seed, "s0-heldout", extra="_mlm15fix")
    row = ledger.by_run_id(rid)
    if not row or row.get("status") != "done":
        raise SystemExit("ledger is not done: " + rid)
    path = Path(args.result_dir) / "result.json"
    with path.open() as fh:
        result = json.load(fh)
    expected = {"run_id": rid, "model": args.model,
                "strategy": args.strategy, "seed": args.seed}
    for key, value in expected.items():
        if result.get(key) != value:
            raise SystemExit("result mismatch: " + key)
    if not str(result.get("protocol", "")).startswith("E6-v1-fixed-mask-mlm"):
        raise SystemExit("wrong E6 protocol")
    if result.get("mask_rate") != 0.15:
        raise SystemExit("wrong mask rate")
    for key in ("pre_nll_a", "pre_nll_b", "noise_band", "post_nll", "delta_nll"):
        if not isinstance(result.get(key), (int, float)) or not math.isfinite(result[key]):
            raise SystemExit("non-finite metric: " + key)
    print("E6_PROOF_OK", rid)


if __name__ == "__main__":
    main()
