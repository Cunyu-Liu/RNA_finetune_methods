# RNA-LM 微调策略评测：验收清单（CHECKLIST）

> 版本：1.16（2026-11-01 修订十六【结论归属与机制/异常复核】：B29改为④等价与⑤scaling分工、成本⑥遗忘⑦；新增B33分类组合图、SpliceAI三种子、MRL负值重评与shuffle停止曲线门禁。）
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
- [ ] B29 **逐结论八任务覆盖与归属**：结论①a/②/③/④/⑤及成本⑥、遗忘⑦均逐任务核对 ncRNA、CRISPR、modification、MRL、SpliceAI、SSP、degradation、SSI；④只做同族 small-full(n)↔large-LoRA(m) 等价，⑤只做模型内三策略 scaling，时间/显存独立为⑥；缺任何任务必须标范围，不得以三任务扩展页、单任务资源图或混乱的⑤c/⑤b子编号代替完整结论【2026-11-01 更新，见 spec §10.39 / tasks N16】
- [ ] B33 **机制组合图与异常复核门禁**：分类任务的表示图必须与同 seed/split 的 full-test 性能同图呈现，SpliceAI 需 seed17/29/43；回归 t-SNE 保留且不算分类 silhouette。MRL 负 Pearson r 必须回源并用逐样本预测或 CUDA 重评复算，不得只用指标定义解释；shuffle 曲线须核对停止合同，不得把早停短曲线误判为漏画【见 spec §10.39 / tasks N16】
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

## F 组：2026-11-01 v16 阶段验收

- [x] F1 输入：v16 共 1092 accepted、1 rejected，RID 唯一，v15 的 1086 行逐字段保留；所有 accepted 行保留 RTX 5090/CUDA 证据。
- [x] F2 SpliceAI：random/family × seed17/29/43 × pre/LoRA/full 组合图均完成，坐标与 full-test macro-F1 逐 seed 对账；两种子页连续呈现。
- [x] F3 页面：当前 PPT 共 30 页，`pptx_lint.py` PASS；`validate_report_layout.py` 的越界、Microsoft YaHei、1.5 倍行距、字号和 ZIP CRC 全过；30 页 PDF 实际渲染复核。
- [x] F4 哈希：PPT=`f4cbfd1bdb6302fd3e3280cf162291f7b78269c4d09465026352d7a5c30fb09b`，PDF=`38ee3c04023b6408c80d9c05948976b300ed99db0a2adab4be34563489e512d3`；主图/分类图 manifest 分别为 79/53 文件。
- [ ] F5 科学边界：④/⑤仍 4/8 面板可判，主矩阵、LR/rank、Frozen scaling、CRISPR 信号档、RNA-Sc 等价线和 E6 大格未全闭合；不得据本阶段验收宣称全部实验完成。
- [ ] F6 最终工作：完成剩余实验后再做全稿图文复核、旧文档/废弃绘图源归档与三地同步。

## G 组：2026-11-01 v17 LR 定向验收

- [x] G1 LR：75/320 complete；18/80 组四档完整，选择只看 held-out best_val，test 不参与；已闭合组未选择 3e-4 只作 interim，未生成 tuned 正式任务。
- [x] G2 主矩阵：per-base 96/270 complete；verify-only 的退出码 1 表示仍有未完成格，不等于训练失败或 proof 冲突。
- [x] G3 v17：1099 accepted、1 rejected，v16 行不变；主图 manifest 81 文件全哈希通过。
- [x] G4 PPT：30 页，SHA256=`4c86074a1de7e40109a994dc038781f72f4c1236786b6661b8f75ac9832f8874`；lint/layout/字体/行距/CRC/渲染通过，原第 18 页（现第 19 页）明确 LR 阶段性边界。
- [ ] G5 未闭合：80 组 LR、default/tuned 正式复测及其余科学矩阵继续执行，当前仍不是全实验终版。

## H 组：complementary 错根恢复验收

- [x] H1 全量审计：276 complete、48 incomplete，其中 4 个真实 conflict；其余 44 格为 runnable/running，未将 verify-only 退出码当作训练失败。
- [x] H2 源证：4 格 `/root` result/plateau/best.ckpt 完整且源路径 proof=complete；无 teams 目标目录和同名活跃 runner，未重训。
- [x] H3 迁移：19 个文件无覆盖复制并逐哈希一致，源目录保留；迁移后 4 格 teams proof=complete。complementary 现为 280/324 complete。
- [x] H4 台账：v20 仅更新 4 行 artifact/result/checkpoint 路径，其他字段不变；总行数 1102，不用路径恢复冒充新科学结果。
- [ ] H5 后续：其余 44 格继续按 proof 补跑；当前 PPT 仍为 v17 阶段讨论版。

## I 组：v28 degradation 等价与 cap 验收

- [x] I1 数据：v28 共 1137 accepted、1 rejected；degradation 33M-full 三档、148M-LoRA 两档三种子，满足④门槛；33M-LoRA 两档，不满足⑤新面板门槛。
- [x] I2 配对：独立复算 full1500≈LoRA1000、full2000(cap1552)≈LoRA1500；full1000↔LoRA1000 未等价。逐 seed 差值和 CI 与构图 metadata 一致。
- [x] I3 cap：5 行 requested=2000/actual=1552，未标注的 1552 格未混入专用档；图注、页内说明和 metadata 一致。
- [x] I4 交付：30 页 PPT SHA256=`6f07cb392db6fc59c5987fe84010c69f87dbaad68a3331b49cc8b5e95ca8b449`；PDF SHA256=`ccdb446c47170ec2f8bedafc4ed0c75a8fdb7eafa45f26ae3b0574437cb0095d`；lint/layout/字体/行距/CRC/渲染通过。
- [ ] I5 边界：④5/8、⑤4/8，其余分层、Frozen、SSI 和全量科学矩阵继续执行，不宣称最终完成。

## J 组：v29 ④/⑤与嵌图一致性验收

- [x] J1 数据：v29 共 1140 accepted、1 rejected；degradation 33M-full/LoRA 均三档，④/⑤均 5/8。
- [x] J2 cap：requested 2000/2500 均 actual=1552，8 个 cap 行入 metadata，图内明确标注，不把重复上限解释为新增数据。
- [x] J3 嵌图：首次发现⑤旧 v4 图片未替换后，已补 `replace_picture()`；最终嵌图与源 PNG SHA=`fc4d4e5822de08ba403960ebc794ada5bc1f0264f00af7538e20a388eaee1e0c` 一致。
- [x] J4 交付：PPT SHA256=`6081017e88ae18eaad8d4325e5a68b13ac4d3d94da8951b14d0a4796be7d3307`；PDF SHA256=`a378075ecc1d754c5ff94bb96e546386165fc00bdb0a418703b242b7574c9ff2`；30 页 lint/layout/CRC/实际渲染通过。
- [ ] J5 边界：其余任务、Frozen 和完整科学矩阵继续执行，④/⑤的 5/8 不是全实验完成。

## K 组：v30 cap 候选与分档验收

- [x] K1 数据：v30 共 1148 accepted、1 rejected；degradation 三臂均至少三档，④/⑤均 5/8。
- [x] K2 候选：full2500(cap1552)≈LoRA1500；full2500≈LoRA2000 也满足规则，页面明确候选非唯一，不写唯一交点。
- [x] K3 cap：2000/2500 同 actual=1552，13 个 cap 行入 metadata，不重复计为新增数据证据。
- [x] K4 交付：PPT SHA256=`4420d4e51fd4e0668a5ff63d9afc5c269c747b4ac8a33f9871391acf2ac5cac1`；PDF SHA256=`9695f050e3e0133924b119f4590c606a727e7830d0e231455d1a0f7af8225d40`；④/⑤ lint/layout/CRC/渲染通过。
- [ ] K5 后续：degradation family/3000 档、SSI 和其他科学矩阵继续执行。

## L 组：v43 SSI scaling 与 cap split 验收

- [x] L1 数据：v43 共 1222 accepted、1 rejected；SSI 33M-full/LoRA 三档三种子，⑤达 6/8，④仍 5/8。
- [x] L2 cap split：首次发现 family actual=1680 混入 random 标签后，已将 cap 限定当前 split；random 只显示 1552，metadata 逐行保留 split。
- [x] L3 交付：PPT SHA256=`e0500164654d1a2548ba46997a6b4538c88b4ce1398bed143e3ab1a944f3d9b6`；PDF SHA256=`0688b217f77ee4292a8d0c15e2a432362f9f56de76292806e4b0086a21f2d8bd`；30 页 lint/layout/CRC/渲染通过。
- [ ] L4 后续：继续 SSI 148M-LoRA 第二档和其他科学矩阵，不提前宣称全实验完成。

## M 组：v51 SSI 等价候选验收

- [x] M1 数据：v51 共 1258 accepted、1 rejected；SSI 148M-LoRA 两档三种子，④达 6/8，⑤保持 6/8。
- [x] M2 配对：只有 full2000≈LoRA1500 合格，Δ=−0.000599762、CI=0.002969352；其他近值 CI 不覆盖 0，不写等价。
- [x] M3 交付：PPT SHA256=`f42956457d25b348073a5a30e30c6053fd4f141fc3ac557ee94ec9c09a80fe27`；PDF SHA256=`6677a73f02f46de13c36752078246ebc569a097cf152a9a20f2470cc8719561b`；④/⑤ lint/layout/CRC/渲染通过。
- [ ] M4 后续：继续其他任务、family、Frozen 和全量科学矩阵，不提前宣称全实验完成。

## N 组：v52 图源一致性与实际渲染验收

- [x] N1 训练：v52 共 1276 accepted、1 rejected；18 个新增格均 proof=complete，result/plateau/checkpoint/CUDA/convergence 独立复核通过。
- [x] N2 科学边界：④/⑤均 6/8；SSI 33M-full/LoRA 五档、148M-LoRA 两档，等价候选不变，mega n2000 未闭合不补点。
- [x] N3 图源：图、CSV、metadata、脚本和 v52 台账统一；150 文件逐哈希，manifest SHA256=`8003394a861f801d70d057f5b246600c366ea4b5e335e529f94220ae3087ffcc`。
- [x] N4 版式与溯源：第25页图片/读图框重叠已修复，显存图旧日期脚注已改为动态 v52；六张嵌图 SHA、30 页 lint/layout/CRC 和实际渲染通过。
- [x] N5 交付哈希：PPT=`1ea24b847e64bdb77238c914de0f8f98b4620363a9236363d622272e48b46505`；PDF=`ed4c7b224e3a846f80022f9a9242714070bfe41d01ac48915835d564ff73d74c`。
- [ ] N6 后续：全量科学矩阵、family、Frozen、LR/rank、CRISPR 信号档、RNA-Sc 与 E6 继续按阶段门执行。

