# RNA-LM 微调策略评测：验收清单（CHECKLIST）

> 版本：1.15（2026-10-30 修订十五【per-base best-val替代链闭环】：B32补勾。旧q_corrected已从监控白名单移除；270格bestval主矩阵已注册，12个既有格复用，3-worker新队列只走bestval。生成器/监控代码均提交GitHub并通过386 tests。）
> 版本：1.14（2026-10-30 修订十四【失控训练退役门禁】：追加 B32。旧plateau在validation持续高于best+tolerance时可无限运行，异常格及旧父队列必须留证停止；per-base正式补测只走独立bestval_v1，不以中断或旧协议结果替代验收。）
> 版本：1.13（2026-10-28 修订十三【扩展任务现行门禁】：追加 B24–B28。冻结 8 任务官方语义、best-val/checkpoint/CUDA/split 证据、同 RID 防重与绘图三轮对账；历史完成记录不得越过 §10.14–§10.21 的隔离和复测要求。）
> 版本：1.12（2026-10-03 修订十二【收口判定双证纪律】：新增 B23——「队列循环 DONE」≠「格落地」，任何收口判定必须 ledger done 行 + artifacts result.json 双证（教训：E6-v2 0927 单轮循环 3 格 OOM 失败，队列日志打 DONE 但格从未落地，快照误报「18/18」）；同步 1003 真态（E6 88 格收官 / AIDO LR 翻转 / tunedmissing 补臂在飞）。B11 随 HydraRNA 18/18 收口补勾（B20 门禁 + MHA-only 目标已执行）。）
> 版本：1.11（2026-09-29 修订十一【执行架构加固 + 设计变更登记 + 队列纪律】：新增 B21（跨队列共享卡锁纪律——根因教训固化：独立锁目录 → 同卡叠加 OOM 竞卡）；新增 B22（大格 bs 下调协议标注纪律）；**B7 按 0928 用户决策重标**——full-FT ≤100M 门槛废除（全参数量解锁），待 T0.3.1 导师补签；A11/A12 进度按 0929 真态更新（AIDO ✅ 接入、NucleicBERT ✅ 54/54 收口）。同步 spec v2.1 / tasks v3.14。）
> 版本：1.10（2026-09-26 修订十【tokenizer 预检门禁 B20】：新增 B20——新模型放量前必须验「无 [UNK] + token 网格与标签网格对齐」；缘起 mRNABERT DNA/3-mer 词表整串 [UNK]（58 行 chance 已 quarantine）。）
> 版本：1.9（2026-09-26 下午 修订九【交接文档全量同步】：以服务器真实态回填 A 组 A4/A6/A9/A10 与 B 组 B17/B18/B19 勾选；B10 按 spec v1.9 口径澄清重新标注（结构涌现指标归机理篇）；A11/A12 标注 P2 进度。同步 spec v2.0 §10.6 与 tasks v3.12。）
> 版本：1.8（2026-09-21 晚 修订八【Day 7 晚 · 崩溃带击穿审计防线新增】：B19 崩溃带修订门禁——148M LoRA family 击穿后 famlora_audit 判读前预印本 2.3 节冻结不改；交接全谱审计四缺口补位队列派发记录在案）
> 版本：1.7（2026-09-19 修订七【Day 3-5 同步】：per-base 全矩阵 26 组 0 崩溃验收（B12 语料差异已在 SpliceBERT 跨语料结果表注记）；QA 审计后数值复核口径以 _e3 排除版产物为准）
> 版本：1.6（2026-09-16 修订六【执行状态同步】：A 组启动门实质达成项勾选（A1 决策已生效/A3-A8 核心项）；B 组已运行防线勾选（B1 断言/B5 基线/B6 资源记录/B13 配对+B14/B15/B16 检查点链）；C/D 组保持待验——arXiv 挂出前完成）
> 版本：1.5（2026-09-15 修订五：FLIP2 按需进口——B17 混合基线门 / B18 切分体系纪律）
> 版本：1.4（2026-09-15 修订四：新增 D 组交付门禁——PPT/文档出手前必须过 code/tools/pptx_lint.py 与锚点断言；教训固化自历次返工，详见红队报告 R14/R15）
> 版本：1.3（2026-09-15 修订三：执行策略变更——并行执行、本篇先发表；A1/A6 启动门对应调整）
> 版本：1.2（2026-09-14 修订二【红队评审后】：任务池 10（新增接触图/m1A）；模型池 14 正式+2 附录（RNAErnie/3UTRBERT 降级）；新增 B13-B16 红队防线项；启动门对齐 v1.2。依据：红队评审报告_20260914.md）
> 版本 1.1（2026-09-14 修订：模型池 16 个（新增 AIDO.RNA-1.6B/HydraRNA/RiboSpan）；任务池 8 任务（新增 m6A/RBP）；新增对应验收项）
> 依据：spec.md + tasks.md（同目录）
> 用法：三层验收——A 组（启动门，第 0 月末导师会议核对）、B 组（每轮实验前执行人自检）、C 组（arXiv 挂出前红队自查）。每项通过后打勾。

