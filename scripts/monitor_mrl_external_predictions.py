"""Evaluate completed external MRL jobs once, without duplicating proof or training."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from expansion_queue import load_jobs, proof_state


def evaluation_path(output_dir, rid):
    return output_dir / rid / f"{rid}_evaluation.json"


def is_valid(path, rid):
    if not path.is_file():
        return False
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        return False
    return (data.get("run_id") == rid and data.get("full_test_metric_match") is True
            and data.get("split_evidence_match") is True
            and data.get("restored_tensor_match") is True
            and data.get("cuda_available") is True
            and isinstance(data.get("y_pred_std"), float)
            and Path(data.get("predictions", "")).is_file())


def evaluation_env():
    return dict(os.environ, PYTHONPATH=os.pathsep.join(
        ["/root/rna-ft-eval/pypath", ".", "scripts"]))


def evaluation_batch_size(model):
    return 2 if model == "AIDO.RNA-1.6B" else 16


def should_exit(args, jobs, evaluated):
    return args.once or (args.exit_when_complete and jobs and evaluated == len(jobs))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs-json", action="append", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--poll-s", type=int, default=300)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--exit-when-complete", action="store_true")
    args = parser.parse_args()
    if args.poll_s <= 0:
        raise ValueError("poll-s must be positive")
    while True:
        jobs = []
        for path in args.jobs_json:
            if Path(path).is_file():
                jobs.extend(load_jobs(path))
        if len({job.rid for job in jobs}) != len(jobs):
            raise ValueError("duplicate external RID")
        complete, pending, evaluated = 0, [], 0
        for job in jobs:
            state, reason = proof_state(job)
            if state != "complete":
                pending.append({"rid": job.rid, "state": state, "reason": reason})
                continue
            complete += 1
            destination = evaluation_path(args.output_dir, job.rid)
            if is_valid(destination, job.rid):
                evaluated += 1
                continue
            out_dir = args.output_dir / job.rid
            out_dir.mkdir(parents=True, exist_ok=True)
            log = out_dir / "evaluation.log"
            with log.open("a") as handle:
                subprocess.run([
                    sys.executable, str(Path(__file__).with_name("evaluate_mrl_checkpoint.py")),
                    "--artifact-dir", job.result_dir, "--reference-result", str(job.result_path),
                    "--output-dir", str(out_dir), "--device", "0", "--wait-free-gb", "10",
                    "--batch-size", str(evaluation_batch_size(job.model)),
                ], check=True, stdout=handle, stderr=subprocess.STDOUT,
                    env=evaluation_env())
            if not is_valid(destination, job.rid):
                raise RuntimeError("evaluation did not produce complete prediction proof: " + job.rid)
            evaluated += 1
        status = {"registered": len(jobs), "complete": complete, "evaluated": evaluated,
                  "pending": pending, "updated_at": time.time()}
        args.output_dir.mkdir(parents=True, exist_ok=True)
        temporary = args.output_dir / "state.json.tmp"
        temporary.write_text(json.dumps(status, indent=2)+"\n")
        os.replace(temporary, args.output_dir / "state.json")
        print(json.dumps({k: v for k, v in status.items() if k != "pending"}), flush=True)
        if should_exit(args, jobs, evaluated):
            return
        time.sleep(args.poll_s)


if __name__ == "__main__":
    main()
