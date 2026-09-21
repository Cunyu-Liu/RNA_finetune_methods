# 预印本中文对照摘要 + 标题备选（v0.6，2026-09-21）

> 用途：用户快速审阅版；英文正文在 paper/preprint_draft.md（v0.6）。
> 数值与 ledger 全量对账通过（2026-09-21，2 处修正已应用）。

## 标题备选

1. **To fine-tune or not to fine-tune RNA language models? A
   controlled strategy comparison reveals task-granularity-dependent
   leakage effects**（当前主用；问句式，呼应 Schmirler 姊妹篇）
2. Fine-tuning RNA language models: task granularity, not strategy,
   decides whether the gains survive family-level splits
   （陈述式；把 C4 主结论前置）
3. Controlled comparison of adaptation strategies for RNA language
   models: leakage, learning rates, and practical recipes
   （保守式；三个关键词全列）

## 中文摘要（对照英文版逐点）

**背景** RNA 语言模型（RNA-LM）的微调被普遍默认优于冻结
embedding，但跨适配策略的受控对比在 RNA 侧至今缺失。

**方法** 仿照蛋白侧 Schmirler et al. (2024) 模板，构建受控矩阵：
**3 种适配策略（frozen+浅头 / LoRA r=8 / 全参微调）× 5 个
RNA-LM（10M–99M：RNA-Sc-10M / SpliceBERT / RiNALMo-micro /
ERNIE-RNA / RNA-FM）× 3 个 BEACON 任务（ncRNA 家族分类 / m6A
修饰 / 二级结构）× 2 种评测切分（随机 vs 家族簇级）× 3 种子**；
每个微调格用独立 tuning 种子（101）选学习率，全部臂带零重叠
断言审计。

**三个发现**

1. **微调有效，但收益大小取决于任务粒度——与切分**。ncRNA
   序列级分类：LoRA/全参在随机切分下相对 frozen 提升 +0.04~
   +0.43（五模型），**家族切分下崩溃至近随机（0.06–0.12 带；148M LoRA 部分逃逸 0.14–0.33）**；
   frozen 仅温和退化。per-base 任务（m6A）：微调双切分均增益
   （LoRA AUC 0.970→0.995）。结构预测（SSP）：双切分下对
   k-mer 基线稳健 2–5× 优势。
2. **泄漏敏感度 = 粒度 × 家族密度（二维判据）**：ncRNA
   （多成员家族 per-seq）Δ +0.68~+0.91 全崩；MRL（单例簇
   per-seq，90,403 簇）仅 Δ 0.04~0.12 温和；per-base m6A/SSP
   免疫——0/39 格在多成员家族 per-seq 之外崩溃；家族崩溃在
   全部 7 个规模档（1M-650M LoRA，3 种子均值 0.064-0.126 带）基本
   成立——规模大体无关，唯一结构化例外：148M mega 三种子全部越带
   （0.139-0.334，均值 0.207），1M/650M 单种子越带——部分逃逸与
   LoRA×预训练充分度相关，非规模单调函数。
3. **默认 LR 全参崩溃是三任务现象 + 机制已解**：MRL 上 5/5
   模型崩（含 RNA-FM——ncRNA/m6A 唯一幸存者）；tuned 全恢复。
   显微镜诊断：崩溃 = 5-10 步内表示秩坍缩（有效秩 300-500→1，
   权重漂移仅 3-5%）；幸存 = 坍缩后回弹能力（配方家族属性，
   D4 剂量实验阴性诚实报告）；LoRA 默认 LR 从不崩（全参特有）。
4. **等价线「小全参 ≈ 大 LoRA」依赖模型家族**：受控系 10M
   full 0.788 ≈ 100M LoRA 0.795（交点 10M-100M）；官方系
   148M full 0.942 仍不敌 650M LoRA 0.969——干净 scaling 早
   交点，官方系大模型优势持续。

   即随机切分下序列级任务的"微调收益"大部分是**家族级泄漏**，
   定量呼应 RNA 基准"simply cheating"批评。
3. **学习率×策略×规模三重交互，且默认 LR 是不挑架构的陷阱——
   但 tuned 后全部恢复**：默认 3e-4 下全参微调在**三种注意力
   架构**上全部崩溃为 ln(C) 熵平原（各 3/3 种子 0.077），唯
   RNA-FM 幸存（0.82–0.84）。**tuned 补跑恢复一切**：
   SpliceBERT full@3e-5 = 0.910（×11.8，超其 LoRA 0.904）、
   ERNIE full@1e-5 = 0.973（×12.6，≈LoRA 0.974）——崩溃是
   LR 伪影非策略属性；且 family 侧 tuned 后仍崩，**排除 C4
   泄漏发现的 LR 混杂**。tuned LR 下序列级位次：
   full ≥ DoRA ≈ LoRA ≫ IA3 > head-only。

**开放资产** 完整 run 级 ledger（200+ runs）、三任务 MMseqs2
0.8/0.8 家族簇切分、LR 网格、官方 BEACON m6A 切分的泄漏审计
（**27.3% test 窗口与训练窗同宿主簇**）。

## 一句话结论（电梯陈述）

> 在 RNA 语言模型上，"该不该微调"的第一判据不是模型大小而是
> **任务粒度**：序列级任务的随机切分收益大半是家族泄漏的假象
> （家族切分下 5/5 模型崩溃，LoRA 与 tuned-full 双臂一致——
> 排除 LR 混杂），per-base 任务微调真增益且抗家族偏移；标注量
> 轴上 tuned full 曲线**非单调**（n=1000 达 0.707 全策略峰值
> 后全量崩溃）——**一千条标注是最优微调点**；学习率不调可让
> 任何策略对比结论翻转。

## 审稿防线自查（对照红队报告）

| 红队条目 | 防线状态 |
|---|---|
| R1 单任务拼盘 | 结论承载类（结构/功能）已覆盖；E3/E4 类结论标注单任务依据 |
| R2 统计 | BH FDR 58 对比 + B14 方向一致性过滤已入图；功效墙 limitation 诚实声明 |
| R5 切分单元 | §3.4 表 + 宿主映射断言（A13）落地 |
| R6 流程倒挂 | B15/B16 检查点自动报告 + 决策文档 |
| R7 决策树事后性 | §4.1 预注册规则节（spec §7-8 冻结版） |
| R11 PEFT 缺全参参照 | E2 六臂含 full（tuned） |
| R9 口径混乱 | 全部表格自动导出（export_c4/e2/resources/stats） |
