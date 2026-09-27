"""NucleicBERT loader for rnafteval (vendored, no pip)."""
from __future__ import annotations

import glob
import os
import sys

import torch.nn as nn

NB_CODE = "/mnt/cunyuliu/hf_home/nucleicbert-code"
NB_CKPT_DIR = "/mnt/cunyuliu/hf_home/models--nucleicbert/snapshots/main"
NB_TOKENIZER = os.path.join(NB_CODE, "nucleicbert/tokenizers/noncoding_seqs.json")

sys.path.insert(0, NB_CODE)


class _NucleicBertTok:
    """U->T char tokenizer with [CLS]/[SEP]; HF-ish __call__ contract."""

    def __init__(self):
        from transformers import PreTrainedTokenizerFast
        self._fast = PreTrainedTokenizerFast(tokenizer_file=NB_TOKENIZER)
        self._vocab = self._fast.vocab
        self.pad_token_id = self._vocab["[PAD]"]
        self.cls_id = self._vocab["[CLS]"]
        self.sep_id = self._vocab["[SEP]"]

    def encode(self, seq):
        seq = seq.upper().replace("U", "T").replace("X", "N").replace("I", "N")
        toks = self._fast.tokenize(seq) or ["[UNK]"]
        return self._fast.convert_tokens_to_ids(toks)

    def __call__(self, seqs, padding=True, truncation=True, max_length=512,
                 return_tensors="pt"):
        import torch
        ids = []
        for s in seqs:
            core = self.encode(s)[: max_length - 2]
            ids.append([self.cls_id] + core + [self.sep_id])
        ml = max(len(x) for x in ids)
        input_ids, attn = [], []
        for x in ids:
            pad_n = ml - len(x)
            input_ids.append(x + [self.pad_token_id] * pad_n)
            attn.append([1] * len(x) + [0] * pad_n)
        return {"input_ids": torch.tensor(input_ids),
                "attention_mask": torch.tensor(attn)}


class _EncoderOutput:
    def __init__(self, h):
        self.last_hidden_state = h


class _NucleicBertPeftShim(nn.Module):
    """Adapt BERTEncoder forward signature for peft PeftModel wrapping:
    peft passes all kwargs (attention_mask etc.) to model.forward —
    BERTEncoder.forward(input_ids, need_weights=...) rejects them.
    Shim swallows extras. Placed between peft and encoder via model.m swap."""

    def __init__(self, enc):
        super().__init__()
        self.enc = enc
        # passthrough attrs peft may probe
        for attr in ("transformer_blocks", "embedding", "config"):
            if hasattr(enc, attr):
                setattr(self, attr, getattr(enc, attr))

    def forward(self, input_ids=None, attention_mask=None,
                need_weights=False, **kw):
        out = self.enc(input_ids, need_weights=need_weights)
        return out

    def __getattr__(self, name):
        try:
            return super().__getattr__(name)
        except AttributeError:
            return getattr(self.enc, name)


class _NucleicBertWrapper:
    """Wrap BERTEncoder into HF .last_hidden_state contract; **kw pass-through
    lets peft/strategies reach the underlying nn.Module via .m."""

    def __init__(self, model):
        self.m = model

    def __call__(self, input_ids=None, attention_mask=None, **kw):
        x, _, _ = self.m(input_ids)
        return _EncoderOutput(x)

    def __getattr__(self, name):
        return getattr(self.m, name)

    def to(self, device):
        self.m = self.m.to(device)
        return self

    def parameters(self):
        return self.m.parameters()

    def train(self, mode=True):
        self.m.train(mode)
        return self

    def eval(self):
        self.m.eval()
        return self


def load_nucleicbert(spec, device):
    import torch
    from nucleicbert.models.bert import BERT, NB_CONFIG

    cks = [f for f in sorted(glob.glob(os.path.join(NB_CKPT_DIR, "*")))
           if f.endswith((".ckpt", ".pt", ".pth", ".bin"))]
    if not cks:
        raise FileNotFoundError(
            "NucleicBERT ckpt missing in %s (Zenodo 10.5281/zenodo.16989562)"
            % NB_CKPT_DIR)
    full = BERT(**NB_CONFIG)
    full.load_state_dict(torch.load(cks[0], map_location="cpu",
                                    weights_only=False))
    enc = full.encoder.to(device).eval()
    return _NucleicBertTok(), _NucleicBertWrapper(enc)
