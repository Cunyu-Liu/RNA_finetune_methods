# 验收清单核对快照（2026-09-16 15:10，Day 2）

## 已满足（附证据位置）
| 项 | 状态 | 证据 |
|---|---|---|
| B1 零重叠断言生效 | ✅ | smoke_matrix.log 8 次 OVERLAP 拦截 + 30+ 队列 dedup 记录 |
| B3 种子协议无污染 | ✅ | formal 173 / tuning 16 / 混入 0（ledger 审计） |
| B4 双切分用家族表 | ✅ | data/family_splits/ 三任务 parquet（MMseqs2 全量构建） |
| B5 基线同数据同切分 | ✅ | artifacts/baseline_*.json 六件（三任务×双切分） |
| B6 资源记录器 | ✅ | 187/193 行 wall_sec+peak_mem_mb |
| B8 注意力池化头 | ✅ | strategies/__init__.py AttentionPool（无 mean-pool） |
| B13 配对分析+BH FDR | ✅ | status/stats.md（56 对比 + BH q=0.05） |
| A8 LR 网格选定冻结 | ✅ | 双模型×4LR×2策略 s101 全谱 + tuned formal 三种子 |
| A5/A7 冒烟矩阵+ledger | ✅ | ledger 193 行 + smoke 全链路 |
| B9 新模型 smoke 先行 | ✅ | SpliceBERT 前向 GPU 验证 → 正式 runs |
| B12 任务专用模型语料标注 | ✅ | SpliceBERT 标"跨域任务"（project_rules + preprint） |
| A13 宿主映射断言 | ✅ | make_family_split_mod 同序列跨侧断言通过 |

## 进行中/待办
| 项 | 状态 | 说明 |
|---|---|---|
| B14 方向一致性标记 | ✅（更新） | C4 表 dir 列（↑*/↓* 一致；±(不定) 不进结论图） |
| B15 检查点分析 | ✅（更新） | docs/checkpoint_b15.md：增益中位数 +0.15，不触发 |
| E2 位次表（C5） | 🟡 | IA3 s43 在跑；DoRA/LoRA/full/head-only 已齐 |
| A1/A2/A9/A14 导师流程项 | ⏳ | 属导师确认环节（文档已备好：spec/docs） |

## 备注
- E2 PEFT = 5 臂（prefix 依赖不兼容，已记录 limitation）
- 验收口径以 ledger/artifacts 产物为准（非口头）
