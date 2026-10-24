import os
import runpy
import sys
from types import SimpleNamespace

import numpy as np
import pytest
import torch

from rnafteval import finetune_clf, finetune_regbase, finetune_spl, ledger
from rnafteval.base_alignment import align_base_labels


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
