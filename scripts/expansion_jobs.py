#!/usr/bin/env python3
"""Derive executable expansion jobs from the task runners' own RID rules.

The registry is an execution manifest, not a scientific completion claim.
Only the explicitly requested wave is emitted; current corrected lanes and
specialized rank8/E6 lanes are not duplicated here.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from types import SimpleNamespace

from rnafteval import valplateau as vp

from rnafteval import (finetune_base, finetune_clf, finetune_mrl,
                       finetune_one, finetune_ssp, ledger)

ROOT = Path(ledger.ARTIFACT_ROOT)
MODELS = ("RiNALMo-micro", "RiNALMo-mega", "RiNALMo-650M",
          "ERNIE-RNA", "RNA-FM")
TASK_MODULES = {
    "noncoding-rna-family": finetune_clf,
    "crispr-off-target": finetune_clf,
    "mrl": finetune_mrl,
    "modification": finetune_base,
    "secondary-structure": finetune_ssp,
}
METRICS = {
    "noncoding-rna-family": "ACC", "crispr-off-target": "PRAUC",
    "mrl": "PEARSON_R", "modification": "AUC",
    "secondary-structure": "F1", "spliceai": "MACRO_F1",
    "degradation": "PCC", "ssi": "PCC",
}
DEFAULTS = {
    "noncoding-rna-family": {"batch": 16, "n_train": 0, "epochs": 10},
    "crispr-off-target": {"batch": 8, "n_train": 0, "epochs": 10},
    "mrl": {"batch": 32, "n_train": 20000, "epochs": 3},
    "modification": {"batch": 32, "n_train": 20000, "epochs": 3},
    "secondary-structure": {"batch": 4, "n_train": 2000, "n_test": 400,
                            "epochs": 3},
    "spliceai": {"batch": 16, "n_train": 0, "epochs": 6},
    "degradation": {"batch": 8, "n_train": 0, "epochs": 3},
    "ssi": {"batch": 8, "n_train": 0, "epochs": 3},
}


def job_for(task, model, strategy, split, seed, protocol="bestval_v1",
             n_train=None, rank=8, out_suffix="", module=None,
             max_len=None, n_test=None, batch_size=None, need_gb=None,
             lr=None, smoke=False, dense_clusters=False):
    runner = module or TASK_MODULES[task]
    config = DEFAULTS[task]
    n_train = config["n_train"] if n_train is None else n_train
    lr = lr or ("1e-5" if strategy == "full" else "3e-4")
    batch_size = batch_size or config["batch"]
    n_test = n_test if n_test is not None else config.get("n_test")
    mode = "bestval" if protocol == "bestval_v1" else "plateau"
    args = SimpleNamespace(lr=float(lr), rank=rank, n_train=n_train,
                           epochs=config["epochs"], smoke=smoke,
                           converge=True, convergence_mode=mode,
                           out_suffix=out_suffix, n_test=n_test,
                           random_init=False, dense_clusters=dense_clusters)
    if dense_clusters and (task != "noncoding-rna-family" or split != "family"
                           or n_train <= 0 or runner is not finetune_one):
        raise ValueError("dense clusters require finetune_one, family split and n_train > 0")
    if protocol != vp.PROTOCOL and protocol != vp.BESTVAL_PROTOCOL:
        raise ValueError("unsupported protocol: " + protocol)
    extra = runner._run_extra(args)
    rid = ledger.run_id(model, task, strategy, seed, split, extra=extra)
    module_name = runner.__name__
    job = {
        "task": task, "model": model, "strategy": strategy, "split": split,
        "seed": seed, "lr": lr, "rank": rank, "n_train": n_train,
        "protocol": protocol, "rid": rid, "dense_clusters": dense_clusters,
        "result_dir": str(ROOT / rid),
        "module": module_name, "expected_metric": METRICS[task],
        "need_gb": need_gb if need_gb is not None else (
            8.0 if model == "RiNALMo-micro" else
            16.0 if model in ("RiNALMo-mega", "ERNIE-RNA", "RNA-FM") else 28.0),
        "args": ["--converge", "--convergence-mode", mode,
                 "--batch-size", str(batch_size), "--rank", str(rank),
                 "--n-train", str(n_train), "--lr", lr],
    }
    if out_suffix:
        job["args"] += ["--out-suffix", out_suffix]
    if dense_clusters:
        job["args"] += ["--dense-clusters"]
    if max_len is not None:
        job["args"] += ["--max-len", str(max_len)]
    if n_test is not None:
        job["args"] += ["--n-test", str(n_test)]
    if smoke:
        job["args"] += ["--smoke"]
    if module is not None:
        job["result_dir"] = str(ROOT / rid)
    return job


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--models", default=",".join(MODELS))
    parser.add_argument("--tasks", default=",".join(TASK_MODULES))
    parser.add_argument("--strategies", default="frozen,lora,full")
    parser.add_argument("--protocol", choices=("bestval_v1", "valplateau_v2"),
                        default="bestval_v1")
    parser.add_argument("--lane", choices=("complementary", "all"),
                        default="complementary",
                        help="exclude cells owned by specialized MRL/m6A/rank8 lanes")
    args = parser.parse_args(argv)
    jobs = []
    for model in args.models.split(","):
        for task in args.tasks.split(","):
            for strategy in args.strategies.split(","):
                if args.lane == "complementary":
                    if task in ("mrl", "modification") and strategy in ("lora", "full"):
                        continue
                    if (task == "noncoding-rna-family"
                            and model == "RiNALMo-micro" and strategy == "lora"):
                        continue
                for split in ("random", "family"):
                    for seed in (17, 29, 43):
                        jobs.append(job_for(task, model, strategy, split, seed,
                                            protocol=args.protocol))
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(jobs, indent=2) + "\n")
    os.replace(temporary, path)
    print(json.dumps({"jobs": len(jobs), "models": args.models,
                      "tasks": args.tasks, "strategies": args.strategies,
                      "protocol": args.protocol, "lane": args.lane,
                      "output": str(path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
