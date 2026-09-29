"""E6-v3 跨任务保持度导出器（C6 v2 扩展；probe-style，0927 派发）。

协议 E6-v3：{RNA-Sc-10M, RNA-Sc-30M, RiNALMo-micro} × {lora, full@tuned} × 3 种子；
每个 run = ncRNA 微调(10 ep)前后各做 m6A/MRL/SSP probe（头 2k 样本/1 epoch），
retention = post_probe / pre_probe（每任务每格）。

诚实口径（写作期强制）：probe 头 2k/1ep 是**表征可迁移性近似**（≠ 完整微调性能），
表述一律用「probe-style retention」；未齐格 → [PENDING]。

用法: python -m rnafteval.export_e6v3 [--out status/e6v3_table.md]
"""
from __future__ import annotations

import argparse
import csv
import json
import os

ROOT = "/mnt/cunyuliu/rna-ft-eval"
ART = os.path.join(ROOT, "artifacts", "e6ret")
MODELS = ["RNA-Sc-10M", "RNA-Sc-30M", "RiNALMo-micro"]
STRATS = ["lora", "full"]
SEEDS = [17, 29, 43]
TASKS = ["modification", "mrl", "secondary-structure"]


def collect() -> dict:
    data = {}
    if not os.path.isdir(ART):
        return data
    for d in sorted(os.listdir(ART)):
        f = os.path.join(ART, d, "result.json")
        if not os.path.isfile(f):
            continue
        try:
            r = json.load(open(f))
        except Exception:
            continue
        data.setdefault((r["model"], r["strategy"]), {})[int(r["seed"])] = r
    return data


def fmt(v):
    return ("%.3f" % v) if v is not None else "—"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "status", "e6v3_table.md"))
    args = ap.parse_args()
    data = collect()
    md = ["# E6-v3 跨任务保持度（probe-style；自动导出）", "",
          "retention = post_probe / pre_probe（ncRNA 微调前后；probe 头 2k/1ep 轻量口径——",
          "表征可迁移性近似，表述不得写成完整微调性能）。>1 = 反升；≈0 = 保持度崩塌。",
          "[PENDING] = 格未齐。", "",
          "| model | strategy | seed | retention m6A | retention MRL | retention SSP |",
          "|---|---|---|---|---|---|"]
    csv_rows = [["model", "strategy", "seed", "ret_modification", "ret_mrl", "ret_ssp"]]
    for m in MODELS:
        for s in STRATS:
            for sd in SEEDS:
                r = data.get((m, s), {}).get(sd)
                ret = (r or {}).get("retention", {})
                vals = [ret.get(t) for t in TASKS]
                pend = " [PENDING]" if r is None else ""
                md.append("| %s | %s | %d | %s | %s | %s%s |" % (
                    m, s, sd, *[fmt(v) for v in vals], pend))
                csv_rows.append([m, s, sd] + vals)
    md += ["", "## 3 种子均值（每任务）", "",
           "| model | strategy | m6A (n) | MRL (n) | SSP (n) |", "|---|---|---|---|---|"]
    for m in MODELS:
        for s in STRATS:
            cells = []
            for t in TASKS:
                vs = []
                for sd in SEEDS:
                    r = data.get((m, s), {}).get(sd)
                    if r and r.get("retention", {}).get(t) is not None:
                        vs.append(r["retention"][t])
                cells.append("%s (%d/3)" % (fmt(sum(vs) / len(vs)) if vs else "—", len(vs)))
            md.append("| %s | %s | %s | %s | %s |" % (m, s, *cells))
    with open(args.out, "w") as fh:
        fh.write("\n".join(md) + "\n")
    with open(args.out.replace(".md", ".csv"), "w", newline="") as fh:
        csv.writer(fh).writerows(csv_rows)
    print("wrote", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())