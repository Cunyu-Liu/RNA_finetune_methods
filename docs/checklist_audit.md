# 验收清单核对快照（2026-09-16 16:35，Day 2 傍晚更新）

## 已满足（附证据位置）
| 项 | 状态 | 证据 |
|---|---|---|
| B1 零重叠断言生效 | ✅ | smoke_matrix.log 8 次 OVERLAP 拦截 + 30+ 队列 dedup 记录 |
| B3 种子协议无污染 | ✅ | formal 173+ / tuning 16 / 混入 0（ledger 审计） |
| B4 双切分用家族表 | ✅ | data/family_splits/ 三任务 parquet（MMseqs2 全量构建） |
| B5 基线同数据同切分 | ✅ | artifacts/baseline_*.json 六件（三任务×双切分） |
| B6 资源记录器 | ✅ | 187+/193+ 行 wall_sec+peak_mem_mb |
| B8 注意力池化头 | ✅ | strategies/__init__.py AttentionPool（无 mean-pool） |
| B13 配对分析+BH FDR | ✅ | status/stats.md（58 对比 + BH q=0.05） |
| A8 LR 网格选定冻结 | ✅ | 双模型×4LR×2策略 s101 全谱 + tuned formal 三种子 |
| A5/A7 冒烟矩阵+ledger | ✅ | ledger 196 行 + smoke 全链路 |
| B9 新模型 smoke 先行 | ✅ | SpliceBERT 前向 GPU 验证 → 正式 runs |
| B12 任务专用模型语料标注 | ✅ | SpliceBERT 标"跨域任务"（project_rules + preprint） |
| A13 宿主映射断言 | ✅（独立复算） | 2026-09-16 独立重验：309,460 行 groupby 复核，同序列 0 跨侧 / 同簇 0 跨侧（每簇均值 1.28 序列，max 721）；mod_family_split.log 留痕 241,984 簇 |
| B14 方向一致性标记（表格） | ✅ | C4 表 dir 列（↑*/↓* 一致；±(不定) 不进结论） |
| B14 方向一致性过滤（图） | ✅（新） | figures.py fig_c4 ± 条目半透明+标记；程序化核对 21 consistent / 3 ± 与 c4_table 完全一致 |
| B15 检查点分析 | ✅ | docs/checkpoint_b15.md：增益中位数 +0.15，不触发 |
| E2 IA3 三种子 | ✅（新） | 0.860×3（s17/29/43 齐锁） |
| E2 DoRA 三种子 | ✅（新） | 0.930/0.930/0.942（s17/29/43 齐锁） |
| 预印本 v0.2 全文 | ✅（新） | paper/preprint_draft.md 198 行：Intro 五贡献 + Discussion 四论点 + Limitations 5 条；数值快照更新至 tuned 协议臂 |

## 进行中/待办
| 项 | 状态 | 说明 |
|---|---|---|
| E2 位次表（C5）终版整合 | 🟡 | 五臂齐；等新模型矩阵收尾后随终版表整合 |
| 新模型三种子矩阵 | 🟡 | G6 链（frozen/lora MIG 侧）+ G7 链（SpliceBERT full）+ G5 轮询链（ERNIE/RNA-FM full + ERNIE lora）三链并行推进中 |
| RiNALMo SSP full tuned 补齐 | 🟡（新） | chain_g7_ssptuned（5 runs: s29/43 random + 3 family @1e-5）已挂 G7 链后 |
| A1/A2/A9/A14 导师流程项 | ⏳ | 属导师确认环节（文档已备好：spec/docs） |

## 备注
- E2 PEFT = 5 臂（prefix 依赖不兼容，已记录 limitation）
- 验收口径以 ledger/artifacts 产物为准（非口头）
- GPU 现状：GPU0-5 他人满载；GPU6/7 = MIG 4.75G 我方双链占用
