"""Run registered RiNALMo checkpoint evaluations only after source proof."""
import argparse
import concurrent.futures
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time

import torch

from expansion_queue import _parse_job, proof_state

METRICS = ("pre_nll_a", "pre_nll_b", "noise_band", "post_nll", "delta_nll")


def valid_result(record):
    path = Path(record["result_dir"]) / "result.json"
    if not path.is_file():
        return False
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        return False
    return (data.get("run_id") == record["evaluation_id"]
            and data.get("source_rid") == record["source_job"]["rid"]
            and data.get("protocol") == "E6-checkpoint-fixed-mask-mlm-v1"
            and data.get("restored_tensor_match") is True
            and data.get("acceptance_eligible") is True
            and data.get("cuda", {}).get("cuda_available") is True
            and all(isinstance(data.get(key), (int, float)) and math.isfinite(data[key])
                    for key in METRICS)
            and len(data.get("holdout_sha256", "")) == 64
            and Path(data.get("source_checkpoint", "")).is_file())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs-json", type=Path, required=True)
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--poll-s", type=int, default=300)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    if args.workers < 1 or args.poll_s <= 0:
        raise ValueError("invalid monitor settings")
    records = json.loads(args.jobs_json.read_text())
    if len(records) != 39 or len({r["evaluation_id"] for r in records}) != 39:
        raise ValueError("39 unique evaluations required")
    args.state_dir.mkdir(parents=True, exist_ok=True)
    source_states = {}
    while True:
        ready, waiting = [], []
        for record in records:
            rid = record["source_job"]["rid"]
            if rid not in source_states or source_states[rid][0] != "complete":
                source_states[rid] = proof_state(_parse_job(record["source_job"], 0))
            if valid_result(record):
                continue
            if source_states[rid][0] == "complete":
                ready.append(record)
            else:
                waiting.append({"rid": rid, "state": source_states[rid][0]})
        completed = sum(valid_result(record) for record in records)
        state = {"total": len(records), "completed": completed, "ready": len(ready),
                 "waiting_sources": waiting, "updated_at": time.time()}
        temporary = args.state_dir / "state.json.tmp"
        temporary.write_text(json.dumps(state, indent=2)+"\n")
        os.replace(temporary, args.state_dir / "state.json")
        print(json.dumps({key: value for key, value in state.items() if key != "waiting_sources"}), flush=True)
        if completed == len(records) or args.verify_only:
            return
        running = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
            while ready or running:
                while ready and len(running) < args.workers:
                    record = next((r for r in ready if torch.cuda.mem_get_info(0)[0] >= r["need_gb"]*1024**3), None)
                    if record is None:
                        break
                    ready.remove(record)
                    out_dir = Path(record["result_dir"])
                    out_dir.mkdir(parents=True, exist_ok=True)
                    log = (out_dir / "evaluation.log").open("a")
                    future = pool.submit(subprocess.run, [
                        sys.executable, str(Path(__file__).with_name("evaluate_rinalmo_forgetting.py")),
                        "--source-rid", record["source_job"]["rid"],
                        "--source-result-dir", record["source_job"]["result_dir"],
                        "--output-dir", record["result_dir"], "--device", "0",
                        "--batch-size", str(record["batch_size"]),
                        "--n-holdout", str(record["n_holdout"]),
                        "--mask-rate", str(record["mask_rate"]),
                    ], stdout=log, stderr=subprocess.STDOUT)
                    running[future] = (record, log)
                if not running:
                    break
                done, _ = concurrent.futures.wait(running, timeout=args.poll_s,
                                                  return_when=concurrent.futures.FIRST_COMPLETED)
                for future in done:
                    record, log = running.pop(future)
                    log.close()
                    if future.result().returncode != 0 or not valid_result(record):
                        raise RuntimeError("evaluation proof failed: " + record["evaluation_id"])
            if not ready and any(not valid_result(r) for r in records):
                time.sleep(args.poll_s)


if __name__ == "__main__":
    main()
