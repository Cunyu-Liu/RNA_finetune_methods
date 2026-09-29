"""plan need 标定器（0929，响应用户「显存必须被占满」）。

问题：q_fill plan 的 `need`（GB）多为保守圆整值（如 RNA-FM full 实测峰值 3.9GB 而 need=10）
→ 卡上剩余显存无法被利用。本脚本按 **ledger 实测 peak_mem_mb** 逐 (model, task, strategy)
重标定：need = max(3, ceil(peak_max × 1.3 / 1000) + 1)（1.3× 缓冲 + 1GB CUDA 上下文余量）。
无实测数据的 (model,task,strategy) 保持原值（不猜）。

用法: python scripts/calibrate_needs.py [--apply] plan.json [plan2.json ...]
（不带 --apply 仅打印 diff）
"""
from __future__ import annotations

import argparse
import collections
import json
import math
import os

ROOT = "/mnt/cunyuliu/rna-ft-eval"
LEDGER = os.path.join(ROOT, "ledger.jsonl")


def measured() -> dict:
    agg = collections.defaultdict(list)
    for l in open(LEDGER):
        l = l.strip()
        if not l:
            continue
        try:
            r = json.loads(l)
        except Exception:
            continue
        if r.get("status") == "done" and r.get("peak_mem_mb"):
            agg[(r.get("model"), r.get("task"), r.get("strategy"))].append(r["peak_mem_mb"])
    return {k: max(v) for k, v in agg.items()}


def need_for(peak):
    return max(3, math.ceil(peak * 1.3 / 1000.0) + 1)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("plans", nargs="+")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    meas = measured()
    for plan_path in args.plans:
        P = json.load(open(plan_path))
        diff = collections.Counter()
        for c in P["runs"]:
            key = (c["model"], c["task"], c["strategy"])
            peak = meas.get(key)
            old = c.get("need")
            if peak is None:
                diff[(key, old, old, "no-data")] += 1
                continue
            new = need_for(peak)
            c["need"] = new
            diff[(key, old, new, "%.1fGB peak" % (peak / 1000.0))] += 1
        print("==", os.path.basename(plan_path))
        for (key, old, new, why), n in sorted(diff.items()):
            flag = "KEEP" if old == new and why != "no-data" else ("NODATA" if why == "no-data" else "")
            print("   %-24s %-22s %-6s need %s -> %s  (%s) x%d %s" % (
                key[0], key[1], key[2], old, new, why, n, flag))
        if args.apply:
            json.dump(P, open(plan_path, "w"), indent=1, ensure_ascii=False)
            print("   APPLIED ->", plan_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())