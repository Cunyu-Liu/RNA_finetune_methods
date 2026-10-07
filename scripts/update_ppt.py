#!/usr/bin/env python3
"""update_ppt.py — PPT 数据表程序化生成（纪律 ③：禁止手抄数字）。

数据源（唯一口径）：服务器 /mnt/cunyuliu/rna-ft-eval/status/*.csv
  - c4_table.csv   : Δ(random-family) 主表（PPT slide3 表A/表B 源）
  - e2_table.csv   : PEFT 五臂（PPT slide5 源）
  - e6_table.csv   : 遗忘矩阵（PPT slide6 源）

用法:
  python3 update_ppt.py --csv-dir <status csv 目录> --out <输出 md/json>
产出:
  1) <out>.md   : 各 slide 表格的 markdown 渲染（可直接粘贴/比对 PPT）
  2) <out>.json : 与 PPT 逐格比对的期望值字典（lint 用）
"""
import argparse
import csv
import json
import os
import sys


def load(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def fmt(v, nd=3):
    try:
        return ("%.3f" % float(v))
    except (TypeError, ValueError):
        return str(v)


def slide3_tables(c4):
    """表A: 17 架构 ncRNA random/family 三策略；表B: m6A per-base 免疫。"""
    models = ["RNA-Sc-10M", "RiNALMo-micro", "SpliceBERT", "ERNIE-RNA", "RNA-FM",
              "UTR-LM", "mRNABERT", "NucleicBERT", "AIDO.RNA-1.6B", "RiboSpan-1K-40",
              "HydraRNA", "RiNALMo-mega", "RiNALMo-650M", "RNA-Sc-1M", "RNA-Sc-30M",
              "RNA-Sc-100M", "RNA-Sc-650M"]
    idx = {}
    for r in c4:
        idx[(r["model"], r["task"], r["strategy"])] = r
    lines = ["## slide3 表A — ncRNA random→family（3-seed mean）", "",
             "| model | frozen R/F | lora R/F | full R/F |", "|---|---|---|---|"]
    for m in models:
        cells = []
        for s in ("frozen", "lora", "full"):
            r = idx.get((m, "noncoding-rna-family", s))
            cells.append(f"{fmt(r['random_mean'])} / {fmt(r['family_mean'])}" if r else "—")
        lines.append(f"| {m} | {cells[0]} | {cells[1]} | {cells[2]} |")
    lines += ["", "## slide3 表B — m6A per-base 免疫（LoRA R/F）", "",
              "| model | LoRA random | LoRA family | ratio |", "|---|---|---|---|"]
    for m in models:
        r = idx.get((m, "modification", "lora"))
        if r and float(r["random_mean"] or 0) > 0:
            ratio = float(r["family_mean"]) / float(r["random_mean"])
            lines.append(f"| {m} | {fmt(r['random_mean'])} | {fmt(r['family_mean'])} | {ratio:.3f} |")
    return lines


def slide5_table(e2_dir):
    return ["## slide5 — E2 五臂（源：e2_table.md 自动导出，直接引用）",
            "", "（e2 为 markdown 导出；数值以 status/e2_table.md 为准，禁止手抄）"]


def slide6_table(e6):
    lines = ["## slide6 — E6 遗忘矩阵（ΔNLL per seed, lora/full）", "",
             "| model | Δlora s17/s29/s43 | Δfull s17/s29/s43 |", "|---|---|---|"]
    for r in e6:
        d = [r.get(k, "—") for k in ("d_lora_s17", "d_lora_s29", "d_lora_s43",
                                      "d_full_s17", "d_full_s29", "d_full_s43")]
        if all(x == "—" for x in d):
            continue
        lines.append(f"| {r.get('model','?')} | {'/'.join(str(x) for x in d[:3])} | "
                     f"{'/'.join(str(x) for x in d[3:])} |")
    return lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv-dir", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    c4 = load(os.path.join(a.csv_dir, "c4_table.csv"))
    parts = ["# PPT 数据表（程序化生成 2026-10-07）", ""]
    parts += slide3_tables(c4)
    parts += [""] + slide5_table(a.csv_dir)
    e6p = os.path.join(a.csv_dir, "e6_table.csv")
    if os.path.exists(e6p):
        parts += [""] + slide6_table(load(e6p))
    md = "\n".join(parts) + "\n"
    with open(a.out + ".md", "w", encoding="utf-8") as f:
        f.write(md)
    idx = {"|".join((r["model"], r["task"], r["strategy"])):
           {"random": r["random_mean"], "family": r["family_mean"], "n": r["n_random"]}
           for r in c4}
    with open(a.out + ".json", "w", encoding="utf-8") as f:
        json.dump(idx, f, ensure_ascii=False, indent=1)
    print("wrote %s.md (+%d c4 rows) and %s.json" % (a.out, len(c4), a.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
