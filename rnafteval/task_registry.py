"""Task dataset registry — BEACON-derived tasks (spec §4 task pool).

Task column semantics (spec §3.4 split-unit table):
  granularity: per-seq | per-base
  split_unit: what must stay on one side of a family split
  host_field: dataset column carrying the split-unit key (transcript/gene id)
Official metrics per task (spec T1.3.5).

BEACON raw data lands at /mnt/cunyuliu/rna-ft-eval/data/beacon_raw/<task>/...
This registry maps task name -> loader, metric, split policy. Loaders are
implemented in rnafteval/tasks/__init__.py as functions are added.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TaskSpec:
    name: str            # canonical task id (beacon folder name)
    family: str          # task family (structure / function / global / engineering / interaction / variant)
    granularity: str     # per-seq | per-base
    split_unit: str      # sequence | transcript | gene | cluster
    host_field: str      # column name for split-unit key ("" if per-seq)
    metric: str          # primary official metric
    binary_dir: str      # beacon raw dir suffix


BEACON_RAW = "/mnt/cunyuliu/rna-ft-eval/data/beacon_raw"

TASKS: dict[str, TaskSpec] = {
    "secondary-structure": TaskSpec(
        "secondary-structure", "structure", "per-base", "sequence", "",
        "F1", "secondary-structure"),
    "contact-map": TaskSpec(
        "contact-map", "structure", "per-base", "sequence", "",
        "F1", "contact-map"),
    "spliceai": TaskSpec(
        "spliceai", "structure", "per-base", "gene", "",
        "AUC", "spliceai"),
    "modification": TaskSpec(
        "modification", "function", "per-base", "transcript", "",
        "AUC", "modification"),
    "noncoding-rna-family": TaskSpec(
        "noncoding-rna-family", "function", "per-seq", "sequence", "",
        "ACC", "noncoding-rna-family"),
    "mean-ribosome-loading": TaskSpec(
        "mean-ribosome-loading", "global", "per-seq", "sequence", "",
        "R2", "mean-ribosome-loading"),
    "degradation": TaskSpec(
        "degradation", "engineering", "per-base", "sequence", "",
        "MCRMSE", "degradation"),
    "crispr-off-target": TaskSpec(
        "crispr-off-target", "interaction", "per-base", "sequence", "",
        "AUC", "crispr-off-target"),
    # placeholder slots; RBP from BEACON/RBP-24 and DMS from RNAGym come later
    "rbp": TaskSpec("rbp", "interaction", "per-base", "transcript", "",
                    "MCC", "rbp"),
    "dms": TaskSpec("dms", "variant", "per-seq", "sequence", "",
                    "Spearman", "dms"),
}


def get(name: str) -> TaskSpec:
    return TASKS[name]
