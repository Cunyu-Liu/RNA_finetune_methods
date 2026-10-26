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

from . import ledger, valplateau as vp
from .base_alignment import align_base_labels
from .splits import (
    assert_cluster_no_overlap, assert_no_overlap, split_train_validation)
from .tasks import spliceai as spl_task

ROOT = "/root/rna-ft-eval"


def encode_seqs(tok, seqs, device, max_len=128):
    enc = tok(seqs, padding=True, truncation=True, max_length=max_len,
              return_tensors="pt")
    return {k: v.to(device) for k, v in enc.items()}


def batches(rows, bs):
    for i in range(0, len(rows), bs):
        yield rows[i:i + bs]


def _run_extra(args):
    lr_tag = "" if abs(args.lr - 3e-4) < 1e-12 else "_lr%g" % args.lr
    rank_tag = "" if args.rank == 8 else "_r%d" % args.rank
    n_tag = "" if args.n_train == 0 else "_e3%d" % args.n_train
    epoch_tag = "" if getattr(args, "converge", False) or args.epochs == 10 \
        else "_ep%d" % args.epochs
    protocol_tag = "_valplateau_v2" if getattr(args, "converge", False) else ""
    return ("_b20fix" + ("_smoke" if args.smoke else "") + n_tag +
            lr_tag + rank_tag + epoch_tag + protocol_tag)


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
    vp.add_convergence_args(ap)
    args = ap.parse_args()

    device = torch.device("cuda:%d" % args.device)
    assert torch.cuda.is_available(), "CUDA unavailable - abort (no CPU fallback)"

    extra = _run_extra(args)
    rid = ledger.run_id(args.model, args.task, args.strategy, args.seed,
                        args.split, extra=extra)
    out_dir = os.path.join(ROOT, "artifacts", rid)
    os.makedirs(out_dir, exist_ok=True)
    claim = ledger.claim(args.model, args.task, args.strategy, args.seed,
                         args.split, device=args.device, out_dir=out_dir,
                         extra=extra)
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
        from .tasks.dedup import dedup
        # Official rows contain exact sequence duplicates across train,
        # validation and test. Preserve the earlier side and never reuse
        # test for validation-loss convergence or model selection.
        train = dedup(sp["train"])
        official_val = dedup(sp["validation"])
        test = dedup(sp["test"])
        seen_train = {r["seq"] for r in train}
        official_val = [r for r in official_val if r["seq"] not in seen_train]
        seen_train.update(r["seq"] for r in official_val)
        test = [r for r in test if r["seq"] not in seen_train]
        if args.converge:
            assert_no_overlap(train, official_val + test, unit="seq")
            assert_no_overlap(official_val, test, unit="seq")

    val = None
    if args.converge:
        train, val = split_train_validation(train, seed=17)
    if args.n_train > 0:
        rng = random.Random(args.seed)
        train = rng.sample(train, min(args.n_train, len(train)))
    if args.smoke:
        train, test = train[:320], test[:320]
        if val is not None:
            val = val[:320]

    if args.converge:
        assert_no_overlap(train, val + test, unit="seq")
        assert_no_overlap(val, test, unit="seq")
        if args.split == "family":
            assert_cluster_no_overlap(train, val + test)
            assert_cluster_no_overlap(val, test)
        print("data: train %d val %d test %d" % (
            len(train), len(val), len(test)), flush=True)
    else:
        print("data: train %d test %d" % (len(train), len(test)), flush=True)

    from .models import load_model
    from .strategies import apply_strategy, TokenHead
    spec, tok, backbone = load_model(args.model, device)
    with torch.no_grad():
        probe = encode_seqs(tok, [train[0]["seq"]], device, args.max_len)
        d = backbone(**probe).last_hidden_state.shape[-1]
    backbone, n_trainable = apply_strategy(backbone, args.strategy,
                                           lora_rank=args.rank)
    # token-level CE head: 3 logits per token
    head = TokenHead(d, 3, hidden=32).to(device)
    train_params = [p for p in head.parameters() if p.requires_grad] + \
        [p for p in backbone.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(train_params, lr=args.lr)
    lossf = torch.nn.CrossEntropyLoss(reduction="none")
    tracker = vp.PlateauTracker(
        out_dir, patience=args.patience, min_delta=args.min_delta,
        run_id=rid) if args.converge else None
    runtime = vp.runtime_evidence(tok, device) if args.converge else None

    def make_batch(b):
        enc = encode_seqs(tok, [r["seq"] for r in b], device, args.max_len)
        y, m = align_base_labels(tok, enc, b, args.max_len, dtype=torch.long)
        return enc, y, m

    for ep in vp.training_epochs(args):
        _sh = random.Random(args.seed * 1000 + ep)
        _rows = list(train)
        _sh.shuffle(_rows)
        backbone.train(args.strategy in ("lora", "full", "dora", "ia3"))
        head.train()
        tot, nb = 0.0, 0
        for b in batches(_rows, args.batch_size):
            enc, y, m = make_batch(b)
            import contextlib
            no_grad = args.strategy in ("frozen", "head-only")
            with contextlib.nullcontext() if not no_grad \
                    else torch.no_grad():
                h = backbone(**enc).last_hidden_state
            pad = enc["attention_mask"] == 0
            logits = head(h, pad)  # [B, L, 3]
            mask = m.float()
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

        _el = tot / max(nb, 1)
        if args.converge:
            backbone.eval()
            head.eval()
            val_tot, val_nb = 0.0, 0
            with torch.no_grad():
                for b in batches(val, args.batch_size * 2):
                    enc, y, m = make_batch(b)
                    h = backbone(**enc).last_hidden_state
                    pad = enc["attention_mask"] == 0
                    logits = head(h, pad)
                    mask = m.float()
                    loss_map = lossf(logits.reshape(-1, 3), y.reshape(-1))
                    val_loss = (loss_map.reshape(len(b), -1) * mask).sum() / \
                        mask.sum().clamp(min=1)
                    val_tot += val_loss.item()
                    val_nb += 1
            _vl = val_tot / max(val_nb, 1)
            print("epoch %d val_loss %.6f" % (ep, _vl), flush=True)
            if tracker.record(ep, _el, _vl):
                print("STOP %s epoch=%d epochs_trained=%d" % (
                    tracker.stop_reason, ep, ep + 1), flush=True)
                ledger.update(rid, "running", note=tracker.stop_reason)
                break
        else:
            # Legacy fixed-epoch evidence remains train-only v1.
            try:
                import json as _json
                _pl = os.path.join(out_dir, "plateau.json")
                _cur = {}
                if os.path.exists(_pl):
                    _cur = _json.load(open(_pl))
                _cur.setdefault("epoch_train_losses", []).append(round(_el, 6))
                _cur["protocol"] = "valplateau_v1"
                _cur["updated_epoch"] = ep
                _tmp = _pl + ".tmp"
                with open(_tmp, "w") as fh:
                    _json.dump(_cur, fh, indent=2)
                os.replace(_tmp, _pl)
            except Exception as _e:
                print("plateau-persist skipped: %s" % _e, flush=True)
        ledger.update(rid, "running", note="epoch %d heartbeat" % ep)

    # --- eval: macro-F1 over non-pad positions (3 classes) ---
    backbone.eval()
    head.eval()
    ys, ps = [], []
    with torch.no_grad():
        for b in batches(test, args.batch_size * 2):
            enc, y, m = make_batch(b)
            h = backbone(**enc).last_hidden_state
            pad = enc["attention_mask"] == 0
            logits = head(h, pad)
            ys.append(y[m].cpu().numpy())
            ps.append(logits[m].argmax(-1).cpu().numpy())
    y_all = np.concatenate(ys)
    p_all = np.concatenate(ps)
    from sklearn.metrics import f1_score
    macro_f1 = float(f1_score(y_all, p_all, average="macro"))
    if not np.isfinite(macro_f1):
        raise FloatingPointError("non-finite primary metric: MACRO_F1")
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
    if args.converge:
        result.update(tracker.result_fields())
        result.update(n_val=len(val), runtime=runtime)
    result_path = os.path.join(out_dir, "result.json")
    tmp_path = result_path + ".tmp"
    with open(tmp_path, "w") as fh:
        json.dump(result, fh, indent=2)
    os.replace(tmp_path, result_path)
    ledger_fields = dict(tracker.result_fields()) if args.converge else {}
    if args.converge:
        ledger_fields["convergence_status"] = ledger_fields.pop("status")
    ledger.update(rid, "done", value=macro_f1, metric="MACRO_F1",
                  extra_fields=result, **ledger_fields)
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
