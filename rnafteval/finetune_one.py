"""Finetune one (model, task, strategy, seed, split) run — GPU-only.

Usage:
  python -m rnafteval.finetune_one --model RiNALMo-micro \
      --task noncoding-rna-family --strategy frozen --seed 17 --split random \
      --device 6 --lr 3e-4 --epochs 10

Discipline:
  - CUDA check first: no CUDA => abort with evidence (no CPU fallback)
  - zero-overlap assertion before training
  - resource recorder (wall-clock / peak memory / ckpt size)
  - ledger claim/update around the run
"""
from __future__ import annotations

import argparse
import json
import os
import time

import torch

from . import ledger
from .splits import assert_no_overlap, family_split, random_split
from .strategies import apply_strategy, make_head
from .tasks import ncrna

ROOT = "/mnt/cunyuliu/rna-ft-eval"
BEACON_RAW = os.path.join(ROOT, "data", "beacon_raw")


def encode_seqs(tok, seqs: list[str], device, max_len: int = 512):
    enc = tok(seqs, padding=True, truncation=True, max_length=max_len,
              return_tensors="pt")
    return {k: v.to(device) for k, v in enc.items()}


def batches(rows, bs):
    for i in range(0, len(rows), bs):
        yield rows[i:i + bs]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--task", required=True)
    ap.add_argument("--strategy", required=True,
                    choices=["frozen", "lora", "head-only", "full"])
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--split", required=True, choices=["random", "family"])
    ap.add_argument("--device", type=int, required=True)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--epochs", type=int, default=10)
    ap.add_argument("--batch-size", type=int, default=32)
    ap.add_argument("--max-len", type=int, default=512)
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()

    # --- GPU discipline: no CUDA => abort with evidence ---
    if not torch.cuda.is_available():
        print(json.dumps({
            "event": "CUDA_UNAVAILABLE_ABORT", "device_arg": args.device,
            "torch_version": torch.__version__,
        }), flush=True)
        return 2
    torch.cuda.set_device(args.device)
    device = "cuda:%d" % args.device

    torch.manual_seed(args.seed)

    # run_id 编码 LR 维度（A8 网格协议）：非默认 3e-4 的 tuning runs 用
    # _lr 后缀区分，避免 ledger claim 误 skip 不同 LR 变体
    lr_tag = "" if abs(args.lr - 3e-4) < 1e-12 else "_lr%g" % args.lr
    extra = ("_smoke" if args.smoke else "") + lr_tag
    rid = ledger.run_id(args.model, args.task, args.strategy, args.seed,
                        args.split, extra)
    out_dir = os.path.join(ROOT, "artifacts", rid)
    os.makedirs(out_dir, exist_ok=True)
    claim = ledger.claim(args.model, args.task, args.strategy, args.seed,
                         args.split, device=args.device, out_dir=out_dir,
                         extra=extra)
    if not claim["claimed"]:
        print("skip (already %s): %s" % (claim["row"]["status"], rid))
        return 0

    t0 = time.time()
    torch.cuda.reset_peak_memory_stats(args.device)

    # --- data ---
    if args.split == "family":
        import pyarrow.parquet as pq
        fpath = os.path.join(ROOT, "data", "family_splits",
                             "noncoding-rna-family.parquet")
        t = pq.read_table(fpath)
        d = t.to_pydict()
        recs = [{"seq": s, "label": int(l), "cluster": c}
                for s, l, c in zip(d["seq"], d["label"], d["cluster_id"])]
        parts = {
            "train": [r for r, sp in zip(recs, d["split"]) if sp == "train"],
            "val": [r for r, sp in zip(recs, d["split"]) if sp == "val"],
            "test": [r for r, sp in zip(recs, d["split"]) if sp == "test"],
        }
    else:
        recs = ncrna.load_ncrna(
            os.path.join(BEACON_RAW, "noncoding-rna-family", "data"))
        from .tasks.dedup import dedup
        n_before = len(recs)
        recs = dedup(recs)
        if len(recs) != n_before:
            print("dedup: %d -> %d (BEACON cross-split exact dups removed)"
                  % (n_before, len(recs)), flush=True)
        parts = random_split(recs, seed=17)
    if args.smoke:
        recs = recs[:600]
        parts = {k: v[:60] for k, v in parts.items()}
    labels = sorted({r["label"] for r in recs})
    lab2id = {l: i for i, l in enumerate(labels)}
    for r in recs:
        r["label_id"] = lab2id[r["label"]]
    for k in parts:
        for r in parts[k]:
            r["label_id"] = lab2id[r["label"]]

    # zero-overlap assertion (B1) — both arms
    assert_no_overlap(parts["train"], parts["val"] + parts["test"], unit="seq")
    print("data: train %d val %d test %d classes %d" % (
        len(parts["train"]), len(parts["val"]), len(parts["test"]),
        len(labels)), flush=True)

    # --- model + strategy ---
    from .models import load_model
    spec, tok, backbone = load_model(args.model, device)
    d_model = spec.d_model
    with torch.no_grad():
        probe = encode_seqs(tok, [recs[0]["seq"]], device, args.max_len)
        h_dim = backbone(**probe).last_hidden_state.shape[-1]
    if h_dim != d_model:
        print("d_model corrected: spec %d -> actual %d" % (d_model, h_dim),
              flush=True)
        d_model = h_dim
    backbone, n_trainable = apply_strategy(backbone, args.strategy)

    head = make_head("per-seq", d_model, len(labels)).to(device)
    head_params = sum(p.numel() for p in head.parameters())
    train_params = [p for p in head.parameters() if p.requires_grad] + \
        [p for p in backbone.parameters() if p.requires_grad]
    if hasattr(backbone, "m"):
        train_params = [p for p in head.parameters() if p.requires_grad] + \
            [p for p in backbone.m.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(train_params, lr=args.lr)
    lossf = torch.nn.CrossEntropyLoss()

    # --- train ---
    for ep in range(args.epochs):
        is_training_backbone = args.strategy in ("lora", "full")
        backbone.train(is_training_backbone)
        head.train()
        tot = 0.0
        nb = 0
        for b in batches(parts["train"], args.batch_size):
            enc = encode_seqs(tok, [r["seq"] for r in b], device, args.max_len)
            y = torch.tensor([r["label_id"] for r in b], device=device)
            if is_training_backbone:
                h = backbone(**enc).last_hidden_state
            else:
                with torch.no_grad():
                    h = backbone(**enc).last_hidden_state
            pad = enc["attention_mask"] == 0
            logits = head(h, pad)
            loss = lossf(logits, y)
            opt.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(train_params, 1.0)
            opt.step()
            tot += loss.item()
            nb += 1
        print("epoch %d loss %.4f" % (ep, tot / max(nb, 1)), flush=True)

    # --- eval ---
    backbone.eval()
    head.eval()
    correct = 0
    total = 0
    with torch.no_grad():
        for b in batches(parts["test"], args.batch_size * 2):
            enc = encode_seqs(tok, [r["seq"] for r in b], device, args.max_len)
            y = torch.tensor([r["label_id"] for r in b], device=device)
            h = backbone(**enc).last_hidden_state
            pad = enc["attention_mask"] == 0
            logits = head(h, pad)
            correct += (logits.argmax(-1) == y).sum().item()
            total += len(b)
    acc = correct / max(total, 1)

    wall = time.time() - t0
    peak_mem = torch.cuda.max_memory_allocated(args.device) / (1 << 20)
    ck_path = os.path.join(out_dir, "head.pt")
    torch.save(head.state_dict(), ck_path)
    ckpt_size = os.path.getsize(ck_path)

    result = {
        "run_id": rid, "model": args.model, "task": args.task,
        "strategy": args.strategy, "seed": args.seed, "split": args.split,
        "metric": "ACC", "value": acc, "n_train": len(parts["train"]),
        "n_test": len(parts["test"]), "n_classes": len(labels),
        "wall_sec": round(wall, 1), "peak_mem_mb": round(peak_mem, 1),
        "ckpt_bytes": ckpt_size, "head_params": head_params,
        "backbone_trainable": n_trainable, "lr": args.lr,
        "epochs": args.epochs, "smoke": args.smoke,
    }
    with open(os.path.join(out_dir, "result.json"), "w") as fh:
        json.dump(result, fh, indent=2)
    ledger.update(rid, "done", **{k: v for k, v in result.items()
                                  if k != "run_id"})
    print(json.dumps(result, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