## O 组：v53 SSI 多候选与队列审计验收

- [x] O1 数据：v53 共 1292 accepted、1 rejected；16 个新增格均 proof=complete，CUDA/convergence 复核通过。
- [x] O2 候选：三组 SSI 等价候选逐 seed 独立复算通过，正文写“候选非唯一”；④/⑤均 6/8，148M-LoRA 四档。
- [x] O3 审计：per-base 105/270、LR 76/320、rank4/16 65/96 为实时 proof 进度，不与 v53 新增混算。
- [x] O4 交付：152 文件 manifest SHA256=`1b9aeb2c0f41bc7786d06faffdb88f24fcd7102f0e7881fa695abce127491d12`；PPT=`f8151e1604663948ece241e6115cf20cd02e594a2ca4390db5759fdacd1ca5da`；PDF=`cfd9726650767e7258cc9648b15603a15f2f653775fe8e215f583330fd6a6ec8`；嵌图、lint/layout/CRC 和实际渲染通过。
- [ ] O5 后续：其余 family、主矩阵、LR/rank、Frozen 和后续阶段继续执行。

## P 组：v54 SSI 三臂与 LR 阶段验收

- [x] P1 数据：v54 共 1315 accepted、1 rejected；23 个新增格均 proof=complete，CUDA/convergence 通过。
- [x] P2 科学边界：SSI random 三臂五档，④候选仍三组；④/⑤均 6/8，family mega n1500 未闭合。
- [x] P3 其他矩阵：LR 76/320、19/80 组闭合，选档未选 3e-4；per-base 106/270、complementary 280/324、rank 65/96。
- [x] P4 交付：154 文件 manifest=`8849f8c6ccc7df35b7f37a14e551e21031469b459e2aaa9d82e0d8dc64f86cca`；PPT=`6936bc7bce748962f7947b243aa2a11258b77f4cde00c4846ec180e5984584d6`；PDF=`94f453080ed96290b74f715db7b02b915943854d41c8256d8cd059fc9db8ad23`；嵌图、lint/layout/CRC、渲染通过。
- [ ] P5 后续：其余 family、主矩阵、LR/rank、Frozen 和后续阶段继续执行。

## Q 组：v55 队列去重与 family 验收

- [x] Q1 数据：v55 共 1324 accepted、1 rejected；9 个新增格最终均 proof=complete。
- [x] Q2 科学边界：SSI family full/micro-LoRA 五档、mega-LoRA 三档；random④/⑤不变。degradation 覆盖仍 14/30，不把阶段表替换计作新增覆盖。
- [x] Q3 去重：较晚重复进程已终止，三个重叠父队列已退休；8 live run/8 RID/0 重复，统一 equiv/lora_tiers 保留。
- [x] Q4 证据与交付：队列证据入源包，157 文件 manifest=`485ac4887b0e6f1b854bc3dd72f88c0ea867cdbfcf2882b44690a53f9c1f2752`；PPT=`e61f2469b78054583ab0e840426c6696b3d2c5b6334358cd0d186477e0b05034`；PDF=`7067c6bd7fd514630a7791678be3fbd695e89069e964dd33b0e3d06211f0a5da`；嵌图、lint/layout/CRC、渲染通过。
- [ ] Q5 后续：不得重启重叠专用队列；继续统一队列和后续科学矩阵。

## R 组：v58 family 图与 32 页验收

- [x] R1 数据：v58 共 1332 accepted、1 rejected；2 格 proof=complete，LR 77/320 但完整组仍 19/80。
- [x] R2 family：④/⑤均 5/8，各 split 候选独立复算；random panels/candidates 不变，degradation cap=1680。
- [x] R3 覆盖：SSI 正式单元修正为 13/30，不用阶段表替代未齐 best-val 种子。
- [x] R4 工程：32 页 ZIP 无重复条目、CRC 通过；克隆 RID 映射和 slide31 冲突已修复；嵌图、字体、行距、布局和实际渲染通过。
- [x] R5 交付：176 文件 manifest=`abf4607438d886299eba5e3d5b15ad30f8c621b246a1b42bba5cf5d980232b10`；PPT=`eab7aabfe732088073df37cf7cf784761335b77702049eb1e38e8f32fd4b067a`；PDF=`01a1371f9af0d686bf68fb7935a9a74add84fa0187fe06b67ea53861154a5990`。
- [ ] R6 后续：ncRNA family 和其他矩阵继续补，不宣称全实验完成。

## S 组：v59 family 五档验收

- [x] S1 数据：v59 共 1340 accepted、1 rejected；8 格 proof=complete，LR 78/320 但完整组仍 19/80。
- [x] S2 family⑤：SSI 三臂五档，degradation 5/5/4 档；family④/⑤仍 5/8，random 不变。
- [x] S3 cap：degradation family 四组候选中 requested 2000–3000 同 actual=1680，不重复计数据收益；MRL/SSI 候选不变。
- [x] S4 交付：178 文件 manifest=`600f1499061c83e2589babf240ec4ebd6b7e7b5854e23b78a26caf1f316c1e68`；PPT=`ef56c08380dbf7afd680e105c5759eaa3075376468fc7fa2a29aeeb704af951f`；PDF=`6d4f49e7f0ab7b646b62b29be5e512c7650ff8edbd41c6425d6cc70894d52bfd`；32 页嵌图、lint/layout/CRC、渲染通过。
- [ ] S5 后续：补推 af3de2f 及后续提交；继续 ncRNA family 和其他真实缺口。

## T 组：v60 正式覆盖与 LR 20 组验收

- [x] T1 数据：v60 共 1344 accepted、1 rejected；4 格 proof=complete。
- [x] T2 主矩阵：ERNIE SSI frozen-random 三种子闭合，①a-4 为 25/26/17/14/14，不用阶段表补齐。
- [x] T3 LR：80/320、20/80 组完整；新组 validation 选 1e-5，test 不参与，选档分布 8/8/4/0。
- [x] T4 交付：180 文件 manifest=`9b385523ccc243af8fb643a26cb337fd726efe36cdc01b54667f667e55a81102`；PPT=`33f45133c73355f6cf29e24cf6280dcb8374a2139bc978ba983a14a700aa2e0d`；PDF=`d49998702494246a37793cee54823dcdacabe509c9cd9cd8b0a5bbbf36b488dc`；32 页嵌图、lint/layout/CRC、渲染通过。
- [ ] T5 后续：补推待推提交，继续主矩阵、ncRNA family 和后续阶段。

## U 组：v64 路径恢复与 LR 21 组验收

- [x] U1 路径：teams 完整副本前后 proof=complete，仅修 ledger 路径、不重跑，artifact SHA 留证；v64 rejected=0。
- [x] U2 数据：1352 accepted、0 rejected；3 格 proof=complete，SpliceAI 覆盖 18/30，SSI 14/30。
- [x] U3 LR：84/320、21/80 组完整；新组 validation 选 1e-5，选档分布 8/8/5/0，test 不参与。
- [x] U4 交付：189 文件 manifest=`0131b8eb5b175ecda8aa968c7d822306d77fa4662e553dfc953db7acc625658e`；PPT=`704ae8f0d45c6298bff1c35b08b9de62807236df3085b20e10e2fdd8b0b8ca6a`；PDF=`f7c5332c4030139a948057e4d721fe066a9b46cbe5ee669faa47bfafa652affc`；32 页嵌图、lint/layout/CRC、渲染通过。
- [ ] U5 后续：继续其他真实缺口并补推待推提交。

## V 组：v65 ERNIE SSI family 验收

- [x] V1 数据：1356 accepted、0 rejected；4 格 proof=complete。
- [x] V2 主矩阵：ERNIE SSI frozen-family 三种子 mean=0.556195802，正式闭合，SSI 覆盖 15/30。
- [x] V3 边界：LR 86/320、完整组仍 21/80；SpliceAI low_signal，④/⑤不变。
- [x] V4 交付：191 文件 manifest=`f875cd1392b2e2e871c5c706ed3cd8af6f5ad9a727d50f501bdfe4ac8773505d`；PPT=`b89a50417f293bb7e7e3148f99f6c7d89fb87e454ddb47aef018704b07790540`；PDF=`53d93740ef9171d56156831e7938c85a5613c7e629d14339d7f61050947dc6d6`；32 页嵌图、lint/layout/CRC、渲染通过。
- [ ] V5 后续：继续其他真实缺口并提交本批交付。

## W 组：v66 RNA-FM CRISPR LR 验收

- [x] W1 数据：1359 accepted、0 rejected；3 格 proof=complete。
- [x] W2 LR：88/320、22/80 组完整；RNA-FM CRISPR full-random validation 选 3e-5，分布 9/8/5/0，test 不参与。
- [x] W3 交付：193 文件 manifest=`10d08978c5cccd93662e4949e9474d78c303a9021a23cb47b0ef74319d1dd366`；PPT=`63ae89e3c4864588999f5d0cd5827f4247fce7921f588f4ee16e290643b06645`；PDF=`46fb153cdcdd541806f1896e1ee4375843b9d935e8469549384f93631978b193`；32 页嵌图、lint/layout/CRC、渲染通过。
- [ ] W4 后续：继续其他真实缺口并提交本批交付。

## X 组：v68 RNA-FM family LR 验收

- [x] X1 数据：1367 accepted、0 rejected；3 格 proof=complete。
- [x] X2 LR：92/320、23/80 组完整；RNA-FM CRISPR full-family validation 选 1e-4，分布 9/9/5/0，test 不参与。
- [x] X3 交付：197 文件 manifest=`521dfaf63b5c46c8508c11db118fe8b15f75a931049bdd0ae83ea1d5e585f097`；PPT=`51810eee3fa4f125d5c41a7db55eaf93e5b51b1a68837bdaf4e1e35625f224ce`；PDF=`3b3acaa39bed1bb86d70fd3eaae0b83fbf062d41f4435af2817635a31ad45d4c`；32 页嵌图、lint/layout/CRC、渲染通过。
- [ ] X4 后续：继续其他真实缺口并提交本批交付。

## Y 组：v69 ERNIE SSI LoRA 与 rank 验收

