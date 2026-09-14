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


def apply_strategy(model: nn.Module, strategy: str, lora_rank: int = 8,
                   lora_alpha: int = 4):
    """Return (model, trainable_param_count) after applying strategy.

    frozen: backbone eval-mode + requires_grad False (head trained separately)
    head-only: same freezing contract, alias for bookkeeping
    lora: peft LoRA on q/k/v/o; rank=8, alpha=4 (spec: alpha=rank/2)
    full: all params trainable
    """
    if strategy in ("frozen", "head-only"):
        for p in model.parameters():
            p.requires_grad = False
        model.eval()
        return model, 0
    if strategy == "full":
        for p in model.parameters():
            p.requires_grad = True
        return model, sum(p.numel() for p in model.parameters() if p.requires_grad)
    if strategy == "lora":
        from peft import LoraConfig, get_peft_model
        cfg = LoraConfig(
            r=lora_rank, lora_alpha=lora_alpha, lora_dropout=0.0,
            target_modules=["q", "k", "v", "o"], bias="none",
            task_type="FEATURE_EXTRACTION",
        )
        pm = get_peft_model(model, cfg)
        n = sum(p.numel() for p in pm.parameters() if p.requires_grad)
        return pm, n
    raise ValueError("unknown strategy %s" % strategy)
