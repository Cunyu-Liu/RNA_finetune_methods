"""Register checkpoint-only RiNALMo forgetting evaluations without retraining sources."""
import argparse
import json
from pathlib import Path

from expansion_queue import _parse_job, proof_state
from rnafteval import ledger

TEAMS = Path("/teams/HoulabData_1788502323/liucunyu/rna-ft-eval")
MODELS = {
    "RiNALMo-micro": (32, 8, 32, 10),
    "RiNALMo-mega": (8, 16, 16, 18),
    "RiNALMo-650M": (8, 28, 4, 20),
}
TASKS = {
    "noncoding-rna-family": ("rnafteval.finetune_clf", "ACC"),
    "mrl": ("rnafteval.finetune_mrl", "PEARSON_R"),
    "modification": ("rnafteval.finetune_base", "AUC"),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--coverage-output", type=Path, required=True)
    args = parser.parse_args()
    records = []
    for model, (train_batch, train_need, eval_batch, eval_need) in MODELS.items():
        for task, (module, metric) in TASKS.items():
            for strategy in ("lora", "full"):
                if task == "noncoding-rna-family" and (
                        strategy == "full" or model != "RiNALMo-650M"):
                    continue
                lr = "3e-4" if strategy == "lora" else "1e-5"
                for seed in (17, 29, 43):
                    rid = ledger.run_id(model, task, strategy, seed, "random", "_bestval_v1")
                    if strategy == "full":
                        rid = ledger.run_id(model, task, strategy, seed, "random", "_lr1e-05_bestval_v1")
                    row = ledger.by_run_id(rid)
                    source_dir = row["out_dir"] if row is not None else str(TEAMS/"artifacts"/rid)
                    source_job = {
                        "task": task, "model": model, "strategy": strategy, "split": "random",
                        "seed": seed, "lr": lr, "rank": 8,
                        "n_train": 0 if task == "noncoding-rna-family" else 20000,
                        "protocol": "bestval_v1", "rid": rid, "result_dir": source_dir,
                        "module": module, "expected_metric": metric, "need_gb": train_need,
                        "args": ["--converge", "--convergence-mode", "bestval",
                                 "--batch-size", str(train_batch), "--rank", "8",
                                 "--n-train", "0" if task == "noncoding-rna-family" else "20000",
                                 "--lr", lr],
                    }
                    job = _parse_job(source_job, len(records))
                    state, reason = proof_state(job)
                    evaluation_id = f"e6ckpt_{rid}_fixedmlm15"
                    records.append({
                        "evaluation_id": evaluation_id, "source_job": source_job,
                        "source_state": state, "source_reason": reason,
                        "result_dir": str(TEAMS/"artifacts/e6_checkpoint_20261112"/evaluation_id),
                        "batch_size": eval_batch, "need_gb": eval_need,
                        "mask_rate": 0.15, "n_holdout": 2000,
                    })
    if len(records) != 39 or len({r["evaluation_id"] for r in records}) != 39:
        raise ValueError("expected 39 unique checkpoint evaluations")
    if len({r["result_dir"] for r in records}) != 39:
        raise ValueError("duplicate evaluation output")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(records, indent=2)+"\n")
    coverage = {"total": len(records)}
    for record in records:
        coverage[record["source_state"]] = coverage.get(record["source_state"], 0)+1
    coverage["records"] = records
    args.coverage_output.write_text(json.dumps(coverage, indent=2)+"\n")
    print(json.dumps({k: v for k, v in coverage.items() if k != "records"}, indent=2))


if __name__ == "__main__":
    main()