- [x] Y1 数据：1371 accepted、0 rejected；4 格 proof=complete。
- [x] Y2 主矩阵：ERNIE SSI LoRA-random 三种子闭合，SSI 覆盖 16/30；per-base 120/270、rank 66/96。
- [x] Y3 边界：LR 93/320、完整组仍 23/80；MRL 新负值仅 tuning 诊断，④/⑤不变。
- [x] Y4 交付：199 文件 manifest=`4b96b214f5d4bf3cb035e8039c50d3e57dec3ddf44b2c16b352c63725ce9c32d`；PPT=`8912ed078a327135503d1f4d24b2635f9a5996bdf879baec4acdfb2b19a59019`；PDF=`ed337eb4eb9af7a2566e9c47ab12f1c39d6fda3c9d218352dcdb8574c5aa5547`；32 页嵌图、lint/layout/CRC、渲染通过。
- [ ] Y5 后续：继续其他真实缺口并提交本批交付。

## Z 组：v76 主矩阵与官方图验收

- [x] Z1 数据：1424 accepted、0 rejected；47 格均 proof=complete，CUDA/convergence 通过。
- [x] Z2 覆盖：①a-4 为 27/26/18/17/16；per-base 142/270、complementary 297/324、rank 67/96；650M frozen 新入库 17 格。
- [x] Z3 官方图：MRL 650M frozen 双 split 闭合，modification random 闭合、family 1/3；动态图仅预期单元变化。
- [x] Z4 LR：103/320、24/80 组完整；mega MRL random 选 3e-5，test r=0.798969709，test 不参与选档。
- [x] Z5 交付：227 文件 manifest=`c2c9df3680940631288228a6cf8ecdb8cb32c09065c7e0d917b39815ab09c3dd`；PPT=`b4c4138d3806d2bfaaccefe95520d794ad2d6df1d8fe9cb96db7ec3629841b17`；PDF=`8a720537b145f26012b5d451b586b48414c9b15ef512843f2f170ae7befd743a`；32 页嵌图、lint/layout/CRC、渲染通过。
- [ ] Z6 后续：继续其他真实缺口并提交动态图脚本与文档。

## AA 组：v77 SpliceAI 与 modification 验收

- [x] AA1 数据：1428 accepted、0 rejected；4 格 proof=complete。
- [x] AA2 主矩阵：mega SpliceAI full-random 三种子闭合，SpliceAI 覆盖 19/30；per-base 144/270、complementary 298/324。
- [x] AA3 650M：modification frozen-family 为 n=2 斜线，random 三种子不变；MRL 和④/⑤不变。
- [x] AA4 交付：229 文件 manifest=`66dc9eb61ae3e09bf75d713d3e687e94da168e2de5eba20659497a4c653c507c`；PPT=`d803f96747c06f9a423e813173ed309d6ba70861930ae6522aa771953962c6ea`；PDF=`85060f303a4516cdb4a176bd709e12c1b57039c7c3158dbe5b46a03a10f37a83`；32 页嵌图、lint/layout/CRC、渲染通过。
- [ ] AA5 后续：继续其他真实缺口并提交本批交付。

## AB 组：v78 650M modification 闭合验收

- [x] AB1 数据：1430 accepted、0 rejected；2 格 proof=complete。
- [x] AB2 主矩阵：650M modification frozen-family 三种子 mean=0.660210309，双 split 闭合；RNA-FM SSI LoRA-random 为 2/3。
- [x] AB3 交付：231 文件 manifest=`780b8fc039487a9c7a086e7097f00777a20fdad61403e577e76a700fddfb774a`；PPT=`fcde2a2d92eeb5927b09618304c8ae723aa2b9d099c23928bb0923f45ba1f3a0`；PDF=`fed444a6657773ac27af0d95ad0fe1daaf0dbd25c0584d379be41ed1a680f941`；32 页嵌图、lint/layout/CRC、渲染通过。
- [ ] AB4 后续：继续其他真实缺口并提交本批交付。

## AC 组：v80 RNA-FM SSI 与 650M SSP 验收

- [x] AC1 数据：1433 accepted、0 rejected；2 格 proof=complete。
- [x] AC2 主矩阵：RNA-FM SSI LoRA-random 三种子 mean=0.630093485，SSI 覆盖 17/30；650M SSP 为 1/3，SSP 仍 26/30。
- [x] AC3 交付：235 文件 manifest=`3198fd091d726d53bb11935016a27cbd1dfacfd6baabcf69b2adec2c7fa71ab4`；PPT=`6049a44feca49f0bf1823d4c84669dadbc0b3bd77a0b749fd0de789536887ae0`；PDF=`b405175eea336c4f34b0a4303a10ee661e699fd60c7f1e72197688104b32955c`；32 页嵌图、lint/layout/CRC、渲染通过。
- [ ] AC4 后续：继续其他真实缺口并提交本批交付。

## AD 组：v86 650M SSP 三种子闭合验收

- [x] AD1 数据：1438 accepted、0 rejected；新增 seed43 pair-F1=0.2636，proof=complete，checkpoint/CUDA/convergence 独立复核通过。
- [x] AD2 科学单元：650M SSP frozen-random 三种子 mean≈0.250967；SSP 覆盖 27/30，①a-4 为 27/27/19/17/17。
- [x] AD3 边界：per-base 146/270、complementary 302/324、LR 107/320（24/80 组）、rank 67/96；④/⑤与 validation 选档规则不变。
- [x] AD4 交付：247 文件 manifest=`845920a3c818a40258ad9fe2c3da6d6dbe1b312a62e84b21ea88c6cb462a8189`；PPT=`83a708ab22ae2f93be732bb4bd622b26239e4d6cd684d3c0feded2d87f503e56`，PDF=`fa11997cbd00e02bba9f24514c24adbfc261e08227c46f7e007cfa184c10a1a7`；32 页嵌图、lint/layout/CRC 和渲染通过。
- [ ] AD5 后续：完成三地同步与 GitHub 提交；继续真实科学缺口，不将此单元闭合视为全实验完成。

## AE 组：v87 staging 与 LR 计数纠偏验收

- [x] AE1 数据：1443 accepted、0 rejected；5 格 proof=complete，CUDA/convergence 通过，未形成新三种子单元。
- [x] AE2 矩阵：per-base 148/270、complementary 302/324、rank 68/96；④/⑤不变。
- [x] AE3 LR：逐格重算 108/320 complete、212 runnable，25/80 组完整，选档 11/9/5/0；第25组为 v79 漏计的 ERNIE MRL random，validation 选 1e-5，非 v87 新组。
- [x] AE4 交付：250 文件 manifest=`b0c2e75bc1caa3c803a0431ccb6822329fa029486103515234c9f9466c064876`；PPT=`4763f848d14edb56370d06c233e46f43762f1529b99e2e9b92772fdb7ce362c2`，PDF=`49fb729fcd327741302774b2ab563796c20fc3f28fe57dab2b1d36b65af475b4`；32 页 lint/layout/CRC、嵌图与 LR 页渲染通过。
- [ ] AE5 后续：三地同步并提交；继续真实科学缺口，80 组全闭合前不冻结正式 tuned 矩阵。

## AF 组：v88 RNA-FM SSI family 验收

- [x] AF1 数据：1446 accepted、0 rejected；3 格 proof=complete，CUDA/convergence 通过。
- [x] AF2 科学单元：RNA-FM SSI LoRA-family 三种子 mean≈0.592750128，SSI 覆盖 18/30，①a-4 为 27/27/19/17/18。
- [x] AF3 边界：650M SSP frozen-family 仅 1/3，SpliceAI tier 低信号；per-base 150/270、complementary 303/324、LR 108/320（25组）、rank 68/96，④/⑤不变。
- [x] AF4 交付：252 文件 manifest=`3ef91e4553c1f874c5d64362fcfe64a961d4da643b8c951aaafa6686f7c49b7e`；PPT=`20b3ffd36d099cea82367892d181e7d7ed4b12866ba9a25c5ce792818cd866fc`，PDF=`3701d2bbba135f33beccc069cc722977d42bf84642b9814f1157407c2c782b80`；十张嵌图、32 页 lint/layout/CRC 和第8/27/28/29页渲染通过。
- [ ] AF5 后续：完成三地同步与 GitHub 同步，继续真实科学缺口。

## AG 组：v89 低信号 staging 验收

- [x] AG1 数据：1447 accepted、0 rejected；新增 SpliceAI family/n3000/seed17 proof=complete，CUDA/convergence 通过。
- [x] AG2 科学边界：macro-F1=0.333280238，仍近随机，不形成新面板、scaling 或等价候选；①a-4 与④/⑤不变。
- [x] AG3 进度与展示：per-base 149/270、complementary 303/324、LR 108/320（25组）、rank 68/96；PPT 和 v83 源包保持 v88。
- [ ] AG4 后续：同步文档并提交，继续真实科学缺口。

## AH 组：v90 注册表计数审计

- [x] AH1 台账：v90 新增 0，仍 1447 accepted、0 rejected；展示版保持 v88。
- [x] AH2 精确计数：per-base 149/270、complementary 303/324、LR 108/320、rank 68/96、equiv 417/420、650M frozen 23/25。
- [x] AH3 纠偏：per-base 的 v86/v88/v89 权威值为 147/149/149，替代此前估算偏差；证据 SHA256=`8082d0df53c3e17c487c54f7c84e8cf35da4e835fa927ce05dcf00aa172c7f82`。
- [ ] AH4 后续：同步并提交审计记录，继续真实科学缺口，不另起重叠队列。

## AI 组：v91 equiv 低信号验收

- [x] AI1 数据：1448 accepted、0 rejected；新增 micro SpliceAI full-family/n3000/seed17 proof=complete，CUDA/convergence 通过。
- [x] AI2 科学边界：macro-F1=0.333280238，仍近随机，不用于等价或 scaling；equiv 418/420，其他矩阵计数不变。
- [x] AI3 展示：无新科学单元，PPT 与 v83 源包保持 v88。
- [ ] AI4 后续：同步并提交文档，继续剩余真实科学缺口。

## AJ 组：v92 650M SSP family n=2 验收

