#!/usr/bin/env python3
"""E6-v2: multi-task-origin forgetting — ncRNA vs m6A starting task.

Same measurement as e6_forget (pre/post S0 held-out NLL + reorder noise band),
but the finetune task is selectable (ncRNA per-seq or modification per-base).
Goal: does per-base (m6A) finetuning forget less than per-seq (ncRNA)?
This fills the 'differential forgetting' gap: granularity of the *finetune task*
vs forgetting magnitude.

Usage:
  python -m rnafteval.e6_forget_task --model RNA-Sc-10M --strategy lora \
      --task modification --seed 17 --device 0
"""
from __future__ import annotations

import argparse
import contextlib
import json
import os
import random
import time

import torch

ROOT = "/mnt/cunyuliu/rna-ft-eval"
S0 = ("/mnt/cunyuliu/tokenizer-benchmark/data/derived/split/"
      "release22_split_8080.parquet")

MODEL_MAXLEN = {"RNA-Sc-1M": 256, "RNA-Sc-10M": 512, "RNA-Sc-30M": 480,
                "RNA-Sc-100M": 768, "RNA-Sc-650M": 1408}
OFFICIAL = {"RiNALMo-micro", "RiNALMo-mega", "RiNALMo-650M"}


def s0_heldout_seqs(n_max=2000):
    import pandas as pd
    df = pd.read_parquet(S0, columns=["canonical_sequence", "split_membership"])
    held = df[df["split_membership"].isin(["test", "family_test"])]
    seqs = [s for s in held["canonical_sequence"].tolist()
            if isinstance(s, str) and 32 <= len(s) <= 512]
    rng = random.Random(101)
    rng.shuffle(seqs)
    return seqs[:n_max]


def encode(tok, seqs, device, max_len=512):
    if hasattr(tok, "mask_token_id"):
        ids, mask = [], []
        for s in seqs:
            t = tok.encode(s[:max_len])
            ids.append(t)
            mask.append([1] * len(t))
        ml = max(len(x) for x in ids)
        for x, m in zip(ids, mask):
            while len(x) < ml:
                x.append(tok.pad_token_id)
                m.append(0)
        return {"input_ids": torch.tensor(ids, device=device),
                "attention_mask": torch.tensor(mask, device=device)}
    V = {"A": 0, "C": 1, "G": 2, "U": 3, "T": 3}
    PAD = 4
    ids, mask = [], []
    for s in seqs:
        t = [V.get(ch, 0) for ch in s[:max_len]]
        ids.append(t)
        mask.append([1] * len(t))
    ml = max(len(x) for x in ids)
    for x, m in zip(ids, mask):
        while len(x) < ml:
            x.append(PAD)
            m.append(0)
    return {"input_ids": torch.tensor(ids, device=device),
            "attention_mask": torch.tensor(mask, device=device)}


def _official_encoder(lm):
    core = lm.m if hasattr(lm, "m") else lm
    if hasattr(core, "base_model") and hasattr(core.base_model, "model"):
        core = core.base_model.model
    if hasattr(core, "model") and hasattr(core.model, "encoder"):
        return core.model
    return core


