"""Summarize the six preregistered P0 cells only from complete formal proof."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from expansion_queue import load_jobs, proof_state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs-json", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    source = Path(args.jobs_json)
    jobs = load_jobs(source)
    if len(jobs) != 18:
        raise ValueError("P0 requires exactly 18 runs")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    groups = {}
    for job in jobs:
        groups.setdefault((job.task, job.strategy, job.split), []).append(job)
    if len(groups) != 6:
        raise ValueError("P0 requires six scientific cells")
    summaries = []
    for (task, strategy, split), items in sorted(groups.items()):
        states = [proof_state(job)[0] for job in items]
        name = f"rinalmo650m_{task}_{strategy}_{split}.json"
        summary = {
            "model": "RiNALMo-650M", "task": task, "strategy": strategy, "split": split,
            "expected_seeds": [17, 29, 43], "status": "complete" if states == ["complete"]*3 else "incomplete",
            "proof_states": states, "source_jobs": str(source),
            "source_jobs_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "records": [],
        }
        if summary["status"] == "complete":
            for job in items:
                result = json.loads(job.result_path.read_text())
                plateau = json.loads(job.plateau_path.read_text())
                assert result["run_id"] == job.rid == plateau["run_id"]
                assert result["seed"] == job.seed and result["protocol"] == "bestval_v1"
                assert result["runtime"]["cuda_available"] is True
                assert plateau["status"] == "CONVERGED"
                assert (Path(job.result_dir)/"best.ckpt").stat().st_size > 0
                summary["records"].append({key: result[key] for key in (
                    "run_id", "seed", "value", "n_train", "n_test", "best_epoch", "best_val",
                    "epochs_trained", "wall_sec", "peak_mem_mb")})
            values = [row["value"] for row in summary["records"]]
            summary["mean"] = float(np.mean(values))
            summary["sample_sd"] = float(np.std(values, ddof=1))
            summary["interpretation"] = "one task/model/strategy/split cell; not a global strategy claim"
        path = args.output_dir / name
        path.write_text(json.dumps(summary, indent=2, allow_nan=False)+"\n")
        summaries.append({"file": str(path), "status": summary["status"],
                          "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    print(json.dumps(summaries, indent=2))


if __name__ == "__main__":
    main()