- [x] AJ1 数据：1449 accepted、0 rejected；新增 seed29 pair-F1=0.2711，proof=complete，CUDA/convergence 通过。
- [x] AJ2 科学边界：seed17/29=0.3237/0.2711，当前 2/3，不写闭合；①a-4 与④/⑤不变，650M frozen 24/25。
- [x] AJ3 交付：264 文件 manifest=`508c6387ab079e36130d938c81de2ceb2ef30860e139b7827f31d9cf3b193d1c`；PPT=`2dfc707a9030c173ea3399662ecdfaa8094bdfdfdc281fd021142b28d2eb385a`，PDF=`acb07573ab8e97f4712c502908963459da6482cf7239db808ba5c6f069815339`；嵌图、lint/layout/CRC 与四个更新页渲染通过。
- [ ] AJ4 后续：三地同步并推送，等待 seed43，继续真实科学缺口。

## AK 组：v93 equiv 与 LR staging 验收

- [x] AK1 数据：1451 accepted、0 rejected；两格 proof=complete，CUDA/convergence 通过。
- [x] AK2 equiv：419/420，新增 SpliceAI 格仍近随机，不用于等价或 scaling。
- [x] AK3 LR：ERNIE MRL family 已有三档、缺 1e-5；109/320，完整组仍25/80，不提前选档。
- [x] AK4 展示：无新科学单元，PPT 与 v84 源包保持 v92。
- [ ] AK5 后续：同步并提交文档，继续剩余真实科学缺口。

## AL 组：v94 在训状态验收

- [x] AL1 台账：v94 新增 0，仍 1451 accepted、0 rejected；展示版保持 v92。
- [x] AL2 进度：SSP seed43 与 equiv degradation 均已有 epoch 推进，mega SpliceAI full-family 未卡死；仅作 RUNNING/PENDING 证据。
- [x] AL3 边界：不得把中间 loss、进程存活或 pre-plateau 写成最终科学结论；证据 SHA256=`b674a7cf5c9e09e2cbfabb9c60c25d5986c2482b64d6e0ce3721e10491246848`。
- [ ] AL4 后续：同步并提交记录，等待完整证明。

## AM 组：v96 equiv canonical 与 family 五档验收

- [x] AM1 数据：v95 无新增；v96 为 1452 accepted、0 rejected，新增格 proof=complete、CUDA 收敛。
- [x] AM2 equiv：canonical 420/420，dense 诊断不计入；其他主矩阵和 LR/rank 继续。
- [x] AM3 family：degradation 三臂五档，④候选不变，cap 边界不变；random④/⑤=6/8、family④/⑤=5/8。
- [x] AM4 交付：275 文件 manifest=`804d3822db3174de2e24628468f3ce52fefc42a99fc37ef790dd2350389fc5fe`；PPT=`0efc70be20c74dbb0e496cf6d60fb5b8a40b1c1af71805f8e5ee6a07f7f7d4a0`，PDF=`418215d64737eeab55a3a662de939d4c3e0f911c4ec38eb225dd47b47778cb75`；嵌图、lint/layout/CRC 与④/⑤渲染通过。
- [ ] AM5 后续：同步并推送，继续真实科学缺口，不宣称全实验完成。

## AN 组：v97 LR 第26组验收

- [x] AN1 数据：1453 accepted、0 rejected；新增 ERNIE MRL family 1e-5 格 proof=complete、CUDA 收敛。
- [x] AN2 选档：四档闭合，validation 选3e-5（best_val=0.516094），test 不参与；LR 110/320、26/80组，分布12/9/5/0。
- [x] AN3 交付：279 文件 manifest=`f7abfe573cf4c5577a1c6a662da644038ca9e089863c624f2e7f6d26ff609117`；PPT=`f30bbce2e888c33c80035df18db0e52c1a42f92a1a7065cafd1853e4c273ae8c`，PDF=`096bb834d6906d765523abc38f1b39b179b70309372ce5d5ec2cf4bdfb85a363`；嵌图、lint/layout/CRC 与 LR 页渲染通过。
- [ ] AN4 后续：三地同步并补推，继续真实科学缺口，80组全闭合前不冻结 tuned 正式矩阵。

## AO 组：v98 650M SSP family 闭合验收

- [x] AO1 数据：1455 accepted、0 rejected；两格 proof=complete、CUDA 收敛。
- [x] AO2 SSP：frozen-family 三种子 mean≈0.291666667，SSP覆盖28/30，①a-4为27/28/19/17/18，650M frozen 25/25。
- [x] AO3 边界：RNA-FM MRL random tuning 仅1/4档，LR 111/320、完整组仍26/80；per-base 149/270、complementary 304/324、rank 68/96、equiv 420/420。
- [x] AO4 交付：282 文件 manifest=`81fccb0f004ab613475bd586273f4118769334fdffcf936f9f29e5decaa4cb2a`；PPT=`cb3ed7103fec5dd578e45b01c886c5b0265d3e8cc722c3bfea1ba197f6f0ad48`，PDF=`e3a1a1d507b82bd0da0b2f7e976ae66994834546296c02dae1db02161ed2c024`；嵌图、lint/layout/CRC 与四个更新页渲染通过。
- [ ] AO5 后续：三地同步并补推，继续真实科学缺口。

## AP 组：v99 LR 第二档 staging 验收

- [x] AP1 数据：1456 accepted、0 rejected；RNA-FM MRL random 1e-4 格 proof=complete、CUDA 收敛。
- [x] AP2 边界：该组仅两档，LR 112/320、完整组仍26/80，不提前选档；其他矩阵计数不变。
- [x] AP3 展示：无新科学单元，PPT 与 v87 源包保持 v98。
- [ ] AP4 后续：同步并提交，等待四档闭合和其他真实科学缺口。

## AQ 组：v100 双 split LR 与 rank16 验收

- [x] AQ1 数据：1466 accepted、0 rejected；10 格 proof=complete、CUDA 收敛。
- [x] AQ2 LR：RNA-FM MRL random 选1e-5、family 选3e-5，test 不参与；120/320、28/80组，分布13/9/6/0。
- [x] AQ3 rank/主矩阵：SpliceAI random rank16 三种子 mean=0.481795666，rank 69/96；mega full-family 仅1/3，per-base 150/270、complementary 304/324。
- [x] AQ4 交付：289 文件 manifest=`7e318f82cf327cbae2787d11e274cecbcb5de48cd36667ad5c9be687c9c6f93f`；PPT=`e875cc79c4fe811eb0f01390763612bac0cb75cc7094a649f7ee514e4f10d0a2`，PDF=`49baa9f9670427aad9f7231ef5b2bb37707c1290b60026366db49f7baa6cc7d5`；嵌图、lint/layout/CRC 与六页渲染通过。
- [ ] AQ5 后续：三地同步并补推，继续真实科学缺口，不将 rank 阶段格写成完整矩阵结论。

## AR 组：v101 650M LoRA 启动验收

- [x] AR1 台账：v101 新增 0，仍 1466 accepted、0 rejected；展示版保持 v100。
- [x] AR2 审计：唯一 runnable 的 650M LoRA 为 CRISPR family/seed43，其他格 complete，无同名 runner。
- [x] AR3 启动：单格队列 need=16、1 worker，父4122509、子4122556，真实 CUDA 参数；启动不记完成，证据 SHA256=`b9d1fe1e4e988b7d45a2005031b9172ce4ca1de5dd1b7e424c5f59c6256547df`。
- [ ] AR4 后续：等待 result/plateau/checkpoint 完整证明，不在资源不足时强行启动大格。

## AS 组：v102 LR 第29组验收

- [x] AS1 数据：1468 accepted、0 rejected；两格 proof=complete、CUDA 收敛。
- [x] AS2 选档：micro SpliceAI full-family 选3e-5，test 不参与；LR 122/320、29/80组，分布14/9/6/0。
- [x] AS3 交付：296 文件 manifest=`46728646ba0b8d54ded25b38ed04a1c517d5fc5d1a410af57b0921bf3308ff73`；PPT=`e545b825f661ea8b93a3c551a0515ec9544305ef573a12114d57f719e5f2b15e`，PDF=`285d7aecd13fa50f21e6c3d4f84c9ca12d6206d6e87ff765598e4ba3501028bf`；嵌图、lint/layout/CRC 与 LR 页渲染通过。
- [ ] AS4 后续：三地同步并推送，继续真实科学缺口，80组全闭合前不冻结 tuned 正式矩阵。

## AT 组：v103 主矩阵、rank 与 LR 验收

- [x] AT1 数据：1537 accepted、0 rejected；69格 proof=complete、CUDA 收敛。
- [x] AT2 主矩阵：CRISPR/SpliceAI 覆盖28/20，①a-4为28/28/20/17/18；per-base 153/270、complementary 306/324。
- [x] AT3 LR：168/320、41/80组，分布19/12/9/1；RNA-FM modification family 默认档最优，旧表述已纠正，test 不参与。
- [x] AT4 rank：88/96、29/32组三种子闭合；只写同模型同split阶段结果，不与rank8直接排名。
- [x] AT5 交付：301 文件 manifest=`fcd8022436870149f0a5c97d4d429a3fc240e9462436479390dd09d011244fc3`；PPT=`9274ee5e25f812e50beefbc60428e83944a74e8851826e231de178e04fcd0291`，PDF=`f3fd759639c84ef4e839aee0019ccccc10e05a81ceb9cc4a696c46a8ef080285`；嵌图、lint/layout/CRC 与六页渲染通过。
- [ ] AT6 后续：三地同步并推送，继续真实科学缺口，不宣称全实验完成。

## AU 组：v104 rank 89/96 验收

- [x] AU1 数据：1539 accepted、0 rejected；两格 proof=complete、CUDA 收敛。
- [x] AU2 边界：ERNIE SSP random 仅2/4档，LR 170/320、完整组仍41/80；SSI family rank4 为2/3。
- [x] AU3 rank：89/96、29/32组三种子闭合，页面只更新进度，不写 SSI family 闭合。
- [x] AU4 交付：305 文件 manifest=`95c0e22718e7ebe7be6aa20a11391ec3c14dd939bb23ca7eba68b4cc1ab3e501`；PPT=`9c1b76dd2fa9cbc8a2621aa54af8d0df9cee2e4beaffdea2d159027800341f5d`，PDF=`28b25d044d13d09c80de1e45f343ccd0c84146b3ce8075429a61e7e54f49e07d`；嵌图、lint/layout/CRC 与 rank 页渲染通过。
- [ ] AU5 后续：三地同步并推送，继续剩余7格和其他真实科学缺口。

## AV 组：v105–v106 在训与资源门验收

- [x] AV1 台账：两版新增0，仍1539 accepted、0 rejected；展示版保持v104。
- [x] AV2 缺口：rank剩余7格全属SSI，未生成result的格不记完成。
- [x] AV3 资源：空闲22.45GiB低于650M full预算28GiB，未强行启动大格；现有队列继续。
- [ ] AV4 后续：同步并提交记录，等待完整证明和自然资源窗口。