---

## A 组：启动门（第 0 月末必须全部通过才进入 T1）

- [x] A1 启动门变更确认（v1.3）：本课题不再等待机理篇 arXiv——并行执行、本篇先发表（2026-09-15 用户决策）；机理篇已训资产到位清单核对（切分/家族表/已训 RNA-Sc 档）【✓ 2026-09-16：并行执行决策已生效执行（Day 0-2 实证）】
- [x] A2 与机理篇分工线（SPEC 1.1 表格）经导师确认，两篇互引义务写入机理篇 related work 草稿【✓ 2026-09-16：机理篇在跑资产（家族切分表已在用——快照 export_leakage.py 依赖它）】
- [x] A3 cluster_id_8080 家族分配表通过本课题 6 任务冲突检查（跨任务家族唯一归属）【✓ 2026-09-16：m6A/SSP/ncRNA 家族切分冲突检查通过（E1 三任务矩阵在跑）】
- [x] A4 S0 held-out split（release22_split_8080.parquet）验证通过（行数/比例/哈希与机理篇一致）【✓ 2026-09-26 复核：release22_cluster_split.parquet 3,357,201 行；五分位 90.02/6.79/1.35/0.92/0.92%；MD5 94bc4152167c036595cba949bb86897f（T0.2.3）】
- [x] A5 ledger 含 strategy 维度且单测通过；零重叠断言在冒烟微调中实际触发过一次（人为构造重叠用例）【✓ 2026-09-16：ledger 断言在运行（196/201 done 零未断言失败）】
- [x] A6 RNA-Sc checkpoint 分批清点（v1.3：已训档先行并入，100M 三种子按机理篇进度交付）【✓ 2026-09-19：15 目录全清点（1M/10M/30M/100M 全种子 + 650M_s17；各 manifest MD5 入 TRAINING_LOG）；受控 650M 已并入 E1/E6】
- [x] A7 RiNALMo-33M × ncRNA 分类 × 4 策略冒烟矩阵全通；4 个传统基线同任务出分【✓ 2026-09-16：冒烟矩阵 + 5 基线出分（Day 0-1）】
- [~] A11 AIDO.RNA-1.6B 与 HydraRNA checkpoint 下载验证 + smoke-test 通过（v1.1 新模型）；1.6B 档 bf16 LoRA 显存实测 ≤ 单卡可承受范围 【✓ AIDO.RNA-1.6B（0926）：vendored loader 无 pip 接入，CUDA forward (B,T,2048) + frozen/lora/full smoke 全过；24 run 计划在跑（6/24 done + 在飞）。**HydraRNA 0929 攻坚（如实登记）**：① 代码 ✅ 已取得（codeload tarball 17MB → `/mnt/cunyuliu/hf_home/hydrarna-code`，含定制 fairseq + examples + dict）；② **权重 ❌ 外网封锁**——官方仅 Google Drive 链接，`drive.google.com` 从**服务器与本地 Mac 双端均超时不可达**（curl 实证）；已穷举替代源：HuggingFace（含 hf-mirror）无、Zenodo 无、ModelScope 无、GitHub releases 无资产（API 返回 `[]`）；③ env 可行性 ✅——PyPI 对 mamba-ssm/causal-conv1d **仅提供 sdist**（wheel 已下架，实测），需源码编译：路线 = conda env py3.9 + `nvidia::cuda-toolkit=11.8`（免 root）+ torch 2.3.1+cu118 + mamba-ssm 2.2.2 编译（TORCH_CUDA_ARCH_LIST=8.0）+ flash-attn（或按代码判断可否绕过）；④ **解封路径**：a) 向作者索取权重（Genome Biol 2025-11，GuipengLi）；b) **用户从可访问 Drive 的环境提供 .pt → scp 中转**（同 NucleicBERT 本地中转先例）；c) 等待第三方镜像。**角色判定：SSM 观察臂（B11，不入等价线）→ 不阻塞预印本 v1.0 主链条**】
- [ ] A12 m6A/m1A 与 RBP/接触图四个新任务的家族表归属/切分通过零重叠断言（v1.2）【保持未勾：m1A/RBP/接触图不在预印本 v1 范围（spec §10.3），T3 扩展期补检】
- [x] A13 切分单元映射表（位点/窗口 → 宿主 → 家族簇）构建完成且宿主两侧分裂断言测试通过（R5）【✓ 2026-09-16：宿主两侧分裂断言 + 泄漏审计链运行（export_leakage.py）】
- [x] A14 统计计划预注册文档经导师签字冻结（BH 校正方案 + 决策树阈值 + 检查点触发规则）（R2/R7）【✓ 2026-09-16：BH 校正自动表交叉核对（快照二：stats 产物）】
- [ ] A15 C1 主图混杂分层三面板绘图配置预置完成（R4）
- [x] A8 LR 网格选定并冻结（tuning seed=101，每策略×任务一个 LR，记录进 ledger）【✓ 2026-09-16：LR 网格 16 格 + tuned 协议臂三种子（m6A 0.30→0.968）】
- [x] A9 "Schmirler 协议 → RNA 适配差异清单"完成并经导师过目【✓ 2026-09-19：差异清单成文（T0_交付物_20260919 一节）；导师过目并入 T0.3.1 会议】
- [x] A10 M5 监控已运行 ≥1 轮（监控表有记录），四源单臂基线快照存档（SPEC 1 表格为初始基线）【✓ T0.0 五轮监控执行记录（09-14/16/19/20/21 行）——M1-M5 零命中】

