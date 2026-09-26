"""T4.3 decision tree / practitioner recipe from the ledger (pre-registered rule).

Pre-registered thresholds (spec §7.8, frozen with the statistical plan):
  gain > 2%  AND BH-FDR significant  ->  RECOMMEND
  0-2% or seed direction inconsistent ->  NEUTRAL
  gain < 0   AND BH-FDR significant  ->  NOT RECOMMEND

Comparison is paired within (task, model, split, seed): relative gain of arm A
over baseline B = (A - B)/|B| * 100. A paired sign test over all (model, seed)
pairs gives the p-value; BH-FDR q=0.05 is applied across all comparisons.

Outputs: status/decision_tree.md, status/decision_tree.csv, status/recipe.md
NOTE: T4.3.0 (advisor sign-off of the frozen rule) is still pending; this is
the engine + draft, not the signed release.
"""
from __future__ import annotations
import json, os, collections, statistics
from scipy.stats import binomtest
from rnafteval.stats import bh_fdr

ROOT = "/mnt/cunyuliu/rna-ft-eval"
LEDGER = os.path.join(ROOT, "ledger.jsonl")
OUT_MD = os.path.join(ROOT, "status", "decision_tree.md")
OUT_CSV = os.path.join(ROOT, "status", "decision_tree.csv")
OUT_RECIPE = os.path.join(ROOT, "status", "recipe.md")
COMPARISONS = [("lora", "frozen"), ("full", "lora"), ("full", "frozen")]
GRAN = {"noncoding-rna-family": "per-seq", "mrl": "per-seq/regression",
        "secondary-structure": "per-base", "modification": "per-base",
        "e6-forgetting": "(forgetting probe)"}


def load_index():
    seen = {}
    for l in open(LEDGER):
        l = l.strip()
        if not l:
            continue
        try:
            r = json.loads(l)
        except Exception:
            continue
        if (r.get("status") == "done" and not r.get("smoke")
                and r.get("seed") != 101 and r.get("value") is not None):
            seen[r.get("run_id")] = r
    idx = collections.defaultdict(dict)
    for r in seen.values():
        idx[(r["task"], r["model"], r["split"], r["strategy"])][r["seed"]] = r["value"]
    return idx


def label(med, sig, npos, n):
    frac = (npos / n) if n else 0.5
    if sig and med > 2:
        return "RECOMMEND"
    if sig and med < 0:
        return "NOT-RECOMMEND"
    if sig and med > 2 and 0.2 < frac < 0.8:
        return "NEUTRAL (dir-inconsistent)"
    return "NEUTRAL"


def main():
    idx = load_index()
    rows = []
    for task in sorted({k[0] for k in idx}):
        models = sorted({k[1] for k in idx if k[0] == task})
        for split in ("random", "family"):
            for a, b in COMPARISONS:
                deltas = []
                for m in models:
                    va = idx.get((task, m, split, a), {})
                    vb = idx.get((task, m, split, b), {})
                    for s in set(va) & set(vb):
                        if vb[s]:
                            deltas.append((va[s] - vb[s]) / abs(vb[s]) * 100.0)
                if not deltas:
                    continue
                n = len(deltas); npos = sum(1 for d in deltas if d > 0)
                med = statistics.median(deltas)
                p = binomtest(npos, n, 0.5).pvalue
                rows.append(dict(task=task, split=split, a=a, b=b, n=n,
                                 npos=npos, med=med, p=p))
    sig = bh_fdr([r["p"] for r in rows])
    for r, s in zip(rows, sig):
        r["sig"] = bool(s)
        r["label"] = label(r["med"], bool(s), r["npos"], r["n"])

    lines = ["# T4.3 决策树引擎输出（预注册规则，spec §7.8）", "",
             "> **T4.3.0 状态：导师签字待办**——本文件为引擎 + 草稿，非签字发布版。", "",
             "规则：增益 >2% 且 BH-FDR(q=0.05) 显著 → 推荐；0-2% 或种子方向不定 → 中性；",
             "<0 且显著 → 不推荐。配对口径：同 (task, model, split, seed) 内比较；",
             "相对增益 = (A−B)/|B|×100；配对数 n = 所有 (model, seed) 对。", "",
             "| task | 粒度 | split | 比较(优势臂 − 基线) | n | 方向(+比例) | 中位增益% | p | BH显著 | 判定 |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for r in sorted(rows, key=lambda x: (x["task"], x["split"], x["a"])):
        lines.append("| %s | %s | %s | %s − %s | %d | %d/%d | %+.1f | %.3g | %s | **%s** |" % (
            r["task"], GRAN.get(r["task"], "?"), r["split"], r["a"], r["b"], r["n"],
            r["npos"], r["n"], r["med"], r["p"], "Y" if r["sig"] else "N", r["label"]))
    lines += ["", "数据源：ledger.jsonl（done / 非 smoke / formal 种子 17·29·43，按 run_id 去重）。"]
    open(OUT_MD, "w").write("\n".join(lines) + "\n")

    with open(OUT_CSV, "w") as fh:
        fh.write("task,granularity,split,arm_a,arm_b,n,n_pos,median_gain_pct,p,bh_sig,label\n")
        for r in rows:
            fh.write("%s,%s,%s,%s,%s,%d,%d,%.3f,%.5g,%d,%s\n" % (
                r["task"], GRAN.get(r["task"], ""), r["split"], r["a"], r["b"],
                r["n"], r["npos"], r["med"], r["p"], int(r["sig"]), r["label"]))

    rec = ["# T4.3.3 实践者配方（草稿，规则同 spec §7.8；T4.3.0 签字待办）", ""]
    for task in sorted({r["task"] for r in rows}):
        rec.append("## %s（%s）" % (task, GRAN.get(task, "?")))
        for split in ("random", "family"):
            sub = {(r["a"], r["b"]): r for r in rows if r["task"] == task and r["split"] == split}
            if not sub:
                continue
            lf = sub.get(("lora", "frozen")); fl = sub.get(("full", "lora"))
            parts = []
            if lf: parts.append("LoRA vs frozen: %+.1f%%（%s）" % (lf["med"], lf["label"]))
            if fl: parts.append("full vs LoRA: %+.1f%%（%s）" % (fl["med"], fl["label"]))
            rec.append("- **%s 切分**：%s" % (split, "；".join(parts) if parts else "数据不足"))
        rec.append("")
    rec += ["", "> 决策树：任务粒度 × 切分场景 → 策略推荐（依据上表，可回溯 C1/C4/C5）。",
            "> 复现包见 T4.3.4（notebook 形式，待整理）。"]
    open(OUT_RECIPE, "w").write("\n".join(rec) + "\n")
    print("\n".join(lines[:9]))
    print("written:", OUT_MD, OUT_CSV, OUT_RECIPE)


if __name__ == "__main__":
    raise SystemExit(main())
