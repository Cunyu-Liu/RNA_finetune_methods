import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import prepare_e3_dense as dense
import expansion_jobs as jobs
from rnafteval import finetune_one


def frame():
    clusters = ["c0", "c0", "c1", "c1", "c1", "c2", "c3", "c3", "c3", "c3"]
    return pd.DataFrame({"split": ["train"] * len(clusters), "cluster_id": clusters})


def test_dense_subsets_are_nested_and_never_split_clusters():
    subsets, n_train = dense.nested_cluster_subsets(
        frame(), levels=(2, 4, 5, 100), seeds=(17, 29))
    assert n_train == 10
    source = frame()
    for seed in (17, 29):
        previous = set()
        for level in (2, 4, 5, 100):
            subset = subsets[(seed, level)]
            rows = set(subset["rows"])
            assert len(rows) == subset["n_rows"]
            assert previous <= rows
            previous = rows
            for cluster in subset["cluster_ids"]:
                expected = set(source.index[source["cluster_id"] == cluster])
                assert expected <= rows
        assert subsets[(seed, 100)]["saturated"]


def test_dense_writer_preserves_manifest_and_rejects_changed_source(tmp_path):
    subsets, _ = dense.nested_cluster_subsets(frame(), levels=(4,), seeds=(17,))
    subset = subsets[(17, 4)]
    metadata = dense.write_subset(tmp_path, "source-sha", 17, 4, subset)
    path = tmp_path / "ncrna_4_s17_dense.txt"
    assert path.read_text() == "".join("%d\n" % index for index in subset["rows"])
    saved = json.loads((tmp_path / "ncrna_4_s17_dense.json").read_text())
    assert saved["whole_clusters"] and saved["source_parquet_sha256"] == "source-sha"
    assert metadata["n_rows"] == len(subset["rows"])
    path.write_text("999\n")
    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        dense.write_subset(tmp_path, "source-sha", 17, 4, subset)


def test_dense_runner_uses_distinct_rid_and_skips_second_row_sampling():
    args = SimpleNamespace(lr=3e-4, rank=8, n_train=1500, smoke=False,
                           random_init=False, converge=True,
                           convergence_mode="bestval", out_suffix="",
                           dense_clusters=True)
    assert finetune_one._run_extra(args) == "_e31500_dense_bestval_v1"
    source = Path(finetune_one.__file__).read_text()
    assert 'args.n_train, args.seed, "_dense" if args.dense_clusters else ""' in source
    assert 'prepare_n = 0 if args.dense_clusters and args.split == "family"' in source
    assert '"whole_cluster_retained_after_prepare": args.dense_clusters' in source


def test_dense_job_registry_preserves_protocol_and_command(tmp_path):
    job = jobs.job_for("noncoding-rna-family", "RiNALMo-micro", "full",
                       "family", 17, n_train=1500, dense_clusters=True,
                       module=finetune_one)
    assert job["rid"] == \
        "ft_rinalmomicro_noncodingrnafamily_full_s17_family_lr1e-05_e31500_dense_bestval_v1"
    assert job["result_dir"].endswith(job["rid"])
    assert "--dense-clusters" in job["args"]
    with pytest.raises(ValueError, match="dense clusters require"):
        jobs.job_for("noncoding-rna-family", "RiNALMo-micro", "full",
                     "random", 17, n_train=1500, dense_clusters=True,
                     module=finetune_one)


def test_c5c_ncrna_wave_has_paired_random_and_dense_family_cells():
    wave = jobs.c5c_ncrna_jobs()
    assert len(wave) == 252
    assert len({job["rid"] for job in wave}) == 252
    family = [job for job in wave if job["split"] == "family"]
    random = [job for job in wave if job["split"] == "random"]
    assert len(family) == len(random) == 126
    assert all(job["dense_clusters"] and "--dense-clusters" in job["args"]
               for job in family)
    assert all(not job["dense_clusters"] for job in random)
    assert {job["n_train"] for job in wave} == set(jobs.DENSE_LEVELS)
    giga_full = [job for job in wave if job["model"] == "RiNALMo-650M"
                 and job["strategy"] == "full"]
    assert all("--batch-size 8" in " ".join(job["args"]) for job in giga_full)
    assert all(job["need_gb"] == 28 for job in giga_full)


def test_c5c_all_tasks_wave_is_unique_and_preserves_task_commands():
    wave = jobs.c5c_all_jobs()
    assert len(wave) == 2016
    assert len({job["rid"] for job in wave}) == 2016
    assert {job["task"] for job in wave} == {
        "noncoding-rna-family", "crispr-off-target", "mrl", "modification",
        "secondary-structure", "spliceai", "degradation", "ssi"}
    assert sum(job["split"] == "family" and job["dense_clusters"] for job in wave) == 126
    assert all("--batch-size 1" in " ".join(job["args"])
               for job in wave if job["task"] == "secondary-structure"
               and job["model"] == "RiNALMo-650M")
