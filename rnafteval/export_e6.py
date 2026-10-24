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

ROOT = "/root/rna-ft-eval"
ART = os.path.join(ROOT, "artifacts", "e6")
CONTROLLED = ["RNA-Sc-1M", "RNA-Sc-10M", "RNA-Sc-30M", "RNA-Sc-100M", "RNA-Sc-650M"]
OFFICIAL = ["RiNALMo-micro", "RiNALMo-mega", "RiNALMo-650M", "ERNIE-RNA", "RNA-FM"]
ORDER = CONTROLLED + OFFICIAL
LABEL = {m: m for m in CONTROLLED}
LABEL.update({m: m + " (official, mlm15fix)" for m in OFFICIAL})
# controlled 系为因果 NLL；official 只接收 fixed-mask 15% 的纠正结果。
CALENDAR = {m: "causal" for m in CONTROLLED}
CALENDAR.update({m: "fixed-mask-mlm15" for m in OFFICIAL})


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
        if r.get("task") == "modification":
            continue
        if m in OFFICIAL and not (
                "_mlm15fix" in r.get("run_id", "")
                and str(r.get("protocol", "")).startswith("E6-v1-fixed-mask-mlm")
                and r.get("mask_rate") == 0.15):
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
             "NLL（test+family_test, n=2000）。controlled = causal NLL + 重排噪声带；",
             "official 仅纳入 `_mlm15fix` = 固定 15% masked-position MLM NLL + 独立掩码/顺序重评差异。",
             "ΔNLL = post − pre；正 = 遗忘，负 = 反向增益；跨协议绝对 NLL 不可比。",
             "forget_ratio = mean ΔNLL(full) / mean ΔNLL(lora)（系内）。", "",
             "| model | pre NLL | Δ lora (s17/s29/s43) | Δ full (s17/s29/s43) | forget_ratio | n(l/f) | lora forgot | full forgot |",
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
        def cells_str(d):
            if not d:
                return "—"
            return "/".join("%+.2f" % r["delta_nll"]
                            for _, r in sorted(d.items()))

        lines.append("| %s | %.4f | %s | %s | %s | %d/%d | %s | %s |" % (
            LABEL[m], pre_v,
            cells_str(dl), cells_str(df), ratio_s, len(dl), len(df),
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
