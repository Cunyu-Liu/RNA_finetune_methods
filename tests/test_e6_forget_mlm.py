from types import SimpleNamespace

import torch

from rnafteval.e6_forget import nll_eval


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
