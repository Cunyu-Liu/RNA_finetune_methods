#!/usr/bin/env python3
"""E6-v2: multi-task-origin forgetting — ncRNA vs m6A starting task.

Same measurement as e6_forget (pre/post S0 held-out NLL + reorder noise band),
but the finetune task is selectable. Both ncRNA and BEACON modification are
sequence-level tasks; modification predicts 12 modification-type labels.
The comparison therefore does not claim a per-base/per-seq granularity effect.

Usage:
  python -m rnafteval.e6_forget_task --model RNA-Sc-10M --strategy lora \
      --task modification --seed 17 --device 0
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import time

import torch

from . import valplateau as vp
from .e6_forget import (
    NCRNA_SPLIT_SEED, TRAINING_SEED_PROTOCOL, epoch_rows,
    nll_eval as fixed_mask_nll_eval, seed_training)

ROOT = "/root/rna-ft-eval"
S0 = ("/root/tokenizer-benchmark/data/derived/split/"
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


def nll_eval(backbone, tok, seqs, device, bs=8, shuffle_seed=None,
             eval_seed=None, mask_rate=0.15):
    if hasattr(tok, "mask_token_id"):
        return fixed_mask_nll_eval(
            backbone, tok, seqs, device, bs=bs, shuffle_seed=shuffle_seed,
            eval_seed=eval_seed, mask_rate=mask_rate)

    order = list(range(len(seqs)))
    if shuffle_seed is not None:
        random.Random(shuffle_seed).shuffle(order)
    tot, cnt = 0.0, 0
    backbone.eval()
    with torch.no_grad():
        for i in range(0, len(order), bs):
            chunk = [seqs[j] for j in order[i:i + bs]]
            enc = encode(tok, chunk, device)
            ids = enc["input_ids"]
            mask = enc["attention_mask"]
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
    ap.add_argument("--batch-size", type=int, default=32)
    ap.add_argument("--mask-rate", type=float, default=0.15)
    ap.add_argument("--out-suffix", default="")
    ap.add_argument("--smoke", action="store_true")
    vp.add_convergence_args(ap)
    args = ap.parse_args()
    if args.task == "modification" and not (
            args.converge and "_seqmlfix" in args.out_suffix):
        raise ValueError(
            "legacy per-base modification is disabled; use --converge and "
            "--out-suffix _seqmlfix for sequence-level 12-label training")
    if args.convergence_mode == "bestval" and not args.converge:
        raise ValueError("bestval requires --converge")
    if not torch.cuda.is_available():
        raise RuntimeError("E6 task training requires real CUDA")
    device = int(args.device)
    torch.cuda.set_device(device)
    t0 = time.time()
    seed_training(args.seed)
    torch.cuda.set_device(device)
    torch.cuda.reset_peak_memory_stats(device)

    if args.lr is None:
        args.lr = 3e-4 if args.strategy == "lora" else (
            1e-5 if args.model in OFFICIAL else 3e-5)
    if args.epochs is None:
        args.epochs = 10 if args.task == "noncoding-rna-family" else 3

    from .models import load_model
    from .strategies import apply_strategy, make_head
    from .ledger import ARTIFACT_ROOT, claim, update
    from .finetune_one import encode_seqs as enc_cls, batches
    from .splits import prepare_convergence_splits, random_split
    from .tasks.ncrna import load_ncrna
    from .tasks import modification as mod_task
    from .tasks.dedup import dedup

    task_tag = "ncrna" if args.task == "noncoding-rna-family" else "m6a"
    protocol_tag = vp.protocol_tag(args)
    smoke_tag = "_smoke" if args.smoke else ""
    out_dir = os.path.join(
        ARTIFACT_ROOT, "e6",
        "%s_%s_task-%s_s%d%s%s" % (args.model, args.strategy, task_tag,
                                   args.seed, args.out_suffix + smoke_tag,
                                   protocol_tag))
    os.makedirs(out_dir, exist_ok=True)
    extra = "_task%s_s0%s%s%s" % (task_tag, args.out_suffix, smoke_tag,
                                  protocol_tag)
    res = claim(args.model, "e6-forgetting", args.strategy, args.seed,
                "s0-heldout", device=device, out_dir=out_dir,
                note="E6-v2 task-origin forgetting", extra=extra)
    # The task/suffix extra keeps the run_id distinct from E6-v1 rows.
    if res is None or res.get("claimed") is False:
        print("skip (ledger: %s)" % (res or {}).get("reason"), flush=True)
        return 75

    hold = s0_heldout_seqs(args.n_holdout)
    print("S0 holdout: %d seqs" % len(hold), flush=True)

    # ---- load task data ----
    if args.task == "noncoding-rna-family":
        recs = load_ncrna(os.path.join(
            ROOT, "data", "beacon_raw", "noncoding-rna-family", "data"))
        recs = dedup(recs)
        parts = random_split(recs, seed=NCRNA_SPLIT_SEED)
        labels = sorted({r["label"] for r in recs})
        lab2id = {l: i for i, l in enumerate(labels)}
        for k in parts:
            for r in parts[k]:
                r["label_id"] = lab2id[r["label"]]
    else:
        sp = mod_task.load_official_split()
        parts = {"train": sp["train"], "val": sp["validation"],
                 "test": sp["test"]}

    data_evidence = None
    if args.converge:
        train, val, test, data_evidence = prepare_convergence_splits(
            parts["train"], parts["val"], parts["test"],
            n_train=args.n_train_cap or 0, sample_seed=args.seed,
            validation_source="official_validation",
            evidence_path=os.path.join(out_dir, "split_evidence.json"),
            protocol=protocol_tag.lstrip("_"))
    else:
        train = parts["train"][:args.n_train_cap] if args.n_train_cap \
            else parts["train"]
        val = parts["val"]
    is_multilabel = args.task == "modification"
    if is_multilabel and any(len(r["labels"]) != 12 for r in train + val):
        raise ValueError("BEACON modification requires 12 sequence-level labels")
    if args.smoke:
        train, val, hold = train[:24], val[:24], hold[:24]

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

    pre_a = nll_eval(backbone, tok, hold, device, shuffle_seed=201,
                     eval_seed=201, mask_rate=args.mask_rate)
    pre_b = nll_eval(backbone, tok, hold, device, shuffle_seed=707,
                     eval_seed=707, mask_rate=args.mask_rate)
    noise_band = abs(pre_b - pre_a)
    print("pre NLL: %.4f / %.4f (noise %.2e)" % (pre_a, pre_b, noise_band),
          flush=True)

    # ---- finetune ----
    backbone, n_trainable = apply_strategy(backbone, args.strategy)
    tr_backbone = args.strategy in ("lora", "full", "dora", "ia3")
    enc_core = _official_encoder(backbone) if is_official else None
    fwd = enc_core if is_official else backbone

    n_outputs = 12 if is_multilabel else len(labels)
    head = make_head("per-seq", d_model, n_outputs).to(device)
    tp = [p for p in head.parameters() if p.requires_grad]
    if hasattr(backbone, "m"):
        tp += [p for p in backbone.m.parameters() if p.requires_grad]
    else:
        tp += [p for p in backbone.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(tp, lr=args.lr)
    lossf = torch.nn.BCEWithLogitsLoss() if is_multilabel \
        else torch.nn.CrossEntropyLoss()

    def make_batch(rows):
        enc = enc_cls(tok, [r["seq"] for r in rows], device, 128)
        target = "labels" if is_multilabel else "label_id"
        y = torch.tensor([r[target] for r in rows], device=device,
                         dtype=torch.float32 if is_multilabel else torch.long)
        return enc, y

    def batch_loss(rows):
        enc, y = make_batch(rows)
        if tr_backbone:
            h = fwd(**enc).last_hidden_state
        else:
            with torch.no_grad():
                h = fwd(**enc).last_hidden_state
        pad = enc["attention_mask"] == 0
        return lossf(head(h, pad), y)

    def save_best(epoch, val_loss):
        vp.save_best_checkpoint(
            os.path.join(out_dir, "best.ckpt"), backbone, head,
            epoch=epoch, best_epoch=epoch, best_val=val_loss)

    tracker = vp.make_tracker(out_dir, args, res["row"]["run_id"], save_best) \
        if args.converge else None
    runtime = vp.runtime_evidence(tok, "cuda:%d" % device) \
        if args.converge else None
    for ep in vp.training_epochs(args):
        backbone.train(tr_backbone)
        head.train()
        tot, nb = 0.0, 0
        rows = epoch_rows(train, args.seed, ep)
        for b in batches(rows, args.batch_size):
            loss = batch_loss(b)
            opt.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(tp, 1.0)
            opt.step()
            tot += loss.item()
            nb += 1
        epoch_loss = tot / max(nb, 1)
        print("epoch %d loss %.4f" % (ep, epoch_loss), flush=True)
        if args.converge:
            backbone.eval()
            head.eval()
            val_tot, val_nb = 0.0, 0
            with torch.no_grad():
                for b in batches(val, args.batch_size * 2):
                    val_loss = batch_loss(b)
                    val_tot += val_loss.item()
                    val_nb += 1
            val_epoch_loss = val_tot / max(val_nb, 1)
            print("epoch %d val_loss %.6f" % (ep, val_epoch_loss), flush=True)
            if tracker.record(ep, epoch_loss, val_epoch_loss):
                print("STOP %s epoch=%d" % (tracker.stop_reason, ep), flush=True)
                update(res["row"]["run_id"], "running", note=tracker.stop_reason)
                break
        update(res["row"]["run_id"], "running", note="epoch %d heartbeat" % ep)

    if args.converge and args.convergence_mode == "bestval":
        vp.restore_best_checkpoint(tracker, backbone, head, "cuda:%d" % device)
    backbone.eval()
    head.eval()

    if is_official and hasattr(backbone, "merge_and_unload") and \
            args.strategy in ("lora", "dora", "ia3", "prefix"):
        merged = backbone.merge_and_unload()
        merged.eval()
        backbone = merged
        print("peft merged back for post-NLL", flush=True)

    post = nll_eval(backbone, tok, hold, device, shuffle_seed=201,
                    eval_seed=201, mask_rate=args.mask_rate)

    if is_official:
        protocol = (
            "E6-v2-fixed-mask-mlm: task-origin forgetting; pre/post S0 heldout "
            "masked-position NLL (mask_rate=%g; pre_a/post eval seed 201, "
            "pre_b eval seed 707); noise_band is an independent mask/order "
            "reevaluation difference" % args.mask_rate)
    else:
        protocol = "E6-v2: task-origin forgetting (ncRNA vs m6A start)"
    result = {
        "run_id": res["row"]["run_id"], "model": args.model,
        "task": args.task, "strategy": args.strategy, "seed": args.seed,
        "split": "s0-heldout", "lr": args.lr, "epochs": args.epochs,
        "batch_size": args.batch_size,
        "training_seed_protocol": TRAINING_SEED_PROTOCOL,
        "train_split": ("official-fixed" if args.task == "modification"
                        else "random-fixed-seed-17"),
        "peak_mem_mb": round(
            torch.cuda.max_memory_allocated(device) / (1 << 20), 1),
        "mask_rate": args.mask_rate,
        "n_holdout": len(hold), "pre_nll_a": pre_a, "pre_nll_b": pre_b,
        "noise_band": noise_band, "post_nll": post,
        "delta_nll": post - pre_a, "forgot": (post - pre_a) > max(noise_band, 1e-6),
        "wall_sec": round(time.time() - t0, 1),
        "forgetting_protocol": protocol,
        "task_label_semantics": "BEACON sequence-level 12-label" \
            if is_multilabel else "BEACON sequence-level ncRNA family",
        "n_train": len(train), "n_val": len(val),
        "smoke": args.smoke,
        "acceptance_eligible": bool(args.converge and not args.smoke),
    }
    if args.converge:
        result.update(tracker.result_fields())
        result.update(forgetting_protocol=protocol,
                      runtime=runtime, data_evidence=data_evidence)
    else:
        result["protocol"] = protocol
    for key in ("pre_nll_a", "pre_nll_b", "noise_band", "post_nll", "delta_nll"):
        if not math.isfinite(result[key]):
            raise FloatingPointError(
                "non-finite E6-v2 metric: %s=%r" % (key, result[key]))
    result_path = os.path.join(out_dir, "result.json")
    tmp_path = result_path + ".tmp"
    with open(tmp_path, "w") as fh:
        json.dump(result, fh, indent=2, allow_nan=False)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp_path, result_path)
    ledger_fields = vp.result_ledger_fields(result) if args.converge else \
        {k: v for k, v in result.items() if k != "run_id"}
    update(res["row"]["run_id"], "done", **ledger_fields)
    print(json.dumps(result, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
