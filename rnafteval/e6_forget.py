"""E6 灾难性遗忘最小实现（v1）：微调前后 S0 held-out 评估 + 噪声带。

协议（spec §3 E6 v1.2 冻结口径的最小可行版）：
- 微调：ncRNA-family 任务（finetune_one 同协议：3 策略 × 种子 × lr tuned）
- 遗忘度量：S0 held-out（release22_cluster_split 五分位第 5 档 = held-out）
  的 nt 级平均 NLL；controlled 用 causal shift，official 用 fixed-mask MLM，
  NucleicBERT 用 hidden-state cosine drift
- 噪声带（NLL 系）：同一未微调 backbone 以 seed 201/707 重评。controlled
  仅改变顺序；official 同时独立改变掩码与顺序，因此不是纯 reorder noise
- 遗忘声明 = ΔNLL(post − pre) 超出噪声带才报
- official 分支：双向 MaskedLM 在每序列 attention=1 且非 special-token 的
  位置固定抽样（默认 15%，至少 1 个），只在掩码位置计算 NLL。逐序列 RNG
  由 eval seed + 原始序列 index 决定；pre_a/post 共用 seed 201 掩码，pre_b
  使用 seed 707 独立掩码。lora 等 peft 臂训练后 merge_and_unload 再评

用法:
  python -m rnafteval.e6_forget --model RNA-Sc-10M --strategy full \
      --seed 17 --lr 3e-5 --device 0 --out-suffix lr3e-05

产物: /root/rna-ft-eval/artifacts/e6/<model>_<strategy>_s<seed>_<suffix>/result.json
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import time

import torch

ROOT = "/root/rna-ft-eval"
S0 = ("/root/tokenizer-benchmark/data/derived/split/"
      "release22_split_8080.parquet")

MODEL = {"RNA-Sc-1M": 256, "RNA-Sc-10M": 512, "RNA-Sc-30M": 480,
         "RNA-Sc-100M": 768, "RNA-Sc-650M": 1408}


def s0_heldout_seqs(n_max=2000):
    """S0 held-out：release22 80/80 簇切分 test + family_test 档的规范序列。"""
    import pandas as pd
    df = pd.read_parquet(S0, columns=["canonical_sequence",
                                      "split_membership"])
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


OFFICIAL = {"RiNALMo-micro", "RiNALMo-mega", "RiNALMo-650M",
            "ERNIE-RNA", "RNA-FM"}
# NucleicBERT: no MLM head / no  TED (k-mer perturbation pretraining).
# E6 metric switch for NB: hidden-state cosine drift on S0 heldout.
NB_DRIFT_MODELS = {"NucleicBERT"}
_LM_CLASS = {
    "RiNALMo-micro": "RiNALMoForMaskedLM", "RiNALMo-mega": "RiNALMoForMaskedLM",
    "RiNALMo-650M": "RiNALMoForMaskedLM",
    "ERNIE-RNA": "ErnieRnaForMaskedLM", "RNA-FM": "RnaFmForMaskedLM",
}


def _official_encoder(lm):
    """取出返回 last_hidden_state 的 RiNALMoModel（剥 peft 再降到 .model）。

    注意顺序：PeftModel 的 __getattr__ 转发会让 hasattr(core,"model")
    先命中被包装的 RiNALMoForMaskedLM——必须先剥 peft 层再降级，
    否则拿到的是 MaskedLM 输出对象（无 last_hidden_state）。"""
    core = lm.m if hasattr(lm, "m") else lm
    if hasattr(core, "base_model") and hasattr(core.base_model, "model"):
        core = core.base_model.model
    if hasattr(core, "model") and hasattr(core.model, "encoder"):
        return core.model
    return core


def drift_eval(backbone, ref_states, tok, seqs, device, bs=8):
    """Mean cosine distance between post-finetune hidden states and pre-finetune
    reference states on the same S0 heldout sequences (NB forgetting proxy).

    ref_states: dict seq_index -> np.ndarray (L, D) from pre-finetune pass.
    Returns mean (1 - cos) over all non-pad positions of all seqs."""
    import numpy as np
    backbone.eval()
    tot, cnt = 0.0, 0
    with torch.no_grad():
        for i in range(0, len(seqs), bs):
            chunk = [seqs[j] for j in range(i, min(i + bs, len(seqs)))]
            enc = encode(tok, chunk, device)
            out = backbone(input_ids=enc["input_ids"],
                           attention_mask=enc["attention_mask"])
            h = out.last_hidden_state
            for k, j in enumerate(range(i, min(i + bs, len(seqs)))):
                if j not in ref_states:
                    continue
                ref = torch.tensor(ref_states[j], device=h.device,
                                   dtype=h.dtype)
                L = min(h.shape[1], ref.shape[0])
                m = enc["attention_mask"][k, :L].bool()
                hh = h[k, :L][m]
                rr = ref[:L][m]
                if hh.numel() == 0:
                    continue
                cos = torch.nn.functional.cosine_similarity(
                    hh, rr, dim=-1)
                tot += float((1.0 - cos).sum().item())
                cnt += int(cos.numel())
    return tot / max(cnt, 1)


def _collect_states(backbone, tok, seqs, device, bs=8):
    """Pre-finetune reference hidden states for drift eval."""
    backbone.eval()
    states = {}
    with torch.no_grad():
        for i in range(0, len(seqs), bs):
            chunk = [seqs[j] for j in range(i, min(i + bs, len(seqs)))]
            enc = encode(tok, chunk, device)
            out = backbone(input_ids=enc["input_ids"],
                           attention_mask=enc["attention_mask"])
            h = out.last_hidden_state
            for k, j in enumerate(range(i, min(i + bs, len(seqs)))):
                states[j] = h[k].float().cpu().numpy()
    return states


def nll_eval(backbone, tok, seqs, device, bs=8, shuffle_seed=None,
             eval_seed=None, mask_rate=0.15):
    """nt-level mean NLL over held-out seqs (PAD excluded).

    controlled 系：shift-by-1 因果 NLL（原 wrapper 前向自带 LM logits）。
    official 系：固定比例 masked-position MLM NLL。每序列的候选位置仅含
    attention=1 且非 special-token 的位置；RNG 由 eval seed 和原始序列
    index 决定，与 batch size 及评估顺序无关。eval_seed 缺省沿用
    shuffle_seed，两者都缺省时使用 0。"""
    order = list(range(len(seqs)))
    if shuffle_seed is not None:
        random.Random(shuffle_seed).shuffle(order)
    tot, cnt = 0.0, 0
    backbone.eval()
    is_official = hasattr(tok, "mask_token_id")
    seq_tot = [0.0] * len(seqs) if is_official else None
    seq_cnt = [0] * len(seqs) if is_official else None
    if is_official:
        if not 0.0 < mask_rate <= 1.0:
            raise ValueError("mask_rate must be in (0, 1]")
        mask_seed = shuffle_seed if eval_seed is None else eval_seed
        mask_seed = 0 if mask_seed is None else int(mask_seed)
        special_ids = set(getattr(tok, "all_special_ids", []) or [])
        for name in ("bos_token_id", "eos_token_id", "cls_token_id",
                     "sep_token_id", "pad_token_id", "mask_token_id",
                     "unk_token_id"):
            token_id = getattr(tok, name, None)
            if token_id is not None:
                special_ids.add(token_id)
    with torch.no_grad():
        for i in range(0, len(order), bs):
            original_indices = order[i:i + bs]
            chunk = [seqs[j] for j in original_indices]
            enc = encode(tok, chunk, device)
            ids = enc["input_ids"]
            mask = enc["attention_mask"]
            if is_official:
                masked_ids = ids.clone()
                batch_positions = []
                for row, seq_index in enumerate(original_indices):
                    candidates = [
                        p for p, (attn, token_id) in enumerate(zip(
                            mask[row].tolist(), ids[row].tolist()))
                        if attn == 1 and token_id not in special_ids
                    ]
                    if not candidates:
                        raise ValueError(
                            "official MLM sequence %d has no maskable positions"
                            % seq_index)
                    n_mask = min(len(candidates), max(
                        1, int(len(candidates) * mask_rate)))
                    rng = random.Random((mask_seed << 32) ^ seq_index)
                    positions = sorted(rng.sample(candidates, n_mask))
                    masked_ids[row, positions] = tok.mask_token_id
                    batch_positions.append(positions)
                out = backbone(input_ids=masked_ids, attention_mask=mask)
                lp = torch.nn.functional.log_softmax(
                    out.logits.float(), dim=-1)
                for row, seq_index in enumerate(original_indices):
                    positions = torch.tensor(batch_positions[row],
                                             device=ids.device, dtype=torch.long)
                    target = ids[row, positions]
                    values = lp[row, positions]
                    nll = -values.gather(1, target.unsqueeze(1)).sum()
                    seq_tot[seq_index] = nll.item()
                    seq_cnt[seq_index] = len(batch_positions[row])
                continue
            core = backbone.m if hasattr(backbone, "m") else backbone
            if hasattr(core, "base_model") and hasattr(core.base_model, "model"):
                core = core.base_model.model
            try:
                out = core(enc["input_ids"], None, return_all_hiddens=False)
            except TypeError:
                # multimolecule/HF-style encoder (ERNIE/RNA-FM/NB): plain HF call
                out = core(input_ids=enc["input_ids"],
                           attention_mask=enc["attention_mask"])
            logits = out[0] if isinstance(out, (tuple, list)) else out
            if hasattr(logits, "last_hidden_state"):
                logits = logits.last_hidden_state
            lp = torch.nn.functional.log_softmax(logits.float(), dim=-1)
            shift_lp = lp[:, :-1]
            shift_ids = ids[:, 1:]
            shift_mask = (mask[:, 1:] == 1)
            sel = shift_mask.reshape(-1)
            tgt = shift_ids.reshape(-1)[sel]
            v = shift_lp.reshape(-1, shift_lp.shape[-1])[sel]
            tot += (-v.gather(1, tgt.unsqueeze(1)).sum()).item()
            cnt += int(sel.sum().item())
    if is_official:
        return math.fsum(seq_tot) / max(sum(seq_cnt), 1)
    return tot / max(cnt, 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--strategy", required=True,
                    choices=["frozen", "lora", "full", "dora", "ia3", "head-only"])
    ap.add_argument("--seed", type=int, default=17)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--device", default="0")
    ap.add_argument("--epochs", type=int, default=10)
    ap.add_argument("--batch-size", type=int, default=32)
    ap.add_argument("--n-holdout", type=int, default=2000)
    ap.add_argument("--n-train-cap", type=int, default=0,
                    help="0 = full ncRNA train set")
    ap.add_argument("--mask-rate", type=float, default=0.15)
    ap.add_argument("--out-suffix", default="")
    args = ap.parse_args()
    device = int(args.device)
    t0 = time.time()

    from .models import load_model
    from .strategies import apply_strategy, make_head
    from .finetune_one import encode_seqs, batches
    from .splits import random_split
    from .tasks.ncrna import load_ncrna
    from .tasks.dedup import dedup
    from .ledger import claim, update

    out_dir = os.path.join(ROOT, "artifacts", "e6",
                           "%s_%s_s%d%s" % (args.model, args.strategy,
                                            args.seed, args.out_suffix))
    os.makedirs(out_dir, exist_ok=True)
    res = claim(args.model, "e6-forgetting", args.strategy, args.seed,
                "s0-heldout", device=device, out_dir=out_dir,
                note="E6 v1: pre/post S0 ppl + noise band",
                extra=args.out_suffix)
    if res is None or res.get("claimed") is False:
        print("skip (ledger: %s)" % (res or {}).get("reason"), flush=True)
        return 75
    rid = res["row"]["run_id"]

    # --- S0 held-out ---
    hold = s0_heldout_seqs(args.n_holdout)
    print("S0 heldout: %d seqs" % len(hold), flush=True)

    # --- ncRNA data (same protocol as finetune_one) ---
    recs = load_ncrna(os.path.join(
        ROOT, "data", "beacon_raw", "noncoding-rna-family", "data"))
    recs = dedup(recs)
    parts = random_split(recs, seed=args.seed)
    labels = sorted({r["label"] for r in recs})
    lab2id = {l: i for i, l in enumerate(labels)}
    for k in parts:
        for r in parts[k]:
            r["label_id"] = lab2id[r["label"]]
    if args.n_train_cap:
        parts["train"] = parts["train"][:args.n_train_cap]

    # --- model ---
    is_official = args.model in OFFICIAL
    is_nb_drift = args.model in NB_DRIFT_MODELS
    if is_official:
        import multimolecule
        from multimolecule import RnaTokenizer
        from .models import hf_path, MODEL_SPECS
        path = hf_path(MODEL_SPECS[args.model].repo)
        tok = RnaTokenizer.from_pretrained(path)
        lm_cls = getattr(multimolecule, _LM_CLASS[args.model])
        lm = lm_cls.from_pretrained(path, trust_remote_code=True)
        if hasattr(lm, "lm_head") and hasattr(lm.lm_head, "decoder") \
                and lm.lm_head.decoder is not None \
                and hasattr(lm.lm_head.decoder, "bias") \
                and lm.lm_head.decoder.bias is not None:
            with torch.no_grad():
                lm.lm_head.decoder.bias.zero_()
        backbone = lm.to(device)
        d_model = MODEL_SPECS[args.model].d_model
    else:
        spec, tok, backbone = load_model(args.model, device)
        d_model = spec.d_model
    with torch.no_grad():
        probe = encode_seqs(tok, [recs[0]["seq"]], device)
        probe_core = _official_encoder(backbone) if is_official else backbone
        h_dim = probe_core(**probe).last_hidden_state.shape[-1]
    if h_dim != d_model:
        d_model = h_dim

    # --- pre-finetune metric: NLL (official) or hidden-drift ref (NB) ---
    if is_nb_drift:
        ref_states = _collect_states(backbone, tok, hold, device)
        pre_drift = 0.0  # drift vs itself = 0 by definition
        noise_band = 0.0
        print("NB drift mode: ref states collected for %d seqs" % len(hold),
              flush=True)
    else:
        pre_a = nll_eval(backbone, tok, hold, device, shuffle_seed=201,
                         eval_seed=201, mask_rate=args.mask_rate)
        pre_b = nll_eval(backbone, tok, hold, device, shuffle_seed=707,
                         eval_seed=707, mask_rate=args.mask_rate)
        noise_band = abs(pre_b - pre_a)
        print("pre NLL: %.4f / %.4f (noise band %.4f)" % (pre_a, pre_b, noise_band),
              flush=True)

    # --- finetune (same loop as finetune_one) ---
    backbone, n_trainable = apply_strategy(backbone, args.strategy)
    head = make_head("per-seq", d_model, len(labels)).to(device)
    tp = [p for p in head.parameters() if p.requires_grad]
    if hasattr(backbone, "m"):
        tp += [p for p in backbone.m.parameters() if p.requires_grad]
    else:
        tp += [p for p in backbone.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(tp, lr=args.lr)
    lossf = torch.nn.CrossEntropyLoss()
    tr_backbone = args.strategy in ("lora", "full", "dora", "ia3", "prefix")
    enc_core = _official_encoder(backbone) if is_official else None
    for ep in range(args.epochs):
        backbone.train(tr_backbone)
        head.train()
        tot, nb = 0.0, 0
        for b in batches(parts["train"], args.batch_size):
            enc = encode_seqs(tok, [r["seq"] for r in b], device)
            y = torch.tensor([r["label_id"] for r in b], device=device)
            if tr_backbone:
                fwd = enc_core if is_official else backbone
                h = fwd(**enc).last_hidden_state
            else:
                with torch.no_grad():
                    fwd = enc_core if is_official else backbone
                    h = fwd(**enc).last_hidden_state
            pad = enc["attention_mask"] == 0
            loss = lossf(head(h, pad), y)
            opt.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(tp, 1.0)
            opt.step()
            tot += loss.item()
            nb += 1
        print("epoch %d loss %.4f" % (ep, tot / max(nb, 1)), flush=True)

    # --- post-finetune S0 NLL ---
    if is_official and hasattr(backbone, "merge_and_unload") and \
            args.strategy in ("lora", "dora", "ia3", "prefix"):
        merged = backbone.merge_and_unload()
        merged.eval()
        backbone = merged
        print("peft merged back into RiNALMoForMaskedLM for post-NLL",
              flush=True)
    if is_nb_drift:
        post_drift = drift_eval(backbone, ref_states, tok, hold, device)
        result = {
            "run_id": rid, "model": args.model, "strategy": args.strategy,
            "seed": args.seed, "lr": args.lr, "epochs": args.epochs,
            "n_holdout": len(hold), "mask_rate": args.mask_rate,
            "metric": "HIDDEN_COSINE_DRIFT", "drift": post_drift,
            "wall_sec": time.time() - t0,
            "protocol": "E6-v1-nb: pre/post S0 heldout hidden cosine drift "
                        "(NB has no MLM head; NLL undefined)",
        }
    else:
        post = nll_eval(backbone, tok, hold, device, shuffle_seed=201,
                        eval_seed=201, mask_rate=args.mask_rate)
        if is_official:
            protocol = (
                "E6-v1-fixed-mask-mlm: pre/post S0 heldout masked-position NLL "
                "(mask_rate=%g; pre_a/post eval seed 201, pre_b eval seed 707); "
                "noise_band is an independent mask/order reevaluation difference"
                % args.mask_rate)
        else:
            protocol = ("E6-v1: pre/post S0 heldout causal shift NLL + "
                        "reorder noise band")
        result = {
            "run_id": rid, "model": args.model, "strategy": args.strategy,
            "seed": args.seed, "lr": args.lr, "epochs": args.epochs,
            "n_holdout": len(hold), "mask_rate": args.mask_rate,
            "pre_nll_a": pre_a, "pre_nll_b": pre_b,
            "noise_band": noise_band, "post_nll": post,
            "delta_nll": post - pre_a,
            "forgot": bool((post - pre_a) > max(noise_band, 1e-6)),
            "wall_sec": time.time() - t0, "protocol": protocol,
        }
    metric_keys = ("drift",) if is_nb_drift else (
        "pre_nll_a", "pre_nll_b", "noise_band", "post_nll", "delta_nll")
    for key in metric_keys:
        if not math.isfinite(result[key]):
            raise FloatingPointError(
                "non-finite E6 metric: %s=%r" % (key, result[key]))
    result_path = os.path.join(out_dir, "result.json")
    tmp_path = result_path + ".tmp"
    with open(tmp_path, "w") as f:
        json.dump(result, f, indent=2, allow_nan=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, result_path)
    fields = {k: v for k, v in result.items() if k not in ("run_id", "protocol")}
    update(rid, status="done", **fields)
    print(json.dumps(result, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
