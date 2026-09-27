#!/usr/bin/env python3
"""C4 collapse timeline evidence: per-epoch test ACC during family-split
fine-tuning — proves WHEN the collapse happens (early epochs vs gradual).

Mirrors finetune_one.py protocol exactly (family split, same head, same LR
grid default 3e-4), only adds an eval hook after each epoch.
Cells: {micro, ERNIE, SpliceBERT, 10M, 30M} × {lora, full@default} × s17
= 10 runs (single seed is enough — collapse is deterministic per diag_a8;
3-seed confirmation already exists in main matrix).

Usage: python -m rnafteval.collapse_timeline --model RiNALMo-micro \
          --strategy full --seed 17 --device 0
"""
from __future__ import annotations

import argparse
import json
import os
import random
import time

import torch

ROOT = "/mnt/cunyuliu/rna-ft-eval"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--strategy", required=True, choices=["lora", "full"])
    ap.add_argument("--seed", type=int, default=17)
    ap.add_argument("--device", type=int, required=True)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--epochs", type=int, default=10)
    ap.add_argument("--batch-size", type=int, default=32)
    args = ap.parse_args()

    if not torch.cuda.is_available():
        print(json.dumps({"event": "CUDA_UNAVAILABLE_ABORT"}), flush=True)
        return 2
    torch.cuda.set_device(args.device)
    device = "cuda:%d" % args.device
    torch.manual_seed(args.seed)
    random.seed(args.seed)
    t0 = time.time()

    from .models import load_model
    from .strategies import apply_strategy, make_head
    from .finetune_one import encode_seqs, batches
    from .tasks.ncrna import load_ncrna
    from .tasks.dedup import dedup
    from .splits import random_split
    from .ledger import claim, update

    extra = "_tl"
    out_dir = os.path.join(ROOT, "artifacts", "collapse_tl",
                           "%s_%s_s%d" % (args.model, args.strategy, args.seed))
    os.makedirs(out_dir, exist_ok=True)
    res = claim(args.model, "collapse-timeline", args.strategy, args.seed,
                "family", device=args.device, out_dir=out_dir,
                note="C4 collapse timeline (per-epoch family test acc)",
                extra=extra)
    if res is None or res.get("claimed") is False:
        print("skip (ledger: %s)" % (res or {}).get("reason"), flush=True)
        return 0

    # family split (same as finetune_one)
    import pyarrow.parquet as pq
    fpath = os.path.join(ROOT, "data", "family_splits",
                         "noncoding-rna-family.parquet")
    t = pq.read_table(fpath).to_pydict()
    recs = [{"seq": s, "label": int(l)} for s, l in zip(t["seq"], t["label"])]
    parts = {"train": [r for r, sp in zip(recs, t["split"]) if sp == "train"],
             "test": [r for r, sp in zip(recs, t["split"]) if sp == "test"]}
    labels = sorted({r["label"] for r in recs})
    lab2id = {l: i for i, l in enumerate(labels)}
    for k in parts:
        for r in parts[k]:
            r["label_id"] = lab2id[r["label"]]

    spec, tok, backbone = load_model(args.model, device)
    with torch.no_grad():
        probe = encode_seqs(tok, [parts["train"][0]["seq"]], device)
        d_model = backbone(**probe).last_hidden_state.shape[-1]

    backbone, n_trainable = apply_strategy(backbone, args.strategy)
    head = make_head("per-seq", d_model, len(labels)).to(device)
    tp = [p for p in head.parameters() if p.requires_grad]
    if hasattr(backbone, "m"):
        tp += [p for p in backbone.m.parameters() if p.requires_grad]
    else:
        tp += [p for p in backbone.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(tp, lr=args.lr)
    lossf = torch.nn.CrossEntropyLoss()
    tr_backbone = args.strategy in ("lora", "full")

    def eval_test():
        backbone.eval()
        head.eval()
        correct = total = 0
        with torch.no_grad():
            for b in batches(parts["test"], args.batch_size * 2):
                enc = encode_seqs(tok, [r["seq"] for r in b], device)
                y = torch.tensor([r["label_id"] for r in b], device=device)
                h = backbone(**enc).last_hidden_state
                pad = enc["attention_mask"] == 0
                logits = head(h, pad)
                correct += (logits.argmax(-1) == y).sum().item()
                total += len(b)
        return correct / max(total, 1)

    timeline = [eval_test()]  # epoch -1 = before training
    print("epoch -1 acc %.4f" % timeline[0], flush=True)
    for ep in range(args.epochs):
        backbone.train(tr_backbone)
        head.train()
        tot = nb = 0
        for b in batches(parts["train"], args.batch_size):
            enc = encode_seqs(tok, [r["seq"] for r in b], device)
            y = torch.tensor([r["label_id"] for r in b], device=device)
            if tr_backbone:
                h = backbone(**enc).last_hidden_state
            else:
                with torch.no_grad():
                    h = backbone(**enc).last_hidden_state
            pad = enc["attention_mask"] == 0
            loss = lossf(head(h, pad), y)
            opt.zero_grad(); loss.backward()
            torch.nn.utils.clip_grad_norm_(tp, 1.0)
            opt.step()
            tot += loss.item(); nb += 1
        acc = eval_test()
        timeline.append(acc)
        print("epoch %d loss %.4f acc %.4f" % (ep, tot / max(nb, 1), acc),
              flush=True)

    result = {"run_id": res["row"]["run_id"], "model": args.model,
              "strategy": args.strategy, "seed": args.seed, "lr": args.lr,
              "epochs": args.epochs, "split": "family",
              "timeline_acc": timeline,
              "first_epoch_below_half": next(
                  (i for i, a in enumerate(timeline)
                   if i >= 1 and a < timeline[0] / 2), None),
              "wall_sec": round(time.time() - t0, 1),
              "protocol": "C4 collapse timeline: per-epoch family test acc"}
    with open(os.path.join(out_dir, "result.json"), "w") as fh:
        json.dump(result, fh, indent=2)
    update(res["row"]["run_id"], "done",
           **{k: v for k, v in result.items() if k != "run_id"})
    print(json.dumps(result), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
