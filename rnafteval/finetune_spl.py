"""Per-base 多分类 runner：spliceai 3 分类（acceptor/donor/background）。

8 任务扩展新任务（碱基级分类第 2 数据集，与 m6A 互证）。
复用 finetune_base 协议（BCE 版）但损失换 CrossEntropy（3 类），
评估换 macro-F1 + 逐类召回（稀疏正点 ~3%，accuracy 无意义）。
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
from .tasks import spliceai as spl_task

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
    ap.add_argument("--task", default="spliceai")
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

    # seed everything (was missing: 3 seeds gave identical results)
    import random as _r, numpy as _np
    _r.seed(args.seed)
    _np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    torch.cuda.manual_seed_all(args.seed)
    t0 = time.time()
    torch.cuda.set_device(args.device)
    torch.cuda.reset_peak_memory_stats(args.device)

    # --- data ---
    if args.split == "family":
        import pyarrow.parquet as pq
        fam = os.path.join(ROOT, "data", "family_splits", "spliceai.parquet")
        assert os.path.exists(fam), "run make_family_split first"
        t = pq.read_table(fam).to_pydict()
        by_side = {}
        for seq, lab, sd, cid in zip(t["seq"], t["labels"], t["split"],
                                     t["cluster_id"]):
            if sd in ("train", "test"):
                by_side.setdefault(sd, []).append(
                    {"seq": seq, "labels": [int(x) for x in lab],
                     "cluster": cid})
        train, test = by_side["train"], by_side["test"]
    else:
        sp = spl_task.load_official_split()
        train, test = sp["train"], sp["test"]

    if args.n_train > 0:
        rng = random.Random(args.seed)
        train = rng.sample(train, min(args.n_train, len(train)))
    if args.smoke:
        train, test = train[:320], test[:320]

    print("data: train %d test %d" % (len(train), len(test)), flush=True)

    from .models import load_model
    from .strategies import apply_strategy, TokenHead
    spec, tok, backbone = load_model(args.model, device)
    with torch.no_grad():
        probe = encode_seqs(tok, [train[0]["seq"]], device, 128)
        d = backbone(**probe).last_hidden_state.shape[-1]
    backbone, n_trainable = apply_strategy(backbone, args.strategy,
                                           lora_rank=args.rank)
    # token-level CE head: 3 logits per token
    head = TokenHead(d, 3, hidden=32).to(device)
    train_params = [p for p in head.parameters() if p.requires_grad] + \
        [p for p in backbone.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(train_params, lr=args.lr)
    lossf = torch.nn.CrossEntropyLoss(reduction="none")

    def make_batch(b):
        enc = encode_seqs(tok, [r["seq"] for r in b], device, 128)
        L = enc["input_ids"].shape[1]
        y = torch.zeros(len(b), L, dtype=torch.long, device=device)
        for i, r in enumerate(b):
            labs = r["labels"][:L]
            y[i, :len(labs)] = torch.tensor(labs, dtype=torch.long,
                                            device=device)
        return enc, y

    for ep in range(args.epochs):
        _sh = random.Random(args.seed * 1000 + ep)
        _rows = list(train)
        _sh.shuffle(_rows)
        backbone.train(args.strategy in ("lora", "full", "dora", "ia3"))
        head.train()
        tot, nb = 0.0, 0
        for b in batches(_rows, args.batch_size):
            enc, y = make_batch(b)
            import contextlib
            no_grad = args.strategy in ("frozen", "head-only")
            with contextlib.nullcontext() if not no_grad \
                    else torch.no_grad():
                h = backbone(**enc).last_hidden_state
            pad = enc["attention_mask"] == 0
            logits = head(h, pad)  # [B, L, 3]
            mask = enc["attention_mask"].float()
            # CE with class weights? no — keep protocol minimal, report macro-F1
            loss_map = lossf(logits.reshape(-1, 3), y.reshape(-1))
            loss = (loss_map.reshape(len(b), -1) * mask).sum() / \
                mask.sum().clamp(min=1)
            opt.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(train_params, 1.0)
            opt.step()
            tot += loss.item()
            nb += 1
        print("epoch %d loss %.4f" % (ep, tot / max(nb, 1)), flush=True)
        ledger.update(rid, "running", note="epoch %d heartbeat" % ep)

    # --- eval: macro-F1 over non-pad positions (3 classes) ---
    backbone.eval()
    head.eval()
    ys, ps = [], []
    with torch.no_grad():
        for b in batches(test, args.batch_size * 2):
            enc, y = make_batch(b)
            h = backbone(**enc).last_hidden_state
            pad = enc["attention_mask"] == 0
            logits = head(h, pad)
            m = enc["attention_mask"].bool()
            ys.append(y[m].cpu().numpy())
            ps.append(logits[m].argmax(-1).cpu().numpy())
    y_all = np.concatenate(ys)
    p_all = np.concatenate(ps)
    from sklearn.metrics import f1_score
    macro_f1 = float(f1_score(y_all, p_all, average="macro"))
    per_class = f1_score(y_all, p_all, average=None, labels=[0, 1, 2])
    f1_acc = float(f1_score(y_all, p_all, average="micro"))

    wall = time.time() - t0
    peak = torch.cuda.max_memory_allocated(args.device) / (1 << 20)
    result = {
        "run_id": rid, "model": args.model, "task": args.task,
        "strategy": args.strategy, "seed": args.seed, "split": args.split,
        "metric": "MACRO_F1", "value": macro_f1,
        "metric2": "MICRO_F1", "value2": f1_acc,
        "f1_bg": float(per_class[0]), "f1_acc_site": float(per_class[1]),
        "f1_donor": float(per_class[2]),
        "n_train": len(train), "n_test": len(test), "n_classes": 3,
        "wall_sec": round(wall, 1), "peak_mem_mb": round(peak, 1),
        "backbone_trainable": n_trainable, "lr": args.lr,
        "epochs": args.epochs, "smoke": args.smoke,
    }
    with open(os.path.join(out_dir, "result.json"), "w") as fh:
        json.dump(result, fh, indent=2)
    ledger.update(rid, "done", value=macro_f1, metric="MACRO_F1",
                  extra_fields=result)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
