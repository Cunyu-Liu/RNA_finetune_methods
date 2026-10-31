import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "scripts"))

import torch
import mechanism_ncrna as common
import mechanism_spliceai as mechanism
from rnafteval import ledger


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--split", choices=("random", "family"), required=True)
    parser.add_argument("--device", type=int, default=0)
    parser.add_argument("--wait-free-gb", type=float, default=3.0)
    args = parser.parse_args()
    common.PERBASE_SOURCE_REGISTRY = args.registry
    summary = {"seed": args.seed, "split": args.split, "completed": [],
               "skipped": [], "deferred": []}
    for strategy in mechanism.STATES:
        diagnostic_dir = mechanism.ARTIFACT_ROOT / mechanism.diagnostic_run_id(
            strategy, args.split, args.seed)
        diagnostic_path = diagnostic_dir / "diagnostic.json"
        if diagnostic_path.is_file():
            diagnostic = json.loads(diagnostic_path.read_text())
            assert diagnostic["status"] == "diagnostic"
            summary["skipped"].append(strategy)
            continue
        if strategy != "pre":
            source_rid = mechanism.source_run_id(strategy, args.split, args.seed)
            row = ledger.by_run_id(source_rid)
            if row is None or row.get("status") != "done" or not row.get("out_dir") or not (
                    Path(row["out_dir"]) / "result.json").is_file():
                summary["deferred"].append({"strategy": strategy, "source_run_id": source_rid})
                continue
        run_args = argparse.Namespace(
            split=args.split, strategy=strategy, seed=args.seed, device=args.device,
            per_class_cap=512, batch_size=16, wait_free_gb=args.wait_free_gb,
            memory_poll_s=30)
        mechanism.run(run_args)
        summary["completed"].append(strategy)
        torch.cuda.empty_cache()
    output_dir = common.TEAMS_ROOT / "status" / "spliceai_mechanism_multiseed"
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / f"summary_s{args.seed}_{args.split}.json"
    output.write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    assert summary["completed"] or summary["skipped"], summary


if __name__ == "__main__":
    main()
