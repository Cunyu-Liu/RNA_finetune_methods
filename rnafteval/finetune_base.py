"""BEACON sequence-level multi-label modification prediction.

Each 101-nt sequence has 12 modification-type targets. The prediction head
uses pooled sequence representations and BCE. The primary reported value is
m6A AUC (label index 7); the 12-label mean AUC is auxiliary.

Usage:
  python -m rnafteval.finetune_base --model RiNALMo-micro --task modification \
      --strategy lora --seed 17 --split random --device 0 --converge
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
from .splits import prepare_convergence_splits
from .tasks import modification as mod_task

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
    e3_tag = ("_e3%d" % args.n_train) if args.n_train != 20000 else ""
    protocol_tag = vp.protocol_tag(args)
    return (("_smoke" if args.smoke else "") + e3_tag + lr_tag + rank_tag +
            protocol_tag + getattr(args, "out_suffix", "_seqmlfix"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--task", default="modification")
    ap.add_argument("--strategy", required=True,
                    choices=["frozen", "lora", "head-only", "full",
                             "dora", "ia3", "prefix"])
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--split", required=True, choices=["random", "family"])
    ap.add_argument("--device", type=int, required=True)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--batch-size", type=int, default=32)
    ap.add_argument("--n-train", type=int, default=20000,
                    help="subsample of train for wall-time control")
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--rank", type=int, default=8,
                    help="LoRA/DoRA rank (E2 sweep; default 8)")
    vp.add_convergence_args(ap)
    ap.add_argument("--out-suffix", default="",
                    help="optional protocol label appended to the run_id")
    args = ap.parse_args()
    vp.validate_convergence_args(args)

    if not torch.cuda.is_available():
        print(json.dumps({"event": "CUDA_UNAVAILABLE_ABORT"}), flush=True)
        return 2
    torch.cuda.set_device(args.device)
    device = "cuda:%d" % args.device
    torch.manual_seed(args.seed)
    random.seed(args.seed)

    extra = _run_extra(args)
    rid = ledger.run_id(args.model, args.task, args.strategy, args.seed,
                        args.split, extra)
    out_dir = os.path.join(ledger.ARTIFACT_ROOT, rid)
    os.makedirs(out_dir, exist_ok=True)
    claim = ledger.claim(args.model, args.task, args.strategy, args.seed,
                         args.split, device=args.device, out_dir=out_dir,
                         extra=extra)
    if not claim["claimed"]:
        print("skip (already %s)" % claim["row"]["status"])
        return 75  # EXIT_CLAIM_BLOCKED (fake-complete fix 1006b)

    t0 = time.time()
    torch.cuda.reset_peak_memory_stats(args.device)

    val = None
    if args.split == "family":
        # cluster-pure split (make_family_split_mod): host-transcript proxy
        # via MMseqs2 80-80 on overlapping 101-nt windows
        import pyarrow.parquet as pq
        fam = os.path.join(ROOT, "data", "family_splits", "modification.parquet")
        if not os.path.exists(fam):
            print("family split missing: %s" % fam, flush=True)
            ledger.update(rid, "failed", note="modification family parquet missing")
            return 3
        t = pq.read_table(fam).to_pydict()
        by_side = {}
        for seq, lab, sd, cid in zip(t["seq"], t["labels"], t["split"],
                                     t["cluster_id"]):
            if sd in ("train", "val", "test"):
                by_side.setdefault(sd, []).append(
                    {"seq": seq, "labels": [int(x) for x in str(lab).split()],
                     "subset": "family_%s" % sd, "cluster": cid})
        train, test = by_side["train"], by_side["test"]
        if args.converge:
            val = by_side.get("val")
        elif 0 < args.n_train < len(train) and args.n_train != 20000:
            # E3: 宿主簇级整簇采样（随机抽簇→整簇纳入，对齐 e3_subsampler）
            by_cl = {}
            for i, row in enumerate(train):
                by_cl.setdefault(row["cluster"], []).append(i)
            cls = sorted(by_cl)
            rng = random.Random(args.seed)
            rng.shuffle(cls)
            picked = []
            for cc in cls:
                picked.extend(by_cl[cc])
                if len(picked) >= args.n_train:
                    break
            train = [train[i] for i in picked]
        else:
            rng = random.Random(args.seed)
            train = rng.sample(train, min(args.n_train, len(train)))
    else:
        sp = mod_task.load_official_split()
        train = sp["train"]
        test = sp["test"]
        if args.converge:
            val = sp.get("validation")
        elif 0 < args.n_train < len(train) and args.n_train != 20000:
            # E3: 用家族表 seq->cluster 映射做宿主簇级整簇采样
            import pyarrow.parquet as pq
            tp = pq.read_table(
                os.path.join(ROOT, "data", "family_splits",
                             "modification.parquet"),
                columns=["seq", "cluster_id"]).to_pydict()
            seq2cl = dict(zip(tp["seq"], tp["cluster_id"]))
            by_cl = {}
            for i, row in enumerate(train):
                by_cl.setdefault(seq2cl.get(row["seq"], "c_solo_%d" % i),
                                 []).append(i)
            cls = sorted(by_cl)
            rng = random.Random(args.seed)
            rng.shuffle(cls)
            picked = []
            for cc in cls:
                picked.extend(by_cl[cc])
                if len(picked) >= args.n_train:
                    break
            train = [train[i] for i in picked]
        else:
            rng = random.Random(args.seed)
            train = rng.sample(train, min(args.n_train, len(train)))
    data_evidence = None
    if args.converge:
        train, val, test, data_evidence = prepare_convergence_splits(
            train, val, test, n_train=args.n_train, sample_seed=args.seed,
            family=args.split == "family",
            validation_source="official_validation" if args.split == "random"
            else "family_validation",
            evidence_path=os.path.join(out_dir, "split_evidence.json"),
            protocol=vp.protocol_tag(args).lstrip("_"))
        print("data: train %d val %d test %d" % (
            len(train), len(val), len(test)), flush=True)
    if args.smoke:
        if val is not None:
            val = val[:320]
        train = train[:320]
        test = test[:320]

    from .models import load_model
    from .strategies import apply_strategy, make_head
    spec, tok, backbone = load_model(args.model, device)
    with torch.no_grad():
        probe = encode_seqs(tok, [train[0]["seq"]], device, 128)
        d = backbone(**probe).last_hidden_state.shape[-1]
    backbone, n_trainable = apply_strategy(backbone, args.strategy, lora_rank=args.rank)
    # BEACON Modification is sequence-level multi-label prediction of 12
    # modification types, not a per-base label grid (official train_modification).
    head = make_head("per-seq", d, 12).to(device)
    train_params = [p for p in head.parameters() if p.requires_grad] + \
        [p for p in backbone.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(train_params, lr=args.lr)
    def save_best(epoch, val_loss):
        vp.save_best_checkpoint(
            os.path.join(out_dir, "best.ckpt"), backbone, head,
            epoch=epoch, best_epoch=epoch, best_val=val_loss)
    tracker = vp.make_tracker(out_dir, args, rid, save_best) \
        if args.converge else None
    runtime = vp.runtime_evidence(tok, device) if args.converge else None

    def make_batch(b):
        enc = encode_seqs(tok, [r["seq"] for r in b], device, 128)
        labels = [r["labels"] for r in b]
        if any(len(x) != 12 for x in labels):
            raise ValueError("BEACON modification requires 12 multi-label targets")
        y = torch.tensor(labels, dtype=torch.float32, device=device)
        return enc, y

    for ep in vp.training_epochs(args):
        import random as _rd
        _epshuf = _rd.Random(args.seed * 1000 + ep)
        _rows = list(train)
        _epshuf.shuffle(_rows)
        backbone.train(args.strategy in ("lora", "full"))
        head.train()
        tot, nb = 0.0, 0
        for b in batches(_rows, args.batch_size):
            enc, y = make_batch(b)
            no_grad = args.strategy in ("frozen", "head-only")
            import contextlib
            with contextlib.nullcontext() if not no_grad \
                    else torch.no_grad():
                h = backbone(**enc).last_hidden_state
            pad = enc["attention_mask"] == 0
            logits = head(h, pad).squeeze(-1)
            mask = torch.ones_like(y)
            loss = torch.nn.functional.binary_cross_entropy_with_logits(
                logits, y, reduction="none") * mask
            loss = loss.sum() / mask.sum().clamp(min=1)
            opt.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(train_params, 1.0)
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
                    enc, y = make_batch(b)
                    h = backbone(**enc).last_hidden_state
                    pad = enc["attention_mask"] == 0
                    logits = head(h, pad).squeeze(-1)
                    mask = torch.ones_like(y)
                    loss_map = torch.nn.functional.binary_cross_entropy_with_logits(
                        logits, y, reduction="none") * mask
                    val_loss = loss_map.sum() / mask.sum().clamp(min=1)
                    val_tot += val_loss.item()
                    val_nb += 1
            val_epoch_loss = val_tot / max(val_nb, 1)
            print("epoch %d val_loss %.6f" % (ep, val_epoch_loss), flush=True)
            if tracker.record(ep, epoch_loss, val_epoch_loss):
                print("STOP %s epoch=%d epochs_trained=%d" % (
                    tracker.stop_reason, ep, ep + 1), flush=True)
                ledger.update(rid, "running", note=tracker.stop_reason)
                break
        ledger.update(rid, "running", note="epoch %d heartbeat" % ep)

    # --- eval: one AUC per modification type, m6A is official label index 7 ---
    if args.converge and args.convergence_mode == "bestval":
        vp.restore_best_checkpoint(tracker, backbone, head, device)
    backbone.eval()
    head.eval()
    ys, ps = [], []
    with torch.no_grad():
        for b in batches(test, args.batch_size * 2):
            enc, y = make_batch(b)
            h = backbone(**enc).last_hidden_state
            pad = enc["attention_mask"] == 0
            logits = head(h, pad)
            ys.append(y.cpu().numpy())
            ps.append(torch.sigmoid(logits).cpu().numpy())
    from sklearn.metrics import roc_auc_score
    y_all = np.concatenate(ys)
    p_all = np.concatenate(ps)
    aucs = np.full(12, 0.5, dtype=float)
    for label_idx in range(12):
        if len(np.unique(y_all[:, label_idx])) > 1:
            aucs[label_idx] = roc_auc_score(
                y_all[:, label_idx], p_all[:, label_idx])
    auc = float(aucs[7])
    mean_auc = float(aucs.mean())

    wall = time.time() - t0
    peak = torch.cuda.max_memory_allocated(args.device) / (1 << 20)
    result = {
        "run_id": rid, "model": args.model, "task": args.task,
        "strategy": args.strategy, "seed": args.seed, "split": args.split,
        "metric": "AUC", "value": auc, "n_train": len(train),
        "n_test": len(test), "wall_sec": round(wall, 1),
        "metric_mean_auc": mean_auc, "aucs_by_modification": aucs.tolist(),
        "label_semantics": "BEACON sequence-level multi-label; m6A index 7",
        "peak_mem_mb": round(peak, 1),
        "backbone_trainable": n_trainable, "lr": args.lr,
        "epochs": args.epochs, "smoke": args.smoke,
    }
    if args.converge:
        if not np.isfinite(auc):
            raise FloatingPointError("non-finite primary metric: AUC")
        result.update(tracker.result_fields())
        result.update(n_val=len(val), runtime=runtime,
                      data_evidence=data_evidence,
                      acceptance_eligible=not args.smoke)
    result_path = os.path.join(out_dir, "result.json")
    with open(result_path + ".tmp", "w") as fh:
        json.dump(result, fh, indent=2)
    os.replace(result_path + ".tmp", result_path)
    ledger_fields = vp.result_ledger_fields(result) if args.converge else \
        {k: v for k, v in result.items() if k != "run_id"}
    ledger.update(rid, "done", **ledger_fields)
    print(json.dumps(result, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