## AW 组：v107 ERNIE SSP family tuning 验收

- [x] AW1 数据：1540 accepted、0 rejected；default格 proof=complete、CUDA 收敛，best_epoch=12、16 epochs。
- [x] AW2 边界：该组仅一档，LR 171/320、完整组仍41/80，不提前选档；其他矩阵计数不变。
- [x] AW3 展示：无新科学单元，PPT 与 v91 源包保持 v104。
- [ ] AW4 后续：同步并提交，等待其余三档和真实科学缺口。

## AX 组：v108 SSI family rank4 验收

- [x] AX1 数据：1541 accepted、0 rejected；新增seed43 proof=complete、CUDA 收敛。
- [x] AX2 rank：SSI family rank4 三种子 mean=0.597495111；90/96、30/32组闭合，剩余6格，不与rank8直接排名。
- [x] AX3 交付：316 文件 manifest=`e79a4715075160608f825f5d81cd28e4140b05a69edf48af111d9f4847564676`；PPT=`bbd35c8f9b5fc6b4d795a98c226f956b741036ced8c83cee20239d7a4eace0c8`，PDF=`610ebaa27e446e08ed7c407ac43d5f577f6e80d3e953f5ff76b2fd69d7eee6e4`；嵌图、lint/layout/CRC 与 rank 页渲染通过。
- [ ] AX4 后续：三地同步并推送，继续剩余6格和其他真实科学缺口。

## AY 组：v109 SpliceAI family 首点验收

- [x] AY1 数据：1543 accepted、0 rejected；两格 proof=complete、CUDA 收敛。
- [x] AY2 主矩阵：mega SpliceAI LoRA-family 仅1/3，覆盖由0改1，三种子单元仍20/30，保留斜线。
- [x] AY3 边界：ERNIE SSP family 为2/4档，LR 172/320、完整组仍41/80；per-base 154/270、complementary 306/324、rank 90/96。
- [x] AY4 交付：319 文件 manifest=`25dcc3bea404cb05b8daaf51f7edcbb4301c387a6d5077062c98ee953ef8ea88`；PPT=`bed1e634abd53e58c0bcc415740c4d03a3e2da762701b4af3962983de68f716e`，PDF=`be6a6481d5d996e06a5801a9be0903ef96b6196a5753608bbc4e4dadfe787bd2`；嵌图、lint/layout/CRC 与四页渲染通过。
- [ ] AY5 后续：三地同步并推送，继续真实科学缺口。

## AZ 组：v110 SSI random rank16 首点验收

- [x] AZ1 数据：1544 accepted、0 rejected；新增seed17 proof=complete、CUDA 收敛。
- [x] AZ2 rank：SSI random rank16 为1/3，91/96、30/32组闭合，剩余5格，不写成三种子闭合。
- [x] AZ3 交付：323 文件 manifest=`f1d3d5f8b2de180ba2d16d2e2ad6a1836d435b0644aa6ce7ab2f3b528ebd9875`；PPT=`4c01e9c2f1122da9aead1c2722b53edfb35db1e387f3055e0d01398e515e3243`，PDF=`151d548f7f202ef38e0c39d4cae8438e25976678a9189b893a5a46c2801019e4`；嵌图、lint/layout/CRC 与 rank 页渲染通过。
- [ ] AZ4 后续：三地同步并推送，继续剩余5格和其他真实科学缺口。

## BA 组：v111 ERNIE SSP family LR 第三档验收

- [x] BA1 数据：1545 accepted、0 rejected；3e-5格 proof=complete、CUDA 收敛。
- [x] BA2 边界：该组已有三档、缺1e-5，LR 173/320、完整组仍41/80，不提前选档。
- [x] BA3 展示：无新科学单元，PPT 与 v94 源包保持 v110。
- [ ] BA4 后续：同步并提交，等待第四档和真实科学缺口。

## BB 组：v112 SSI random rank16 第二种子验收

- [x] BB1 数据：1546 accepted、0 rejected；新增seed29 proof=complete、CUDA 收敛。
- [x] BB2 rank：SSI random rank16 为2/3，92/96、30/32组闭合，剩余4格，不写成三种子闭合。
- [x] BB3 交付：330 文件 manifest=`fb9ee5b869877e551e1327acff1dfb615f870a35a4e68adb93ad7b07149b8b16`；PPT=`417c5b50358cef089baa6d598103c6e0dd0a1704f5dede02c47042a790b9095e`，PDF=`90f2f0b7424a5e7b5a11907680c138b15d573ece1ea970d752044281332bc468`；嵌图、lint/layout/CRC 与 rank 页渲染通过。
- [ ] BB4 后续：三地同步并补推，继续剩余4格和其他真实科学缺口。

## BC 组：v113 LR 第42组验收

- [x] BC1 数据：1547 accepted、0 rejected；新增 ERNIE SSP family 1e-5格 proof=complete、CUDA 收敛。
- [x] BC2 选档：四档闭合，validation 选1e-4（best_val=0.388270），test 不参与；LR 174/320、42/80组，分布19/13/9/1。
- [x] BC3 交付：334 文件 manifest=`eb7a3065eef5fba25eb025a4f931075396189de33f6c94251fa9fa6d512c78d2`；PPT=`3e5c3b95c440293d203f5262d94e6bb156738e7c0e84ab8b39cd7e3e58e803a4`，PDF=`9e4c0be9e0d1e8d51b6efbca3332bece0b8c10a6a720174132aed75e5be22500`；嵌图、lint/layout/CRC 与 LR 页渲染通过。
- [ ] BC4 后续：三地同步并补推，继续真实科学缺口，80组全闭合前不冻结 tuned 正式矩阵。

## BD 组：v114 SSI random rank16 验收

- [x] BD1 数据：1549 accepted、0 rejected；两格 proof=complete、CUDA 收敛。
- [x] BD2 rank：SSI random rank16 三种子 mean=0.634602631；93/96、31/32组闭合，仅剩family rank16三格。
- [x] BD3 边界：RNA-FM SSP random default 仅1/4档，LR 175/320、完整组仍42/80；per-base 154/270、complementary 306/324。
- [x] BD4 交付：338 文件 manifest=`711969fb0eeb7eb7534f1f2068b3c823242755d3f9adc75e21f82d163454a895`；PPT=`2064f15759c017dd664dace4230cf1de7e0a1bbdcab124d4c3c3350a971eb492`，PDF=`2d9a0f8693d92e7c754bd10d77b5bdb44eaf9680218afd377c0b734ab3c212fb`；嵌图、lint/layout/CRC 与 rank 页渲染通过。
- [ ] BD5 后续：三地同步并补推，继续剩余3格和其他真实科学缺口。

## BE 组：ncRNA 性能总览页验收

- [x] BE1 数据：ncRNA 28/30 个三种子单元，沿用 v114，不重跑实验。
- [x] BE2 图源：固定 LR 六柱、mean±SD、斜线=n<3、空白=NA；源包344文件，manifest=`4498127752f24a2932529585a98fa43dc383d8ab8cfca8e82948beb4681f3d44`。
- [x] BE3 结构：第5页性能总览与第6页机制诊断并存，后续页顺延；slide33重名已修复。
- [x] BE4 交付：33页 lint/layout/CRC、字体行距、11张嵌图与双页渲染通过；PPT=`15dfbef9ffb10fd3776a9d969dbe96bcd18b31584d1e64cadd7c87d52c65cae9`，PDF=`70f5dfe1a1b00cba8fe92aedb3311f48e0454999b3ab5d1ee3c6cad6c786a0c4`。
- [ ] BE5 后续：三地同步并推送，继续在安全预算内补位和完成真实科学缺口。

## BF 组：LR 小格优先调度验收

- [x] BF1 防重：旧父暂停后确认唯一子进程 ledger=running，仅终止父，不杀训练。
- [x] BF2 注册表：全部320格、原RID/result_dir/need_gb不变，按need升序；原表备份，new SHA256=`f9fdc348314be90a0a9c1de8e61d8efc582de3ba2557e8c31daea208c2bd9a9e`。
- [x] BF3 恢复：原state-dir新父45383，旧子43189继续；新父proof扫描不记完成，证据 SHA256=`f2261b6177f9f4ba85aff54ae7279d6a91fae6f43bdab3b0663956f75514882a`。
- [ ] BF4 后续：核验新子进程、唯一RID与实际显存，不为占显存制造OOM；同步并提交记录。

## BG 组：v115 rank 95/96 验收

- [x] BG1 数据：1553 accepted、0 rejected；4格 proof=complete、CUDA 收敛。
- [x] BG2 rank：SSI family rank16 为2/3，95/96、31/32组闭合，仅剩1格，不提前写成闭合。
- [x] BG3 LR：RNA-FM SSP random 已有三档、缺1e-5，LR 177/320、完整组仍42/80。
- [x] BG4 交付：348 文件 manifest=`2a48336dd0d650e82a11c0548c59affe4b0cec17851e08c7109b2f11ac3663b0`；PPT=`eb957ab8c154c555d2b71be1135196038ee18ad3f0e5ff693cf565c1cd98d0e5`，PDF=`b4d04ecf675779911e10ab2758a53c7a2aede081f6a6dbc2fb1101082c4243ba`；嵌图、33页 lint/layout/CRC 与 rank 页渲染通过。
- [ ] BG5 后续：三地同步并补推，继续最后1个rank格和其他真实科学缺口。

## BH 组：v116 rank 全闭合与 LR 第43组验收

- [x] BH1 数据：1558 accepted、0 rejected；5格 proof=complete、CUDA 收敛。
- [x] BH2 rank：96/96、32/32组三种子全部闭合；SSI family rank16 均值0.597398120。
- [x] BH3 LR：RNA-FM SSP random 默认3e-4最优，test 不参与；181/320、43/80组，分布19/13/9/2。
- [x] BH4 交付：353 文件 manifest=`9d0c18b2b209a411ebb5d93c48125218debd4b7d75cba24254a0e87eae6ec341`；PPT=`f23c69ad533b139409c93c29e9eea52c0687937d3abca68a8635166a8fd27d3e`，PDF=`b90f166d5f71795917908dcc2aad104bd278bbfd2ffabf8b44bcca38dd190c32`；嵌图、lint/layout/CRC 与第20/21页渲染通过。
- [ ] BH5 后续：三地同步并推送，继续真实科学缺口，不宣称全实验完成。

