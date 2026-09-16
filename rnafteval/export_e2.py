"""Export E2 PEFT horizontal-comparison table (C5).

Ledger -> markdown + CSV for preprint §2.3. Five arms on the RiNALMo-micro
ncRNA-family random split: full (LR-tuned protocol arm) / DoRA / LoRA /
IA3 / head-only. Tuning rows (seed 101) excluded; tuned-LR rows
(_lr1e-05) override default-LR rows per the A8 protocol arm.

Usage: python -m rnafteval.export_e2 [--out status/e2_table.md]
"""
from __future__ import annotations

import argparse
import collections
import json
import os

ROOT = "/mnt/cunyuliu/rna-ft-eval"
LEDGER = os.path.join(ROOT, "ledger.jsonl")

ARM_ORDER = ["full", "dora", "lora", "ia3", "headonly"]
ARM_LABEL = {"full": "full FT (LR-tuned 1e-5)", "dora": "DoRA r=8",
             "lora": "LoRA r=8", "ia3": "IA3",
             "headonly": "head-only"}
ARM_PARAMS = {"full": 33482412, "dora": 574560, "lora": 545280,
              "ia3": 11520, "headonly": 0}


def rows_by_arm() -> dict[str, dict[int, float]]:
    rows = [json.loads(l) for l in open(LEDGER) if l.strip()]
    out: dict[str, dict[int, float]] = collections.defaultdict(dict)
    for r in rows:
        if r.get("status") != "done" or r.get("smoke"):
            continue
        rid = r["run_id"]
        if "rinalmomicro_noncodingrnafamily_" not in rid:
            continue
        if r.get("seed") == 101:
            continue
        if "_random" not in rid:
            continue
        for arm in ARM_ORDER:
            tag = "_%s_" % arm if arm != "headonly" else "_headonly_"
            if tag in rid:
                if "_lr" in rid:
                    if arm == "full" and "_lr1e-05" in rid:
                        out[arm][r["seed"]] = float(r["value"])
                else:
                    out[arm].setdefault(r["seed"], float(r["value"]))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "status",
                                                  "e2_table.md"))
    args = ap.parse_args()
    arms = rows_by_arm()

    lines = ["# E2 PEFT 五臂横评（C5）— RiNALMo-micro, ncRNA-family, random",
             "",
             "协议：formal seeds 17/29/43；full = tuned-LR 协议臂（_lr1e-05"
             " 覆盖默认 3e-4 崩溃行）；PEFT 臂默认 LR 3e-4。",
             ""]
    header = ("| arm | 3-seed mean | seeds | per-seed | trainable "
              "(backbone) |")
    sep = "|---|---|---|---|---|"
    lines += [header, sep]
    ranked = sorted(
        ((arm, sum(v.values()) / len(v), v) for arm, v in arms.items()
         if v),
        key=lambda x: -x[1])
    for arm, mean, seeds in ranked:
        per_seed = ", ".join("s%d %.4f" % (sd, v)
                             for sd, v in sorted(seeds.items()))
        params = ARM_PARAMS.get(arm)
        p_str = ("33.5M" if params and params > 1e6
                 else ("~%.2fM" % (params / 1e6) if params
                       else "0"))
        lines.append("| %s | %.3f | %d | %s | %s + 16K head |"
                     % (ARM_LABEL.get(arm, arm), mean, len(seeds),
                        per_seed, p_str))
    lines += ["",
              "注：DoRA/LoRA 训练参数 ~0.55–0.57M（r=8, qkv+out）；IA3 "
              "11.5K；prefix-tuning 不可行（peft 0.13 / transformers 5.0 "
              "Cache API 不兼容，见 preprint limitations）。",
              "数据源：ledger.jsonl（自动导出，export_e2.py）。"]
    body = "\n".join(lines) + "\n"
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    open(args.out, "w").write(body)
    csv_path = os.path.splitext(args.out)[0] + ".csv"
    with open(csv_path, "w") as f:
        f.write("arm,mean,n_seeds,params_backbone\n")
        for arm, mean, _v in ranked:
            f.write("%s,%.4f,%d,%d\n" % (arm, mean, len(arms[arm]),
                                          ARM_PARAMS.get(arm, 0)))
    print(body)
    print("written:", args.out, "and", csv_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
