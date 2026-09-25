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
4. **等价线「小全参 ≈ 大 LoRA」依赖模型家族（严谨口径，650M 已收口）**：
   受控系 5 档全谱（1M-650M）：full 0.700/0.808/0.862/0.824/**0.896**
   vs LoRA 0.639/0.746/0.773/0.795/**0.855**——受控系 5/5 尺度 full 全胜
   同尺度 LoRA；交点在 10M-30M 且**大端不回吐**（30M full 0.862 ≈ 650M
   LoRA 0.855，+0.007；650M full 0.896 > 650M lora 0.855 达 +0.040）；
   官方系三档全谱方向完全相反：33M full 0.938 < 148M full 0.945 <
   650M full 0.957 仍均不敌对应 LoRA（148M 0.949 / 650M 0.969），
   33M full 与 148M LoRA 差 -0.011——**两系在所有测过的尺度上方向相反；
   交点现象仅在自训受控系一个家族中观察到，不作为普适规律主张**；
   可靠结论是方向性（已发布家族大模型 LoRA 优势持续 vs 受控系全谱
   full 优势），受控系作为存在性反例界定主张边界（spec v1.7
   预分配角色）。受控 650M family 崩塌为最彻底形态：LoRA 三种子
   同值 0.064（多数类退化），tuned full 0.064-0.096 亦入带，
   frozen 0.516——「微调破坏 frozen 家族表征」的第八个尺度证据。
   **m6A 侧六档全谱收口（0925）**：受控系 lora 1M-650M 全饱和
   （0.941-0.948，1M 即达天花板）；**650M 粒度×策略镜像**——m6A
   lora 0.948 > full 0.927（+0.021）vs ncRNA full 0.896 > lora
   0.855（+0.040）：同一 checkpoint 两任务方向相反，最优策略是
   任务粒度的属性而非模型的属性。

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
5. **等价线「小全参 ≈ 大 LoRA」两系全谱方向相反（650M 已收口）**：
   受控系（RNA-Sc 同配方 1M-650M 五档）full 五档全胜同尺度
   LoRA，30M full 0.862 已打平最大档 650M LoRA 0.855；官方
   RiNALMo 三档 LoRA 处处领先（650M：0.969 vs 0.957）——
   **交点是否出现取决于训练配方**，不作为普适规律主张（可靠
   结论 = 方向性，受控系为界定主张边界的存在性反例）。
6. **灾难性遗忘真实存在、尺度非单调、且适配器主要保护尾部
   （C6 首数据，24 格矩阵，0925）**：ncRNA 微调（tuned LR、
   10 ep、3 种子）前后 S0 held-out NLL（29M 序列 release-22
   簇切分的 test+family-test 档，n=2000，重排噪声带 <3e-8 全
   格显著）：**30M 是遗忘峰值带**——full +4.12/+26.24/+22.67
   （两种子近崩溃，post NLL 30.8）vs LoRA 最差 +3.38（尾部
   压缩 ~8×，且一种子为负）；**10M 双臂负遗忘**（微调反而
   改善 S0）；**100M full 回稳而 LoRA 恒小正**；官方
   RiNALMo-33M 微忘自身预训练分布 6/6 格（+0.11~+0.16，
   MLM 伪似然口径，系内可比）。**部署视角：LoRA 是有界保费的
   遗忘保险**；1M/650M 端点在跑（谱线补全）。

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
任何策略对比结论翻转；而「小模型全参 vs 大模型 LoRA」的
   答案随训练配方翻转——官方家族大 LoRA 持续占优，受控家族
   30M 全参即打平 650M LoRA。

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
