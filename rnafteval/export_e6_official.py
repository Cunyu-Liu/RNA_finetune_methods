"""E6 官方系谱线导出器（C6 官方线扩展：micro/mega/650M × {lora, full}；0928-29 补位数据）。

数据源：artifacts/e6/<model>_<strategy>_s<seed>[_lr3e-04]/result.json（以 result.json 的 lr 字段分组，
不靠目录名解析）。official 系全部 MLM 全上下文口径（基线 ~0.06-0.09）——跨系绝对值不可比，
只看系内 ΔNLL 与随规模趋势。

协议注记（P4 决策项）：mega lora 历史格为 lr=1e-5（与 micro/受控系 lora@3e-4 不一致），
0929 已补 `_lr3e-04` 对照 3 格——本表按 lr 分组并列，切换口径与否由 P4 决策，不静默混用。

用法: python -m rnafteval.export_e6_official [--out status/e6_official_table.md]
"""
from __future__ import annotations

import argparse
import csv
import json
import os

ROOT = "/mnt/cunyuliu/rna-ft-eval"
ART = os.path.join(ROOT, "artifacts", "e6")
MODELS = ["RiNALMo-micro", "RiNALMo-mega", "RiNALMo-650M"]
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
    md = ["# E6 官方系遗忘谱线（micro / mega / 650M；自动导出）", "",
          "ΔNLL = post − pre（S0 held-out, n=2000, MLM 全上下文口径，噪声带 ~1e-9~1e-8）。",
          "契约：official 系逐尺度谱线（micro→mega→650M）——遗忘随规模的变化方向。",
          "lr 分组并列（mega lora 的 1e-5 历史格与 3e-4 对照格不混用；P4 决策口径）。",
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