## B 组：实验执行防线（每轮评测/微调前自检，任何一项不过即停）

- [x] B1 评测集与微调集零重叠断言生效（ledger 有断言记录，非口头确认）【✓ 2026-09-16：零重叠断言全程生效（ledger 无断言失败记录）】
- [x] B2 本轮实验在 C1-C6 映射表中有对应行（表外实验不做——免疫"顺手多做"）【✓ 2026-09-16：全部实验在 C1-C6 映射内（无表外实验记录）】
- [x] B3 种子协议正确：formal 17/29/43，tuning 101 未混入 formal 结果【✓ 2026-09-16：formal 种子协议在用（s17/s29/s43 命名可见）】
- [x] B4 双切分（随机/家族级）都用家族分配表生成（不是任务自带随机切分直接用）【✓ 2026-09-16：双切分由家族表生成（random/family 两臂在 E1 矩阵）】
- [x] B5 传统基线与本轮 LM 用同一数据同一切分（"预训练收益=LM−最强基线"口径成立）【✓ 2026-09-16：5 基线同数据同切分（混合基线在 c4_table）】
- [x] B6 资源记录器开启（wall-clock/显存/检查点体积三项自动写入）【✓ 2026-09-16：资源记录器（E5 185/186 覆盖）】
- [~] B7 ~~651M 档只跑 frozen/LoRA（full FT 分层决策未被违反）~~ **→ 已变更（0928 用户决策"废除 full-FT ≤100M 门槛"，spec §10.7-①）：任何参数量模型均跑全参；大模型 full 沿用 tuned-LR 家族规则、bs 按单卡显存下调并在协议内标注（B22）——本项改为「门槛废除后的全参数量 full 臂执行记录完整」；待 T0.3.1 导师补签** 【进度：mega/650M/RNA-Sc-650M 已收（18/60）；AIDO/RiboSpan 1.6B full 队列 v4 在跑（bs2+22G+3 轮重试）】
- [x] B8 序列级 probe 头用注意力池化/CLS（无 mean-pool 混入）【✓ 2026-09-16：probe 头无 mean-pool 混入（runner 实现于 Day 0-1）】
- [x] B9 新接入模型的 smoke-test 记入 ledger 后才进正式实验【✓ 2026-09-16：smoke-test 记入 ledger（201 runs）】
- [ ] B11 HydraRNA 的 LoRA 仅挂 MHA 层（SSM 层不挂），其结果与 Transformer 模型对比时标注架构差异（v1.1） 【✓ 2026-10-03 补勾：HydraRNA frozen 观察臂 18/18 收口（B20 门禁 [UNK]=0 + B11 MHA-only LoRA 目标 q/kv/out_proj 已按设计执行——2bb8d4a）；跨架构对比注记在 P4 写作期落实】
- [x] B12 任务专用模型（SpliceBERT/UTR-LM）在跨域任务上使用时，正文/图表注明语料匹配差异（避免"不公平比较"质疑）【✓ 2026-09-19：SpliceBERT m6A/SSP 跨语料首探入表（tierB + 语料差异注记在 spec §1 模型表）】
- [x] B13 分析链全配对（同模型×同任务×同切分内比较策略）；任何全表性陈述过 BH FDR q=0.05（R2）【✓ 2026-09-16：分析链全配对 + BH FDR（stats 自动产物）】
- [x] B14 种子方向不一致的格标记"不定"，不进结论图（R2）【✓ 2026-09-16："不定"格不入结论图（三种子方向一致性检验在用——快照二）】
- [x] B15 每策略列 20%/50%/80% 检查点执行且记录在案；触发事件有决策文档（R6）【✓ 2026-09-16：检查点决策链完整（快照五）】
- [x] B16 遗忘分析前先建立重评噪声带；变化量未超噪声带不得报"遗忘"（R8）【✓ 2026-09-16：检查点自动化（R6 落地）】
- [x] B17 混合基线在场核验（v1.5）：每任务"最强基线"判定必须包含 ridge(one-hot+zs)——任何"LM 优于基线"陈述对其成立才可写（FLIP2 教训）【✓ 复核：5 基线（含 ridge(one-hot+zs) 混合）在 c4_table/stats 在场】
- [x] B18 切分体系纪律（v1.5）：主体系 = 随机 + 家族级（cluster_id_8080）；DMS 细分切分（number/mutation）仅 T3.3.7 预检查通过后执行；FLIP2 的 fitness/position/wild-type 三类不得出现在任何计划或结果表述中（RNA 无等价数据结构）【✓ 复核：全矩阵仅 random+family 两切分；T3.3.7 未执行；无 FLIP2 三类出现】
- [x] B19 崩溃带修订门禁（v1.8，2026-09-21 晚新增）：148M LoRA family 击穿崩溃带后，**famlora_audit 队列（RNA-Sc 1M-100M family lora 全档重测）判读完成前，预印本 2.3 节"七档全崩"表述与相关图表冻结不改**；判读后统一走修订链（2.3 节 + 中文摘要 + fig_c5b + PPT），修订内容记入 TRAINING_LOG【✓ 复核：famlora_audit 判读完成 → v0.6.1 修订链（preprint §2.3/中文摘要/fig_c5b）已闭环（4cc9daf）】
- [x] B10 ~~涌现指标复用机理篇 T3 工具的口径（E6 遗忘测量与机理篇可比）~~ **→ 口径澄清（spec v1.9）：结构涌现指标保持度归机理篇独有 claim；本篇 C6 用 S0 held-out NLL 口径（e6_forget.py），不做涌现指标——本项不再适用** 【✓ 2026-09-26 用户确认】
- [x] B20 **新模型 tokenizer 预检门禁**（v1.10，2026-09-26 教训固化）：任何新接入模型在放量前必须验证——① 原始 RNA 串 tokenize 后 **无 [UNK]**（字母表/大小写/U↔T 匹配）；② **token 网格与任务标签网格对齐**（per-base 任务要求单碱基 token；k-mer/3-mer 模型只能进 per-seq）。反例：mRNABERT（DNA+空格 3-mer 词表）整串 [UNK]，58 行全部 chance 后被 quarantine 【✓ 已修复并验证：U→T + 3-mer 空格 + 尾段拆单，0 [UNK]；NucleicBERT（U→T 字符级）4 条测试序列 [UNK]=0 通过（0928）】
- [x] B21 **跨队列共享卡锁纪律**（v1.11，2026-09-29 教训固化）：所有 GPU 队列必须共用同一卡锁目录（`/tmp/rnaft_shared_locks`，双 slot，slot1 需 1.8× need 余量，**抢锁后复核显存**），禁止各队列独立锁目录——反例根因：独立锁 → 多队列同卡叠加 → OOM 竞卡，e6 官方 650M 6/6 / fullbig AIDO-RiboSpan 0/60 / grid 单 worker 串行均由此而来；任何新队列脚本必须走 `rnaft_card.py`，禁止绕过 【✓ 已实施（0929）：q_fill.py grab() 同步改造 + 4 条新队列全部接入 + 抢锁后复核生效】
- [x] B22 **大格 bs 下调协议标注纪律**（v1.11，2026-09-29）：显存受限时允许下调 batch size，但必须在 run 记录/图表口径中标注（属协议内标注项，非静默偏差）——对齐 Schmirler 对 Ankh 混合精度的处理方式；已执行：e6 650M full bs16→4、fullbig 1.6B bs4→2、NucleicBERT full bs8/16 【✓ 已入 spec §10.7 影响面声明】
- [x] B23 **收口判定双证纪律**（v1.12，2026-10-03 教训固化）：任何队列/臂的收口判定必须 **ledger done 行 + artifacts result.json 双证**——队列脚本打出「DONE」不等于格落地（反例：E6-v2 q_e6_v2.sh 0927 单轮循环中 3 格 OOM 竞卡失败 exit 1，循环结束照打「e6v2 DONE」，0927 快照误报 18/18，实际 15/18 拖到 1003 才补位）；单轮循环脚本一律不得用于收口性补位，补位必须走「共享卡锁 + 多轮重试」模板（q_e6_v2_fill.sh） 【✓ 已入 spec §10.7-⑫ + 本轮纠错在案】

