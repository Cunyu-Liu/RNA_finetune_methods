"""E3 小数据矩阵导出器（C3 数据源）。

ledger _e3 标签行 + 全量 family 正式行 → markdown/CSV。
每（模型×档×策略）：3 种子均值、min-max、最优标记。

用法: python -m rnafteval.export_e3 [--out status/e3_table.md]
"""
from __future__ import annotations

import argparse
import collections
import json
import os

ROOT = "/mnt/cunyuliu/rna-ft-eval"
FULL_N = 6859
ORDER = ["rinalmomicro", "rnasc10m"]
MODEL_LABEL = {"rinalmomicro": "RiNALMo-micro", "rnasc10m": "RNA-Sc-10M"}


def cells() -> dict:
    rows = [json.loads(l) for l in open(os.path.join(
        ROOT, "ledger.jsonl")) if l.strip()]
    data = collections.defaultdict(dict)
    for r in rows:
        if r.get("status") != "done" or r.get("smoke"):
            continue
        rid = r["run_id"]
        if "noncodingrnafamily" not in rid:
            continue
        parts = rid.split("_")
        model, strat, seed = parts[1], parts[3], parts[4][1:]
        if "_e3" in rid:
            n = int(rid.rsplit("_e3", 1)[1])
            data[(model, n, strat)][seed] = float(r["value"])
        elif (r.get("seed") in (17, 29, 43) and rid.endswith("_family")
              and "_lr" not in rid):
            data[(model, FULL_N, strat)][seed] = float(r["value"])
    return data


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "status",
                                                  "e3_table.md"))
    args = ap.parse_args()
    data = cells()
    lines = ["# E3 小数据矩阵（C3 数据源，自动导出）", "",
             "协议：簇级降采样（e3_subsampler, 抽簇→整簇）；",
             "family 切分；3 种子；full=6859 全量。full-FT 小数据档",
             "为默认 LR（A8 崩溃口径，非数据量效应）。", "",
             "| model | n | frozen | lora | full | 最优 |",
             "|---|---|---|---|---|---|"]
    for model in ORDER:
        for n in [10, 100, 1000, FULL_N]:
            row = {"frozen": None, "lora": None, "full": None}
            complete = True
            for strat in row:
                d = data.get((model, n, strat), {})
                if d and len(d) >= 3:
                    row[strat] = sum(d.values()) / len(d)
                else:
                    complete = False
            if not any(v is not None for v in row.values()):
                continue
            cells_str = []
            for strat in ["frozen", "lora", "full"]:
                v = row[strat]
                cells_str.append("%.3f" % v if v is not None else "—")
            best = ""
            if complete:
                b = max(row, key=lambda k: row[k])
                best = "**%s**" % b
            lines.append("| %s | %d | %s | %s |" % (
                MODEL_LABEL.get(model, model), n,
                " | ".join(cells_str), best))
    lines += ["",
              "数据源：ledger.jsonl（_e3 标签行 + 全量 family 行；",
              "自动导出，export_e3.py）。"]
    body = "\n".join(lines) + "\n"
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    open(args.out, "w").write(body)
    csv_path = os.path.splitext(args.out)[0] + ".csv"
    with open(csv_path, "w") as f:
        f.write("model,n,strategy,mean,min,max,n_seeds\n")
        for (model, n, strat), d in sorted(data.items()):
            if d:
                vals = list(d.values())
                f.write("%s,%d,%s,%.4f,%.4f,%.4f,%d\n" % (
                    model, n, strat, sum(vals) / len(vals),
                    min(vals), max(vals), len(vals)))
    print(body)
    print("written:", args.out, "and", csv_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