## BI 组：v117 LR 第44组与计数纠偏验收

- [x] BI1 数据：1562 accepted、0 rejected；4格 proof=complete、CUDA 收敛。
- [x] BI2 选档：degradation family 选3e-5，test 不参与；LR 184/320、44/80组，分布20/13/9/2，random default仍缺。
- [x] BI3 纠偏：v113–v116 accepted=173/174/176/180，此前均多1；完整组和选档不受影响，v117=184。
- [x] BI4 交付：357 文件 manifest=`4aea79e4e400a6d73045fe6d5dfe2bea5e1438de5307ac18956dc4aa39a5f7c1`；PPT=`bad37b10d3fdfe5c421788452aec8fe200b257e30b7de0a48b39fb0e793d0e9d`，PDF=`d6430dc92cc0dbf32ea9e3abd324b56e161219a38e2a5cf536a74f08426bfe08`；嵌图、lint/layout/CRC 与 LR 页渲染通过。
- [ ] BI5 后续：三地同步并推送，继续真实科学缺口。

## BJ 组：v118 ERNIE SSP random LR 第三档验收

- [x] BJ1 数据：1563 accepted、0 rejected；1e-4格 proof=complete、CUDA 收敛。
- [x] BJ2 边界：该组已有三档、缺 default，LR 185/320、完整组仍44/80，不提前选档。
- [x] BJ3 展示：无新科学单元，PPT 与 v101 源包保持 v117。
- [ ] BJ4 后续：同步并提交，等待 default 和真实科学缺口。

## BK 组：v119 LR 第45组验收

- [x] BK1 数据：1564 accepted、0 rejected；新增 ERNIE SSP random default 格 proof=complete、CUDA 收敛。
- [x] BK2 选档：四档闭合，validation 选1e-4（best_val=0.439936），test 不参与；LR 186/320、45/80组，分布20/14/9/2。
- [x] BK3 交付：364 文件 manifest=`f52c318385550b1bd0227a1ee23f1eaa243553c05096af9c16fbd0eb9a6bfde0`；PPT=`fd8908ae4071913292b4d177c22114d00cf87f83499eb92de599ad9377788eb6`，PDF=`8ed95f15f868db550dcd9322f3313b89d00ce481a88ddde981fb49da851e85d0`；嵌图、lint/layout/CRC 与 LR 页渲染通过。
- [ ] BK4 后续：三地同步并补推，继续真实科学缺口，80组全闭合前不冻结 tuned 正式矩阵。

## BL 组：v120–v121 长训与资源复核

- [x] BL1 台账：两版新增0，仍1564 accepted、0 rejected；展示版保持v119。
- [x] BL2 在训：SpliceAI seed29 的 plateau 正常推进，其他目标为pre-plateau，不把长训写成卡死或收敛。
- [x] BL3 资源：空闲23.36GiB低于650M full预算28GiB，未强行启动；证据 SHA256=`f475ef816c2c0b2f6a34a5545ffe2bfb184ac661cbfbb7217d87d47b7883ea21`。
- [ ] BL4 后续：同步并提交记录，等待完整证明和自然窗口。

## BM 组：v123 mega SpliceAI LoRA-family 第二种子验收

- [x] BM1 数据：1565 accepted、0 rejected；seed29 macro-F1=0.5265341727629625，proof=complete、CUDA收敛，独立证明SHA256=`1bac2265fa7d309a5b284b51611004cc299d6c4ac3f2b38201ac4ccbe89ff534`。
- [x] BM2 边界：seed17/29仅2/3，仍缺seed43；SpliceAI覆盖20/30，不提前写成闭合或更新三种子均值。
- [x] BM3 交付：374文件 manifest=`8e50aa4789314dac72f50e6d3b2da99db37f50d02e69f63f030d98598f3116a6`；PPT=`d942e4ff8442f0afd748dd9ceaa74894b685246206dc67c2c550bcbb1ddbaaa5`，PDF=`b2f4351c7b499ce21c294ab161f49547138601ffad02e1ef462cb509e4ec2413`。
- [x] BM4 展示：33页lint/layout/CRC与11张嵌图SHA通过；第9/28/29/30页实际渲染通过，n=2斜线和覆盖计数一致，未闭合项不补零。
- [x] BM5 同步：v123三地逐哈希一致，`e9618af`已推送；继续其他真实科学缺口。

## BN 组：v124 staging 与共享锁补位验收

- [x] BN1 台账：v124新增0，1565 accepted、0 rejected；无新proof，展示版保持v123。
- [x] BN2 防重：补位父63074与旧per-base父3431052共享state-dir/model locks；34格注册表SHA256=`2031be076eae1908ea8e591b7c37e3d9d0f3b70f08f9953e8ec542d869788f35`，旧父不重启。
- [x] BN3 在训：子63193为RNA-FM SpliceAI full-random/seed17/lr1e-5，device0；LR父45383与旧训练均未中断。
- [x] BN4 资源：used/free=16061/16051MiB，不强行启动16/28GiB格；证据SHA256=`ef12ad58578a7067934422aaf11b2854fcf4e2e2deb66a8314d83c7091aa2cb7`。
- [x] BN5 同步：v124记录已三地同步，`831bd60`已推送；等待真实完成格和独立proof。

## BO 组：v126–v127 staging 与历史图件归档验收

- [x] BO1 数据：v126/v127新增0，1565 accepted、0 rejected；PPT保持v123。
- [x] BO2 引用：20261028包的shuffle诊断、正式图CSV和机制坐标仍现役，不整体移动；30个无现役引用历史图件才归档。
- [x] BO3 哈希：归档30文件与moved manifest=`b762d3af8cd038dece84a9d01f572a0ba403961f58fa7c0193db6359bb24280e`一致；移动前manifest保留。
- [x] BO4 回归：现役81文件manifest=`45fa55e9057eff66d19c2104991212114e10cf9b60ecc067e7ceaf4657177bc9`；v14=374、组合图=53逐哈希通过，PPT SHA与ZIP CRC不变。
- [x] BO5 交付：归档副本、清单和五文档三地一致，`24df2ce`已提交；不删远端历史证据，GitHub推送待网络恢复。

## BP 组：v130 在训 PID 映射纠偏验收

- [x] BP1 台账：v130新增0，1565 accepted、0 rejected；PPT保持v123。
- [x] BP2 纠偏：PID63193/58794/54448按manifest确认均为SpliceAI，旧degradation推断已从五文档更正；无重复训练。
- [x] BP3 进度：mega与ERNIE seed17有epoch0，ERNIE seed101两轮stale=1/3，RNA-FM pre-plateau；均不记完成。
- [x] BP4 OOM：历史degradation PID49138与当前SpliceAI PID54448不同RID；证据SHA256=`7f29abe189eb26cbfceaff7b7c6119258cdf1ffff77b7ba9926aa1f538163c94`。
- [x] BP5 交付：纠偏证据与五文档三地一致，`d22895b`已提交；待真实proof与GitHub网络恢复。

## BQ 组：v132 staging 与 GPU 进程实证验收

- [x] BQ1 台账：v132新增0，1565 accepted、0 rejected；PPT保持v123。
- [x] BQ2 设备：4个训练PID均在nvidia-smi compute-apps中，显存3926/3312/3312/3482MiB，无CPU降级。
- [x] BQ3 证据：SHA256=`a517e11fab1d71c08e73bc0c656711b34aa50a0cc266007760a93dd904b686fa`，不代替收敛proof。
- [x] BQ4 交付：v132三地同步，`e702957`已提交并推送；等待真实完成格。

## BR 组：模型外锁修复与 OOM 恢复验收

- [x] BR1 回归：新测试在旧代码失败，证明外部模型锁导致漏调度。
- [x] BR2 修复：外锁等待、跨模型继续、下轮重试；完整调度测试连续两次51 passed，`87d1c28`已推送。
- [x] BR3 恢复：仅原OOM RID，父71153共享LR state-dir；注册表SHA256=`14cb904f637d82f29ffa2a9d06518117585e68ea07a903927375bfe0ace8650c`。
- [x] BR4 边界：free=14.677GiB、无子进程，等待而非强行启动；证据SHA256=`4dee861cb3fd11714aca9efb107f42d7ea3630b5985ff70dd12890b9efb6e383`。
- [x] BR5 交付：调度修复文档与证据三地一致，`6e14739`已推送；等待真实启动和完整proof。

## BS 组：v134–v135 与生产等待验证

- [x] BS1 台账：v134/v135新增0，1565 accepted、0 rejected；PPT保持v123。
- [x] BS2 生产行为：恢复父71153正常，原RID无新manifest记录、无子进程，pending未被错误跳过。
- [x] BS3 证据：SHA256=`99218d3f9cb6274327042e40d89f7e4629b14f98563e0877e5d548964682dbde`，不代替训练proof。
- [x] BS4 交付：生产等待验证三地同步，`9f16018`已推送；等待安全启动与真实完成格。

## BT 组：v136–v137 在训 plateau 验收

- [x] BT1 台账：v136/v137新增0，1565 accepted、0 rejected；PPT保持v123。
- [x] BT2 进度：ERNIE seed17有新最佳loss；seed101三轮stale=2/3，未收敛；其他两格继续长epoch。
- [x] BT3 证据：SHA256=`d14c2e0e11bf67279740dcf17cfbb6342ef89cbedf62dae3b477023dbdf12d78`，不把stale=2/3写成完成。
- [x] BT4 交付：v136–v137三地同步，`5f0208d`已推送；等待完整proof。

## BU 组：v140 日志与 plateau 分离验收

- [x] BU1 台账：v140新增0，1565 accepted、0 rejected；PPT保持v123。
- [x] BU2 进度：mega有epoch1；RNA-FM日志有两轮但plateau未更新，ERNIE继续训练。
- [x] BU3 证据：SHA256=`a84327420499adebc68aa5812855cee9a9402a607348ef2d036dc1b397b53f89`，日志epoch不代替收敛proof。
- [x] BU4 交付：v140三地同步，`7528361`已推送；等待plateau与完整proof。

## BV 组：v144–v145 集中闭合与展示验收

