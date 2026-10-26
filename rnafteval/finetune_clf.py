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

from . import ledger, valplateau as vp
from .splits import (
    assert_cluster_no_overlap, assert_no_overlap, random_split, seq_hash)

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
    protocol_tag = vp.protocol_tag(args)
    return (("_smoke" if args.smoke else "") + n_tag + lr_tag + rank_tag +
            epoch_tag + protocol_tag)


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
    vp.add_convergence_args(ap)
    args = ap.parse_args()
    vp.validate_convergence_args(args)

    device = torch.device("cuda:%d" % args.device)
    assert torch.cuda.is_available(), "CUDA unavailable - abort (no CPU fallback)"

    extra = _run_extra(args)
    rid = ledger.run_id(args.model, args.task, args.strategy, args.seed,
                        args.split, extra=extra)
    out_dir = os.path.join(ledger.ARTIFACT_ROOT, rid)
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
    if args.task == "crispr-off-target":
        from .tasks import crispr as cr_task
        if args.split == "family":
            import pyarrow.parquet as pq
            fam = os.path.join(ROOT, "data", "family_splits",
                               "crispr-off-target.parquet")
            assert os.path.exists(fam), "run make_family_split first"
            t = pq.read_table(fam).to_pydict()
            lab_col = t["label"] if "label" in t else t["labels"]
            def _int_label(l):
                if isinstance(l, (list, tuple)):
                    return int(l[0])
                return int(l)
            recs = [{"seq": s, "label": _int_label(l), "cluster": c}
                    for s, l, c in zip(t["seq"], lab_col, t["cluster_id"])]
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
            # Formal seeds vary training/subsampling, not the data split.
            # Keep this identical to finetune_one and the preregistered protocol.
            parts = random_split(recs, seed=17)

    data_evidence = None
    if args.converge:
        source = "family_validation" if args.split == "family" else (
            "official_validation" if args.task == "crispr-off-target"
            else "random_split_validation")
        data_evidence = {
            "protocol": vp.protocol_tag(args).lstrip("_"),
            "split_source": source, "split": args.split,
            "n_train": len(parts["train"]), "n_val": len(parts["val"]),
            "n_test": len(parts["test"]), "status": "CHECKING",
        }
        sides = {side: {seq_hash(row["seq"]) for row in rows}
                 for side, rows in parts.items()}
        overlaps = {"%s_%s" % (a, b): sorted(sides[a] & sides[b])
                    for a, b in (("train", "val"), ("train", "test"),
                                 ("val", "test"))}
        data_evidence["sequence_cross_split_overlap"] = {
            pair: len(hashes) for pair, hashes in overlaps.items()}
        data_evidence["sequence_cross_split_examples"] = {
            pair: hashes[:20] for pair, hashes in overlaps.items()}
        data_evidence["deduplicated"] = all(
            len(hashes) == len(parts[side]) for side, hashes in sides.items())
        if args.split == "family":
            cluster_sides = {side: {str(row["cluster"]) for row in rows}
                             for side, rows in parts.items()}
            cluster_overlaps = {
                "%s_%s" % (a, b): sorted(cluster_sides[a] & cluster_sides[b])
                for a, b in (("train", "val"), ("train", "test"),
                             ("val", "test"))}
            data_evidence["cluster_cross_split_overlap"] = {
                pair: len(clusters) for pair, clusters in cluster_overlaps.items()}
            data_evidence["cluster_cross_split_examples"] = {
                pair: clusters[:20] for pair, clusters in cluster_overlaps.items()}
        evidence_path = os.path.join(out_dir, "split_evidence.json")
        with open(evidence_path + ".tmp", "w") as fh:
            json.dump(data_evidence, fh, indent=2)
        os.replace(evidence_path + ".tmp", evidence_path)
        try:
            assert_no_overlap(parts["train"], parts["val"], unit="seq")
            assert_no_overlap(parts["train"], parts["test"], unit="seq")
            assert_no_overlap(parts["val"], parts["test"], unit="seq")
            if args.split == "family":
                assert_cluster_no_overlap(parts["train"], parts["val"])
                assert_cluster_no_overlap(parts["train"], parts["test"])
                assert_cluster_no_overlap(parts["val"], parts["test"])
        except Exception as exc:
            data_evidence["status"] = "INVALID"
            data_evidence["error"] = str(exc)
            with open(evidence_path + ".tmp", "w") as fh:
                json.dump(data_evidence, fh, indent=2)
            os.replace(evidence_path + ".tmp", evidence_path)
            raise
    if args.n_train > 0:
        rng = random.Random(args.seed)
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
    if args.converge:
        supported = {row["label"] for row in parts["train"]}
        data_evidence["label_support"] = {
            side: {str(label): sum(row["label"] == label for row in parts[side])
                   for label in labels}
            for side in ("train", "val", "test")}
        data_evidence["missing_label_support"] = {
            side: sorted(row["label"] for row in parts[side]
                         if row["label"] not in supported)
            for side in ("train", "val", "test")}
        data_evidence["n_train"] = len(parts["train"])
        data_evidence["n_val"] = len(parts["val"])
        data_evidence["n_test"] = len(parts["test"])
        data_evidence["status"] = "OK"
        with open(evidence_path + ".tmp", "w") as fh:
            json.dump(data_evidence, fh, indent=2)
        os.replace(evidence_path + ".tmp", evidence_path)
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
    def save_best(epoch, val_loss):
        vp.save_best_checkpoint(
            os.path.join(out_dir, "best.ckpt"), backbone, head,
            epoch=epoch, best_epoch=epoch, best_val=val_loss)
    tracker = vp.make_tracker(out_dir, args, rid, save_best) \
        if args.converge else None
    runtime = vp.runtime_evidence(tok, device) if args.converge else None
    if args.converge and not parts["val"]:
        raise ValueError("--converge requires a non-empty validation split")

    def run_batch(b):
        enc = encode_seqs(tok, [r["seq"] for r in b], device, args.max_len)
        y = torch.tensor([r["label_id"] for r in b], device=device)
        return enc, y

    for ep in vp.training_epochs(args):
        _sh = random.Random(args.seed * 1000 + ep)
        _rows = list(parts["train"])
        _sh.shuffle(_rows)
        backbone.train(args.strategy in ("lora", "full", "dora", "ia3"))
        head.train()
        tot, nb = 0.0, 0
        for b in batches(_rows, args.batch_size):
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

        _el = tot / max(nb, 1)
        if args.converge:
            backbone.eval()
            head.eval()
            val_tot, val_nb = 0.0, 0
            with torch.no_grad():
                for b in batches(parts["val"], args.batch_size * 2):
                    enc, y = run_batch(b)
                    h = backbone(**enc).last_hidden_state
                    pad = enc["attention_mask"] == 0
                    val_loss = lossf(head(h, pad), y)
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

    # --- eval ---
    if args.converge and args.convergence_mode == "bestval":
        vp.restore_best_checkpoint(tracker, backbone, head, device)
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

    if not np.isfinite(value):
        raise FloatingPointError("non-finite primary metric: %s" % metric)
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
    if args.converge:
        result.update(tracker.result_fields())
        result.update(n_val=len(parts["val"]), runtime=runtime,
                      data_evidence=data_evidence,
                      acceptance_eligible=not args.smoke)
    result_path = os.path.join(out_dir, "result.json")
    tmp_path = result_path + ".tmp"
    with open(tmp_path, "w") as fh:
        json.dump(result, fh, indent=2)
    os.replace(tmp_path, result_path)
    if args.converge:
        ledger.update(rid, "done", **vp.result_ledger_fields(result))
    else:
        ledger.update(rid, "done", value=value, metric=metric,
                      extra_fields=result)
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
