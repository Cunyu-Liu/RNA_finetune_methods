"""E6 灾难性遗忘最小实现（v1）：微调前后 S0 held-out 困惑度 + 噪声带。

协议（spec §3 E6 v1.2 冻结口径的最小可行版）：
- 微调：ncRNA-family 任务（finetune_one 同协议：3 策略 × 种子 × lr tuned）
- 遗忘度量：S0 held-out（release22_cluster_split 五分位第 5 档 = held-out）
  的 nt 级平均 NLL（RNA-Sc wrapper 前向自带 LM logits）
- 噪声带：同一未微调 backbone 对同一 held-out 集 eval 两次（batch 顺序
  打乱 seed 不同）——两次 NLL 之差即重评噪声带（spec E6 对照臂）
- 遗忘声明 = ΔNLL(post − pre) 超出噪声带才报
- official（RiNALMo）分支：AutoModel 无 LM 头——直接类加载 RiNALMoForMaskedLM
  （28 词表，model=encoder + lm_head）；双向模型不能 shift-by-1，NLL 用
  MLM leave-one-out 伪似然（每个非特殊位单独 mask，其余全可见）；
  lora 等 peft 臂训练后 merge_and_unload 原地回迁再评

用法:
  python -m rnafteval.e6_forget --model RNA-Sc-10M --strategy full \
      --seed 17 --lr 3e-5 --device 0 --out-suffix lr3e-05

产物: /mnt/cunyuliu/rna-ft-eval/artifacts/e6/<model>_<strategy>_s<seed>_<suffix>/result.json
"""
from __future__ import annotations

import argparse
import json
import os
import random
import time

import torch

ROOT = "/mnt/cunyuliu/rna-ft-eval"
S0 = ("/mnt/cunyuliu/tokenizer-benchmark/data/derived/split/"
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
            t = tok(s[:max_len], truncation=True, max_length=max_len + 2)
            t = t["input_ids"] if isinstance(t, dict) else t
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


OFFICIAL = {"RiNALMo-micro", "RiNALMo-mega", "RiNALMo-650M"}


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


def nll_eval(backbone, tok, seqs, device, bs=8, shuffle_seed=None):
    """nt-level mean NLL over held-out seqs (PAD excluded).

    controlled 系：shift-by-1 因果 NLL（原 wrapper 前向自带 LM logits）。
    official 系：RiNALMo 双向 + RiNALMoForMaskedLM——MLM leave-one-out
    伪似然（每个非特殊位单独换 <mask>，其余位置全可见）。"""
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
        return
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
        probe = encode_seqs(tok, [recs[0]["seq"]], device)
        probe_core = _official_encoder(backbone) if is_official else backbone
        h_dim = probe_core(**probe).last_hidden_state.shape[-1]
    if h_dim != d_model:
        d_model = h_dim

    # --- pre-finetune S0 NLL + noise band (two evals, different order) ---
    pre_a = nll_eval(backbone, tok, hold, device, shuffle_seed=201)
    pre_b = nll_eval(backbone, tok, hold, device, shuffle_seed=707)
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
    post = nll_eval(backbone, tok, hold, device, shuffle_seed=201)

    result = {
        "run_id": rid, "model": args.model, "strategy": args.strategy,
        "seed": args.seed, "lr": args.lr, "epochs": args.epochs,
        "n_holdout": len(hold), "pre_nll_a": pre_a, "pre_nll_b": pre_b,
        "noise_band": noise_band, "post_nll": post,
        "delta_nll": post - pre_a,
        "forgot": bool((post - pre_a) > max(noise_band, 1e-6)),
        "wall_sec": time.time() - t0,
        "protocol": "E6-v1: pre/post S0 heldout NLL + reorder noise band",
    }
    with open(os.path.join(out_dir, "result.json"), "w") as f:
        json.dump(result, f, indent=2)
    fields = {k: v for k, v in result.items() if k not in ("run_id", "protocol")}
    update(rid, status="done", **fields)
    print(json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    main()
