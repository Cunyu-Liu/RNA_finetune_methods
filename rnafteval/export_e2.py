"""Export E2 PEFT horizontal-comparison table (C5) — dual-model,
dual-task.

Ledger -> markdown + CSV. Panels: {RiNALMo-micro, RNA-Sc-10M} ×
{ncRNA (per-seq), m6A (per-base)} — five arms (head-only where run),
formal seeds 17/29/43.

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
ARM_LABEL = {"full": "full FT (LR-tuned)", "dora": "DoRA r=8",
             "lora": "LoRA r=8", "ia3": "IA3",
             "headonly": "head-only"}
ARM_PARAMS = {"full": None, "dora": 574560, "lora": 545280,
              "ia3": 11520, "headonly": 0}
# 每模型 full 的 backbone 参数量（ncRNA 与 m6A 同模型同参）
FULL_BASE = {"rinalmomicro": "33.5M", "rnasc10m": "10M"}
PANELS = [
    ("rinalmomicro", "noncoding-rna-family", "RiNALMo-micro (33M), ncRNA", "33.5M"),
    ("rnasc10m", "noncoding-rna-family", "RNA-Sc-10M (10M, controlled), ncRNA", "10M"),
    ("rinalmomicro", "modification", "RiNALMo-micro (33M), m6A (per-base)", "33.5M"),
    ("rnasc10m", "secondary-structure", "RNA-Sc-10M (10M, controlled), SSP (per-base)", "10M"),
]


def rows_by_arm(model: str, task: str) -> dict:
    rows = [json.loads(l) for l in open(LEDGER) if l.strip()]
    out = collections.defaultdict(dict)
    for r in rows:
        if r.get("status") != "done" or r.get("smoke"):
            continue
        # model 用 run_id 前缀匹配（ledger model 字段为显示名）
        if not r["run_id"].startswith("ft_%s_" % model):
            continue
        if r["task"] != task:
            continue
        if r.get("seed") == 101 or "_e3" in r["run_id"]:
            continue
        if r["split"] != "random":
            continue
        for arm in ARM_ORDER:
            tag = "_%s_" % arm if arm != "headonly" else "_headonly_"
            if tag in r["run_id"]:
                if "_lr" in r["run_id"]:
                    # tuned 协议臂: full 的 _lr 行覆盖（RiNALMo ncrna/m6A
                    # 均为 1e-05; RNA-Sc 无 _lr 行——默认 LR 正常）
                    if arm == "full":
                        out[arm][r["seed"]] = float(r["value"])
                else:
                    out[arm].setdefault(r["seed"], float(r["value"]))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "status",
                                                  "e2_table.md"))
    args = ap.parse_args()
    lines = []
    csv_rows = []
    for model, task, plabel, pbase in PANELS:
        arms = rows_by_arm(model, task)
        if not any(arms.get(a) for a in ARM_ORDER):
            continue
        lines += [
            "# E2 PEFT 五臂横评（C5）— %s" % plabel,
            "",
            "协议：formal seeds 17/29/43；random 切分；full = tuned 协议臂"
            "（_lr 覆盖, RNA-Sc 为默认 LR——A8 网格下正常）；PEFT 臂默认"
            " LR 3e-4。head-only 若未单独跑则缺（= frozen 代码路径）。",
            "",
            "| arm | 3-seed mean | seeds | per-seed |"
            " trainable (backbone) |",
            "|---|---|---|---|---|",
        ]
        ranked = sorted(
            ((arm, sum(v.values()) / len(v), v) for arm, v in arms.items()
             if v), key=lambda x: -x[1])
        for arm, mean, seeds in ranked:
            per_seed = ", ".join("s%d %.4f" % (sd, v)
                                 for sd, v in sorted(seeds.items()))
            if arm == "full":
                p_str = pbase
            else:
                params = ARM_PARAMS[arm]
                p_str = ("~%.2fM" % (params / 1e6)) if params else "0"
            lines.append("| %s | %.3f | %d | %s | %s + head |"
                         % (ARM_LABEL.get(arm, arm), mean, len(seeds),
                            per_seed, p_str))
            csv_rows.append((model, task, arm, mean, len(seeds)))
        lines += ["",
                  "注：DoRA/LoRA ~0.55–0.57M（r=8, qkv+out）；IA3 11.5K；"
                  "prefix-tuning 不可行（peft 0.13 / transformers 5.0 "
                  "Cache API 不兼容，见 preprint limitations）。",
                  "数据源：ledger.jsonl（自动导出，export_e2.py）。",
                  ""]
    body = "\n".join(lines) + "\n"
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    open(args.out, "w").write(body)
    csv_path = os.path.splitext(args.out)[0] + ".csv"
    with open(csv_path, "w") as f:
        f.write("model,task,arm,mean,n_seeds\n")
        for model, task, arm, mean, n in csv_rows:
            f.write("%s,%s,%s,%.4f,%d\n" % (model, task, arm, mean, n))
    print(body)
    print("written:", args.out, "and", csv_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
