"""E6 灾难性遗忘矩阵导出器（C6 数据源）。

artifacts/e6/*/result.json（_smoke 标签过滤）→ markdown/CSV。
每（模型×策略）：3 种子 ΔNLL 均值±min-max、遗忘判定格数；末列 full/lora
遗忘倍率 = mean ΔNLL(full) / mean ΔNLL(lora)（正=full 遗忘更重）。

用法: python -m rnafteval.export_e6 [--out status/e6_table.md]
"""
from __future__ import annotations

import argparse
import json
import os
import re

ROOT = "/mnt/cunyuliu/rna-ft-eval"
ART = os.path.join(ROOT, "artifacts", "e6")
ORDER = ["RNA-Sc-10M", "RNA-Sc-30M", "RNA-Sc-100M", "RiNALMo-micro"]
LABEL = {"RNA-Sc-10M": "RNA-Sc-10M", "RNA-Sc-30M": "RNA-Sc-30M",
         "RNA-Sc-100M": "RNA-Sc-100M", "RiNALMo-micro": "RiNALMo-micro (official)"}
# controlled 系 NLL 为因果口径（非均匀基线 ~4.5），official 为 MLM 全上下文
# 口径（基线 ~0.09）——绝对值跨系不可比，判读只看系内 ΔNLL 与倍率。
CALENDAR = {"RNA-Sc-10M": "causal", "RNA-Sc-30M": "causal",
            "RNA-Sc-100M": "causal", "RiNALMo-micro": "mlm-full-context"}


def collect() -> dict:
    """[(model, strategy)] -> {seed: result}"""
    data = {}
    for d in sorted(os.listdir(ART)):
        f = os.path.join(ART, d, "result.json")
        if not os.path.isfile(f):
            continue
        if "_smoke" in d:
            continue
        try:
            r = json.load(open(f))
        except Exception:
            continue
        m, s, seed = r["model"], r["strategy"], int(r["seed"])
        if m not in ORDER or s not in ("lora", "full"):
            continue
        data.setdefault((m, s), {})[seed] = r
    return data


def fmt(v):
    return ("%+.3f" % v) if v is not None else "—"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "status",
                                                  "e6_table.md"))
    args = ap.parse_args()
    data = collect()
    lines = ["# E6 灾难性遗忘矩阵（C6 数据源，自动导出）", "",
             "协议 E6-v1：ncRNA-family 微调（tuned-LR, 10 ep）前后 S0 held-out",
             "NLL（test+family_test, n=2000）+ 重排噪声带（~1e-8, 所有格显著）。",
             "controlled 系 = 因果 NLL（基线 ~4.5）；official = MLM 全上下文",
             "（基线 ~0.09）。ΔNLL = post − pre；正 = 遗忘，负 = 反向增益。",
             "forget_ratio = mean ΔNLL(full) / mean ΔNLL(lora)（系内）。", "",
             "| model | pre NLL | Δ lora | Δ full | forget_ratio | n(l/f) | lora forgot | full forgot |",
             "|---|---|---|---|---|---|---|---|"]
    for m in ORDER:
        dl = data.get((m, "lora"), {})
        df = data.get((m, "full"), {})
        if not dl and not df:
            continue
        pre = [r["pre_nll_a"] for r in dl.values()] or \
              [r["pre_nll_a"] for r in df.values()]
        pre_v = sum(pre) / len(pre) if pre else None
        dl_v = [r["delta_nll"] for r in dl.values()]
        df_v = [r["delta_nll"] for r in df.values()]
        l_mean = sum(dl_v) / len(dl_v) if dl_v else None
        f_mean = sum(df_v) / len(df_v) if df_v else None
        if l_mean is not None and f_mean is not None and abs(l_mean) > 1e-6:
            ratio = f_mean / l_mean
            ratio_s = "%+.2f×" % ratio
        else:
            ratio_s = "—"
        fl = "%d/%d" % (sum(1 for r in dl.values() if r["forgot"]),
                        sum(1 for r in df.values() if r["forgot"]))
        lines.append("| %s | %.4f | %s | %s | %s | %d/%d | %s | %s |" % (
            LABEL[m], pre_v,
            fmt(l_mean), fmt(f_mean), ratio_s, len(dl), len(df),
            "/".join(("Y" if r["forgot"] else "n")
                     for _, r in sorted(dl.items())) or "—",
            "/".join(("Y" if r["forgot"] else "n")
                     for _, r in sorted(df.items())) or "—"))
    lines += ["", "seed 顺序 = 17/29/43；Y=遗忘超噪声带, n=未遗忘。", ""]
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        f.write("\n".join(lines))
    csv = args.out.replace(".md", ".csv")
    with open(csv, "w") as f:
        f.write("model,strategy,seed,pre_nll,post_nll,delta_nll,forgot\n")
        for (m, s), seeds in sorted(data.items()):
            for seed in sorted(seeds):
                r = seeds[seed]
                f.write("%s,%s,%d,%.6f,%.6f,%+.6f,%s\n" % (
                    m, s, seed, r["pre_nll_a"],
                    r["post_nll"], r["delta_nll"], r["forgot"]))
    print("%d cells -> %s (+%s)" % (sum(len(v) for v in data.values()),
                                    args.out, csv))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
