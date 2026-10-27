import os
import ast
import json
import runpy
import sys
from types import SimpleNamespace

import numpy as np
import pytest
import torch

from rnafteval import (
    finetune_base, finetune_clf, finetune_mrl, finetune_one,
    finetune_regbase, finetune_spl, finetune_ssp, ledger, valplateau)
from rnafteval.base_alignment import align_base_labels
from rnafteval.splits import (
    assert_cluster_no_overlap, assert_no_overlap, prepare_convergence_splits,
    seeded_sample, split_train_validation)


class _MockTokenizer:
    prefix = ()
    suffix = ()
    _pad_id = 0
    _base_ids = {"A": 1, "C": 2, "G": 3, "U": 4, "T": 4, "N": 5}

    def _core(self, seq):
        return [self._base_ids[base] for base in seq]

    def __call__(self, seqs, padding=True, truncation=True, max_length=512,
                 return_tensors="pt"):
        rows = []
        for seq in seqs:
            core = self._core(seq)
            if truncation:
                core = core[:max(0, max_length - len(self.prefix) - len(self.suffix))]
            rows.append(list(self.prefix) + core + list(self.suffix))
        width = max(map(len, rows))
        input_ids, attention = [], []
        for row in rows:
            pad_n = width - len(row)
            input_ids.append(row + [self._pad_id] * pad_n)
            attention.append([1] * len(row) + [0] * pad_n)
        return {"input_ids": torch.tensor(input_ids),
                "attention_mask": torch.tensor(attention)}


class _HFTok(_MockTokenizer):
    prefix = (90,)
    suffix = (91,)
    cls_token_id = 90
    eos_token_id = 91
    pad_token_id = 0
    all_special_ids = (0, 90, 91)

    def get_special_tokens_mask(self, ids, already_has_special_tokens=False):
        assert already_has_special_tokens
        return [int(token_id in self.all_special_ids) for token_id in ids]


class _NucleicBERTTok(_MockTokenizer):
    prefix = (80,)
    suffix = (81,)
    cls_id = 80
    sep_id = 81
    pad_token_id = 0


class _RnaScTok(_MockTokenizer):
    pass