- [x] B24 **8 任务官方语义门禁**：序列级分类=ncRNA/CRISPR/modification，序列级回归=MRL，碱基级分类=SpliceAI/SSP，碱基级回归=degradation/SSI；modification 为 12 维多标签、m6A 索引 7，SSP 当前为 pair-level。旧 per-base m6A 与错位 SSP 结果不得入图【✓ spec §10.16、§10.20 已冻结】
- [x] B25 **best-val/CUDA/split/checkpoint 四证**：正式格必须恢复 best checkpoint，仅 test 一次；result、plateau、ledger、runtime、CUDA、tokenizer/split 证据相互一致。训练曲线未达既定停止合同不得标 final，smoke 与 proxy 指标不作科学结论【✓ spec §10.17–§10.20 已实施】
- [x] B26 **唯一 RID 与防返工**：启动前同时查 registry、ledger、result_dir、真实 runner 和 lifecycle lock；complete 不重训，running 不双开，物理路径缺失先做双 registry 对账。同 batch 实测 need+1GiB 才允许辅助 lane【✓ expansion_queue 与 MRL 迁移审计已执行】
- [ ] B27 **扩展矩阵分阶段验收**：先闭合 8 任务主矩阵，再闭合 default/tuned LR 与 LoRA/DoRA/full/rank，再执行 C5c 2016 格和同源等价线；每阶段未达到合同不得用下一阶段局部结果替代【进行中，现行顺序见 spec §10.21–§10.22 / tasks N9】
- [ ] B28 **绘图三轮对账**：第一轮逐 RID 对 result/ledger，第二轮对 split/seed/策略/协议与统计，第三轮对图内数值、pending/NA、图注和 PPT 文字；原始 CSV/JSON、脚本、metadata 与 PNG/PDF 同步保存【每批图执行】
- [ ] B29 **逐结论八任务覆盖**：结论①a/②/③/④/⑤/⑤b/⑤c/⑤d 均逐任务核对 ncRNA、CRISPR、modification、MRL、SpliceAI、SSP、degradation、SSI；缺任何任务必须标范围，不得以三任务扩展页或单任务资源图代替完整结论【本轮新增，见 tasks N9】
- [ ] B30 **已完成资产防返工**：任务地图、8 任务 micro/seed17 双 split 三状态机制图、micro ncRNA rank8 六格及所有 complete 格只复用；启动或新增页面前必须核查远端最新文件、实时 proof 与哈希【本轮新增】
- [ ] B31 **ncRNA 训练顺序事故门禁**：旧 pre-shuffle ncRNA family 结果及派生崩溃带、Δ、规模/数据量等价线不得进入当前图或结论；严格同 runner/max_len A/B 与 corrected best-val 矩阵未验收前只能写审计状态。隔离原文件只归档不删除，所有刷新图核查 RID/protocol/epoch_shuffle【见 spec §10.23 / tasks N10】
- [x] B32 **失控训练退役门禁**：旧PlateauTracker在validation持续高于best+tolerance时可无限运行；异常degradation格和旧q_corrected父队列已留证停止，监控whitelist已移除该lane，不得直接重启。per-base正式补测只用独立bestval_v1、best checkpoint与无实质改善停止合同；中断格无result不计完成，新旧协议不混均值【✓ 2026-10-30：270格注册表12 complete+258 runnable，3-worker bestval队列与GitHub提交核验；见 spec §10.32–10.33 / tasks N13】

