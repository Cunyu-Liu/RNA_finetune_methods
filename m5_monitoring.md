# M5 竞争监控记录（T0.0.5）

## 2026-09-15 首轮（建档基线复核）

| 检索 | 结论 |
|---|---|
| arXiv/bioRxiv "RNA fine-tuning / LoRA / PEFT / adaptation"（近 90 天） | 未发现 RNA 侧多策略受控对比工作。命中的均为：通用 PEFT 方法学（S0 tuning/MiCA，非 RNA）、低资源文本分类 PEFT 横评（非 RNA）、指令微调数据集（Biology-Instructions，非策略对比）、生物推理后训练分析（RNA 只是 SFT/RL 场景之一，非策略隔离对比）。 |
| BEACON 团队（terry-r123/RNABenchmark） | 仓库无新 commit 涉及 LoRA/PEFT 臂。 |
| 四源单臂状态 | 与 spec v1.2 §1 基线一致：BEACON 全微调单臂 / Zablocki 冻结单臂 / 深圳湾 zero-shot / 良渚统一微调。 |

**判定：无触发**（M5 未命中）。"RNA 侧受控策略对比"空白仍在。
注意项：S0 tuning（recurrent state 调优）与 MiCA（minor-subspace）属新 PEFT 方法，与 E2 横评的方法清单不重叠，但写作期 related work 应引用作为"PEFT 方法空间正在扩张"的佐证。

（下次执行：每月 1 日；若命中重叠 → 7 天内评估，arXiv 窗口压缩决策）

## 2026-10-07 第 2 轮（超期补救，两轮 web 检索）

| 检索 | 结论 |
|---|---|
| "RNA language model fine-tuning LoRA PEFT controlled comparison benchmark 2026" + "RiNALMo BEACON" | **未发现 RNA 侧多策略受控对比工作。** RNA 侧空白仍在（与 09-15 首轮一致）。 |
| 近邻信号（非重叠，related-work 引用候选） | ① NVIDIA BioNeMo Recipes（2026-06-15 博客）：Evo2-1B DNA 拼接位点 LoRA 52.3%→96.6%（1.4% 参数）——DNA 侧单任务 LoRA 教程，无受控策略对比、无家族切分、无遗忘度量；② arXiv 2606.06920 "Fine-Tuning Trap"（Sub-1B 数学推理，LoRA/DoRA/full 负迁移）：**与我们 A8/E2 结论同向**（LoRA 常胜 full@小规模）但为纯 NLP 域——写作期可引用作跨域佐证；③ GradES（arXiv 2509.01842）早停法与 PEFT 组合，非策略对比。 |
| 判定 | **无触发（M5 未命中）。**"RNA 侧受控策略对比"空白保持；无 7 天评估需求。 |
| 备注 | Fine-Tuning Trap 与我们叙事共振点：full-FT 在 sub-1B 崩溃带（其"Stability Cliff below 200M"）——若引用注意标注域差异（数学推理 vs RNA BEACON）。 |

（下次执行：2026-11-01；预印本挂出后加密至每两周。若命中重叠 → 7 天内评估。）
