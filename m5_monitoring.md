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
