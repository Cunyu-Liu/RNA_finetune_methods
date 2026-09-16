"""E5 资源实测摘要（B6/S7 支撑）——ledger -> 按策略汇总表。

对齐 Schmirler Fig.5 协议口径：每策略的 wall-clock 中位数、峰值显存
中位数、检查点体积（mean）、每 run 均值。只统计 done 且非 smoke 的
formal 行（tuning seed 101 单独一档，不与 formal 混）。

用法: python -m rnafteval.export_resources [--out status/resources.md]
"""
from __future__ import annotations

import argparse
import json
import os
import statistics

ROOT = "/mnt/cunyuliu/rna-ft-eval"
LEDGER = os.path.join(ROOT, "ledger.jsonl")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "status",
                                                  "resources.md"))
    args = ap.parse_args()
    rows = [json.loads(l) for l in open(LEDGER) if l.strip()]
    formal = [r for r in rows if r.get("status") == "done"
              and not r.get("smoke")]
    tuning = [r for r in formal if r.get("seed") == 101]
    formal = [r for r in formal if r.get("seed") != 101]

    def agg(pool, label):
        by_s = {}
        for r in pool:
            s = r.get("strategy")
            if s not in by_s:
                by_s[s] = []
            by_s[s].append(r)
        out = []
        for s, rs in sorted(by_s.items()):
            walls = [r["wall_sec"] for r in rs if r.get("wall_sec")]
            peaks = [r["peak_mem_mb"] for r in rs
                     if r.get("peak_mem_mb")]
            ckpts = [r["ckpt_bytes"] for r in rs if r.get("ckpt_bytes")]
            row = {
                "strategy": s, "n": len(rs), "pool": label,
                "wall_med": statistics.median(walls) if walls else None,
                "wall_max": max(walls) if walls else None,
                "peak_med": statistics.median(peaks) if peaks else None,
                "peak_max": max(peaks) if peaks else None,
                "ckpt_mean": (sum(ckpts) / len(ckpts)) if ckpts else None,
            }
            out.append(row)
        return out

    table_rows = agg(formal, "formal") + agg(tuning, "tuning(101)")

    lines = ["# E5 资源实测摘要（自动导出）", "",
             "口径：done 且非 smoke；formal（17/29/43）与 tuning（101）"
             "分池；wall/peak 为中位数（跨模型混合，模型差异见逐 run "
             "ledger）。", "",
             "| pool | strategy | n | wall med (min) | wall max (min) | "
             "peak mem med (MB) | peak max (MB) | ckpt mean (MB) |",
             "|---|---|---|---|---|---|---|---|"]
    for t in table_rows:
        def f(v, k=1.0):
            return ("%.1f" % (v / k)) if v is not None else "—"
        lines.append(
            "| %s | %s | %d | %s | %s | %s | %s | %s |" % (
                t["pool"], t["strategy"], t["n"],
                f(t["wall_med"], 60), f(t["wall_max"], 60),
                f(t["peak_med"]), f(t["peak_max"]),
                f(t["ckpt_mean"], 1024 * 1024)))
    lines += ["",
              "覆盖：wall_sec/peak_mem_mb 字段覆盖率 = %d/%d（formal+"
              "tuning done）" % (
                  sum(1 for r in formal + tuning if r.get("wall_sec")
                      and r.get("peak_mem_mb")),
                  len(formal) + len(tuning)),
              "数据源：ledger.jsonl（run 级，含 device/peak/wall 全字段）。",
              "用途：S7（Supp）；策略成本侧写正文 Methods 摘引。"]

    body = "\n".join(lines) + "\n"
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    open(args.out, "w").write(body)
    print(body)
    print("written:", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
