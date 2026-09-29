"""random-init 对照臂导出器（C4/A8 归因数据源；0928 用户设计，NucleicBERT 表 1 同构）。

预注册问题：「崩溃带是**预训练表征**的属性，还是（BERT）**训练动力学**的属性？」
- 数据源：ledger.jsonl——随机初始化臂 run_id 以 `_ri` 结尾（`--random-init`，默认 LR 3e-4）；
  对照组 = 同 (model, strategy, split, seed) 的 pretrained 行（无 `_ri` 后缀，默认 LR 3e-4）。
- 指标口径：ncRNA-family 测试集 acc（ledger.value）。
- 判读纪律（写作期）：家族切分下 random-init 落 0.06-0.08 带 → 崩溃带**位置**由任务结构
  （多成员家族 × per-seq）决定、不依赖预训练；随机切分下 pretrained−randominit gap →
  预训练表征的**同分布记忆价值**。未齐格 → [PENDING]，不得写入结论。

用法: python -m rnafteval.export_randinit [--out status/randinit_table.md]
"""
from __future__ import annotations

import argparse
import csv
import json
import os

ROOT = "/mnt/cunyuliu/rna-ft-eval"
LEDGER = os.path.join(ROOT, "ledger.jsonl")
MODELS = ["RiNALMo-micro", "RNA-Sc-10M", "RNA-Sc-30M"]
STRATS = ["lora", "full"]
SPLITS = ["random", "family"]
SEEDS = [17, 29, 43]


def load() -> list:
    rows = []
    for l in open(LEDGER):
        l = l.strip()
        if not l:
            continue
        try:
            rows.append(json.loads(l))
        except Exception:
            pass
    return rows


def pick(rows, model, strat, split, seed, ri):
    """返回 (value, run_id) 或 (None, None)；ri=是否随机初始化臂。"""
    for r in rows:
        rid = r.get("run_id", "")
        if (r.get("model") == model and r.get("task") == "noncoding-rna-family"
                and r.get("strategy") == strat and r.get("split") == split
                and r.get("seed") == seed and r.get("status") == "done"
                and r.get("value") is not None):
            if ri and rid.endswith("_ri"):
                return r["value"], rid
            if (not ri) and (not rid.endswith("_ri")):
                return r["value"], rid
    return None, None


def mean_std(vals):
    if not vals:
        return None, None
    m = sum(vals) / len(vals)
    if len(vals) == 1:
        return m, 0.0
    var = sum((v - m) ** 2 for v in vals) / (len(vals) - 1)
    return m, var ** 0.5


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "status", "randinit_table.md"))
    args = ap.parse_args()
    rows = load()

    md = ["# random-init 对照臂（C4/A8 归因；自动导出）", "",
          "预注册问题：崩溃带是预训练表征的属性，还是训练动力学的属性？",
          "协议：同架构随机初始化 backbone + 同协议微调（ncRNA-family, 10 ep, 默认 LR 3e-4）；",
          "对照 = pretrained 同 (模型, 策略, 切分, 种子) 行。value = 测试 acc（3 种子）。",
          "gap = pretrained − random-init（正 = 预训练占优）。[PENDING] = 格未齐。", "",
          "| model | strategy | split | pretrained (mean±sd, n/3) | random-init (mean±sd, n/3) | gap | note |",
          "|---|---|---|---|---|---|---|"]
    csv_rows = [["model", "strategy", "split", "pretrained_mean", "pretrained_sd",
                 "n_pretrained", "randinit_mean", "randinit_sd", "n_randinit", "gap"]]
    for m in MODELS:
        for s in STRATS:
            for sp in SPLITS:
                pre, ri = [], []
                for sd in SEEDS:
                    v, _ = pick(rows, m, s, sp, sd, ri=False)
                    if v is not None:
                        pre.append(v)
                    v2, _ = pick(rows, m, s, sp, sd, ri=True)
                    if v2 is not None:
                        ri.append(v2)
                pm, ps = mean_std(pre)
                rm, rs = mean_std(ri)
                gap = (pm - rm) if (pm is not None and rm is not None) else None
                pend = (len(pre) < 3) or (len(ri) < 3)
                note = "[PENDING]" if pend else ""
                f = lambda v, sd: ("%.3f±%.3f" % (v, sd)) if v is not None else "—"
                md.append("| %s | %s | %s | %s (%d/3) | %s (%d/3) | %s | %s |" % (
                    m, s, sp, f(pm, ps), len(pre), f(rm, rs), len(ri),
                    ("%+.3f" % gap) if gap is not None else "—", note))
                csv_rows.append([m, s, sp, pm, ps, len(pre), rm, rs, len(ri), gap])
    with open(args.out, "w") as fh:
        fh.write("\n".join(md) + "\n")
    csv_path = args.out.replace(".md", ".csv")
    with open(csv_path, "w", newline="") as fh:
        csv.writer(fh).writerows(csv_rows)
    print("wrote", args.out, "+", csv_path)
    for line in md[-9:]:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())