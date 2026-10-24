"""E6 official corrected fixed-mask MLM spectrum exporter.

Only `_mlm15fix` results with the E6-v1-fixed-mask-mlm protocol are eligible.
Legacy unmasked/full-context results are excluded even if their files remain.
Rows are grouped by model, strategy and LR, and never silently mixed.

用法: python -m rnafteval.export_e6_official [--out status/e6_official_table.md]
"""
from __future__ import annotations

import argparse
import csv
import json
import os

ROOT = "/root/rna-ft-eval"
ART = os.path.join(ROOT, "artifacts", "e6")
MODELS = ["RiNALMo-micro", "RiNALMo-mega", "RiNALMo-650M", "ERNIE-RNA", "RNA-FM"]
STRATS = ["lora", "full"]
SEEDS = [17, 29, 43]


def collect() -> dict:
    """(model, strategy, lr) -> {seed: result}"""
    data = {}
    if not os.path.isdir(ART):
        return data
    for d in sorted(os.listdir(ART)):
        f = os.path.join(ART, d, "result.json")
        if not os.path.isfile(f) or "_smoke" in d:
            continue
        try:
            r = json.load(open(f))
        except Exception:
            continue
        if r.get("model") not in MODELS or r.get("strategy") not in STRATS:
            continue
        if r.get("task") == "modification":
            continue
        if not ("_mlm15fix" in r.get("run_id", "")
                and str(r.get("protocol", "")).startswith("E6-v1-fixed-mask-mlm")
                and r.get("mask_rate") == 0.15):
            continue
        try:
            lr = float(r.get("lr"))
        except Exception:
            continue
        data.setdefault((r["model"], r["strategy"], lr), {})[int(r["seed"])] = r
    return data


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "status", "e6_official_table.md"))
    args = ap.parse_args()
    data = collect()
    md = ["# E6 官方系遗忘谱线（5 模型；fixed-mask corrected；自动导出）", "",
          "ΔNLL = post − pre（S0 held-out, n=2000）。仅纳入 `_mlm15fix`：固定 15% masked-position MLM NLL + 独立掩码/顺序重评差异。",
          "旧 MLM 全上下文结果已隔离；跨协议绝对 NLL 不可比。",
          "lr 分组并列（不同 LR 不混用；P4 决策口径）。",
          "[PENDING] = 3 种子未齐。", "",
          "| model | strategy | lr | Δ s17 | Δ s29 | Δ s43 | mean | n/3 | forgot |",
          "|---|---|---|---|---|---|---|---|---|"]
    csv_rows = [["model", "strategy", "lr", "d17", "d29", "d43", "mean", "n", "forgot"]]
    for m in MODELS:
        keys = sorted([k for k in data if k[0] == m], key=lambda k: (k[1], k[2]))
        if not keys:
            for s in STRATS:
                md.append("| %s | %s | — | — | — | — | — | 0/3 | [PENDING] |" % (m, s))
                csv_rows.append([m, s, None, None, None, None, None, 0, "PENDING"])
            continue
        for (mm, s, lr) in keys:
            dd = data[(mm, s, lr)]
            vals = [dd[sd]["delta_nll"] for sd in SEEDS if sd in dd]
            mean = sum(vals) / len(vals) if vals else None
            forgot = sum(1 for sd in SEEDS if sd in dd and dd[sd].get("forgot"))
            f = lambda v: ("%+.3f" % v) if v is not None else "—"
            lr_s = ("%.0e" % lr)
            pend = " [PENDING]" if len(vals) < 3 else ""
            row = [mmm for mmm in [f(dd[sd]["delta_nll"]) if sd in dd else "—" for sd in SEEDS]]
            md.append("| %s | %s | %s | %s | %s | %s | %s | %d/3 | %d%s |" % (
                mm, s, lr_s, row[0], row[1], row[2], f(mean), len(vals), forgot, pend))
            csv_rows.append([mm, s, lr] + [dd[sd]["delta_nll"] if sd in dd else None for sd in SEEDS]
                            + [mean, len(vals), forgot])
    with open(args.out, "w") as fh:
        fh.write("\n".join(md) + "\n")
    with open(args.out.replace(".md", ".csv"), "w", newline="") as fh:
        csv.writer(fh).writerows(csv_rows)
    print("wrote", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())