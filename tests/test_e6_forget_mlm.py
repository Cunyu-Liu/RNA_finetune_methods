from types import SimpleNamespace

import pytest
import torch

from rnafteval.e6_forget import (
    convergence_out_suffix, epoch_rows, nll_eval, seed_training)


class ToyTokenizer:
    mask_token_id = 5
    pad_token_id = 0
    cls_token_id = 1
    eos_token_id = 2
    all_special_ids = [0, 1, 2, 5]
    vocab_size = 12

    def encode(self, seq):
        vocab = {"A": 3, "C": 4, "G": 6, "U": 7, "T": 7}
        return [self.cls_token_id] + [vocab[ch] for ch in seq] + [self.eos_token_id]


class IdentityLogitBackbone(torch.nn.Module):
    """Gives the input token the highest logit to expose target leakage."""

    def __init__(self, tok):
        super().__init__()
        self.tok = tok
        self.seen = []

    def forward(self, input_ids, attention_mask):
        self.seen.append((input_ids.cpu().clone(), attention_mask.cpu().clone()))
        logits = torch.zeros(
            *input_ids.shape, self.tok.vocab_size, device=input_ids.device)
        logits.scatter_(2, input_ids.unsqueeze(2), 20.0)
        return SimpleNamespace(logits=logits)


SEQS = [("AUGC" * 10)[:n] for n in (20, 24, 28, 32)]


def run_eval(seqs=SEQS, bs=2, eval_seed=201, shuffle_seed=201,
             mask_rate=0.15):
    tok = ToyTokenizer()
    backbone = IdentityLogitBackbone(tok)
    value = nll_eval(backbone, tok, seqs, "cpu", bs=bs,
                     shuffle_seed=shuffle_seed, eval_seed=eval_seed,
                     mask_rate=mask_rate)
    return value, backbone


def masks_by_length(backbone):
    tok = backbone.tok
    observed = {}
    for ids, attention in backbone.seen:
        for row in range(ids.shape[0]):
            length = int(attention[row].sum().item())
            positions = (ids[row, :length] == tok.mask_token_id).nonzero()
            observed[length] = tuple(positions.flatten().tolist())
    return observed


def test_identity_logits_do_not_make_masked_nll_near_zero():
    value, backbone = run_eval(seqs=["AUGC" * 8], bs=1)
    assert value > 10.0
    assert masks_by_length(backbone)[34]


def test_same_eval_seed_is_exact_across_batch_size_and_order():
    value_a, backbone_a = run_eval(bs=1, eval_seed=201, shuffle_seed=11)
    value_b, backbone_b = run_eval(bs=4, eval_seed=201, shuffle_seed=999)
    assert value_a == value_b
    masks_a = masks_by_length(backbone_a)
    assert masks_a == masks_by_length(backbone_b)
    for length, positions in masks_a.items():
        expected = max(1, int((length - 2) * 0.15))
        assert len(positions) == expected


def test_different_eval_seed_uses_independent_masks():
    _, backbone_a = run_eval(eval_seed=201, shuffle_seed=11)
    _, backbone_b = run_eval(eval_seed=707, shuffle_seed=11)
    assert masks_by_length(backbone_a) != masks_by_length(backbone_b)


def test_special_tokens_and_padding_are_never_masked():
    _, backbone = run_eval(seqs=["AU", "AUG"], bs=2, eval_seed=201)
    tok = backbone.tok
    for ids, attention in backbone.seen:
        masked = ids == tok.mask_token_id
        assert torch.all(attention[masked] == 1)
        for row in range(ids.shape[0]):
            length = int(attention[row].sum().item())
            positions = masked[row, :length].nonzero().flatten().tolist()
            assert positions
            assert 0 not in positions
            assert length - 1 not in positions


def test_e6v2_official_nll_delegates_to_fixed_mask():
    from rnafteval import e6_forget_task

    assert e6_forget_task.fixed_mask_nll_eval is nll_eval
    tok = ToyTokenizer()
    backbone = IdentityLogitBackbone(tok)
    value = e6_forget_task.nll_eval(
        backbone, tok, ["AUGC" * 8], "cpu", bs=1,
        shuffle_seed=201, eval_seed=201, mask_rate=0.15)
    assert value > 10.0
    assert masks_by_length(backbone)[34]


def test_modification_e6_is_sequence_multilabel_and_legacy_is_disabled():
    from pathlib import Path
    from rnafteval.task_registry import TASKS
    source = Path(__file__).parents[1].joinpath(
        "rnafteval/e6_forget_task.py").read_text()
    assert TASKS["modification"].granularity == "per-seq"
    assert "n_outputs = 12 if is_multilabel else len(labels)" in source
    assert 'make_head("per-seq", d_model, n_outputs)' in source
    assert "BCEWithLogitsLoss" in source
    assert "TokenHead" not in source
    assert "legacy per-base modification is disabled" in source
    assert "prepare_convergence_splits" in source
    assert "restore_best_checkpoint" in source


def test_training_seed_controls_python_numpy_and_torch():
    import random
    import numpy as np

    def draw(seed):
        seed_training(seed)
        return random.random(), float(np.random.rand()), float(torch.rand(1))

    assert draw(17) == draw(17)
    assert draw(17) != draw(29)


def test_epoch_rows_are_seeded_per_epoch_and_do_not_mutate_split():
    source = list(range(64))
    original = list(source)
    assert epoch_rows(source, 17, 0) == epoch_rows(source, 17, 0)
    assert epoch_rows(source, 17, 0) != epoch_rows(source, 29, 0)
    assert epoch_rows(source, 17, 0) != epoch_rows(source, 17, 1)
    assert source == original


def test_e6_convergence_suffix_isolated_without_touching_legacy():
    assert convergence_out_suffix(False, "_mlm15fix_seedfix") == "_mlm15fix_seedfix"
    assert convergence_out_suffix(True, "_mlm15fix_seedfix") == \
        "_mlm15fix_seedfix_valplateau_v2"
    assert convergence_out_suffix(True, "_valplateau_v2") == "_valplateau_v2"
    assert convergence_out_suffix(True, "_seedfix", "bestval") == \
        "_seedfix_bestval_v1"
    assert convergence_out_suffix(True, "_bestval_v1", "bestval") == \
        "_bestval_v1"
    with pytest.raises(ValueError, match="requires --converge"):
        convergence_out_suffix(False, "_valplateau_v2")
    with pytest.raises(ValueError, match="requires --converge"):
        convergence_out_suffix(False, "_bestval_v1", "bestval")
