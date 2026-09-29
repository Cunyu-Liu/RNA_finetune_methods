"""C4 崩溃时间轴导出器（A8 机制故事；0927 派发）。

协议：{RiNALMo-micro, ERNIE-RNA, SpliceBERT, RNA-Sc-10M, RNA-Sc-30M} × {lora, full@默认LR}
× s17 × family 切分——逐 epoch 记录 family 测试 acc，回答「崩在第几个 epoch」。

判读纪律：timeline_acc[0] = 微调前（起点）；ep1 = timeline_acc[1]。
「崩溃在第 1 epoch 内完成」判据：ep1 ≤ 起点（不升反降，与 diag_a8 的秩坍缩时间尺度互证）。
未落地 → [PENDING]。

用法: python -m rnafteval.export_collapse [--out status/collapse_table.md]
"""
from __future__ import annotations

import argparse
import csv
import json
import os

ROOT = "/mnt/cunyuliu/rna-ft-eval"
ART = os.path.join(ROOT, "artifacts", "collapse_tl")
MODELS = ["RiNALMo-micro", "ERNIE-RNA", "SpliceBERT", "RNA-Sc-10M", "RNA-Sc-30M"]
STRATS = ["lora", "full"]


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
        if r.get("model") in MODELS:
            data[(r["model"], r["strategy"])] = r
    return data


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "status", "collapse_table.md"))
    args = ap.parse_args()
    data = collect()
    md = ["# C4 崩溃时间轴（family 切分，逐 epoch acc；自动导出）", "",
          "timeline[0] = 微调前起点；epoch1 = 第一个 epoch 末。",
          "判据：ep1 ≤ 起点 → 崩溃在第 1 epoch 内完成（无「先涨后崩」轨迹）。",
          "[PENDING] = 未落地。", "",
          "| model | strategy | init | ep1 | ep2 | ep3 | min | max | ep1/init | verdict |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    csv_rows = [["model", "strategy", "init", "ep1", "ep2", "ep3", "min", "max", "ratio_ep1_init", "verdict"]]
    for m in MODELS:
        for s in STRATS:
            r = data.get((m, s))
            if r is None:
                md.append("| %s | %s | — | — | — | — | — | — | — | [PENDING] |" % (m, s))
                csv_rows.append([m, s] + [None] * 8 + ["PENDING"])
                continue
            tl = r.get("timeline_acc") or []
            init = tl[0] if len(tl) > 0 else None
            ep1 = tl[1] if len(tl) > 1 else None
            ratio = (ep1 / init) if (init and ep1 is not None) else None
            verdict = "collapse-in-ep1" if (ratio is not None and ratio <= 1.0) else "rising"
            f = lambda v: ("%.3f" % v) if v is not None else "—"
            md.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
                m, s, f(init), f(ep1), f(tl[2] if len(tl) > 2 else None),
                f(tl[3] if len(tl) > 3 else None), f(min(tl) if tl else None),
                f(max(tl) if tl else None),
                ("%.2f" % ratio) if ratio is not None else "—", verdict))
            csv_rows.append([m, s, init, ep1, tl[2] if len(tl) > 2 else None,
                             tl[3] if len(tl) > 3 else None, min(tl) if tl else None,
                             max(tl) if tl else None, ratio, verdict])
    with open(args.out, "w") as fh:
        fh.write("\n".join(md) + "\n")
    with open(args.out.replace(".md", ".csv"), "w", newline="") as fh:
        csv.writer(fh).writerows(csv_rows)
    print("wrote", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())