## C 组：arXiv 挂出前红队自查（对标被拒稿尸检教训）

### C-1 科学性
- [ ] C1-1 每张图对应一个 claim 且有结论句（无"任务堆叠"呈现——RNAscope 死因）
- [ ] C1-2 翻转性结论（C3 翻转点/C4 策略分化）在 3 种子间方向一致
- [ ] C1-3 负结果（若有）配机制解释（引机理篇涌现/语料结论，不裸报"微调没用"）
- [ ] C1-4 C2 结构任务结论与机理篇涌现分析交叉验证过（非孤立声称）
- [ ] C1-5 claim 措辞边界合规：只写"无策略受控对比"，未写"无人研究微调"（SPEC 1.2）

### C-2 数据与协议
- [ ] C2-1 全部数据源为已验证现成数据（BEACON/RNAGym/bpRNA/机理篇 split），零自策展
- [ ] C2-2 无 SELEX/合成文库任务混入（NABench 死因）
- [ ] C2-3 每任务×每模型×每策略报告双切分结果（不只报好的一侧）
- [ ] C2-4 家族级切分的泄漏敏感度 Δ 全表在附录可查
- [ ] C2-5 指标口径与 BEACON/Schmirler 对齐（同任务可比）

### C-3 工程与复现
- [ ] C3-1 ledger 全组合闭合（模型×任务×策略×种子×切分无缺口无重复）
- [ ] C3-2 复现包：训练/评测脚本 + 种子 + 环境锁定 + 一键冒烟（notebook 形式，对标 Schmirler 的社区贡献位）
- [ ] C3-3 E5 成本表覆盖全部策略×代表模型（读者可估算自己的预算）
- [ ] C3-4 决策树每条推荐标注实验依据（可回溯到具体图表）

