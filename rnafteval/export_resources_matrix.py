"""E5 T4.1.2/T4.1.3: per-(model,strategy) cost matrix + single-card lookup table.

Extends export_resources.py (which aggregates by strategy only). Here we
condition on model x strategy so a practitioner can read off:
  - wall-clock median / peak-memory median+max per (model, strategy)
  - whether that configuration fits a single 24GB / 40GB card
  - cost-vs-accuracy rows (task x model x strategy) for the Fig.5-style curve

Source of truth: ledger.jsonl (run-level). done & non-smoke only; formal
seeds (17/29/43) and tuning (101) reported separately.

usage: python -m rnafteval.export_resources_matrix
"""
from __future__ import annotations
import json, os, statistics, collections

ROOT = "/mnt/cunyuliu/rna-ft-eval"
LEDGER = os.path.join(ROOT, "ledger.jsonl")
OUT_MD = os.path.join(ROOT, "status", "resources_matrix.md")
OUT_CSV = os.path.join(ROOT, "status", "resources_costbenefit.csv")

try:
    from rnafteval.models import MODEL_SPECS
    PARAMS = {k: v.params_m for k, v in MODEL_SPECS.items()}
except Exception:
    PARAMS = {}


def main() -> int:
    rows = []
    for l in open(LEDGER):
        l = l.strip()
        if not l:
            continue
        try:
            r = json.loads(l)
        except Exception:
            continue
        if r.get("status") == "done" and not r.get("smoke") and r.get("seed") != 101:
            rows.append(r)

    seen = {}
    for r in rows:
        seen[r.get("run_id")] = r
    rows = list(seen.values())

    def pos(v):
        try:
            return v is not None and float(v) > 0
        except Exception:
            return False

    by = collections.defaultdict(list)
    for r in rows:
        by[(r.get("model"), r.get("strategy"))].append(r)

    def med(v):
        v = [x for x in v if x is not None]
        return statistics.median(v) if v else None

    table = []
    for (m, s), rs in by.items():
        walls = [r.get("wall_sec") for r in rs if pos(r.get("wall_sec"))]
        peaks = [r.get("peak_mem_mb") for r in rs if pos(r.get("peak_mem_mb"))]
        wmed = statistics.median(walls) if walls else None
        wmax = max(walls) if walls else None
        pmed = statistics.median(peaks) if peaks else None
        pmax = max(peaks) if peaks else None
        table.append({
            "model": m, "params_M": PARAMS.get(m), "strategy": s, "n": len(rs),
            "wall_med_min": (wmed / 60.0) if wmed is not None else None,
            "wall_max_min": (wmax / 60.0) if wmax is not None else None,
            "peak_med_MB": pmed, "peak_max_MB": pmax,
            "fits_24GB": (pmax is not None and pmax <= 24 * 1024),
            "fits_40GB": (pmax is not None and pmax <= 40 * 1024),
        })

    def sortkey(t):
        return (t["params_M"] if t["params_M"] is not None else -1, t["strategy"])
    table.sort(key=sortkey)

    lines = ["# E5 资源矩阵：单卡可跑性速查（T4.1.2/T4.1.3，自动导出）", "",
             "口径：ledger done & 非 smoke & formal 种子(17/29/43)；peak 为 run 级 "
             "`torch.cuda.max_memory_allocated` 实测；fits 判据用 **peak_max**（最保守，"
             "留 OOM 余量）。GPU 实测：常规 A100-40GB torch 视图 39.49GiB。已按 run_id 去重；wall/peak 小于等于 0 视为未记录（finetune_mrl 不写 wall/peak，MRL 成本侧缺失）。", "",
             "| model | params(M) | strategy | n | wall med(min) | wall max(min) | "
             "peak med(MB) | peak max(MB) | fits 24GB | fits 40GB |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for t in table:
        def f(v, k=1.0):
            return ("%.1f" % (v / k)) if v is not None else "—"
        lines.append("| %s | %s | %s | %d | %s | %s | %s | %s | %s | %s |" % (
            t["model"], ("%.1f" % t["params_M"]) if t["params_M"] is not None else "—",
            t["strategy"], t["n"], f(t["wall_med_min"]), f(t["wall_max_min"]),
            f(t["peak_med_MB"]), f(t["peak_max_MB"]),
            "Y" if t["fits_24GB"] else "N", "Y" if t["fits_40GB"] else "N"))
    lines += ["", "数据源：ledger.jsonl（run 级）。用途：T4.1.3 实践者速查表 + "
              "preprint Fig.5 式成本-收益曲线底表（resources_costbenefit.csv）。"]
    os.makedirs(os.path.dirname(OUT_MD), exist_ok=True)
    open(OUT_MD, "w").write("\n".join(lines) + "\n")
    print("\n".join(lines[:6]))

    cb = collections.defaultdict(list)
    for r in rows:
        v = r.get("value")
        if v is None or not pos(r.get("wall_sec")):
            continue
        cb[(r.get("task"), r.get("model"), r.get("strategy"))].append(r)
    with open(OUT_CSV, "w") as fh:
        fh.write("task,model,params_M,strategy,n,metric,value_mean,wall_med_min,peak_med_MB\n")
        for (task, m, s), rs in sorted(cb.items()):
            vals = [r["value"] for r in rs if r.get("value") is not None]
            walls = [r["wall_sec"] for r in rs if pos(r.get("wall_sec"))]
            peaks = [r["peak_mem_mb"] for r in rs if pos(r.get("peak_mem_mb"))]
            metric = rs[0].get("metric", "")
            fh.write("%s,%s,%s,%s,%d,%s,%.4f,%.1f,%.1f\n" % (
                task, m, PARAMS.get(m, ""), s, len(rs), metric,
                sum(vals) / len(vals), med(walls) / 60.0, med(peaks) or 0.0))
    print("written:", OUT_MD, OUT_CSV)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
