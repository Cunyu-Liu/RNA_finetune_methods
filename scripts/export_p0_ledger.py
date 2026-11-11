"""Export only proof-complete P0 runs into the established ledger schema."""
import argparse
import csv
import json
from pathlib import Path

from expansion_queue import load_jobs, proof_state

FIELDS = "run_id,model,task,strategy,split,seed,metric,value,n_train,n_val,n_test,best_epoch,best_val,epochs_trained,wall_sec,peak_mem_mb,lr,protocol,stop_reason,artifact_dir,resolved_artifact_dir,result_path,best_checkpoint,cuda_device,cuda_device_name,cuda_runtime_version,tokenizer_name_or_path".split(",")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs-json", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = []
    for job in load_jobs(args.jobs_json):
        if proof_state(job)[0] != "complete":
            continue
        result = json.loads(job.result_path.read_text())
        row = {key: result.get(key) for key in FIELDS}
        row.update(run_id=job.rid, artifact_dir=job.result_dir,
                   resolved_artifact_dir=job.result_dir, result_path=str(job.result_path),
                   best_checkpoint=str(Path(job.result_dir)/"best.ckpt"))
        runtime = result["runtime"]
        row.update(cuda_device=runtime["cuda_device"],
                   cuda_device_name=runtime["cuda_device_name"],
                   cuda_runtime_version=runtime["cuda_runtime_version"],
                   tokenizer_name_or_path=runtime["tokenizer_name_or_path"])
        rows.append(row)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({"complete_rows": len(rows), "output": str(args.output)}))


if __name__ == "__main__":
    main()