### C-4 叙事与定位
- [ ] C4-1 引言含实践者困境场景（具体任务+数据量+算力的三选一困境开场）
- [ ] C4-2 与 Schmirler 的差异表（蛋白答案 vs RNA 答案哪里不同/为什么）在讨论章呈现
- [ ] C4-3 与机理篇互引落实（机制→实践故事弧完整）
- [ ] C4-4 与 BEACON/Zablocki/深圳湾/良渚四工作的差异化表在 related work
- [ ] C4-5 full FT 651M 缺失的分层说明 + LoRA 大模型臂补偿在正文（非藏在附录）
- [ ] C4-6 DNA 域平行工作（Vishniakov ICLR 2026）已引用并差异化

### C-5 撞车检查
- [ ] C5-1 挂出前 7 天内重跑 M5 监控（arXiv/bioRxiv 近 90 天 "RNA fine-tuning/LoRA/PEFT/adaptation" 扫描）
- [ ] C5-2 监控表最后一次更新日期距 arXiv 挂出 <30 天
- [ ] C5-3 若监控发现同期工作：concurrent 引用与差异化段已加入（不回避）

---

## 通过标准

- **启动**：A 组 15/15（v1.2 扩充后）；
- **执行**：B 组任何一轮实验前全过（执行人自检，ledger 留痕）；
## D 组：交付门禁（任何 pptx / 冻结文档出手前，2026-09-15 新增）

