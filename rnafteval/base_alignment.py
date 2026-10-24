"""B20 token/label alignment for per-base splice and regression tasks."""
from __future__ import annotations

import numpy as np
import torch


_SPECIAL_ID_ATTRS = (
    "pad_token_id", "cls_token_id", "sep_token_id", "bos_token_id",
    "eos_token_id", "cls_id", "sep_id",
)


def _rows2d(value):
    if torch.is_tensor(value):
        return value.detach().cpu().tolist()
    if hasattr(value, "tolist"):
        value = value.tolist()
    return [list(row.ids) if hasattr(row, "ids") else list(row)
            for row in value]


def _encoded_rows(enc):
    ids = _rows2d(enc["input_ids"])
    attention = enc.get("attention_mask")
    if attention is None:
        raise ValueError("B20: attention_mask is required for base alignment")
    attention = _rows2d(attention)
    if len(ids) != len(attention):
        raise ValueError("B20: input_ids/attention_mask batch mismatch")
    return ids, attention


def _special_mask(tok, ids):
    mask = np.zeros(len(ids), dtype=bool)
    getter = getattr(tok, "get_special_tokens_mask", None)
    if getter is not None:
        try:
            raw = getter(list(ids), already_has_special_tokens=True)
        except (TypeError, NotImplementedError):
            raw = None
        if raw is not None:
            if len(raw) != len(ids):
                raise ValueError("B20: special-token mask length mismatch")
            mask |= np.asarray(raw, dtype=bool)
    special_ids = set(getattr(tok, "all_special_ids", None) or [])
    for attr in _SPECIAL_ID_ATTRS:
        token_id = getattr(tok, attr, None)
        if token_id is not None:
            special_ids.add(token_id)
    if special_ids:
        mask |= np.asarray([token_id in special_ids for token_id in ids],
                           dtype=bool)
    return mask


def _base_positions(tok, ids, attention):
    if len(ids) != len(attention):
        raise ValueError("B20: token/attention row length mismatch")
    special = _special_mask(tok, ids)
    active = np.asarray(attention) == 1
    return np.flatnonzero(active & ~special), active, special


def align_base_labels(tok, enc, rows, max_len, dtype=torch.float32,
                      allow_short_labels=False):
    """Return dense labels and the bool supervision mask for a token batch.

    Full, untruncated tokenization is checked separately so k-mer tokenization
    cannot hide behind max_len truncation. Truncated base tokens must be the
    deterministic right-truncated prefix of the full base-token sequence.
    """
    ids, attention = _encoded_rows(enc)
    seqs = [row["seq"] for row in rows]
    if len(ids) != len(rows):
        raise ValueError("B20: encoding/row batch mismatch")
    full_limit = max(max_len, max(map(len, seqs)) + 2)
    full_enc = tok(seqs, padding=True, truncation=False,
                   max_length=full_limit, return_tensors="pt")
    full_ids, full_attention = _encoded_rows(full_enc)

    input_ids = enc["input_ids"]
    device = input_ids.device if torch.is_tensor(input_ids) else torch.device("cpu")
    y = torch.zeros((len(rows), input_ids.shape[1]), dtype=dtype,
                    device=device)
    supervision = torch.zeros((len(rows), input_ids.shape[1]), dtype=torch.bool,
                              device=device)
    for i, row in enumerate(rows):
        seq = row["seq"]
        full_pos, _, _ = _base_positions(
            tok, full_ids[i], full_attention[i])
        if len(full_pos) != len(seq):
            raise ValueError(
                "B20 token/base mismatch at row %d: %d tokens for %d bases; "
                "per-base tasks require single-base tokens"
                % (i, len(full_pos), len(seq)))
        pos, active, special = _base_positions(tok, ids[i], attention[i])
        full_special_n = int((np.asarray(full_attention[i]) == 1).sum()) - len(full_pos)
        expected_n = min(len(seq), max(0, max_len - full_special_n))
        if len(pos) != expected_n:
            raise ValueError(
                "B20 truncation mismatch at row %d: got %d base tokens, "
                "expected %d" % (i, len(pos), expected_n))
        core_ids = np.asarray(ids[i], dtype=np.int64)[pos]
        full_core_ids = np.asarray(full_ids[i], dtype=np.int64)[full_pos]
        if not np.array_equal(core_ids, full_core_ids[:expected_n]):
            raise ValueError(
                "B20: only deterministic right truncation is supported (row %d)"
                % i)
        labels = np.asarray(row["labels"])
        if labels.ndim != 1:
            raise ValueError("B20: labels must be one-dimensional (row %d)" % i)
        if len(labels) > len(seq) or (
                not allow_short_labels and len(labels) != len(seq)):
            raise ValueError(
                "B20 label/sequence mismatch at row %d: %d labels for %d bases"
                % (i, len(labels), len(seq)))
        scored_n = min(len(labels), expected_n)
        row_mask = np.zeros(len(ids[i]), dtype=bool)
        row_mask[pos[:scored_n]] = True
        assert not np.any(row_mask & ~active), "B20: PAD entered supervision"
        assert not np.any(row_mask & special), "B20: special token entered supervision"
        if scored_n:
            y[i, pos[:scored_n]] = torch.as_tensor(
                labels[:scored_n], dtype=dtype, device=device)
            supervision[i, pos[:scored_n]] = True
    return y, supervision
