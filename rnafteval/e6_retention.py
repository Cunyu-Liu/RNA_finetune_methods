#!/usr/bin/env python3
"""E6-v3: cross-task retention — the user-required axis.

Design: for each (model, strategy, seed) cell, fine-tune on ncRNA (10 ep, tuned
LR as v1), then evaluate on ALL OTHER implemented tasks (m6A, MRL, SSP) with
the *frozen head* protocol (train nothing — measure backbone representation
quality via a quick head trained on 2k samples of the *other* task's train
split, evaluated on its test split). Compare pre-finetune vs post-finetune.

This is a probe-style retention metric: "how well does the fine-tuned backbone
still support solving a DIFFERENT task with a fresh head". Paired with the
untuned backbone doing the same probe → retention ratio per task.

To keep compute sane: probe head = linear on mean-pooled hidden (per-seq tasks)
or TokenHead (per-base), trained 1 epoch on 2000 samples, n=3 seeds inherited
from the finetune seed. 3 models × 2 strategies × 3 seeds × 4 probes ≈ 72 probes
(each ~2-5 min) + 18 finetune runs already done in E6 v1 (backbones not saved —
must re-finetune; we piggyback on e6_forget_task infra and save backbone this
time via --save-ckpt).

Usage:
  python -m rnafteval.e6_retention --model RNA-Sc-10M --strategy lora \
      --seed 17 --task noncoding-rna-family --device 0
"""
from __future__ import annotations

import argparse
import contextlib
import json
import os
import random
import time

import numpy as np
import torch

ROOT = "/mnt/cunyuliu/rna-ft-eval"
S0 = ("/mnt/cunyuliu/tokenizer-benchmark/data/derived/split/"
      "release22_split_8080.parquet")
OFFICIAL = {"RiNALMo-micro", "RiNALMo-mega", "RiNALMo-650M"}


def _official_encoder(lm):
    core = lm.m if hasattr(lm, "m") else lm
    if hasattr(core, "base_model") and hasattr(core.base_model, "model"):
        core = core.base_model.model
    if hasattr(core, "model") and hasattr(core.model, "encoder"):
        return core.model
    return core


def encode_seqs(tok, seqs, device, max_len=512):
    enc = tok(seqs, padding=True, truncation=True, max_length=max_len,
              return_tensors="pt")
    return {k: v.to(device) for k, v in enc.items()}


