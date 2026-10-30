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
                       finetune_one, finetune_regbase, finetune_spl,
                       finetune_ssp, ledger)

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
DENSE_LEVELS = (10, 100, 1000, 1500, 2000, 2500, 3000)
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


def c5c_ncrna_jobs():
    jobs = []
    for model in ("RiNALMo-micro", "RiNALMo-mega", "RiNALMo-650M"):
        for strategy in ("lora", "full"):
            for split in ("random", "family"):
                for level in DENSE_LEVELS:
                    for seed in (17, 29, 43):
                        batch_size = (32 if model == "RiNALMo-micro" else
                                      16 if model == "RiNALMo-mega" and strategy == "lora" else 8)
                        need_gb = 8 if model == "RiNALMo-micro" else (
                            16 if model == "RiNALMo-mega" else 28)
                        jobs.append(job_for(
                            "noncoding-rna-family", model, strategy, split, seed,
                            n_train=level, module=finetune_one,
                            dense_clusters=split == "family",
                            batch_size=batch_size, need_gb=need_gb))
    return jobs


def c5c_other_task_jobs():
    runners = dict(TASK_MODULES, spliceai=finetune_spl,
                   degradation=finetune_regbase, ssi=finetune_regbase)
    jobs = []
    for task in ("crispr-off-target", "mrl", "modification",
                 "secondary-structure", "spliceai", "degradation", "ssi"):
        for model in ("RiNALMo-micro", "RiNALMo-mega", "RiNALMo-650M"):
            for strategy in ("lora", "full"):
                for split in ("random", "family"):
                    for level in DENSE_LEVELS:
                        for seed in (17, 29, 43):
                            base = DEFAULTS[task]["batch"]
                            if model == "RiNALMo-650M":
                                batch_size = 1 if task == "secondary-structure" \
                                    else min(base, 4 if strategy == "full" else 8)
                            elif model == "RiNALMo-mega" and strategy == "full":
                                batch_size = 2 if task == "secondary-structure" \
                                    else min(base, 8)
                            else:
                                batch_size = base
                            jobs.append(job_for(
                                task, model, strategy, split, seed,
                                n_train=level, module=runners[task],
                                batch_size=batch_size,
                                need_gb=8 if model == "RiNALMo-micro" else
                                16 if model == "RiNALMo-mega" else 28))
    return jobs


def c5c_all_jobs():
    return c5c_ncrna_jobs() + c5c_other_task_jobs()


def equivalence_rnasc_jobs():
    """Register the controlled 30M-full versus 650M-LoRA budget curves."""
    runners = dict(TASK_MODULES, spliceai=finetune_spl,
                   degradation=finetune_regbase, ssi=finetune_regbase)
    jobs = []
    for task in ("noncoding-rna-family", "crispr-off-target", "mrl",
                 "modification", "secondary-structure", "spliceai",
                 "degradation", "ssi"):
        for split in ("random", "family"):
            for level in DENSE_LEVELS:
                for seed in (17, 29, 43):
                    for model, strategy in (("RNA-Sc-30M", "full"),
                                            ("RNA-Sc-650M", "lora")):
                        base = DEFAULTS[task]["batch"]
                        small = model == "RNA-Sc-30M"
                        batch_size = (32 if task == "noncoding-rna-family" else base) if small else (
                            1 if task == "secondary-structure" else
                            8 if task == "noncoding-rna-family" else min(base, 8))
                        jobs.append(job_for(
                            task, model, strategy, split, seed,
                            n_train=level,
                            module=finetune_one if task == "noncoding-rna-family" else runners[task],
                            lr="3e-5" if small else "3e-4",
                            dense_clusters=(task == "noncoding-rna-family" and split == "family"),
                            batch_size=batch_size, need_gb=8 if small else 28))
    return jobs


def lr_tuning_jobs():
    """Register seed-101 validation-only LR selection runs for full FT."""
    runners = dict(TASK_MODULES, spliceai=finetune_spl,
                   degradation=finetune_regbase, ssi=finetune_regbase)
    jobs = []
    for task in ("noncoding-rna-family", "crispr-off-target", "mrl",
                 "modification", "secondary-structure", "spliceai",
                 "degradation", "ssi"):
        for model in MODELS:
            for split in ("random", "family"):
                for lr in ("3e-4", "1e-4", "3e-5", "1e-5"):
                    base = DEFAULTS[task]["batch"]
                    if model == "RiNALMo-650M":
                        batch_size = 1 if task == "secondary-structure" else min(base, 4)
                    elif model == "RiNALMo-mega":
                        batch_size = 2 if task == "secondary-structure" else min(base, 8)
                    else:
                        batch_size = base
                    jobs.append(job_for(
                        task, model, "full", split, 101, lr=lr,
                        module=runners[task], batch_size=batch_size,
                        need_gb=8 if model == "RiNALMo-micro" else
                        16 if model in ("RiNALMo-mega", "ERNIE-RNA", "RNA-FM") else 28))
    return jobs


