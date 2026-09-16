"""A8 LR 网格表自动导出（seed 101 tuning runs）。

ledger 的 *_s101_*lr* 行 -> markdown + CSV。网格: 模型 × 策略 ×
LR（1e-5/3e-5/1e-4/3e-4）@ tuning seed 101, RiNALMo/ncRNA +
RiNALMo-micro m6A/SSP + RNA-Sc/ncRNA 复现任务。含 default-LR
(3e-4 无 _lr 后缀) 行以对齐网格左端。

用法: python -m rnafteval.export_lr_grid [--out status/lr_grid_table.md]
"""
from __future__ import annotations

import argparse
import json
import os

ROOT = "/mnt/cunyuliu/rna-ft-eval"
LEDGER = os.path.join(ROOT, "ledger.jsonl")
LRS = ["1e-05", "3e-05", "0.0001", "0.0003"]
LR_LABEL = {"1e-05": "1e-5", "3e-05": "3e-5",
            "0.0001": "1e-4", "0.0003": "3e-4 (default)"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "status",
                                                  "lr_grid_table.md"))
    args = ap.parse_args()
    rows = [json.loads(l) for l in open(LEDGER) if l.strip()]
    def lr_norm(x):
        if x is None:
            return None
        for l in LRS:
            if abs(float(x) - float(l)) < 1e-12:
                return l
        return None

    grid = {}
    for r in rows:
        if r.get("status") != "done" or r.get("smoke"):
            continue
        if r.get("seed") != 101:
            continue
        rid = r["run_id"]
        if "ncodingrnafamily" not in rid:
            continue
        model = r["model"]
        strat = r["strategy"]
        key = (model, strat)
        lk = lr_norm(r.get("lr"))
        if lk:
            grid.setdefault(key, {})[lk] = float(r["value"])

    lines = ["# A8 LR 网格（tuning seed 101, ncRNA, 自动导出）", "",
             "协议：每（模型×策略）4 点网格；formal 种子(17/29/43)在"
             "选定的 LR 上重跑。3e-4 为管线默认。", "",
             "| model | strategy | " + " | ".join(
                 LR_LABEL[l] for l in LRS) + " |",
             "|---|---|" + "---|" * len(LRS)]
    for (model, strat) in sorted(grid):
        cells = []
        for l in LRS:
            v = grid[(model, strat)].get(l)
            cells.append("%.3f" % v if v is not None else "—")
        lines.append("| %s | %s | %s |" % (model, strat,
                                           " | ".join(cells)))

    body = "\n".join(lines) + "\n"
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    open(args.out, "w").write(body)
    csv_path = os.path.splitext(args.out)[0] + ".csv"
    with open(csv_path, "w") as f:
        f.write("model,strategy,lr,value\n")
        for (model, strat) in sorted(grid):
            for l, v in sorted(grid[(model, strat)].items()):
                f.write("%s,%s,%s,%.4f\n" % (model, strat, l, v))
    print(body)
    print("written:", args.out, "and", csv_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