def nll_eval(backbone, tok, seqs, device, bs=8, shuffle_seed=None):
    order = list(range(len(seqs)))
    if shuffle_seed is not None:
        random.Random(shuffle_seed).shuffle(order)
    tot, cnt = 0.0, 0
    backbone.eval()
    is_official = hasattr(tok, "mask_token_id")
    with torch.no_grad():
        for i in range(0, len(order), bs):
            chunk = [seqs[j] for j in order[i:i + bs]]
            enc = encode(tok, chunk, device)
            ids = enc["input_ids"]
            mask = enc["attention_mask"]
            if is_official:
                out = backbone(input_ids=ids, attention_mask=mask)
                logits = out.logits
                lp = torch.nn.functional.log_softmax(logits.float(), dim=-1)
                sel = (mask == 1)
                tgt = ids.reshape(-1)[sel.reshape(-1)]
                v = lp.reshape(-1, lp.shape[-1])[sel.reshape(-1)]
                tot += (-v.gather(1, tgt.unsqueeze(1)).sum()).item()
                cnt += int(sel.sum().item())
                continue
            core = backbone.m if hasattr(backbone, "m") else backbone
            if hasattr(core, "base_model") and hasattr(core.base_model, "model"):
                core = core.base_model.model
            out = core(enc["input_ids"], None, return_all_hiddens=False)
            logits = out[0] if isinstance(out, (tuple, list)) else out
            lp = torch.nn.functional.log_softmax(logits.float(), dim=-1)
            shift_lp = lp[:, :-1]
            shift_ids = ids[:, 1:]
            shift_mask = (mask[:, 1:] == 1)
            sel = shift_mask.reshape(-1)
            tgt = shift_ids.reshape(-1)[sel]
            v = shift_lp.reshape(-1, shift_lp.shape[-1])[sel]
            tot += (-v.gather(1, tgt.unsqueeze(1)).sum()).item()
            cnt += int(sel.sum().item())
    return tot / max(cnt, 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--task", default="noncoding-rna-family",
                    choices=["noncoding-rna-family", "modification"])
    ap.add_argument("--strategy", required=True,
                    choices=["lora", "full"])
    ap.add_argument("--seed", type=int, default=17)
    ap.add_argument("--lr", type=float, default=None)
    ap.add_argument("--device", default="0")
    ap.add_argument("--epochs", type=int, default=None)
    ap.add_argument("--n-train-cap", type=int, default=20000)
    ap.add_argument("--n-holdout", type=int, default=2000)
    args = ap.parse_args()
    device = int(args.device)
    t0 = time.time()

    if args.lr is None:
        args.lr = 3e-4 if args.strategy == "lora" else (
            1e-5 if args.model in OFFICIAL else 3e-5)
    if args.epochs is None:
        args.epochs = 10 if args.task == "noncoding-rna-family" else 3

    from .models import load_model
    from .strategies import apply_strategy, make_head, TokenHead
    from .ledger import claim, update
    from .finetune_one import encode_seqs as enc_cls, batches
    from .splits import random_split
    from .tasks.ncrna import load_ncrna
    from .tasks import modification as mod_task
    from .tasks.dedup import dedup

    tag = "" if args.model not in OFFICIAL else "_off"
    out_dir = os.path.join(
        ROOT, "artifacts", "e6",
        "%s_%s_task-%s_s%d" % (args.model, args.strategy,
                               "ncrna" if args.task == "noncoding-rna-family"
                               else "m6a", args.seed))
    os.makedirs(out_dir, exist_ok=True)
    res = claim(args.model, "e6-forgetting", args.strategy, args.seed,
                "s0-heldout", device=device, out_dir=out_dir,
                note="E6-v2 task-origin forgetting",
                extra="_task%s_s%d" % (
                    "ncrna" if args.task == "noncoding-rna-family" else "m6a",
                    0))
    # Use a unique run_id via extra tag so claim won't collide with v1 rows:
    # claim() builds rid from extra; we recompute our own below for ledger
    # consistency.
    if res is None or res.get("claimed") is False:
        print("skip (ledger: %s)" % (res or {}).get("reason"), flush=True)
        return 0

    hold = s0_heldout_seqs(args.n_holdout)
    print("S0 holdout: %d seqs" % len(hold), flush=True)

    # ---- load task data ----
    if args.task == "noncoding-rna-family":
        recs = load_ncrna(os.path.join(
            ROOT, "data", "beacon_raw", "noncoding-rna-family", "data"))
        recs = dedup(recs)
        parts = random_split(recs, seed=args.seed)
        labels = sorted({r["label"] for r in recs})
        lab2id = {l: i for i, l in enumerate(labels)}
        for k in parts:
            for r in parts[k]:
                r["label_id"] = lab2id[r["label"]]
        train = parts["train"][:args.n_train_cap] if args.n_train_cap else parts["train"]
        is_per_base = False
    else:
        sp = mod_task.load_official_split()
        train = sp["train"][:args.n_train_cap] if args.n_train_cap else sp["train"]
        is_per_base = True

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
        d_model = MODEL_SPECS[args.model].d_model
    else:
        spec, tok, backbone = load_model(args.model, device)
        d_model = spec.d_model

    with torch.no_grad():
        probe = enc_cls(tok, [train[0]["seq"]], device)
        probe_core = _official_encoder(backbone) if is_official else backbone
        h_dim = probe_core(**probe).last_hidden_state.shape[-1]
    if h_dim != d_model:
        d_model = h_dim

    pre_a = nll_eval(backbone, tok, hold, device, shuffle_seed=201)
    pre_b = nll_eval(backbone, tok, hold, device, shuffle_seed=707)
    noise_band = abs(pre_b - pre_a)
    print("pre NLL: %.4f / %.4f (noise %.2e)" % (pre_a, pre_b, noise_band),
          flush=True)

    # ---- finetune ----
    backbone, n_trainable = apply_strategy(backbone, args.strategy)
    tr_backbone = args.strategy in ("lora", "full", "dora", "ia3")
    enc_core = _official_encoder(backbone) if is_official else None
    fwd = enc_core if is_official else backbone

    if not is_per_base:
        head = make_head("per-seq", d_model, len(labels)).to(device)
        tp = [p for p in head.parameters() if p.requires_grad]
        if hasattr(backbone, "m"):
            tp += [p for p in backbone.m.parameters() if p.requires_grad]
        else:
            tp += [p for p in backbone.parameters() if p.requires_grad]
        opt = torch.optim.AdamW(tp, lr=args.lr)
        lossf = torch.nn.CrossEntropyLoss()
        for ep in range(args.epochs):
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
    else:
        head = TokenHead(d_model, 1, hidden=32).to(device)
        tp = [p for p in head.parameters() if p.requires_grad] + \
            [p for p in backbone.parameters() if p.requires_grad]
        opt = torch.optim.AdamW(tp, lr=args.lr)

        def make_batch(b):
            enc = enc_cls(tok, [r["seq"] for r in b], device, 128)
            L = enc["input_ids"].shape[1]
            y = torch.zeros(len(b), L, device=device)
            for i, r in enumerate(b):
                labs = r["labels"][:L]
                y[i, :len(labs)] = torch.tensor(
                    labs, dtype=torch.float32, device=device)
            return enc, y

        for ep in range(args.epochs):
            backbone.train(tr_backbone)
            head.train()
            tot, nb = 0.0, 0
            for b in batches(train, 32):
                enc, y = make_batch(b)
                no_grad = not tr_backbone
                with contextlib.nullcontext() if not no_grad \
                        else torch.no_grad():
                    h = fwd(**enc).last_hidden_state
                pad = enc["attention_mask"] == 0
                logits = head(h, pad).squeeze(-1)
                mask = enc["attention_mask"].float()
                loss = torch.nn.functional.binary_cross_entropy_with_logits(
                    logits, y, reduction="none") * mask
                loss = loss.sum() / mask.sum().clamp(min=1)
                opt.zero_grad(); loss.backward()
                torch.nn.utils.clip_grad_norm_(tp, 1.0)
                opt.step()
                tot += loss.item(); nb += 1
            print("epoch %d loss %.4f" % (ep, tot / max(nb, 1)), flush=True)

    if is_official and hasattr(backbone, "merge_and_unload") and \
            args.strategy in ("lora", "dora", "ia3", "prefix"):
        merged = backbone.merge_and_unload()
        merged.eval()
        backbone = merged
        print("peft merged back for post-NLL", flush=True)

    post = nll_eval(backbone, tok, hold, device, shuffle_seed=201)

    result = {
        "run_id": res["row"]["run_id"], "model": args.model,
        "task": args.task, "strategy": args.strategy, "seed": args.seed,
        "lr": args.lr, "epochs": args.epochs,
        "n_holdout": len(hold), "pre_nll_a": pre_a, "pre_nll_b": pre_b,
        "noise_band": noise_band, "post_nll": post,
        "delta_nll": post - pre_a, "forgot": (post - pre_a) > max(noise_band, 1e-6),
        "wall_sec": round(time.time() - t0, 1),
        "protocol": "E6-v2: task-origin forgetting (ncRNA vs m6A start)",
    }
    with open(os.path.join(out_dir, "result.json"), "w") as fh:
        json.dump(result, fh, indent=2)
    update(res["row"]["run_id"], "done", **{k: v for k, v in result.items()
                                             if k != "run_id"})
    print(json.dumps(result, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