def lr_default_jobs():
    """Register formal full-FT controls using the default LR=3e-4."""
    runners = dict(TASK_MODULES, spliceai=finetune_spl,
                   degradation=finetune_regbase, ssi=finetune_regbase)
    jobs = []
    for task in ("noncoding-rna-family", "crispr-off-target", "mrl",
                 "modification", "secondary-structure", "spliceai",
                 "degradation", "ssi"):
        for model in MODELS:
            for split in ("random", "family"):
                for seed in (17, 29, 43):
                    base = DEFAULTS[task]["batch"]
                    if model == "RiNALMo-650M":
                        batch_size = 1 if task == "secondary-structure" else min(base, 4)
                    elif model == "RiNALMo-mega":
                        batch_size = 2 if task == "secondary-structure" else min(base, 8)
                    else:
                        batch_size = base
                    jobs.append(job_for(
                        task, model, "full", split, seed, lr="3e-4",
                        module=runners[task], batch_size=batch_size,
                        need_gb=8 if model == "RiNALMo-micro" else
                        16 if model in ("RiNALMo-mega", "ERNIE-RNA", "RNA-FM") else 28))
    return jobs


def lr_tuned_jobs(selection):
    """Build formal full-FT jobs from frozen validation-LR selections."""
    runners = dict(TASK_MODULES, spliceai=finetune_spl,
                   degradation=finetune_regbase, ssi=finetune_regbase)
    expected = {(task, model, split)
                for task in runners for model in MODELS for split in ("random", "family")}
    selected = {(row["task"], row["model"], row["split"]): row["selected_lr"]
                for row in selection}
    if set(selected) != expected or len(selection) != 80:
        raise ValueError("LR selection must cover exactly 80 task/model/split groups")
    if set(selected.values()) - {"3e-4", "1e-4", "3e-5", "1e-5"}:
        raise ValueError("selected LR is outside the registered grid")
    jobs = []
    for task, model, split in sorted(expected):
        for seed in (17, 29, 43):
            base = DEFAULTS[task]["batch"]
            if model == "RiNALMo-650M":
                batch_size = 1 if task == "secondary-structure" else min(base, 4)
            elif model == "RiNALMo-mega":
                batch_size = 2 if task == "secondary-structure" else min(base, 8)
            else:
                batch_size = base
            jobs.append(job_for(
                task, model, "full", split, seed,
                lr=selected[(task, model, split)], module=runners[task],
                batch_size=batch_size,
                need_gb=8 if model == "RiNALMo-micro" else
                16 if model in ("RiNALMo-mega", "ERNIE-RNA", "RNA-FM") else 28))
    return jobs


def peft_rank_jobs():
    """Register the complete LoRA-rank/DoRA wave without launching it."""
    runners = dict(TASK_MODULES, spliceai=finetune_spl,
                   degradation=finetune_regbase, ssi=finetune_regbase)
    jobs = []
    for task in ("noncoding-rna-family", "crispr-off-target", "mrl",
                 "modification", "secondary-structure", "spliceai",
                 "degradation", "ssi"):
        for model in MODELS:
            for strategy, ranks in (("lora", (4, 8, 16)), ("dora", (8,))):
                for rank in ranks:
                    for split in ("random", "family"):
                        for seed in (17, 29, 43):
                            base = DEFAULTS[task]["batch"]
                            batch_size = (1 if task == "secondary-structure"
                                          else min(base, 8)) if model == "RiNALMo-650M" else base
                            jobs.append(job_for(
                                task, model, strategy, split, seed, rank=rank,
                                module=runners[task], batch_size=batch_size,
                                need_gb=8 if model == "RiNALMo-micro" else
                                16 if model in ("RiNALMo-mega", "ERNIE-RNA", "RNA-FM") else 28))
    return jobs


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
    parser.add_argument("--wave", choices=("complementary", "c5c-ncrna", "c5c-all",
                                           "equivalence-rnasc", "peft-rank", "lr-tuning",
                                           "lr-default", "lr-tuned"),
                        default="complementary")
    parser.add_argument("--lr-selection", help="validation-LR selection JSON for --wave lr-tuned")
    args = parser.parse_args(argv)
    if args.wave == "c5c-ncrna":
        jobs = c5c_ncrna_jobs()
    elif args.wave == "c5c-all":
        jobs = c5c_all_jobs()
    elif args.wave == "equivalence-rnasc":
        jobs = equivalence_rnasc_jobs()
    elif args.wave == "peft-rank":
        jobs = peft_rank_jobs()
    elif args.wave == "lr-tuning":
        jobs = lr_tuning_jobs()
    elif args.wave == "lr-default":
        jobs = lr_default_jobs()
    elif args.wave == "lr-tuned":
        if not args.lr_selection:
            parser.error("--wave lr-tuned requires --lr-selection")
        selection_doc = json.loads(Path(args.lr_selection).read_text())
        jobs = lr_tuned_jobs(selection_doc["rows"])
    else:
        jobs = []
        runners = dict(TASK_MODULES, spliceai=finetune_spl,
                       degradation=finetune_regbase, ssi=finetune_regbase)
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
                                                protocol=args.protocol,
                                                module=runners[task]))
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(jobs, indent=2) + "\n")
    os.replace(temporary, path)
    print(json.dumps({"jobs": len(jobs),
                      "models": sorted({job["model"] for job in jobs}),
                      "tasks": sorted({job["task"] for job in jobs}),
                      "strategies": sorted({job["strategy"] for job in jobs}),
                      "protocol": args.protocol, "lane": args.lane,
                      "wave": args.wave, "output": str(path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
