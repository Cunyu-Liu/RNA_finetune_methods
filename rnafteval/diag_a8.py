"""A8 崩溃机制显微镜：默认 LR 3e-4 全参微调的首 N 步动态。

对比崩溃 vs 幸存模型：梯度范数 / 权重漂移（分桶）/ 表示熵与有效秩。
复刻 finetune_base m6A 训练环（BCE+pad mask / clip 1.0 / AdamW）。

用法: python -m rnafteval.diag_a8 --model SpliceBERT --device 4 --steps 100
产物: artifacts/a8_diag/<model>.json（不写 ledger——诊断非正式实验）
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random

import numpy as np
import torch

from .models import load_model
from .strategies import apply_strategy, TokenHead
from .tasks import modification as mod_task

ROOT = "/mnt/cunyuliu/rna-ft-eval"


def encode_seqs(tok, seqs, device, max_len=128):
    enc = tok(seqs, padding=True, truncation=True, max_length=max_len,
              return_tensors="pt")
    return {k: v.to(device) for k, v in enc.items()}


def eff_rank(x):
    """有效秩 = 归一化奇异值分布的指数熵。"""
    s = torch.linalg.svdvals(x.float())
    p = s / s.sum().clamp(min=1e-12)
    p = torch.clamp(p, min=1e-12)
    return float(torch.exp(-(p * p.log()).sum()))


def cos_uniformity(x):
    """平均非对角余弦——越高表示越坍缩到一致方向。"""
    x = x.float()
    x = x / x.norm(dim=-1, keepdim=True).clamp(min=1e-8)
    g = x @ x.t()
    n = g.shape[0]
    off = (g.sum() - g.diagonal().sum()) / (n * (n - 1))
    return float(off)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--device", type=int, required=True)
    ap.add_argument("--steps", type=int, default=100)
    ap.add_argument("--batch-size", type=int, default=32)
    ap.add_argument("--lr", type=float, default=3e-4)
    args = ap.parse_args()

    device = "cuda:%d" % args.device
    torch.manual_seed(17)
    random.seed(17)

    sp = mod_task.load_official_split()
    train, test = sp["train"], sp["test"]
    rng = random.Random(17)
    train = rng.sample(train, args.steps * args.batch_size)
    probe_rows = test[:64]

    spec, tok, backbone = load_model(args.model, device)
    with torch.no_grad():
        pe = encode_seqs(tok, [train[0]["seq"]], device, 128)
        d = backbone(**pe).last_hidden_state.shape[-1]
    backbone, _ = apply_strategy(backbone, "full")
    head = TokenHead(d, 1, hidden=32).to(device)
    params = list(head.parameters()) + list(backbone.parameters())
    opt = torch.optim.AdamW(params, lr=args.lr)

    # 权重分桶快照（embed / early / late / head）
    named = list(backbone.named_parameters())
    n_pr = len(named)
    w0 = {}
    buckets = {"embed": [], "early": [], "late": [], "head": []}
    for i, (nm, p) in enumerate(named):
        w0[nm] = p.detach().clone()
        if "embed" in nm.lower() or "tok" in nm.lower():
            buckets["embed"].append(nm)
        elif i < n_pr // 2:
            buckets["early"].append(nm)
        else:
            buckets["late"].append(nm)

    def drift():
        out = {}
        for b, names in buckets.items():
            num, den = 0.0, 0.0
            for nm in names:
                p = dict(backbone.named_parameters())[nm]
                num += float((p.detach() - w0[nm]).pow(2).sum())
                den += float(w0[nm].pow(2).sum())
            out[b] = math.sqrt(num / max(den, 1e-12))
        return out

    def repr_stats():
        backbone.eval()
        with torch.no_grad():
            enc = encode_seqs(tok, [r["seq"] for r in probe_rows],
                              device, 128)
            out = backbone(**enc)
            h = out.last_hidden_state
            m = enc["attention_mask"].bool()
            x = h[m]
            r = {"effrank_last": eff_rank(x), "cos_last": cos_uniformity(x),
                 "featnorm_last": float(x.norm(dim=-1).mean())}
            hs = getattr(out, "hidden_states", None)
            if hs and len(hs) > 2:
                mid = hs[len(hs) // 2]
                xm = mid[m]
                r["effrank_mid"] = eff_rank(xm)
                r["cos_mid"] = cos_uniformity(xm)
        backbone.train()
        return r

    def make_batch(b):
        enc = encode_seqs(tok, [r["seq"] for r in b], device, 128)
        L = enc["input_ids"].shape[1]
        y = torch.zeros(len(b), L, device=device)
        for i, r in enumerate(b):
            labs = r["labels"][:L]
            y[i, :len(labs)] = torch.tensor(labs, dtype=torch.float32,
                                             device=device)
        return enc, y

    log = {"model": args.model, "lr": args.lr, "steps": args.steps,
           "records": []}
    backbone.train()
    ckpts = {0} | {1, 2, 5, 10, 20, 50, args.steps}
    losses = []
    bi = 0
    for step in range(args.steps + 1):
        if step > 0:
            b = train[bi:bi + args.batch_size]
            bi += args.batch_size
            enc, y = make_batch(b)
            h = backbone(**enc).last_hidden_state
            pad = enc["attention_mask"] == 0
            logits = head(h, pad).squeeze(-1)
            mask = enc["attention_mask"].float()
            loss = torch.nn.functional.binary_cross_entropy_with_logits(
                logits, y, reduction="none") * mask
            loss = loss.sum() / mask.sum().clamp(min=1)
            opt.zero_grad()
            loss.backward()
            gn = float(torch.nn.utils.clip_grad_norm_(params, 1.0))
            opt.step()
            losses.append(float(loss.item()))
        else:
            gn = 0.0
        if step in ckpts:
            rec = {"step": step, "grad_norm": gn,
                   "loss_run": float(np.mean(losses[-10:])) if losses else None,
                   "drift": drift(), "repr": repr_stats()}
            log["records"].append(rec)
            print(json.dumps({"step": step, "gn": round(gn, 3),
                              "loss": rec["loss_run"]}), flush=True)

    out_dir = os.path.join(ROOT, "artifacts", "a8_diag")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "%s.json" % args.model.replace("-", "_"))
    with open(out, "w") as f:
        json.dump(log, f, indent=1)
    print("written:", out)


if __name__ == "__main__":
    raise SystemExit(main())
