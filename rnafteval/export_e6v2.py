"""E6-v2 任务起点差分导出器（C6 起点面普遍性；0927 派发）。

协议 E6-v2：{RNA-Sc-10M, RNA-Sc-30M, RiNALMo-micro} × {m6A 起点} × {lora, full@tuned} × 3 种子
（`artifacts/e6/<model>_<strategy>_task-m6a_s<seed>/result.json`）；
对照 = E6-v1 的 ncRNA 起点同 (模型, 策略, 种子) 格。
回答问题：「换任务起点，遗忘结论变吗？」→ per-base 起点（m6A）是否比 per-seq 起点（ncRNA）更轻。

判读纪律：未齐格 → [PENDING]；跨系 NLL 绝对值不可比，只看系内 ΔNLL 与差分。

用法: python -m rnafteval.export_e6v2 [--out status/e6v2_table.md]
"""
from __future__ import annotations

import argparse
import csv
import json
import os

ROOT = "/mnt/cunyuliu/rna-ft-eval"
ART = os.path.join(ROOT, "artifacts", "e6")
MODELS = ["RNA-Sc-10M", "RNA-Sc-30M", "RiNALMo-micro"]
STRATS = ["lora", "full"]
SEEDS = [17, 29, 43]


def collect() -> dict:
    """(model, strategy, tag) -> {seed: result}；tag = 'm6a' | 'ncrna'"""
    data = {}
    for d in sorted(os.listdir(ART)):
        f = os.path.join(ART, d, "result.json")
        if not os.path.isfile(f) or "_smoke" in d:
            continue
        try:
            r = json.load(open(f))
        except Exception:
            continue
        if r.get("model") not in MODELS:
            continue
        tag = "m6a" if "task-m6a" in d else "ncrna"
        data.setdefault((r["model"], r["strategy"], tag), {})[int(r["seed"])] = r
    return data


def fmt(v):
    return ("%+.3f" % v) if v is not None else "—"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "status", "e6v2_table.md"))
    args = ap.parse_args()
    data = collect()
    md = ["# E6-v2 任务起点差分（C6 起点面；自动导出）", "",
          "ΔNLL = post − pre（S0 held-out NLL, n=2000, 噪声带 ~1e-8）；正 = 遗忘。",
          "ncRNA 起点 = E6-v1 同模型同策略格；m6A 起点 = E6-v2（任务=modification）。",
          "差分 Δ(m6A) − Δ(ncRNA)：负 = per-base 起点遗忘更轻（标签密度稀释假说方向）。",
          "[PENDING] = 格未齐。", "",
          "| model | strategy | seed | Δ ncRNA-start | Δ m6A-start | diff |",
          "|---|---|---|---|---|---|"]
    csv_rows = [["model", "strategy", "seed", "delta_ncrna", "delta_m6a", "diff"]]
    for m in MODELS:
        for s in STRATS:
            for sd in SEEDS:
                a = data.get((m, s, "ncrna"), {}).get(sd)
                b = data.get((m, s, "m6a"), {}).get(sd)
                da = a["delta_nll"] if a else None
                db = b["delta_nll"] if b else None
                diff = (db - da) if (da is not None and db is not None) else None
                pend = " [PENDING]" if (da is None or db is None) else ""
                md.append("| %s | %s | %d | %s | %s | %s%s |" % (
                    m, s, sd, fmt(da), fmt(db), fmt(diff), pend))
                csv_rows.append([m, s, sd, da, db, diff])
    # 汇总：每 (model, strategy) 的均值
    md += ["", "## 3 种子均值", "",
           "| model | strategy | mean Δ ncRNA | mean Δ m6A | mean diff | n |",
           "|---|---|---|---|---|---|"]
    for m in MODELS:
        for s in STRATS:
            aa = [data.get((m, s, "ncrna"), {}).get(sd) for sd in SEEDS]
            bb = [data.get((m, s, "m6a"), {}).get(sd) for sd in SEEDS]
            aa = [x["delta_nll"] for x in aa if x]
            bb = [x["delta_nll"] for x in bb if x]
            ma = sum(aa) / len(aa) if aa else None
            mb = sum(bb) / len(bb) if bb else None
            md.append("| %s | %s | %s | %s | %s | %d/%d |" % (
                m, s, fmt(ma), fmt(mb),
                fmt((mb - ma) if (ma is not None and mb is not None) else None),
                len(aa), len(bb)))
    with open(args.out, "w") as fh:
        fh.write("\n".join(md) + "\n")
    with open(args.out.replace(".md", ".csv"), "w", newline="") as fh:
        csv.writer(fh).writerows(csv_rows)
    print("wrote", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())