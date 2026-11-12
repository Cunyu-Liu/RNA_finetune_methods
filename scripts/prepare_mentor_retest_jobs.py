#!/usr/bin/env python3
import hashlib
import json
import os
from pathlib import Path

os.environ["RNAFT_ARTIFACT_ROOT"] = "/teams/HoulabData_1788502323/liucunyu/rna-ft-eval/artifacts"

from expansion_jobs import job_for
from expansion_queue import load_jobs

OUT = Path(__file__).resolve().parent
SPLITS = ("random", "family")
SEEDS = (17, 29, 43)
LRS = ("3e-4", "1e-4", "3e-5", "1e-5")


def write_registry(name, jobs):
    for job in jobs:
        job["result_dir"] = os.environ["RNAFT_ARTIFACT_ROOT"] + "/" + job["rid"]
    path = OUT / name
    path.write_text(json.dumps(jobs, ensure_ascii=False, indent=2) + "\n")
    loaded = load_jobs(path)
    assert len(loaded) == len(jobs)
    assert len({j.rid for j in loaded}) == len(jobs)
    assert len({j.result_dir for j in loaded}) == len(jobs)
    assert len({j.job_key for j in loaded}) == len(jobs)
    return {
        "file": name,
        "n_jobs": len(jobs),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def main():
    p0 = []
    for split in SPLITS:
        for seed in SEEDS:
            p0.append(job_for("mrl", "RiNALMo-650M", "full", split, seed,
                              lr="1e-5", batch_size=8, need_gb=28))
        for strategy, lr, need in (("lora", "3e-4", 18), ("full", "1e-5", 28)):
            for seed in SEEDS:
                p0.append(job_for("modification", "RiNALMo-650M", strategy,
                                  split, seed, lr=lr, batch_size=8, need_gb=need))
    reports = [write_registry("main_remaining_650m_18_jobs_20261111.json", p0)]

    external = []
    for model, default_lr, batch, need in (
        ("NucleicBERT", "3e-5", 8, 12),
    ):
        for split in SPLITS:
            for lr in LRS:
                external.append(job_for(
                    "mrl", model, "full", split, 101, lr=lr,
                    out_suffix="_reval20261111", batch_size=batch, need_gb=need))
            for seed in SEEDS:
                external.append(job_for(
                    "mrl", model, "full", split, seed, lr=default_lr,
                    out_suffix="_reval20261111", batch_size=batch, need_gb=need))
    for job in external:
        if not job["rid"].endswith("_reval20261111"):
            job["rid"] += "_reval20261111"
        job["result_dir"] = str(Path(job["result_dir"]).with_name(job["rid"]))
    reports.append(write_registry("mrl_external_nuc_tuning_default_14_jobs_20261112.json", external))

    tuned = {
        "status": "blocked_until_validation_complete",
        "required_jobs": 6,
        "models": ["NucleicBERT"],
        "deferred_models": ["AIDO.RNA-1.6B"],
        "splits": list(SPLITS),
        "seeds": list(SEEDS),
        "out_suffix": "_reval20261111",
        "rule": "Select one LR per model×split by held-out best_val from four completed tuning runs; never use test for selection.",
        "source_registry": "mrl_external_nuc_tuning_default_14_jobs_20261112.json",
    }
    tuned_path = OUT / "mrl_nuc_tuned_6_required_20261112.json"
    tuned_path.write_text(json.dumps(tuned, ensure_ascii=False, indent=2) + "\n")
    reports.append({
        "file": tuned_path.name,
        "required_jobs": 6,
        "sha256": hashlib.sha256(tuned_path.read_bytes()).hexdigest(),
    })
    summary = {
        "p0_canonical": 18,
        "external_tuning_and_default": 14,
        "external_tuned_pending": 6,
        "external_total": 28,
        "deferred_models": ["AIDO.RNA-1.6B"],
        "deferred_cells": 14,
        "registries": reports,
    }
    summary_path = OUT / "mentor_retest_jobs_20261111_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