- [x] BV1 数据：1633 accepted、0 rejected；68格独立proof、CUDA与收敛通过。
- [x] BV2 矩阵：per-base 215/270、LR 194/320；SpliceAI/degradation/SSI=25/24/25，148M八任务全闭合，未闭合格不补零。
- [x] BV3 LR：47/80组，分布20/14/11/2；SpliceAI双split选1e-5，test不参与，证据SHA256=`9947decc342e65c3191e7b3a1e4cdff76b44b74ffb13f16ee3cf358a5527031b`。
- [x] BV4 交付：429文件manifest=`792db6e9cef61eaf238b88d3aa82b76cb956f1421ca3d6bb5bc18c28ffd3ad98`；PPT=`c8987fb49f832dea90b4a1938884127c44dc1a08aae863f7f493d7bdbd8e19a5`，PDF=`fd6125244ba2eef2fcaac0bd3e37c7e28215ef4be6cc78cbbd0c84ff8b4b601f`。
- [x] BV5 渲染：原生PowerPoint中文PDF正常，33页lint/layout/CRC、嵌图与第9/20/28/29/30页通过；第28页旧文案已纠正。
- [x] BV6 交付：v145三地逐哈希一致，`df915f1`已推送；继续真实科学缺口。

## BW 组：v146 650M SpliceAI LoRA-random 首点验收

- [x] BW1 数据：1636 accepted、0 rejected；3格proof=complete，证明SHA256=`bdd04fa1025d2ba8bf938ae17f2e40d215915618eeabfe3bf4158eec4a89ef55`。
- [x] BW2 边界：per-base 216/270、LR 196/320，47组与选档不变；650M该格仅n=1，不写成闭合。
- [x] BW3 交付：433文件manifest=`6c6457d748f277cb094232a4cc8a02d84573537ad951bb7ba841184d626c5f6b`；PPT=`176a32ccc9b5517016c66546b226270ccdc0a827bca0b41c2d4b2adbfbe520a2`，PDF=`0188c6d005153949bfa6a723f8965cea362a80eebf116a1b8fe419f576f6d505`。
- [x] BW4 渲染：33页lint/layout/CRC与第9/28/29/30页通过，n=1斜线与覆盖数一致。
- [x] BW5 交付：v146三地同步，`a06f718`已推送；继续真实科学缺口。

## BX 组：v147 staging 与 mega LR 补位验收

- [x] BX1 台账：v147新增0，1636 accepted、0 rejected；PPT保持v146。
- [x] BX2 防重：父655319共享LR state-dir/model locks，25格注册表SHA256=`8a156cbbd8d9664167358f8461154a44f1b833a2855e3f76592c678beead5098`。
- [x] BX3 在训：子655372为mega degradation full-family/seed101/default LR，device0；free=14.985GiB，不启动28GiB full。
- [x] BX4 证据：SHA256=`3af6f1d79d14e7dc89416eb062890f13ee7ad4e8ff796d29f0e65d3580fa68f8`，不代替完成proof。
- [x] BX5 交付：mega补位记录三地一致，`aa5be4d`已推送；等待真实完成格。

## BY 组：v148 mega degradation default LR staging 验收

- [x] BY1 数据：1637 accepted、0 rejected；新增格proof=complete，证明SHA256=`d669b90289396d481d042a15ae224ac0396f7557957bb86be9651e85e9f0fdf0`。
- [x] BY2 边界：LR=197/320，47组与选档不变；tuning不进正式均值，证据SHA256=`8113b629d6d1ea075c0db603f10e773d5793f85671c5817fa04f77581e044fa6`。
- [x] BY3 展示：无新科学单元，PPT与v105源包保持v146。
- [x] BY4 交付：v148 staging三地一致，`0815a48`已推送；等待真实可见更新。

## BZ 组：v149 五个 LR 组与 650M 第二种子验收

- [x] BZ1 数据：1652 accepted、0 rejected；15格proof=complete，证明SHA256=`5d940382fc8d8d87e336c466fb4019c74365403a37b91e8ce45cbf2d129231f1`。
- [x] BZ2 边界：per-base 217/270、LR 211/320；650M仅n=2，不写成闭合。
- [x] BZ3 LR：52/80组，分布23/16/11/2；五个新组均按best_val选档，test不参与，证据SHA256=`da7361bcbf0f0589377d0c70dd8cf17a03326fdc254ff7ab49a75aee683220c0`。
- [x] BZ4 交付：437文件manifest=`8f815649dbe1a70be29686121e3548cc10ab2cccaf5a4f0c6709653edecf4079`；PPT=`237a1330708b4e0a290b2dc5562cf0971ebb1e7a0cae2c32893f1fcc1e40f341`，PDF=`d3af3dfdd5412525e0d600514e104e8592a02b01a6ac84496c19308663dcca3f`。
- [x] BZ5 渲染：33页lint/layout/CRC与第9/20/28/29/30页通过，n=2和52组图文一致。
- [x] BZ6 交付：v149三地同步，`9272936`已推送；继续真实科学缺口。

## CA 组：官方模型全阶段后台流水线验收

- [x] CA1 范围：RNA-Sc 672格暂缓；core/frozen/crispr=180/990/108，1278个唯一RID。
- [x] CA2 安全：动态排除accepted，need+1GiB，同模型串行，现有父不中断，阶段proof失败即停止后续。
- [x] CA3 验证：56 passed，`ccdae6b`与`5518866`已推送；prepare-only未启动训练。
- [x] CA4 在途：监控PID761383，waiting_existing；证据SHA256=`3152defedf7b20ab6c4179b6242caa57a3aa26964914884c54bb3678cd01b94a`。
- [x] CA5 交付：监控记录三地一致，`725db0a`已推送；等待真实完成格，不将启动状态写成科学结论。

## CB 组：v150 650M SpliceAI LoRA-random 闭合验收

- [x] CB1 数据：1654 accepted、0 rejected；两格proof=complete，证明SHA256=`b4e9edcd8784c5269a1806d46aed8e93369fc5ced521bfd58f06193463f8f06b`。
- [x] CB2 结论：三种子mean=0.501479636、SD=0.150308697，正式闭合并注明种子变异；per-base 218/270、LR 212/320。
- [x] CB3 交付：441文件manifest=`1a9c8db34f3077dc9e58a18cc6379024e79995b226789eda63f7015cb2254a62`；PPT=`cad8627a298055d4da16b3ddf52a302b0bb75313fc9f76696b2689f0c7ce7b2d`，PDF=`b426adb6c0ef9ab95ddeca07b64d586b12b2434121e436a72b8511d53d84965a`。
- [x] CB4 渲染与监控：33页lint/layout/CRC与第9/28/29/30页通过；PID761383健康，RNA-Sc继续暂缓。
- [x] CB5 交付：v150三地同步，`42b09c2`已推送；继续官方真实科学缺口。

## CC 组：显存利用调整与父调度清理验收

- [x] CC1 安全：旧父3431054停止态、子僵尸，仅终止父调度，未中断训练；PID761383健康。
- [x] CC2 补位：ERNIE degradation frozen-family/seed17实际在训，父845090/子845112，共享per-base锁；证据SHA256=`57df33aa6176890c5ab9a7b5947e72aa6c3d03573651c7dbda0d1fc0a60374a5`。
- [x] CC3 预算：剩余need=3/20/28GiB，free=15.177GiB，无12GiB候选，不强行追加；证据SHA256=`a5ce4aec7e70d8280d9385a6a93577e82a9ebc3f895a67a42d4dd20b9a8fe026`。
- [x] CC4 交付：显存调整记录三地一致，`06ed429`已推送；等待自然窗口与真实proof。

## CD 组：v151 650M SpliceAI LoRA-family 首点验收

- [x] CD1 数据：1657 accepted、0 rejected；3格proof=complete，证明SHA256=`ed0ae03ca1b9f281efa49dbee520f92eae33f856866e6929d031176e09df1acc`。
- [x] CD2 边界：650M该格仅n=1；degradation 25/30，per-base 220/270、LR 213/320，52组与选档不变。
- [x] CD3 交付：445文件manifest=`32196c399038ca114cd6dc5248cd7165b87caf620a3873d6274829ae744a59fa`；PPT=`be36d5f3da62377f216e57f5203b622d0bd54889d6729a816fd54e5da866d840`，PDF=`03401896560c312d044bef4f51d4aac2e283924bf70e06aac3b1c3730b426cf5`。
- [x] CD4 渲染：33页lint/layout/CRC与第9/28/29/30页通过，n=1和覆盖数一致。
- [x] CD5 交付：v151三地同步，`89b0cfb`已推送；继续官方真实科学缺口。

## CE 组：v158 650M 三个 LoRA 任务闭合验收

- [x] CE1 数据：1673 accepted、0 rejected；16格proof=complete，证明SHA256=`3cd5417f8ce62a4ebbf223fd2aff73c85ca6f4b20cdca4bd4203f8d736f48c61`。
- [x] CE2 闭合：650M degradation/SpliceAI/SSI LoRA均六臂闭合，覆盖27/27/26；per-base 234/270、LR 215/320。
- [x] CE3 LR：53/80组，分布23/16/12/2；mega SpliceAI family选1e-5，test不参与，证据SHA256=`d4d756e5a27c9e613ccd486945b7c78c1526f4884c50818f53f8db5d4c2ca251`。
- [x] CE4 交付：449文件manifest=`68e3e35ab72c7658b425bb96e90d3c59cba0337ff37025578563380718ea9794`；PPT=`3f458b659c414c275322dabe57fc6dc04539892e2d3073aaf4591771c4212f2b`，PDF=`840abaf7b332ab4dd31e37083a557da28d6ca89f105724d4dbaaafb15948fb8d`。
- [x] CE5 渲染：33页lint/layout/CRC与第9/20/28/29/30页通过，三任务闭合与53组图文一致。
- [x] CE6 交付：v158三地同步，`59caf70`已推送；继续官方真实科学缺口。

## CF 组：空闲窗口 RNA-FM LR 补位验收

- [x] CF1 调度：per-base need20清零，选择非mega LR 16+1GiB，父1190497共享LR锁，workers=1。
- [x] CF2 在训：子1190658为RNA-FM degradation full-family/seed101/default LR，device0；注册表SHA256=`00f3c39e77eca4cb2d9c6c9219cffd975d0f573c4552d189e0fcaa9a92d7c205`。
- [x] CF3 边界：启动后free=18.662GiB，不重复开同模型任务；证据SHA256=`0940337567c2058be96413e0399a0a2cd2c74a4965228ed4551475b7e4b2abe5`，不记完成。
- [x] CF4 交付：补位记录三地一致，`759a908`已推送；等待真实proof与下一自然窗口。

## CG 组：v163 RNA-FM degradation family LR staging 验收