class _ThreeMerTok(_HFTok):
    def _core(self, seq):
        return [10 + i for i in range(len(seq) // 3)]


def _align(tok, rows, max_len, **kwargs):
    enc = tok([row["seq"] for row in rows], padding=True, truncation=True,
              max_length=max_len, return_tensors="pt")
    y, mask = align_base_labels(tok, enc, rows, max_len, **kwargs)
    return enc, y, mask


def test_hf_special_tokens_and_padding_are_excluded_per_row():
    rows = [{"seq": "ACGU", "labels": [0, 1, 2, 1]},
            {"seq": "AC", "labels": [2, 0]}]
    _, y, mask = _align(_HFTok(), rows, max_len=8, dtype=torch.long)
    assert y.tolist() == [[0, 0, 1, 2, 1, 0], [0, 2, 0, 0, 0, 0]]
    assert mask.tolist() == [
        [False, True, True, True, True, False],
        [False, True, True, False, False, False],
    ]


def test_nucleicbert_cls_sep_are_excluded():
    row = {"seq": "ACG", "labels": np.array([0.1, 0.2, 0.3])}
    _, y, mask = _align(_NucleicBERTTok(), [row], max_len=5)
    assert torch.allclose(y, torch.tensor([[0.0, 0.1, 0.2, 0.3, 0.0]]))
    assert mask.tolist() == [[False, True, True, True, False]]


def test_rnasc_without_special_tokens_keeps_every_base():
    row = {"seq": "ACGU", "labels": [0.1, 0.2, 0.3, 0.4]}
    _, y, mask = _align(_RnaScTok(), [row], max_len=4)
    assert torch.allclose(y, torch.tensor([[0.1, 0.2, 0.3, 0.4]]))
    assert mask.all()


def test_three_mer_mismatch_is_fatal_even_when_truncated():
    row = {"seq": "ACGUAC", "labels": [0, 1, 2, 0, 1, 2]}
    with pytest.raises(ValueError, match="B20 token/base mismatch"):
        _align(_ThreeMerTok(), [row], max_len=4, dtype=torch.long)


def test_degradation_short_labels_define_scored_window():
    row = {"seq": "ACGUAC", "labels": np.array([0.1, 0.2, 0.3])}
    _, y, mask = _align(_HFTok(), [row], max_len=8,
                        allow_short_labels=True)
    assert torch.allclose(y[mask], torch.tensor([0.1, 0.2, 0.3]))
    assert mask[0].nonzero().flatten().tolist() == [1, 2, 3]


def test_max_len_uses_deterministic_right_truncation_before_alignment():
    row = {"seq": "ACGUAC", "labels": [0, 1, 2, 0, 1, 2]}
    enc, y, mask = _align(_HFTok(), [row], max_len=5, dtype=torch.long)
    assert enc["input_ids"].tolist() == [[90, 1, 2, 3, 91]]
    assert y.tolist() == [[0, 0, 1, 2, 0]]
    assert mask.tolist() == [[False, True, True, True, False]]


def test_ssp_pair_targets_and_scores_follow_aligned_base_tokens():
    rec = {"seq": "ACGU", "L": 4, "pairs": [(0, 2), (1, 3)]}
    tok = _HFTok()
    enc = tok([rec["seq"]], padding=True, truncation=True,
              max_length=6, return_tensors="pt")
    positions = finetune_ssp.aligned_base_positions(tok, enc, [rec], 6)[0]
    assert positions.tolist() == [1, 2, 3, 4]
    target, mask = finetune_ssp.pair_target_and_mask(
        rec, positions, width=6, device=torch.device("cpu"))
    assert target[1, 3] == 1 and target[3, 1] == 1
    assert target[2, 4] == 1 and target[4, 2] == 1
    assert int(mask.sum()) == 6
    assert not mask[0].any() and not mask[:, 0].any()
    assert not mask[5].any() and not mask[:, 5].any()
    scores = torch.arange(36).reshape(6, 6)
    aligned = finetune_ssp.aligned_pair_scores(scores, positions)
    assert aligned.tolist() == [[7, 8, 9, 10], [13, 14, 15, 16],
                                [19, 20, 21, 22], [25, 26, 27, 28]]


def test_ssp_pair_alignment_uses_right_truncated_effective_pairs():
    rec = {"seq": "ACGUAC", "L": 6, "pairs": [(0, 5), (1, 2)]}
    tok = _HFTok()
    enc = tok([rec["seq"]], padding=True, truncation=True,
              max_length=5, return_tensors="pt")
    positions = finetune_ssp.aligned_base_positions(tok, enc, [rec], 5)[0]
    assert positions.tolist() == [1, 2, 3]
    assert finetune_ssp.effective_pairs(rec, len(positions)) == [(1, 2)]
    target, mask = finetune_ssp.pair_target_and_mask(
        rec, positions, width=5, device=torch.device("cpu"))
    assert target[2, 3] == 1 and target[3, 2] == 1
    assert int(target.sum()) == 2
    assert int(mask.sum()) == 3


def test_ssp_pair_alignment_supports_rnasc_and_rejects_kmer():
    rec = {"seq": "ACGU", "L": 4, "pairs": [(0, 2)]}
    tok = _RnaScTok()
    enc = tok([rec["seq"]], padding=True, truncation=True,
              max_length=4, return_tensors="pt")
    positions = finetune_ssp.aligned_base_positions(tok, enc, [rec], 4)[0]
    assert positions.tolist() == [0, 1, 2, 3]
    with pytest.raises(ValueError, match="B20 token/base mismatch"):
        kmer = _ThreeMerTok()
        bad = dict(rec, seq="ACGUAC", L=6)
        enc = kmer([bad["seq"]], padding=True, truncation=True,
                   max_length=8, return_tensors="pt")
        finetune_ssp.aligned_base_positions(kmer, enc, [bad], 8)


def test_ssp_pairalign_rid_separates_fixed_and_legacy_runs():
    base = SimpleNamespace(lr=3e-4, rank=8, n_train=2000, n_test=400,
                           smoke=False, converge=False)
    assert finetune_ssp._run_extra(base) == "_pairalign"
    bestval = SimpleNamespace(**{**vars(base), "converge": True,
                                 "convergence_mode": "bestval"})
    assert finetune_ssp._run_extra(bestval) == "_pairalign_bestval_v1"
    smoke = SimpleNamespace(**{**vars(base), "smoke": True})
    assert finetune_ssp._run_extra(smoke) == "_smoke_pairalign"


def test_run_id_extra_marks_b20fix_and_separates_nondefaults():
    for runner, default_epochs in ((finetune_spl, 10),
                                   (finetune_regbase, 3),
                                   (finetune_clf, 10)):
        defaults = SimpleNamespace(lr=3e-4, rank=8, n_train=0,
                                   epochs=default_epochs, smoke=False)
        default_extra = runner._run_extra(defaults)
        if runner is finetune_clf:
            assert default_extra == ""
        else:
            assert default_extra == "_b20fix"
        base_rid = ledger.run_id("m", "t", "frozen", 17, "random",
                                 default_extra)
        for field, value, tag in (("lr", 1e-5, "_lr1e-05"),
                                  ("rank", 16, "_r16"),
                                  ("n_train", 123, "_e3123"),
                                  ("epochs", 4, "_ep4")):
            args = SimpleNamespace(**vars(defaults))
            setattr(args, field, value)
            extra = runner._run_extra(args)
            assert tag in extra
            assert ("_b20fix" in extra) is (runner is not finetune_clf)
            assert ledger.run_id("m", "t", "frozen", 17, "random", extra) != base_rid


def test_converge_rid_isolated_and_ignores_fixed_epoch_budget():
    for runner in (finetune_clf, finetune_spl, finetune_regbase):
        base = SimpleNamespace(lr=3e-4, rank=8, n_train=0, epochs=10,
                               smoke=False, converge=False)
        legacy = runner._run_extra(base)
        new = SimpleNamespace(**vars(base))
        new.converge = True
        new.epochs = 1
        tagged = runner._run_extra(new)
        assert tagged.endswith("_valplateau_v2")
        bestval = SimpleNamespace(**vars(new))
        bestval.convergence_mode = "bestval"
        bestval_extra = runner._run_extra(bestval)
        assert bestval_extra.endswith("_bestval_v1")
        assert bestval_extra != tagged and "_valplateau_v2" not in bestval_extra
        assert tagged != legacy
        assert "_ep1" not in tagged
        assert ledger.run_id("m", "t", "frozen", 17, "random", tagged) != \
            ledger.run_id("m", "t", "frozen", 17, "random", legacy)


def test_train_validation_holdout_is_deterministic_and_three_way_disjoint():
    official_train = [{"seq": "ACGU" * 5 + str(i), "labels": [0]}
                      for i in range(40)]
    official_test = [{"seq": "UGCA" * 5 + str(i), "labels": [0]}
                     for i in range(10)]
    train_a, val_a = split_train_validation(official_train, seed=17)
    train_b, val_b = split_train_validation(official_train, seed=17)
    assert train_a == train_b and val_a == val_b
    assert len(train_a) == 36 and len(val_a) == 4
    assert_no_overlap(train_a, val_a + official_test)
    assert_no_overlap(val_a, official_test)
    assert {r["seq"] for r in train_a + val_a} == {
        r["seq"] for r in official_train}
    assert not set(r["seq"] for r in official_test) & {
        r["seq"] for r in train_a + val_a}


def test_family_validation_holdout_keeps_clusters_together():
    rows = [{"seq": "ACGU" * 4 + str(i), "labels": [0],
             "cluster": "cluster-%d" % (i // 2)} for i in range(20)]
    train, val = split_train_validation(rows, seed=17)
    train_clusters = {row["cluster"] for row in train}
    val_clusters = {row["cluster"] for row in val}
    assert train_clusters.isdisjoint(val_clusters)
    assert len(train) + len(val) == len(rows)
    assert_cluster_no_overlap(train, val)
    with pytest.raises(AssertionError, match="FAMILY OVERLAP"):
        assert_cluster_no_overlap(train, train[:1])
    assert len(train) + len(val) == len({row["seq"] for row in rows})


def test_uneven_family_clusters_do_not_drop_training_rows():
    rows = []
    for cluster, count in (("large", 100), ("small-a", 10), ("small-b", 5)):
        for i in range(count):
            rows.append({"seq": "%s-%d" % (cluster, i), "cluster": cluster,
                         "labels": [0]})
    train, val = split_train_validation(rows, seed=17, val_fraction=0.1)
    assert len(train) + len(val) == len(rows)
    assert val
    assert_cluster_no_overlap(train, val)


def test_seeded_training_subsample_changes_with_formal_seed():
    rows = [{"seq": "ACGU" * 4 + str(i)} for i in range(50)]
    sample17 = seeded_sample(rows, 10, 17)
    sample17_again = seeded_sample(rows, 10, 17)
    sample29 = seeded_sample(rows, 10, 29)
    sample43 = seeded_sample(rows, 10, 43)
    assert sample17 == sample17_again
    assert len(sample17) == len(sample29) == len(sample43) == 10
    assert sample17 != sample29 != sample43
    assert sample17 != rows[:10]
    assert seeded_sample(rows, 0, 17) is rows
    assert seeded_sample(rows, 100, 17) is rows


def test_train_validation_holdout_rejects_sequence_leakage():
    rows = [{"seq": "ACGU"}, {"seq": "ACGT"}, {"seq": "ACGU"}]
    with pytest.raises(AssertionError, match="OVERLAP DETECTED"):
        split_train_validation(rows, seed=17)


def test_spliceai_official_validation_is_not_test(monkeypatch):
    calls = []
    monkeypatch.setattr(finetune_spl.spl_task, "load_official_split",
                        lambda: calls.append(()) or {
                            "train": [], "validation": [], "test": []})
    source = finetune_spl.__file__
    assert source
    text = open(source).read()
    assert 'sp["validation"]' in text
    assert 'sp["val"]' not in text
    assert 'sp["train"], sp["test"]' not in text
    from rnafteval.tasks.dedup import dedup
    official = {
        "train": [{"seq": "A"}, {"seq": "B"}],
        "validation": [{"seq": "B"}, {"seq": "C"}],
        "test": [{"seq": "C"}, {"seq": "D"}],
    }
    train = dedup(official["train"])
    val = [r for r in dedup(official["validation"])
           if r["seq"] not in {x["seq"] for x in train}]
    test = [r for r in dedup(official["test"])
            if r["seq"] not in {x["seq"] for x in train + val}]
    assert_no_overlap(train, val + test, unit="seq")
    assert_no_overlap(val, test, unit="seq")
    assert [r["seq"] for r in val] == ["C"]
    assert [r["seq"] for r in test] == ["D"]


@pytest.mark.parametrize("module_name", ["rnafteval.finetune_clf",
                                         "rnafteval.finetune_spl"])
def test_claim_blocked_module_exit_uses_rc75_and_keyword_device(
        monkeypatch, module_name):
    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    monkeypatch.setattr(os, "makedirs", lambda *args, **kwargs: None)
    monkeypatch.setattr(sys, "argv", [
        module_name, "--model", "mock", "--strategy", "frozen",
        "--split", "random", "--device", "3",
    ])
    call = {}

    def fake_claim(*args, **kwargs):
        call["args"] = args
        call["kwargs"] = kwargs
        return {"claimed": False, "row": {"status": "done"}}

    monkeypatch.setattr(ledger, "claim", fake_claim)
    monkeypatch.delitem(sys.modules, module_name, raising=False)
    with pytest.raises(SystemExit) as exc_info:
        runpy.run_module(module_name, run_name="__main__")
    assert exc_info.value.code == 75
    assert len(call["args"]) == 5
    assert call["kwargs"]["device"] == 3
    expected_rid = ledger.run_id(*call["args"],
                                 extra=call["kwargs"]["extra"])
    assert call["kwargs"]["out_dir"].endswith(expected_rid)


@pytest.mark.parametrize("runner,defaults,legacy_extra", [
    (finetune_one, dict(n_train=0), ""),
    (finetune_base, dict(n_train=20000), ""),
    (finetune_mrl, dict(n_train=20000), ""),
    (finetune_ssp, dict(n_train=2000, n_test=400), "_pairalign"),
])
def test_old_runners_converge_rid_isolated_and_nonconverge_extra_registered(
        runner, defaults, legacy_extra):
    base = SimpleNamespace(lr=3e-4, rank=8, epochs=3, smoke=False,
                           random_init=False, converge=False,
                           out_suffix="", **defaults)
    assert runner._run_extra(base) == legacy_extra
    legacy_rid = ledger.run_id("m", "t", "frozen", 17, "random", legacy_extra)
    converged = SimpleNamespace(**vars(base))
    converged.converge = True
    converged.epochs = 1
    extra = runner._run_extra(converged)
    assert extra.endswith("_valplateau_v2")
    bestval = SimpleNamespace(**vars(converged))
    bestval.convergence_mode = "bestval"
    bestval_extra = runner._run_extra(bestval)
    assert bestval_extra.endswith("_bestval_v1")
    assert bestval_extra != extra and "_valplateau_v2" not in bestval_extra
    assert ledger.run_id("m", "t", "frozen", 17, "random", extra) != legacy_rid
    converged.smoke = True
    smoke_extra = runner._run_extra(converged)
    assert "_smoke" in smoke_extra and smoke_extra != extra


def test_ssp_converge_rid_separates_data_budgets():
    base = SimpleNamespace(lr=3e-4, rank=8, n_train=2000, n_test=400,
                           smoke=False, converge=True)
    bestval = SimpleNamespace(**vars(base), convergence_mode="bestval")
    assert finetune_ssp._run_extra(bestval).endswith("_bestval_v1")
    small = SimpleNamespace(**vars(base))
    small.n_train = 100
    small_test = SimpleNamespace(**vars(base))
    small_test.n_test = 100
    assert finetune_ssp._run_extra(small).endswith(
        "_e3100_valplateau_v2")
    assert finetune_ssp._run_extra(small_test).endswith(
        "_nt100_valplateau_v2")
    assert len({finetune_ssp._run_extra(x) for x in (base, small, small_test)}) == 3


def test_convergence_ledger_status_never_overwrites_completion():
    result = {
        "run_id": "rid", "protocol": "valplateau_v2", "status": "CONVERGED",
        "epoch_val_losses": [1.0, 0.62, 0.61, 0.605, 0.602],
        "stop_reason": valplateau.STOP_REASON, "n_val": 4,
    }
    fields = valplateau.result_ledger_fields(result)
    assert "status" not in fields
    assert fields["convergence_status"] == "CONVERGED"
    assert fields["protocol"] == "valplateau_v2"
    with pytest.raises(RuntimeError, match="refusing ledger done"):
        valplateau.result_ledger_fields(dict(result, status="RUNNING"))
    with pytest.raises(RuntimeError, match="refusing ledger done"):
        valplateau.result_ledger_fields(dict(result, status="INVALID"))


def test_official_validation_is_reused_and_never_replaced_by_test(tmp_path):
    train = [{"seq": "A" * 8}, {"seq": "C" * 8}, {"seq": "G" * 8}]
    official_val = [{"seq": "N" * 8}]
    test = [{"seq": "T" * 8}, {"seq": "G" * 8}]
    evidence_path = tmp_path / "split.json"
    tr, va, te, evidence = prepare_convergence_splits(
        train, official_val, test, validation_source="official_validation",
        evidence_path=str(evidence_path))
    assert va == official_val and va is not test
    assert te == test
    assert [r["seq"] for r in tr] == ["A" * 8, "C" * 8]
    assert_no_overlap(tr, va + te)
    assert_no_overlap(va, te)
    saved = json.loads(evidence_path.read_text())
    assert saved["validation_source"] == "official_validation"
    assert saved["removed_cross_split"]["train"] == 1
    assert saved["status"] == "OK"


def test_convergence_train_sampling_uses_formal_seed_not_prefix():
    rows = [{"seq": ("ACGU" * 5) + str(i)} for i in range(60)]
    official_val = [{"seq": "N" * 12}]
    test = [{"seq": "G" * 12}]

    def draw(seed):
        return prepare_convergence_splits(
            rows, official_val, test, n_train=10, sample_seed=seed)

    train17, val17, _, evidence = draw(17)
    train17_again, _, _, _ = draw(17)
    train29, val29, _, _ = draw(29)
    assert train17 == train17_again and train17 != train29
    assert train17 != rows[:10]
    assert val17 == val29 == official_val
    assert evidence["train_sampling"] == {
        "method": "seeded_sample", "n_train": 10, "seed": 17,
        "rows_before": 60, "rows_after": 10}


def test_family_convergence_split_is_three_way_cluster_isolated(tmp_path):
    train = [{"seq": ("ACGU" * 4) + str(i), "cluster": "tr-%d" % (i // 2)}
             for i in range(20)]
    official_val = [{"seq": "N" * 20, "cluster": "va"},
                    {"seq": "C" * 20, "cluster": "vb"}]
    test = [{"seq": "G" * 20, "cluster": "te"}]
    evidence_path = tmp_path / "family.json"
    tr, va, te, _ = prepare_convergence_splits(
        train, official_val, test, family=True,
        evidence_path=str(evidence_path))
    assert_cluster_no_overlap(tr, va + te)
    assert_cluster_no_overlap(va, te)
    assert va == official_val and te == test

    tr2, va2, te2, _ = prepare_convergence_splits(
        train, None, test, family=True, validation_source="train_holdout")
    assert not va2 or set(r["cluster"] for r in va2).isdisjoint(
        r["cluster"] for r in tr2 + te2)
    assert_cluster_no_overlap(tr2, va2 + te2)
    assert_cluster_no_overlap(va2, te2)


def test_family_cluster_overlap_fails_and_preserves_evidence(tmp_path):
    train = [{"seq": "A" * 12, "cluster": "same"}]
    val = [{"seq": "C" * 12, "cluster": "same"}]
    test = [{"seq": "G" * 12, "cluster": "test"}]
    path = tmp_path / "invalid.json"
    with pytest.raises(AssertionError, match="FAMILY OVERLAP"):
        prepare_convergence_splits(
            train, val, test, family=True, evidence_path=str(path))
    saved = json.loads(path.read_text())
    assert saved["status"] == "INVALID"
    assert "FAMILY OVERLAP" in saved["error"]


def test_clf_random_split_is_independent_of_formal_training_seed():
    from rnafteval.splits import random_split
    source = open(finetune_clf.__file__).read()
    assert "parts = random_split(recs, seed=17)" in source
    assert "parts = random_split(recs, seed=args.seed)" not in source
    rows = [{"seq": "ACGU" * 5 + str(i)} for i in range(100)]
    assert random_split(rows, seed=17) == random_split(rows, seed=17)
    assert random_split(rows, seed=17) != random_split(rows, seed=29)


@pytest.mark.parametrize("module_name", [
    "rnafteval.finetune_one", "rnafteval.finetune_base", "rnafteval.finetune_mrl",
    "rnafteval.finetune_clf", "rnafteval.finetune_spl", "rnafteval.finetune_regbase",
    "rnafteval.finetune_ssp", "rnafteval.e6_forget"])
def test_bestval_without_converge_fails_before_cuda_or_training(
        module_name, monkeypatch):
    argv = [module_name, "--model", "mock", "--strategy", "frozen",
            "--seed", "17", "--device", "0",
            "--convergence-mode", "bestval"]
    if module_name != "rnafteval.e6_forget":
        argv += ["--split", "random"]
    monkeypatch.setattr(sys, "argv", argv)
    monkeypatch.setattr(torch.cuda, "is_available",
                        lambda: pytest.fail("CUDA was touched before argument validation"))
    if module_name == "rnafteval.finetune_regbase":
        argv += ["--task", "degradation"]
    elif module_name == "rnafteval.finetune_one":
        argv += ["--task", "noncoding-rna-family"]
    with pytest.raises(ValueError, match="requires --converge"):
        runpy.run_module(module_name, run_name="__main__")


def test_e6_restore_precedes_post_eval_and_save_checkpoint():
    from rnafteval import e6_forget
    source = open(e6_forget.__file__).read()
    restore = source.index("vp.restore_best_checkpoint")
    assert source.index("post_drift = drift_eval", restore) > restore
    assert source.index("post = nll_eval", restore) > restore
    assert "vp.validate_convergence_args(args)" in source
    assert "vp.make_tracker(out_dir, args, rid, save_best)" in source


def test_all_runners_guard_bestval_and_restore_before_eval():
    runners = (finetune_one, finetune_base, finetune_mrl, finetune_clf,
               finetune_spl, finetune_regbase, finetune_ssp)
    for runner in runners:
        tree = ast.parse(open(runner.__file__).read())
        main = next(node for node in tree.body
                    if isinstance(node, ast.FunctionDef) and node.name == "main")
        lines = open(runner.__file__).read().splitlines()
        validated = restored = False
        for node in ast.walk(main):
            if not isinstance(node, (ast.If, ast.Expr)):
                continue
            text = ast.get_source_segment("\n".join(lines), node)
            if "vp.validate_convergence_args(args)" in text:
                validated = True
            if isinstance(node, ast.If) and "vp.restore_best_checkpoint(" in text:
                restored = True
                test = ast.get_source_segment("\n".join(lines), node.test)
                assert "args.converge" in test
                assert 'args.convergence_mode == "bestval"' in test
                body = ast.get_source_segment("\n".join(lines), node)
                if runner is finetune_ssp:
                    assert open(runner.__file__).read().index(
                        "vp.restore_best_checkpoint") < open(
                            runner.__file__).read().index(
                                "val_scores, val_golds = collect_scores(val)")
                assert not any(isinstance(child, ast.IfExp)
                               for child in ast.walk(node))
        assert validated and restored, runner.__name__


def test_bestval_runner_result_contracts_include_acceptance():
    for runner in (finetune_one, finetune_base, finetune_mrl, finetune_clf,
                   finetune_spl, finetune_regbase, finetune_ssp):
        source = open(runner.__file__).read()
        assert "acceptance_eligible=not args.smoke" in source
        assert "vp.make_tracker(out_dir, args, rid, save_best)" in source
    source = open(finetune_clf.__file__).read()
    assert "split_evidence.json" in source
    assert "data_evidence=data_evidence" in source


def test_modification_is_sequence_multilabel_not_per_base():
    source = open(finetune_base.__file__).read()
    assert 'make_head("per-seq", d, 12)' in source
    assert "align_base_labels" not in source
    assert "aucs[7]" in source
    assert "BEACON sequence-level multi-label; m6A index 7" in source
    from rnafteval.task_registry import TASKS
    assert TASKS["modification"].granularity == "per-seq"
    source_one = open(finetune_one.__file__).read()
    assert 'protocol=vp.protocol_tag(args).lstrip("_")' in source_one
    assert 'protocol=vp.protocol_tag(args).lstrip("_")' in source
    from rnafteval import finetune_mrl, finetune_ssp
    for runner in (finetune_mrl, finetune_ssp):
        assert 'protocol=vp.protocol_tag(args).lstrip("_")' in open(runner.__file__).read()


def test_clf_converged_ledger_update_has_no_duplicate_metric():
    source = open(finetune_clf.__file__).read()
    assert 'ledger.update(rid, "done", **vp.result_ledger_fields(result))' in source
    assert 'extra_fields=result, **ledger_fields' not in source


def test_perbase_converged_ledger_updates_have_no_duplicate_value_or_metric():
    for runner in (finetune_spl, finetune_regbase):
        source = open(runner.__file__).read()
        assert 'ledger.update(rid, "done", **vp.result_ledger_fields(result))' in source
        assert 'extra_fields=result, **ledger_fields' not in source
        assert 'ledger_fields.update(vp.result_ledger_fields(result))' not in source
