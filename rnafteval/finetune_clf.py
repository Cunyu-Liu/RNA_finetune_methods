"""Per-seq 分类 runner（泛化版）：ncRNA 家族 / crispr-off-target 二分类。

复用 finetune_one 协议（CUDA 纪律/ledger/资源记录/zero-overlap 断言）。
与 finetune_one 的差异：
  - --task 分派数据源（noncoding-rna-family | crispr-off-target）
  - crispr 主指标 = PR-AUC（0.59% 极不平衡，PR-AUC 才有区分度）+ AUC 副指标
  - crispr 输入 46nt（sgrna+target 拼接）
"""
from __future__ import annotations

import argparse
import json
import os
import random
import time

import numpy as np
import torch

from . import ledger
from .splits import assert_no_overlap, random_split

ROOT = "/root/rna-ft-eval"


def encode_seqs(tok, seqs, device, max_len=128):
    enc = tok(seqs, padding=True, truncation=True, max_length=max_len,
              return_tensors="pt")
    return {k: v.to(device) for k, v in enc.items()}


def batches(rows, bs):
    for i in range(0, len(rows), bs):
        yield rows[i:i + bs]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--task", default="noncoding-rna-family",
                    choices=["noncoding-rna-family", "crispr-off-target"])
    ap.add_argument("--strategy", required=True,
                    choices=["frozen", "lora", "head-only", "full",
                             "lora-scaled", "dora", "ia3"])
    ap.add_argument("--seed", type=int, default=17)
    ap.add_argument("--split", required=True, choices=["random", "family"])
    ap.add_argument("--device", type=int, default=0)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--epochs", type=int, default=10)
    ap.add_argument("--batch-size", type=int, default=16)
    ap.add_argument("--rank", type=int, default=8)
    ap.add_argument("--max-len", type=int, default=128)
    ap.add_argument("--n-train", type=int, default=0)
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--random-init", action="store_true")
    args = ap.parse_args()

    device = torch.device("cuda:%d" % args.device)
    assert torch.cuda.is_available(), "CUDA unavailable - abort (no CPU fallback)"

    rid = ledger.run_id(args.model, args.task, args.strategy, args.seed,
                        args.split, extra="")
    out_dir = os.path.join(ROOT, "artifacts", rid)
    os.makedirs(out_dir, exist_ok=True)
    claim = ledger.claim(args.model, args.task, args.strategy, args.seed,
                         args.split, rid, out_dir, extra="")
    if not claim.get("claimed", False):
        print("skip (already %s)" % claim["row"].get("status", "unknown"))
        return 75

    t0 = time.time()
    torch.cuda.set_device(args.device)
    torch.cuda.reset_peak_memory_stats(args.device)

    # --- data ---
    if args.task == "crispr-off-target":
        from .tasks import crispr as cr_task
        if args.split == "family":
            import pyarrow.parquet as pq
            fam = os.path.join(ROOT, "data", "family_splits",
                               "crispr-off-target.parquet")
            assert os.path.exists(fam), "run make_family_split first"
            t = pq.read_table(fam).to_pydict()
            recs = [{"seq": s, "label": int(l), "cluster": c}
                    for s, l, c in zip(t["seq"], t["label"], t["cluster_id"])]
            parts = {
                "train": [r for r, sp in zip(recs, t["split"]) if sp == "train"],
                "val": [r for r, sp in zip(recs, t["split"]) if sp == "val"],
                "test": [r for r, sp in zip(recs, t["split"]) if sp == "test"],
            }
        else:
            sp = cr_task.load_official_split()
            parts = {"train": sp["train"], "val": sp["val"], "test": sp["test"]}
            # label field: float 0/1 -> int
            for k in parts:
                for r in parts[k]:
                    r["label"] = int(r["label"])
            # BEACON cross-split exact dups (133+271 pairs) — dedup rule:
            # keep the FIRST occurrence in side order train > val > test
            # (same protocol as ncrna dedup; assert_no_overlap then passes)
            seen = set()
            for k in ("train", "val", "test"):
                keep = []
                for r in parts[k]:
                    kk = r["seq"]
                    if kk in seen:
                        continue
                    seen.add(kk)
                    keep.append(r)
                parts[k] = keep
    else:
        from .tasks import ncrna
        if args.split == "family":
            import pyarrow.parquet as pq
            fpath = os.path.join(ROOT, "data", "family_splits",
                                 "noncoding-rna-family.parquet")
            t = pq.read_table(fpath).to_pydict()
            recs = [{"seq": s, "label": int(l), "cluster": c}
                    for s, l, c in zip(t["seq"], t["label"], t["cluster_id"])]
            parts = {
                "train": [r for r, sp in zip(recs, t["split"]) if sp == "train"],
                "val": [r for r, sp in zip(recs, t["split"]) if sp == "val"],
                "test": [r for r, sp in zip(recs, t["split"]) if sp == "test"],
            }
        else:
            recs = ncrna.load_ncrna(os.path.join(
                ROOT, "data", "beacon_raw", "noncoding-rna-family", "data"))
            from .tasks.dedup import dedup
            recs = dedup(recs)
            parts = random_split(recs, seed=17)

    if args.n_train > 0:
        rng = random.Random(17)
        parts["train"] = rng.sample(parts["train"],
                                    min(args.n_train, len(parts["train"])))
    if args.smoke:
        parts = {k: v[:60] for k, v in parts.items()}

    labels = sorted({r["label"] for r in parts["train"] +
                     parts["val"] + parts["test"]})
    lab2id = {l: i for i, l in enumerate(labels)}
    for k in parts:
        for r in parts[k]:
            r["label_id"] = lab2id[r["label"]]
    assert_no_overlap(parts["train"], parts["val"] + parts["test"], unit="seq")
    print("data: train %d val %d test %d classes %d" % (
        len(parts["train"]), len(parts["val"]), len(parts["test"]),
        len(labels)), flush=True)

    # --- model + strategy ---
    from .models import load_model
    from .strategies import apply_strategy, make_head
    spec, tok, backbone = load_model(args.model, device,
                                     random_init=args.random_init)
    with torch.no_grad():
        probe = encode_seqs(tok, [parts["train"][0]["seq"]], device,
                            args.max_len)
        d = backbone(**probe).last_hidden_state.shape[-1]
    backbone, n_trainable = apply_strategy(backbone, args.strategy,
                                           lora_rank=args.rank)
    head = make_head("per-seq", d, len(labels)).to(device)
    params = [p for p in head.parameters() if p.requires_grad] + \
        [p for p in backbone.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(params, lr=args.lr)
    lossf = torch.nn.CrossEntropyLoss()

    def run_batch(b):
        enc = encode_seqs(tok, [r["seq"] for r in b], device, args.max_len)
        y = torch.tensor([r["label_id"] for r in b], device=device)
        return enc, y

    for ep in range(args.epochs):
        backbone.train(args.strategy in ("lora", "full", "dora", "ia3"))
        head.train()
        tot, nb = 0.0, 0
        for b in batches(parts["train"], args.batch_size):
            enc, y = run_batch(b)
            import contextlib
            no_grad = args.strategy in ("frozen", "head-only")
            with contextlib.nullcontext() if not no_grad \
                    else torch.no_grad():
                h = backbone(**enc).last_hidden_state
            pad = enc["attention_mask"] == 0
            logits = head(h, pad)
            loss = lossf(logits, y)
            opt.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(params, 1.0)
            opt.step()
            tot += loss.item()
            nb += 1
        print("epoch %d loss %.4f" % (ep, tot / max(nb, 1)), flush=True)
        ledger.update(rid, "running", note="epoch %d heartbeat" % ep)

    # --- eval ---
    backbone.eval()
    head.eval()
    ys, ps = [], []
    with torch.no_grad():
        for b in batches(parts["test"], args.batch_size * 2):
            enc, y = run_batch(b)
            h = backbone(**enc).last_hidden_state
            pad = enc["attention_mask"] == 0
            logits = head(h, pad)
            ys.append(y.cpu().numpy())
            ps.append(torch.softmax(logits, -1).cpu().numpy())
    y_all = np.concatenate(ys)
    p_all = np.concatenate(ps)

    if args.task == "crispr-off-target":
        from sklearn.metrics import average_precision_score, roc_auc_score
        # binary: positive-class probability = column 1
        pos_p = p_all[:, 1]
        prauc = float(average_precision_score(y_all, pos_p))
        auc = float(roc_auc_score(y_all, pos_p))
        metric, value, metric2, value2 = "PRAUC", prauc, "AUC", auc
        acc = float((y_all == (pos_p > 0.5).astype(int)).mean())
    else:
        pred = p_all.argmax(-1)
        acc = float((pred == y_all).mean())
        metric, value, metric2, value2 = "ACC", acc, "None", 0.0

    torch.save(head.state_dict(), os.path.join(out_dir, "head.pt"))
    wall = time.time() - t0
    peak = torch.cuda.max_memory_allocated(args.device) / (1 << 20)
    result = {
        "run_id": rid, "model": args.model, "task": args.task,
        "strategy": args.strategy, "seed": args.seed, "split": args.split,
        "metric": metric, "value": value,
        "metric2": metric2, "value2": value2,
        "n_train": len(parts["train"]), "n_test": len(parts["test"]),
        "n_classes": len(labels), "wall_sec": round(wall, 1),
        "peak_mem_mb": round(peak, 1), "backbone_trainable": n_trainable,
        "lr": args.lr, "epochs": args.epochs, "smoke": args.smoke,
    }
    with open(os.path.join(out_dir, "result.json"), "w") as fh:
        json.dump(result, fh, indent=2)
    ledger.update(rid, "done", value=value, metric=metric, extra_fields=result)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