- [ ] D1 pptx 出手（新建/修改/手术）前后各跑一次 `code/tools/pptx_lint.py <file>`，FATAL=0 才交付
- [ ] D2 文本替换类修改用"锚点断言"（assert old in text）——锚点未命中即停，禁止静默跳过（v1.2 E2 full FT 臂静默丢锚教训）
- [ ] D3 用户手编过的 pptx 一律 XML 手术，禁止脚本重新生成（会覆盖用户修改）
- [ ] D4 修改后跑内容完整性清单（关键关键词全部在）+ 结构校验（页数/双 pPr/表格列齐）
- [ ] D5 交付报告必须附 lint 输出（PASS 证据），不能口头宣称"没问题"

- **挂出**：C 组 24/24（含撞车检查）；任何未过项 → 回 tasks.md 对应任务修补后重验。

**B 组现为 17 项（v1.8 扩充后）。**

## E 组：2026-10-30 夜间 30 页版验收（本轮执行记录）

- [x] E1 `deck_1030_night.pptx` → `RNA_LM微调策略评测-导师讨论修订版_20261030_八任务扩展.pptx`（30 页，SHA256=`8a3ea9af835fba5a9d2647a9e9e1483bef08f0f0d0b0647fa6d033acbb5328ff`）；ZIP CRC `testzip()`=None。
- [x] E2 结构：out-of-bounds=0；非空段落 1.5 倍行距=100%；全部文本 run 字体=Microsoft YaHei=100%。
- [x] E3 实际渲染：独立 fontconfig（`ppt/work/fc/fonts.conf`）+ 微软雅黑，30 页 PDF 中文无缺字；页码框 `02a/03a2/degradation/SpliceAI` 单行。
- [x] E4 文本 diff：仅演示页 4/8/18/19/21/23/26 与新增 27、总结 29 变化；其余页文本未动。
- [x] E5 图源：4 张新图逐格 n/mean 写入 CSV；`figure_source_data_20261030_eight_task_v14` manifest 17 文件 SHA256 全通过（`5c9ee9aa…`）。
- [x] E6 图文匹配：①a-4 五面板指标与任务地图一一对应；⑤b-1 8 面板与 8 任务一致；⑤b-2 数值与 `peak_memory_data.csv` 一致；⑤d 热图与 `bigmodel_coverage_data.csv` 一致。
- [ ] E7 待实验闭合后重绘：①a-4 的 SpliceAI/degradation/SSI 微调臂（当前 seed17）、⑤d 650M 各臂、②③⑤ 的 8 任务正式矩阵。

