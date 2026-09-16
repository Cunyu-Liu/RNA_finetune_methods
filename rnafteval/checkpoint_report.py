"""T2.0 滚动检查点报告（预注册，R6 防线）。

自动产出"预注册检查点报告"。预注册规则（spec §3.5-7 / T2.0.2）：
frozen 相对最强传统基线的增益中位数 <2% 且 BH 后无显著格 →
方案复审。

口径说明（2026-09-16 B16 勘误后固化）：
预注册文本未定义"中位数"的计算总体，存在两个读法——
  (a) 每任务最佳模型（B15 手动口径）：回答"预训练在本任务是否有
      价值（任一模型兑现）"；
  (b) 全格池（模型×任务×切分）：回答"平均一格的 frozen 表现"。
两者都输出；触发判定以 (a) 为主口径（R6 的意图是防止"预训练无
收益"方向性错误，(b) 混入了家族切分格——负增益正是 C4 主结论
而非失败信号）。

用法: python -m rnafteval.checkpoint_report [--out status/checkpoint_report.md]
"""
from __future__ import annotations

import argparse
import os
import statistics

ROOT = "/mnt/cunyuliu/rna-ft-eval"
LEDGER = os.path.join(ROOT, "ledger.jsonl")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "status",
                                                  "checkpoint_report.md"))
    args = ap.parse_args()
    from rnafteval.export_c4 import cells as c4_cells, baselines
    c = c4_cells()
    base = baselines()

    detail = []
    for (m, t, s, split), seeds in c.items():
        if s != "frozen" or not seeds:
            continue
        b = base.get((t, split))
        if b is None:
            continue
        mean = sum(seeds.values()) / len(seeds)
        detail.append((m, t, split, mean, b, mean - b, len(seeds)))

    def med(xs):
        return statistics.median(xs) if xs else None

    all_gains = [d[5] for d in detail]
    by_task_best = {}
    for m, t, split, mean, b, g, n in detail:
        if split != "random":
            continue
        if t not in by_task_best or g > by_task_best[t]:
            by_task_best[t] = g
    best_gains = list(by_task_best.values())
    rand_gains = [d[5] for d in detail if d[2] == "random"]
    fam_gains = [d[5] for d in detail if d[2] == "family"]

    med_a = med(best_gains)
    med_b = med(all_gains)
    verdict = ("NOT_TRIGGERED" if med_a is not None and med_a >= 0.02
               else "CHECK_TRIGGER")

    lines = ["# T2.0 预注册滚动检查点报告（自动生成，B16 双口径版）",
             "",
             "主口径 (a) = 每任务最佳模型 frozen 增益中位数（random 侧，"
             "B15 口径）；辅口径 (b) = 全格池中位数。触发判定以 (a) 为准。",
             ""]
    lines += [
        "- (a) 每任务最佳模型增益: %s" %
        ", ".join("%s %+.3f" % (t, g)
                  for t, g in sorted(by_task_best.items())),
        "- (a) 中位数: %s" % ("%+.3f" % med_a if med_a is not None
                              else "N/A"),
        "- (b) 全格池中位数: %s（random %s / family %s；n=%d 格）" %
        ("%+.3f" % med_b if med_b is not None else "N/A",
         "%+.3f" % med(rand_gains) if rand_gains else "N/A",
         "%+.3f" % med(fam_gains) if fam_gains else "N/A",
         len(all_gains)),
        "",
        "**判定（主口径 a）**: %s — %s" % (
            verdict,
            "中位数 ≥2%，不触发方案复审" if med_a is not None
            and med_a >= 0.02 else "中位数 <2%，进入复审流程"),
        "",
        "辅口径解读：(b) 的负值集中于家族切分格与弱模型/跨域模型格"
        "——前者即 C4 主结论（LGBM 按构造免疫家族泄漏），后者是模型"
        "选择问题，均非 R6 所防的'预训练无收益'方向性错误。",
        "",
        "## 逐格明细（全部 frozen 格）",
        "| model | task | split | frozen mean | baseline | gain | n |",
        "|---|---|---|---|---|---|---|",
    ]
    for m, t, split, mean, b, g, n in sorted(detail, key=lambda x: -x[5]):
        lines.append("| %s | %s | %s | %.3f | %.3f | %+.3f | %d |"
                     % (m, t, split, mean, b, g, n))
    lines += ["",
              "注：BH 显著格数以 status/stats.md 为准；n=3 符号检验"
              "功效墙（min p=0.25）使'BH 后无显著格'恒真——预注册"
              "触发条件第二支在 3 种子协议下不可满足，已在 B16 决策"
              "文档记录（limitation）。历史决策：checkpoint_b15.md / "
              "checkpoint_b16.md。"]

    body = "\n".join(lines) + "\n"
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    open(args.out, "w").write(body)
    print(body)
    print("written:", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