- [x] CG1 数据：1675 accepted、0 rejected；两格proof=complete，证明SHA256=`ffcf6a33a15296373f80012d9735b0424a510bd2f2a7551770596d3102c3fffe`。
- [x] CG2 边界：LR=217/320，53组与选档不变；tuning不进正式均值，证据SHA256=`cac6c077b1cacdb18979a295081e538c3b0d659247326bd7dd29f2f9fec62991`。
- [x] CG3 展示：无新科学单元，PPT与v109源包保持v158。
- [x] CG4 交付：v163三地同步，`8c54186`已推送；等待真实可见更新。

## CH 组：v164 RNA-FM degradation family LR staging 验收

- [x] CH1 数据：1676 accepted、0 rejected；新增1e-5格proof=complete，证明SHA256=`ad46fe5503138196c52f88ca1c5d5c6321e1fea631354f972fc1a594efb71905`。
- [x] CH2 结果：PCC=0.38693849945802145、best_val=0.227363、best_epoch=4、8 epochs，CUDA/checkpoint/plateau通过。
- [x] CH3 边界：LR=218/320，53组与选档23/16/12/2不变，仍缺3e-5；证据SHA256=`7b8d86e7bb360b45dbcc1de699e4ff29a59cbaf443538e1426cfdb0a4418de2c`。
- [x] CH4 展示：仅tuning，无新科学单元，PPT与v109源包保持v158。
- [x] CH5 交付：v164三地同步，`a85fc34`已推送；等待真实可见更新。

## CI 组：v165 RNA-FM degradation family LR 闭合验收

- [x] CI1 数据：1678 accepted、0 rejected；两格proof=complete、CUDA/checkpoint/plateau通过，证明SHA256=`1ee8fcdb9fc99b798cee9ee8a6f0c4268547121080e0f9eb5cb76bf0a72e96b1`。
- [x] CI2 LR：220/320，54/80组，分布24/16/12/2；family按best_val选3e-5，test不参与，证据SHA256=`3435b554c401bb337de86ff6d46075d44a4a2254dc1466c34d23f8682b9855da`。
- [x] CI3 交付：453文件manifest=`2efd7200776c9d8f1931045e035757ac3ac1064beb7240694691b0fe2fc6500c`；PPT=`c5356b63c0d5fd18f0a3ea4ddb321948a895972ebac896503810f288fcbed101`，PDF=`354486bde1f0c3f059274c6d84ff2661eb55ccfe64307dcb5b0dc44821f07521`。
- [x] CI4 渲染：33页lint/layout/CRC及第20页原生渲染通过；54组、24个3e-5和新增选档图文一致。
- [x] CI5 交付：v165三地同步，`f15f7ae`已推送；继续官方真实科学缺口。

## CJ 组：v166 RNA-FM degradation random LR 闭合验收

- [x] CJ1 数据：1682 accepted、0 rejected；四格proof=complete，证明SHA256=`da64c73fe6d79fe025a865cb7f17cef322998cb19ef40a16b2d17d1866ac0686`。
- [x] CJ2 LR：224/320，55/80组，分布24/17/12/2；random按best_val选1e-4，证据SHA256=`9ed542978f6736071f01531cb56418e4b7da88c4dcb5fb52999a88dbdeeb1655`。
- [x] CJ3 交付：462文件manifest=`9e3d6f5e7984fd23a25431ba945cd31ec7320ef5fed1503d21b79eba74e2f6e4`；PPT=`9bed0d665050e5369df1ca54b16cff1b72e97770a0e1ec01b6ea82204f27a272`，PDF=`832de2ae99f6a4ca2aa01688ff9e7eda5fb144cdd7c8497c82ab7caa5b7deb68`。
- [x] CJ4 渲染：33页lint/layout/CRC与第20页原生渲染通过，55组与双split选档图文一致。
- [x] CJ5 交付：v166三地同步，`f793e1c`已推送；继续官方核心缺口。

## CM 组：v167 RNA-FM SSP family LR 与 Frozen 验收

- [x] CM1 数据：1690 accepted、0 rejected；八格proof=complete，证明SHA256=`d43f4048f099ca89829df694e74c6b4a5692c9888dcfe0b45fe29575bcac3733`。
- [x] CM2 LR：228/320，56/80组，分布24/18/12/2；SSP family选1e-4，证据SHA256=`6a323cf9eea13278620cce6f175c3c560bcf638da30bf42d837db53dfa8e8396`。
- [x] CM3 Frozen：n=10三种子完成；n=100/seed17=0.6165501165501166、45 epochs，仅单种子，不提前推广。
- [x] CM4 交付：466文件manifest=`dfe447b3cce8ec4fe1facea0b71a16a8c6b303f058c44e141f53fd79956ec9eb`；PPT=`bcf0f81377afe9e74615754fad3783fad323a5fea2c5033b073a8084bdcad314`，PDF=`07e987a7d30c42ecdaaad3563afd9c7ca41b61d3d70623782fea7447bf42c908`。
- [x] CM5 渲染：33页lint/layout/CRC及第20页原生渲染通过，56组与SSP family选档一致。
- [x] CM6 交付：v167三地同步，`51a6e9e`已推送；继续核心优先与补位格验收。

## CN 组：v168 micro ncRNA Frozen n=100 第二种子验收

- [x] CN1 数据：1691 accepted、0 rejected；seed29 proof=complete，证明SHA256=`c6fdac8fbd2010a4efac055b9c4f888fff747167e0e36cc3ad09760c154a6910`。
- [x] CN2 结果：ACC=0.6503496503496503、best_val=1.225773、best_epoch=55、59 epochs，CUDA/checkpoint/plateau通过。
- [x] CN3 边界：n=100为2/3，仍缺seed43；主矩阵与56组选档不变，证据SHA256=`df3b66091df075994869a250c88bfc8c7901479161eb78e44b29705b051fa75e`。
- [x] CN4 展示：无新完整科学单元，PPT与v112源包保持v167。
- [x] CN5 交付：v168三地同步，`94da36d`已推送；等待seed43完整proof。

## CO 组：v169 micro ncRNA Frozen n=100 闭合验收

- [x] CO1 数据：1692 accepted、0 rejected；seed43 proof=complete，证明SHA256=`d8477590ef0efed334e354cd8d53906877c8286e17806239da6ce1d126172000`。
- [x] CO2 闭合：n=100 mean=0.6184926184926185、SD=0.030931560682770833；CUDA/checkpoint/plateau通过。
- [x] CO3 边界：该点低于主图1000–3000预算，不将单点写成scaling趋势；主矩阵与56组选档不变。
- [x] CO4 展示：PPT与v112源包保持v167，n=1000/seed17仅在途。
- [x] CO5 交付：v169三地同步，`463518e`已推送；等待更多Frozen档位形成曲线。

## CP 组：八任务收益分层与队列验收

- [x] CP1 科学性：八任务用于异质性与反例，不当作n=8独立重复；主矩阵/LR高收益，其他结论按边际收益分层。
- [x] CP2 当前缺口：per-base 36、complementary 18、LR 92及24组，替代v166旧计数96格/25组。
- [x] CP3 队列：core→frozen→crispr不变，29GiB核心窗口；E6三格pending不双开，tuned 240未达生成门不提前派发。
- [x] CP4 减负：PEFT全量与C5c全量不阻塞汇报，④复用⑤、⑥复用runtime，RNA-Sc 672继续暂停。
- [x] CP5 审计：Frozen 29/1008、PEFT 324/960、C5c 689/2016、CRISPR 0/108；LR余92含1 running，E6三格pending。证据SHA256=`6c01ea96fdc0fd24e6f333c26787bbb1524280bc6a92971632b37a488135e820`。
- [x] CP6 验收边界：accepted复用+未接受格实时proof，不重复加载全部checkpoint；不删注册表、不降低CUDA/收敛/三种子验收。

## CQ 组：v170 micro Frozen 曲线与展示验收

- [x] CQ1 数据：1699 accepted、0 rejected；七格proof=complete，证明SHA256=`6aa919fdd47de731db4ff81f9e2d5b70b123182162c3263d5d62446ea389ec16`。
- [x] CQ2 曲线：n=1000/1500三种子mean=0.742424/0.763403，n=2000单种子不画点；family SSP Frozen为全量参照。
- [x] CQ3 图源：33M Frozen加入曲线，random[2,5,5,5]、family SSP[1,5,5,5]；v170台账、图、CSV和正文一致。
- [x] CQ4 交付：479文件manifest=`90d3ed5757c185a0b3159bb0c3da63fb0f673abf9e1cdbac40fdee45401a4526`；PPT=`cdeabb404271a1ae01a80bccbb5e5d5956de7f9d57c5afc55702c44a3c75b60f`，PDF=`3ee341114f2753463cc4031e62995e58fb025bdc8539b526a7bca14ea6ce818f`。
- [x] CQ5 渲染：33页lint/layout/CRC与第26/27/29/30页原生渲染通过，family旧“三臂”措辞已纠正。
- [ ] CQ6 后续：三地同步并提交，继续n=2000种子与核心队列。

## CK 组：显存补位与 Frozen 路径修复验收

- [x] CK1 预算：micro Frozen按9GiB含余量调度，28GiB核心大格不在不足窗口强行启动；正式阶段门不变。
- [x] CK2 路径：3个错位产物逐哈希迁至teams，ledger路径修正，原目录保留，独立proof=complete；无覆盖或删除实验数据。
- [x] CK3 防重：同模型串行、共享state-dir；首父仅在自有子进程自然结束后退出，后续单格显式继承产物环境。
- [x] CK4 在训：父1273621/子1273646为micro ncRNA Frozen n=100/seed17，CUDA在训；证据SHA256=`f9092a2b8aad2e18d5a487c6a7592e7ce7ec1cb45cd83025c01fd32d293401be`。
- [x] CK5 验收：n=100/seed17完整proof通过；按窗口接续，不把补位记录当科学结论。

## CL 组：长期显存补位监控验收

- [x] CL1 环境：脚本显式固定teams产物根目录，共享模型锁、每格need+1GiB，dense不进入补位。
- [x] CL2 门禁：free<29且≥9GiB才补位，free≥29GiB让位核心；running/conflict/proof异常停止。
- [x] CL3 测试：目标与调度回归共60 passed，`3b7c7b5`已推送。
- [x] CL4 生产：PID1276604已启动n=100/seed29，registry SHA256=`4b801bba70029c266a98cc3fbe47293f32d683319964958dda6738946b2a73b3`，状态与日志文件留存。
- [ ] CL5 后续：当前格proof后再记完成，PPT保持v166，继续核心优先。

