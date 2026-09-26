"""Training strategies (frozen / lora / head-only / full) — spec §3 definitions.

Head spec (frozen口径): single-hidden-layer MLP, hidden width 32 (Schmirler-aligned)
for per-seq tasks with attention pooling over non-pad tokens (mean-pool FORBIDDEN).
"""
from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F


class AttentionPool(nn.Module):
    """Attention pooling over non-pad tokens (order-aware)."""

    def __init__(self, d_model: int):
        super().__init__()
        self.score = nn.Linear(d_model, 1)

    def forward(self, h: torch.Tensor, pad_mask: torch.Tensor) -> torch.Tensor:
        s = self.score(h).squeeze(-1)
        s = s.masked_fill(pad_mask, float("-inf"))
        w = F.softmax(s, dim=-1)
        return (h * w.unsqueeze(-1)).sum(dim=1)


class SeqMLPHead(nn.Module):
    """Per-seq head: attention pool -> Linear(D,32) -> GELU -> Linear(32,C)."""

    def __init__(self, d_model: int, n_classes: int, hidden: int = 32):
        super().__init__()
        self.pool = AttentionPool(d_model)
        self.fc1 = nn.Linear(d_model, hidden)
        self.fc2 = nn.Linear(hidden, n_classes)

    def forward(self, h: torch.Tensor, pad_mask: torch.Tensor) -> torch.Tensor:
        z = self.pool(h, pad_mask)
        return self.fc2(F.gelu(self.fc1(z)))


class TokenHead(nn.Module):
    """Per-base head: Linear(D, hidden) -> GELU -> Linear(hidden, C)."""

    def __init__(self, d_model: int, n_classes: int, hidden: int = 32):
        super().__init__()
        self.fc1 = nn.Linear(d_model, hidden)
        self.fc2 = nn.Linear(hidden, n_classes)

    def forward(self, h: torch.Tensor, pad_mask: torch.Tensor) -> torch.Tensor:
        z = self.fc2(F.gelu(self.fc1(h)))
        return z.masked_fill(pad_mask.unsqueeze(-1), 0.0)


def make_head(granularity: str, d_model: int, n_classes: int,
              hidden: int = 32) -> nn.Module:
    if granularity == "per-seq":
        return SeqMLPHead(d_model, n_classes, hidden)
    return TokenHead(d_model, n_classes, hidden)


def apply_strategy(model, strategy: str, lora_rank: int = 8,
                   lora_alpha: int = 4):
    """Return (model, trainable_param_count) after applying strategy.

    model may be an HF nn.Module OR a wrapper with .m (RNA-Sc custom arch).
    frozen / head-only: freeze everything (head trained separately).
    lora: peft on the underlying nn.Module; HF models target q/k/v/o,
    RNA-Sc targets qkv/out projections (its attention exposes qkv+out).
    full: all params trainable.
    """
    core = model.m if hasattr(model, "m") else model

    if strategy in ("frozen", "head-only"):
        for p in core.parameters():
            p.requires_grad = False
        core.eval()
        return model, 0
    if strategy == "full":
        for p in core.parameters():
            p.requires_grad = True
        return model, sum(p.numel() for p in core.parameters()
                          if p.requires_grad)
    if strategy == "lora":
        from peft import LoraConfig, get_peft_model
        hf_style = hasattr(core, "config") and hasattr(core, "forward")
        rnasc_style = hasattr(core, "blocks")
        if rnasc_style:
            target = ["qkv", "out"]
        elif hf_style:
            # multimolecule RiNALMo/ERNIE expose query/key/value/dense (BERT-style)
            names = {n for n, _ in core.named_modules()}
            for cand in (["query", "key", "value", "dense"],
                         ["Wqkv", "attention.output.dense"],
                         ["qkv_proj", "out_proj"],
                         ["q", "k", "v", "o"]):
                if all(any(c in n for n in names) for c in cand):
                    target = cand
                    break
            else:
                target = ["query", "value"]
        else:
            target = ["query", "value"]
        cfg = LoraConfig(
            r=lora_rank, lora_alpha=lora_alpha, lora_dropout=0.0,
            target_modules=target, bias="none",
            task_type="FEATURE_EXTRACTION",
        )
        pm = get_peft_model(core, cfg)
        if hasattr(model, "m"):
            model.m = pm
        else:
            model = pm
        n = sum(p.numel() for p in pm.parameters() if p.requires_grad)
        return model, n
    raise ValueError("unknown strategy %s" % strategy)
