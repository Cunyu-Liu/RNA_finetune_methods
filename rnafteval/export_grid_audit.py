"""s101 tuned-LR 网格一致性审计（B1 防线：网格只在 VL0 选优、formal 种子另跑）。

背景（0928 用户审计）：76 格网格补全计划覆盖 (full, random, s101) × LR{1e-5, 3e-5}。
网格落齐后，凡 formal 种子（17/29/43）**tuned 臂**实际 LR ≠ 网格最优 LR 的 (model, task)
→ 需按「网格最优口径」重跑 formal（P1.4 收口清单）。

臂识别（三遍核对后的口径，0929）：
- **tuned 臂**：run_id 以 `_lr<val>` 结尾（如 `..._full_s17_random_lr1e-05`）；
- **default 臂（A8 对照）**：同位置无 `_lr` 后缀（lr=3e-4）——不参与比对；
- **E3 变体**（`_e3100/_e31000/_e310000`）与 `_smoke` 行排除；
- 网格行 = s101 + `_lr` 后缀。

判定：MATCH（tuned LR = 网格最优）/ RERUN-NEEDED（tuned 臂存在但 LR ≠ 最优）/
TUNED-MISSING（formal 无 tuned 臂——仅 default 或完全缺失）/ PENDING（网格未齐）。

用法: python -m rnafteval.export_grid_audit [--plan scripts/p2_grid_fill_plan.json]
"""
from __future__ import annotations

import argparse
import json
import os
import re
from collections import defaultdict

ROOT = "/mnt/cunyuliu/rna-ft-eval"
LEDGER = os.path.join(ROOT, "ledger.jsonl")
DEFAULT_PLAN = os.path.join("/home/cunyuliu/rna-ft-eval", "scripts", "p2_grid_fill_plan.json")
TUNED_RE = re.compile(r"_lr[0-9.eE+-]+$")


def load_rows() -> list:
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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", default=DEFAULT_PLAN)
    ap.add_argument("--out", default=os.path.join(ROOT, "status", "grid_audit.md"))
    args = ap.parse_args()
    P = json.load(open(args.plan))
    rows = load_rows()

    targets = defaultdict(set)          # (model, task) -> {lr}
    for c in P["runs"]:
        targets[(c["model"], c["task"])].add(float(c["lr"]))

    grid = defaultdict(dict)            # (model, task) -> {lr: value}       (s101)
    tuned = defaultdict(set)            # (model, task) -> {lr}              (formal tuned arm)
    tuned_unfinished = defaultdict(bool)
    default_arm = defaultdict(set)      # (model, task) -> {lr}              (formal default arm)
    for r in rows:
        if r.get("strategy") != "full":
            continue
        rid = r.get("run_id", "")
        if "_smoke" in rid or "_e3" in rid:
            continue
        key = (r.get("model"), r.get("task"))
        if key not in targets:
            continue
        try:
            lr = float(r.get("lr"))
        except Exception:
            continue
        is_tuned = bool(TUNED_RE.search(rid))
        if r.get("split") == "random" and r.get("seed") == 101:
            if r.get("status") == "done" and r.get("value") is not None and is_tuned:
                grid[key][lr] = r["value"]
        elif r.get("split") == "random" and r.get("seed") in (17, 29, 43):
            if is_tuned:
                if r.get("status") == "done":
                    tuned[key].add(lr)
                else:
                    tuned_unfinished[key] = True
            else:
                default_arm[key].add(lr)

    md = ["# s101 tuned-LR 网格一致性审计（B1 防线；自动导出）", "",
          "规则：网格最优 LR（VL0 选优）≠ formal **tuned 臂**实际 LR → 需重跑 formal。",
          "臂口径：tuned = run_id 带 `_lr<val>` 后缀；default = 无后缀（A8 对照，3e-4，不比对）；",
          "E3 变体与 smoke 行排除。PENDING = 网格未齐（不下结论）。", "",
          "| model | task | grid 1e-5 | grid 3e-5 | best lr | formal tuned lr | default arm lr | verdict |",
          "|---|---|---|---|---|---|---|---|"]
    rerun, missing, n_match, n_pend = [], [], 0, 0
    for key in sorted(targets):
        m, t = key
        g = grid.get(key, {})
        need = targets[key]
        have = set(k for k in need if k in g)
        tl = tuned.get(key, set())
        dl = default_arm.get(key, set())
        if len(have) < len(need):
            verdict = "PENDING"
            n_pend += 1
        else:
            best = max(g, key=lambda k: g[k])
            if not tl:
                verdict = "TUNED-MISSING"
                missing.append((m, t, best, g[best]))
            elif all(abs(x - best) < 1e-12 for x in tl):
                verdict = "MATCH"
                n_match += 1
            else:
                verdict = "RERUN-NEEDED"
                rerun.append((m, t, best, g[best], sorted(tl)))
        fmtv = lambda v: ("%.4f" % v) if v is not None else "—"
        best_s = ("%.0e" % max(g, key=lambda k: g[k])) if (len(have) == len(need) and g) else "—"
        t_s = ",".join("%.0e" % x for x in sorted(tl)) if tl else "—"
        d_s = ",".join("%.0e" % x for x in sorted(dl)) if dl else "—"
        md.append("| %s | %s | %s | %s | %s | %s | %s | %s |" % (
            m, t, fmtv(g.get(1e-05)), fmtv(g.get(3e-05)), best_s, t_s, d_s, verdict))
    md += ["", "## 汇总", "",
           "- MATCH: %d；RERUN-NEEDED: %d；TUNED-MISSING: %d；PENDING: %d" % (
               n_match, len(rerun), len(missing), n_pend), ""]
    if rerun:
        md += ["### A. 重跑清单（tuned 臂存在但 LR ≠ 网格最优）", "",
               "| model | task | grid best lr | grid value | tuned lr（现用） |", "|---|---|---|---|---|"]
        for m, t, best, bv, tl in rerun:
            md.append("| %s | %s | %.0e | %.4f | %s |" % (m, t, best, bv, ",".join("%.0e" % x for x in tl)))
        md.append("")
    if missing:
        md += ["### B. tuned 臂缺位清单（formal 无 `_lr` 后缀行——需按网格最优 LR 补跑）", "",
               "| model | task | grid best lr | grid value |", "|---|---|---|---|"]
        for m, t, best, bv in missing:
            md.append("| %s | %s | %.0e | %.4f |" % (m, t, best, bv))
    with open(args.out, "w") as fh:
        fh.write("\n".join(md) + "\n")
    print("\n".join(md[-min(len(md), 40):]))
    print("wrote", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())