def probe_task(backbone, tok, task, device, seed, is_official):
    """Train a small head on `task` (2k samples, 1 epoch) and return test metric."""
    from .splits import random_split
    from .tasks.ncrna import load_ncrna
    from .tasks import modification as mod_task
    from .strategies import make_head, TokenHead
    from .tasks.dedup import dedup

    fwd = _official_encoder(backbone) if is_official else backbone
    torch.manual_seed(seed)
    random.seed(seed)

    if task == "noncoding-rna-family":
        recs = load_ncrna(os.path.join(
            ROOT, "data", "beacon_raw", "noncoding-rna-family", "data"))
        recs = dedup(recs)
        parts = random_split(recs, seed=seed)
        labels = sorted({r["label"] for r in recs})
        lab2id = {l: i for i, l in enumerate(labels)}
        train = parts["train"][:2000]
        test = parts["test"][:1000]
        d = None
        with torch.no_grad():
            probe = encode_seqs(tok, [train[0]["seq"]], device)
            d = fwd(**probe).last_hidden_state.shape[-1]
        head = make_head("per-seq", d, len(labels)).to(device)
        opt = torch.optim.AdamW(head.parameters(), lr=3e-4)
        lossf = torch.nn.CrossEntropyLoss()
        backbone.eval()
        for ep in range(1):
            for i in range(0, len(train), 32):
                b = train[i:i + 32]
                enc = encode_seqs(tok, [r["seq"] for r in b], device)
                y = torch.tensor([lab2id[r["label"]] for r in b], device=device)
                with torch.no_grad():
                    h = fwd(**enc).last_hidden_state
                pad = enc["attention_mask"] == 0
                loss = lossf(head(h, pad), y)
                opt.zero_grad(); loss.backward(); opt.step()
        correct = tot = 0
        with torch.no_grad():
            for i in range(0, len(test), 64):
                b = test[i:i + 64]
                enc = encode_seqs(tok, [r["seq"] for r in b], device)
                y = torch.tensor([lab2id[r["label"]] for r in b], device=device)
                h = fwd(**enc).last_hidden_state
                pad = enc["attention_mask"] == 0
                pred = head(h, pad).argmax(-1)
                correct += (pred == y).sum().item()
                tot += len(b)
        return correct / max(tot, 1)

    if task == "modification":
        sp = mod_task.load_official_split()
        train = sp["train"][:2000]
        test = sp["test"][:1000]
        with torch.no_grad():
            probe = encode_seqs(tok, [train[0]["seq"]], device, 128)
            d = fwd(**probe).last_hidden_state.shape[-1]
        head = TokenHead(d, 1, hidden=32).to(device)
        opt = torch.optim.AdamW(head.parameters(), lr=3e-4)
        backbone.eval()

        def make_batch(b):
            enc = encode_seqs(tok, [r["seq"] for r in b], device, 128)
            L = enc["input_ids"].shape[1]
            y = torch.zeros(len(b), L, device=device)
            for i, r in enumerate(b):
                labs = r["labels"][:L]
                y[i, :len(labs)] = torch.tensor(
                    labs, dtype=torch.float32, device=device)
            return enc, y

        for ep in range(1):
            for i in range(0, len(train), 32):
                b = train[i:i + 32]
                enc, y = make_batch(b)
                with torch.no_grad():
                    h = fwd(**enc).last_hidden_state
                pad = enc["attention_mask"] == 0
                logits = head(h, pad).squeeze(-1)
                mask = enc["attention_mask"].float()
                loss = torch.nn.functional.binary_cross_entropy_with_logits(
                    logits, y, reduction="none") * mask
                loss = loss.sum() / mask.sum().clamp(min=1)
                opt.zero_grad(); loss.backward(); opt.step()
        ys, ps = [], []
        with torch.no_grad():
            for i in range(0, len(test), 64):
                b = test[i:i + 64]
                enc, y = make_batch(b)
                h = fwd(**enc).last_hidden_state
                pad = enc["attention_mask"] == 0
                logits = head(h, pad).squeeze(-1)
                m = enc["attention_mask"].bool()
                ys.append(y[m].cpu().numpy())
                ps.append(torch.sigmoid(logits[m]).cpu().numpy())
        from sklearn.metrics import roc_auc_score
        y_all = np.concatenate(ys); p_all = np.concatenate(ps)
        if len(set(y_all.tolist())) <= 1:
            return float("nan")
        return float(roc_auc_score(y_all, p_all))

    if task == "mrl":
        from .tasks import mrl as mrl_task
        data = mrl_task.load_official_split(
            "/mnt/cunyuliu/rna-ft-eval/data/beacon_raw/"
            "mean-ribosome-loading/data")
        tr = data["train"][:2000]
        te = data["test"][:1000]
        with torch.no_grad():
            probe = encode_seqs(tok, [tr[0]["seq"]], device, 128)
            d = fwd(**probe).last_hidden_state.shape[-1]
        import torch.nn as nn
        pool = nn.Sequential(nn.Linear(d, 32), nn.GELU(), nn.Linear(32, 1)).to(device)
        opt = torch.optim.AdamW(pool.parameters(), lr=3e-4)
        lossf = nn.MSELoss()
        backbone.eval()

        def embed(b):
            enc = encode_seqs(tok, [r["seq"] for r in b], device, 128)
            with torch.no_grad():
                h = fwd(**enc).last_hidden_state
                pad = enc["attention_mask"] == 0
                h = h.masked_fill(pad.unsqueeze(-1), 0.0)
                return h.sum(1) / pad.logical_not().sum(1, keepdim=True).clamp(min=1)

        for ep in range(1):
            for i in range(0, len(tr), 32):
                b = tr[i:i + 32]
                x = embed(b)
                y = torch.tensor([float(r["label"]) for r in b], device=device)
                loss = lossf(pool(x).squeeze(-1), y)
                opt.zero_grad(); loss.backward(); opt.step()
        ys, ps = [], []
        with torch.no_grad():
            for i in range(0, len(te), 64):
                b = te[i:i + 64]
                x = embed(b)
                ps.append(pool(x).squeeze(-1).cpu().numpy())
                ys.append(np.array([float(r["label"]) for r in b]))
        from scipy.stats import pearsonr
        return float(pearsonr(np.concatenate(ys), np.concatenate(ps))[0])

    if task == "secondary-structure":
        from .tasks import ssp as ssp_task
        tr = ssp_task.load_split("TR0", max_seqs=2000)
        te = ssp_task.load_split("TS0", max_seqs=1000)
        for r in tr + te:
            if "labels" not in r:
                import numpy as _np
                pair = set(r.get("pairs") or [])
                L = r["L"]
                lab = [0] * L
                for i, j in pair:
                    if i < L and j < L:
                        lab[i] = 1
                        lab[j] = 1
                r["labels"] = lab
        with torch.no_grad():
            probe = encode_seqs(tok, [tr[0]["seq"]], device, 192)
            d = fwd(**probe).last_hidden_state.shape[-1]
        from .strategies import TokenHead as TH
        head = TH(d, 1, hidden=32).to(device)
        opt = torch.optim.AdamW(head.parameters(), lr=3e-4)
        backbone.eval()

        def make_batch(b):
            enc = encode_seqs(tok, [r["seq"] for r in b], device, 192)
            L = enc["input_ids"].shape[1]
            y = torch.zeros(len(b), L, device=device)
            for i, r in enumerate(b):
                labs = r["labels"][:L]
                y[i, :len(labs)] = torch.tensor(
                    labs, dtype=torch.float32, device=device)
            return enc, y

        for ep in range(1):
            for i in range(0, len(tr), 32):
                b = tr[i:i + 32]
                enc, y = make_batch(b)
                with torch.no_grad():
                    h = fwd(**enc).last_hidden_state
                pad = enc["attention_mask"] == 0
                logits = head(h, pad).squeeze(-1)
                mask = enc["attention_mask"].float()
                loss = torch.nn.functional.binary_cross_entropy_with_logits(
                    logits, y, reduction="none") * mask
                loss = loss.sum() / mask.sum().clamp(min=1)
                opt.zero_grad(); loss.backward(); opt.step()
        ys, ps = [], []
        with torch.no_grad():
            for i in range(0, len(te), 64):
                b = te[i:i + 64]
                enc, y = make_batch(b)
                h = fwd(**enc).last_hidden_state
                pad = enc["attention_mask"] == 0
                logits = head(h, pad).squeeze(-1)
                m = enc["attention_mask"].bool()
                ys.append(y[m].cpu().numpy())
                ps.append(torch.sigmoid(logits[m]).cpu().numpy())
        from sklearn.metrics import matthews_corrcoef
        y_all = np.concatenate(ys); p_all = (np.concatenate(ps) > 0.5).astype(int)
        try:
            return float(matthews_corrcoef(y_all.astype(int), p_all))
        except Exception:
            return float("nan")

    raise ValueError("unknown probe task " + task)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--strategy", required=True, choices=["lora", "full"])
    ap.add_argument("--seed", type=int, default=17)
    ap.add_argument("--device", default="0")
    args = ap.parse_args()
    device = int(args.device)
    t0 = time.time()

    from .models import load_model
    from .ledger import claim, update
    from .e6_forget import s0_heldout_seqs, nll_eval  # reuse

    out_dir = os.path.join(ROOT, "artifacts", "e6ret",
                           "%s_%s_s%d" % (args.model, args.strategy, args.seed))
    os.makedirs(out_dir, exist_ok=True)
    res = claim(args.model, "e6-retention", args.strategy, args.seed,
                "cross-task", device=device, out_dir=out_dir,
                note="E6-v3 cross-task retention",
                extra="_ct")
    if res is None or res.get("claimed") is False:
        print("skip (ledger: %s)" % (res or {}).get("reason"), flush=True)
        return 0

    is_official = args.model in OFFICIAL
    if is_official:
        from multimolecule import RiNALMoForMaskedLM, RnaTokenizer
        from .models import hf_path, MODEL_SPECS
        path = hf_path(MODEL_SPECS[args.model].repo)
        tok = RnaTokenizer.from_pretrained(path)
        lm = RiNALMoForMaskedLM.from_pretrained(path, trust_remote_code=True)
        with torch.no_grad():
            lm.lm_head.decoder.bias.zero_()
        backbone = lm.to(device)
    else:
        spec, tok, backbone = load_model(args.model, device)

    probe_tasks = ["modification", "mrl", "secondary-structure"]
    pre = {}
    for t in probe_tasks:
        try:
            pre[t] = probe_task(backbone, tok, t, device, args.seed, is_official)
            print("pre %s = %.4f" % (t, pre[t]), flush=True)
        except Exception as e:
            pre[t] = None
            print("pre %s FAILED: %s" % (t, e), flush=True)

    # ---- finetune on ncRNA (same protocol as E6 v1) ----
    from .strategies import apply_strategy, make_head
    from .finetune_one import encode_seqs as enc_cls, batches
    from .splits import random_split
    from .tasks.ncrna import load_ncrna
    from .tasks.dedup import dedup

    recs = load_ncrna(os.path.join(
        ROOT, "data", "beacon_raw", "noncoding-rna-family", "data"))
    recs = dedup(recs)
    parts = random_split(recs, seed=args.seed)
    labels = sorted({r["label"] for r in recs})
    lab2id = {l: i for i, l in enumerate(labels)}
    for k in parts:
        for r in parts[k]:
            r["label_id"] = lab2id[r["label"]]
    train = parts["train"]

    with torch.no_grad():
        probe = enc_cls(tok, [train[0]["seq"]], device)
        fwd0 = _official_encoder(backbone) if is_official else backbone
        d_model = fwd0(**probe).last_hidden_state.shape[-1]

    lr = 3e-4 if args.strategy == "lora" else (
        1e-5 if is_official else 3e-5)
    backbone, n_trainable = apply_strategy(backbone, args.strategy)
    head = make_head("per-seq", d_model, len(labels)).to(device)
    tp = [p for p in head.parameters() if p.requires_grad]
    if hasattr(backbone, "m"):
        tp += [p for p in backbone.m.parameters() if p.requires_grad]
    else:
        tp += [p for p in backbone.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(tp, lr=lr)
    lossf = torch.nn.CrossEntropyLoss()
    tr_backbone = args.strategy in ("lora", "full")
    enc_core = _official_encoder(backbone) if is_official else None
    fwd = enc_core if is_official else backbone
    for ep in range(10):
        backbone.train(tr_backbone)
        head.train()
        tot, nb = 0.0, 0
        for b in batches(train, 32):
            enc = enc_cls(tok, [r["seq"] for r in b], device)
            y = torch.tensor([r["label_id"] for r in b], device=device)
            if tr_backbone:
                h = fwd(**enc).last_hidden_state
            else:
                with torch.no_grad():
                    h = fwd(**enc).last_hidden_state
            pad = enc["attention_mask"] == 0
            loss = lossf(head(h, pad), y)
            opt.zero_grad(); loss.backward()
            torch.nn.utils.clip_grad_norm_(tp, 1.0)
            opt.step()
            tot += loss.item(); nb += 1
        print("epoch %d loss %.4f" % (ep, tot / max(nb, 1)), flush=True)

    if is_official and hasattr(backbone, "merge_and_unload"):
        backbone = backbone.merge_and_unload()
    backbone.eval()

    post = {}
    for t in probe_tasks:
        try:
            post[t] = probe_task(backbone, tok, t, device, args.seed, is_official)
            print("post %s = %.4f" % (t, post[t]), flush=True)
        except Exception as e:
            post[t] = None
            print("post %s FAILED: %s" % (t, e), flush=True)

    result = {
        "run_id": res["row"]["run_id"], "model": args.model,
        "strategy": args.strategy, "seed": args.seed,
        "finetune_task": "noncoding-rna-family",
        "pre": pre, "post": post,
        "retention": {t: (round(post[t] / pre[t], 4)
                          if pre.get(t) and post.get(t) and pre[t] != 0 else None)
                      for t in probe_tasks},
        "wall_sec": round(time.time() - t0, 1),
        "protocol": "E6-v3: cross-task retention (probe head 2k/1ep)",
    }
    with open(os.path.join(out_dir, "result.json"), "w") as fh:
        json.dump(result, fh, indent=2)
    update(res["row"]["run_id"], "done", **{k: v for k, v in result.items()
                                             if k != "run_id"})
    print(json.dumps(result, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
