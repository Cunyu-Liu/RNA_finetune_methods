# RNA-LM 微调策略评测：项目规格说明书（SPEC）

> **进度注记 2026-10-06（Day 20 · 假完成缺陷根治 + 审计口径纠错 + PPT 全表核对 + 项目反思成文）**：本 session 完成四件大事（详 STATUS_SNAPSHOT_20261006.md + 项目反思与叙事链改进_20261006.md）。**① 假完成死亡链根治（1006b）**：OOM→running 残留→claim 被拒 exit 0→worker 误判完成退出的链条已两层根治——4 个 runner claim 失败返回 rc=75（EXIT_CLAIM_BLOCKED）+ q_fill 对 75 走等待重试；配套 NB ncRNA need 三轮法证校准（34G→19G→bs8 协议对齐→22G，OOM 堆栈显示 NB 显式注意力矩阵 bs32 自用 28.9G vs 网格 bs8 peak 16.7G）。**② grid_audit 审计口径纠错（1006d）**：覆盖规则从「random 切片 LR 集合」改为「per-LR 双切分 6 行覆盖」——12 个假 RERUN-NEEDED 全部转 MATCH（ledger 逐格验证双切分×3 种子齐备）；**全项目唯一真缺口 = NB ncRNA 6 格（TUNED-MISSING，在训）**。**③ PPT 全表核对**：60+ 数值格 vs 1006 刷新版 c4_table——19/20 组通过；修正 1 处真实错误（mRNABERT lora family 0.072→0.086）；lint PASS。**④ 项目反思成文**：叙事主线诊断（六 claim 平铺→「幻觉→机制→条件→路线→代价→配方」六幕因果链重构方案）+ 证据强度审计表 + 系统性问题 P1-P8 清单 + 流程防再错制度化（need 标定必须同 bs 语境引用 ledger peak；审计器口径必须与 plan 落地口径字段级对齐；PPT 数字程序化生成）。**真态**：HEAD `92f622a`（本轮 6 连提交：5ecf487/65a5d6f/dbc3c76/57a58aa/5dccec7/92f622a）；ledger 1905 行（done 1891）。**收口自动化**：final_close_monitor cron */10（tm+ranksweep 双 0 缺 → 自动触发 q_refresh_final 全链重刷，marker .refresh_final_1006c）。
> **进度注记 2026-10-03（Day 18 · 全局缺口总账收官期 + 交接真态核验 + 两处记录纠错）**：本 session 完成 0929→1003 四天推进的全面对账（本地文档落后服务器 21 个提交）。**真态**：HEAD `2c71bd3`；ledger **1769 行**（1003b 去重 330 重复行后口径，done 1757）。**已收口**（程序化 0-miss 审计）：E1 全矩阵 8 个 P2 plan 全 0 miss（aido/ribo/NB/utrlm/mrnabert 24/24/54/36/18 + formal_rerun 60 + rerun2 72）；s101 网格 76/76；E6 遗忘全谱 **88 unique 格全 done（全项目收官）**——650M 谱 lora ΔNLL {0.017,0.017,0.044} vs full {0.098,0.124,0.154}（**LoRA 遗忘少 5-9×**）；random-init 36/36；E2-ext 24/24；E6-v3 18/18；collapse 10/10；HydraRNA 18/18（frozen 观察臂；**纠错：实际 18 格非「54 runs」**）。**本轮纠错一处**：E6-v2 起点差分实为 **15/18**（0927 快照「18/18」不实——micro lora s17 / 30M lora s29/s43 在单轮循环中 OOM 失败从未落地；e6v2_table.md 导出器一直如实标 [PENDING]）→ 已派 q_e6_v2_fill.sh 补位（共享卡锁+多轮重试）。**新派两队列**：TUNED-MISSING 6 格（NB 4 任务 + Sc-650M mrl/SSP）× 2 × 3 = 36 runs @grid-best 1e-05（2c71bd3）+ fullbig formal 剩 9 格（AIDO 6 @1e-05 网格翻转口径 + RiboSpan 3）。**关键科学信号（1003b）**：AIDO 1.6B 网格 LR 翻转 1e-05=0.720 vs 3e-05=0.520——大模型 full-FT 需更小 LR，formal 12 格已切 1e-05。**在飞**：fullbig 3+2/14、tunedmissing 36、e6v2_fill 3——**全部落齐 = 项目数据全收口** → 重刷链 → P4 预印本 v1.0。详 STATUS_SNAPSHOT_20261003.md。
> **进度注记 2026-09-29（Day 14-15 · 服务器真态全量核验 + 全队列复原 + 执行架构加固 + 文档同步）**：本 session 以「服务器 ledger/git/ps/nvidia-smi 实测」为唯一口径完成三件事。**① 真态核验**：HEAD `96ce6b7`（本轮 queue-hardening 提交在其上）；ledger **1607 行**（done 1546 / running 1 / pending 60）；strategy：frozen 369 / head-only 48 / lora 470 / full 589 / dora 67 / ia3 64；task：ncRNA-family 544 / modification 370 / mrl 302 / secondary-structure 261 / e6-forgetting 95 / e6-retention 18 / collapse-timeline 10。**② 队列复原与结构加固**：盘点发现 6 条队列「假死/半死」——共 103 个科学格未落（random-init 7、grid 56、aido 18、ribospan 12、e6-650M 6、collapse 4）→ 全部重派；根因 = 各队列独立锁目录 → 多队列同卡叠加 OOM 竞卡反复打掉大格 → 统一改造为**跨队列共享卡锁 `/tmp/rnaft_shared_locks`（双 slot；slot1 需 1.8× 余量）+ 抢锁后复核 + 定向 done-skip + 真 CUDA 断言 + 多轮重试**；大格降 bs 换落地率（e6 650M full bs16→4；fullbig bs4→2）。**③ 修正三处不实记录**：random-init 实为 **29/36**（0929 报告「36/36 DONE」不实，7 格从未落格）；e6 官方系 650M **0/6**（artifact dirs 空，从未落格）；fullbig 正式 60 格实为 **18/60**（mega/RiNALMo-650M/RNA-Sc-650M 各 6；AIDO/RiboSpan 从未落地）。**已收口**：E2-ext 24/24 ✅、NucleicBERT 54/54 ✅、UTR-LM 36/36 ✅、mRNABERT 18/18 ✅、E6-v3 17/18、collapse 6/10。详 STATUS_SNAPSHOT_20260929.md + 巡检日志「0929 第 12 轮」。
> **进度注记 2026-09-22 晨**：五波交接补位收官（ledger 838→953，~115 runs 净增）——崩溃带修订完成（v0.6.1）；**C4 执行期发现⑤：崩溃需要骨干更新**（head-only/frozen family 0.68-0.72 不崩，同任务 LoRA/full 才崩——入摘要）；MRL 大档判据完整；等价线 100M full tuned 数据落地中。详 STATUS_SNAPSHOT_20260922_晨.md。
> **进度注记 2026-09-21 晚**：交接全谱审计（etc_audit）发现四类切片缺口已全部派发补位（m6A dora/ia3 family、SSP full tuned 三模型、MRL/等价线补臂）；**148M LoRA family 三种子击穿崩溃带（0.139-0.334）**——famlora_audit 队列（RNA-Sc 1M-100M family lora 全档重测）判读前，预印本 2.3 节"七档全崩"表述冻结不改。详 STATUS_SNAPSHOT_20260921_晚.md。
> **进度注记 2026-09-21**：预印本 v0.6 成文且全量数字对账通过（Day 7）——C5b 等价线双系收官（等价线依赖家族，spec 预注册分歧分支命中）；A8 机制诊断完成（秩坍缩/回弹能力，D4 剂量阴性诚实记录）；C4 升级为粒度×家族密度二维判据。执行状态详 STATUS_SNAPSHOT_20260921.md。冻结口径（定位/切分单元表/统计计划）自 v1.4 起未变更。
> **进度注记 2026-09-26 上午**：**C6 遗忘轴收口（自 v2 范围提前）**——E6 灾难性遗忘矩阵 **24/24 全落地（0925 21:06）**（受控 10M/30M/100M + 官方 RiNALMo-micro × {lora, full@tuned-LR} × 3 种子，噪声带 <2.5e-8 全格显著）。**口径诚实声明**：E6-v1 实测 = 微调前后 S0 held-out NLL（test+family_test, n=2000）+ 重排噪声带；**结构涌现指标保持度归机理篇**（§1.1 分工线；本篇不承担该实验，仅交叉互证引用其结论），跨任务保持度为 **v2 扩展**（T4.2.3 注记）。**E6-EXT 谱线端点全收口（12/12，0926 上午）**：1M 6/6 + 650M 6/6 全落地（650M {lora,full} × 3 种子 04:47/06:27/07:54 done；期间经 worker D 逐卡原子锁防同卡碰撞 f230f31 + 若干 OOM 重试后全成）→ **C6 受控系 1M→650M 全 6 档 × {LoRA,full} × 3 种子 = 36 格全谱闭合**；谱线终形态 = 非单调、中段危险带（1M 轻微 → 10M 负 → **30M 峰值**（full 均值 +17.7、最差 +26.2；LoRA ~8× 尾部压缩）→ 100M 回稳 → 650M 再负）。**C6 导出链端点修复**：export_e6.py 原硬编码 ORDER 仅 10M/30M/100M/micro、静默丢弃 1M/650M 端点格 → 已扩为 1M→650M 全谱（e6_table 36 格）；新增 rnafteval/fig_e6.py（受控系 ΔNLL vs 规模谱线图 fig_e6_spectrum）。**preprint v0.9**（1dc1751：§2.8 表 6 行 + 三发现 + abstract finding 5 24→36 cell + limitations 去「in flight」+ header v0.4→v0.9；c89d64d：中文摘要 finding 6 + 送审速览 v0.9；bb37a29：§2.3 补 fig_c5b 引用）。HEAD bb37a29。详 §10.4 + STATUS_DUALTRACK.md v4。
> **进度注记 2026-09-26 下午（交接文档全量同步 + 后续交接工作启动）**：本 session 完成「交接文档 ↔ 服务器真实态」全量对账并同步回填（spec v2.0 / tasks v3.12 / checklist v1.9 / 新增 STATUS_SNAPSHOT_20260926.md；此前 tasks.md 多处未勾选但实际已完成）。**服务器事实核验**（以 ledger + git + status 产物为准）：HEAD bb37a29；ledger **1149 行**（done 1145 / cancelled 2 / pending 2）；已实现任务 **4 个**（noncoding-rna-family / mrl / modification(m6A) / secondary-structure）；已接入模型 **11 个**（RiNALMo micro/mega/650M + RNA-FM/ERNIE-RNA/SpliceBERT + 受控 RNA-Sc 1M/10M/30M/100M/650M）；GPU 实测 **8 卡**（0-5 为常规 A100-40GB，torch 视图 39.49GiB；6/7 为 MIG 1g.5gb，torch 视图仅 4.75GiB——`total<20GiB` 过滤为物理正确，非策略 gate）；**当前 rna-ft-eval 无在跑任务、显存空闲**。据此启动后续交接工作四条线（详 §10.6）。
> **进度注记 2026-09-19**：Day 5 收官——per-base 矩阵 26 组 0 崩溃全量（冻结口径不变）；E2 四面板；预印本 v0.5-core。执行状态详 §10 + STATUS_SNAPSHOT_20260919.md。本文件冻结口径（定位/切分单元表/统计计划）自 v1.4 起未变更。

> 版本：2.17（2026-10-29 修订二十七【C5c micro/mega 五档与29页阶段交付】：新增 §10.24。固定 ncRNA random×LoRA 的33M/148M五档已完成范围、当前29页PPT基底、385行best-val源包和后续 micro full-FT/650M/等价线交接；不得把该局部闭合误写为八任务或完整C5c完成。）
> 版本：2.16（2026-10-28 修订二十六【ncRNA 训练顺序伪影隔离】：新增 §10.23。旧 ncRNA family 结果所用 pre-shuffle runner 与标签成块输入形成高风险管理缺陷；在严格同 runner/max_len A/B 验收期间，旧 family 坍缩、E3 崩溃带、规模/等价线及其派生结论全部暂停科学判读，保留法证但不得进入 PPT 或预印本结论。）
> 版本：2.15（2026-10-28 修订二十五【八任务逐结论全覆盖复核】：新增 §10.22。将用户本轮要求逐条映射到结论①a/②/③/④/⑤/⑤b/⑤c/⑤d，明确八任务覆盖、官方模型优先、真实缺口、图文匹配、原数据归档与代码同步门禁；已完成任务地图、八任务 seed17 机制图和 micro rank8 六格只复用不重复。）
> 版本：2.14（2026-10-28 修订二十四【导师汇报续接与防返工总账】：新增 §10.21。以 28 页阶段修订版为当前 PPT 基底；任务地图、8 任务 seed17 机制图和 micro rank8 六格不得重复执行。补测按主矩阵→LR/rank→C5c/C5d→同源等价线推进，所有图只接受三轮对账后的正式结果。）
> 版本：2.13（2026-10-28 修订二十三【MRL LoRA/full artifact 迁移与复用】：新增 §10.20.19。以双 registry 区分物理路径冲突与真实缺口；完成 41 格哈希迁移、12 格既有链接和 1 格 teams 原生结果的三轮审计，54 格 complete 可复用，只有 6 个 650M full 格仍 runnable。）
> 版本：2.12（2026-10-28 修订二十二【best-val 异常种子与早停敏感性边界】：新增 §10.20.18。异常性能先对账 plateau/best checkpoint/test，再判断评测错误；不得事后修改 bestval_v1 停止规则或混用额外诊断臂。）
> 版本：2.11（2026-10-27 修订二十一【通用单格辅助队列】：新增 §10.20.17，将单格辅助 lane 的 RID 唯一性、主 busy child、显存预算和 proof 防重规则扩展到 complementary 官方模型矩阵；不改变任何任务协议或指标。）
> 版本：2.10（2026-10-27 修订二十【SSI 同序列记录与记录级诊断身份】：冻结 random SSI 的 sequence-hash 分组 holdout、同序列不同标签保留、official test 记录级 token ID 与逐记录 MCRMSE；不得去重或折叠不同标签。）
> 版本：2.9（2026-10-27 修订十九【per-base 并行源格与诊断接力】：在主单 worker 队列外增加单格辅助 lane 的唯一 RID、父进程占用、显存余量和 proof 防重合同；科学指标与验收口径不变。）
> 版本：2.7（2026-10-26 修订十七【导师汇报扩展与证据修复】：新增 §10.15，冻结 8 任务真实粒度分类、validation 收敛门禁、结论①-⑤与机制图的补测矩阵及 PPT 证据边界。用户已确认按最终注册表执行，不强行凑成每类两个。）
> 版本：2.6（2026-10-24 修订十六【科学完整性复审 + B20/E6 纠正协议】：新增 §10.14——实测确认三类新 per-base 任务 special-token 标签错位、official E6 未掩码标签泄漏及调度/旧入口风险；冻结受影响旧结论，规定 `_b20fix`/`_mlm15fix` 隔离重跑、8 任务唯一指标注册表、validation 平台验收和恢复门禁。§1-§9 冻结科学问题不变，纠正属实现错误修复与执行协议澄清，不作事后结果包装。）
> 版本：2.5（2026-10-23 修订十五【新集群 RTX5090 迁移 + 8 任务扩展登记】：新增 §10.13（硬件换档复现基准 / 8 任务矩阵执行扩展 / 工程修复链 / 执行状态 / GitHub·teams 双通道 / SSH 端口纪律第九条 / HydraRNA 待传）。执行状态同步，§1-§9 冻结口径未变——8 任务扩展属 §10.6 P 线执行扩展（用户 10-18 拍板），非 §1-§9 设计变更。）
> 版本：2.4（2026-10-07 修订十四【P4 v1.0 完成 + 假完成第三层 + E6 导出器根因】：新增 §10.9（预印本 v1.0 六幕重写交付 / 第 3 遍对账 12+ 处修正 / q_fill smoke 假 skip 根治 / E6 导出器 m6A-start 混写根因修复 / M5 第 2 轮无触发 / 纪律第四条）。前一版本 2.3（2026-10-06 修订十三【假完成根治 + 审计纠错 + 反思成文】：新增顶部进度注记 1006；§10.5 执行期发现登记保持；**新增 §10.8 项目反思与叙事链改进登记**（叙事主线六幕重构方案 / 证据强度审计 / 系统性问题 P1-P8 / 流程防再错三条新纪律：need 标定同 bs 语境、审计器口径字段级对齐、PPT 数字程序化）。工程修复链：rc=75 协议（1006b）/ grid_audit 覆盖规则（1006d）/ NB bs8 协议对齐（1006e-f）/ final_close_monitor 收口自动化（1006c）。执行状态同步，§1-§9 冻结口径未变。）
> 版本：2.2（2026-10-03 修订十二【全局缺口总账收官期 + 交接真态核验】：以服务器实测为唯一口径——新增顶部进度注记 1003；§10.4 刷新为 1003 全队列状态（E6 88 格收官 / AIDO LR 翻转 / fullbig v5 并行化 / stale-running 根治）；§10.5 新增发现⑫（LoRA 遗忘 5-9× 优势跨尺度闭合）⑬（AIDO 1.6B 网格 LR 翻转——大模型 full-FT 需更小 LR）；§10.7 新增登记⑪ tuned-missing 补臂与⑫ e6-v2 补位；**纠错两处**：E6-v2 实为 15/18（0927「18/18」不实，3 格 OOM 失败从未落地）、HydraRNA 实为 18 格（非 54 runs）。执行状态同步，§1-§9 冻结口径未变。）
> 版本：2.1（2026-09-29 修订十一【执行态全量同步 + 设计变更登记 + 文档纠错】：以服务器实测为唯一口径——更新 §10.4（0929 在跑与队列快照）、§10.5 新增发现⑦-⑪（random-init 判读 / E6-v2 起点差分 / E6-v3 跨任务保持 / collapse 时间轴 / 等价线官方系全谱闭合）、§10.6 P 线进度回填、**新增 §10.7 设计变更与新增臂登记**（B7 门槛废除 / random-init / E6-v2/v3 / collapse / 网格补全 / E2-ext / NucleicBERT / e6 官方臂 lr 协议修正 / 共享卡锁）；§3/§4/§5 对应处标注变更（待 T0.3.1 补签）。**纠错三处**：random-init 29/36（非 36/36）、e6 650M 0/6、fullbig 18/60。执行状态同步，§1-§9 冻结口径除显式标注的变更外未变。）
> 版本：2.0（2026-09-26 下午 修订十【交接文档全量同步 · 执行状态对齐真实态】：以服务器 ledger/git/status 产物为唯一口径，回填 §10.6 后续交接工作四条线（P1 E1 缺口补齐 / P2 剩余架构接入 / P3 终端交付物 / P4 预印本 v1.0）并同步进度注记与版本号。执行状态同步，§1-§9 冻结口径未变。）
> 版本：1.9（2026-09-26 修订九【C6 口径澄清·结构涌现归机理篇】：用户 2026-09-26 指出并确认——**结构涌现指标保持度属机理篇独有 claim**（§1.1 分工线左列"涌现分析"），本篇不承担该实验、仅交叉互证引用其结论。据此修正 §2 C6 行、§3 E6 行中把"微调后结构涌现指标保持度 / 机理篇 T3 涌现指标"列入本篇的措辞（与 §1.1 冲突的笔误口径，非设计变更）。本篇 C6 = 成本 / 遗忘（NLL 口径）/ 配方；跨任务保持度仍属本篇 v2。待导师签字确认。）
> 版本：1.8（2026-09-16 修订八【执行状态同步】：新增 §10 执行状态节——接入 STATUS_SNAPSHOT_20260916.md（Day 2 收官：E1 矩阵 80%、E4 主结论锁定、E2 五臂齐、预印本 v0.2.1 成文）；三大执行期发现对预注册 claim 的对照登记（任务粒度判别器→C4 预注册结果的更强版；LR×规模×策略三重交互→C1 条件化的新自变量；官方 split 泄漏→E4 的第三方实证）；时间线对照表更新——多项提前于冻结计划）
> 版本：1.7（2026-09-15 修订七【E2 最终设计·用户拍板方案 X】：等价线改为**双家族同源对比**——RiNALMo micro-33M ↔ giga-651M（官方同源系）+ RNA-Sc 1M ↔ 100M（受控同配方系）两条独立线互证，等价线结论跨家族一致才算稳健（与 Li et al. 的 ESM+CARP 双家族结构同构）；HydraRNA 经核验**无官方小尺寸版**（仅 84M 单模型，消融轴为架构/mask 长度/输入长度而非规模，GitHub 仅单一 checkpoint）——以单点进横评任 SSM 架构观察臂（B11），不入等价线。废弃 v1.6 的跨架构对比设计（RiNALMo×HydraRNA 小大对比存在规模+架构+语料三重混杂））
> 版本：1.6（2026-09-15 修订六：E2 代表模型按用户 PPT 决策调整为 RiNALMo micro-33M × HydraRNA ~0.9B 跨架构小大对比（原 v1.4 为 RiNALMo micro/giga 同家族两档）——设计变更记录：跨架构对比牺牲同源性换取架构泛化性（等价线结论可跨架构推广则更稳）；RNA-Sc 1M/100M 受控重复保留为同源佐证；等价线表述改「跨架构等价对」）
> 版本：1.5（2026-09-15 修订五【FLIP2 调研后·按需进口】：① 传统基线组扩充第 5 呭——ridge(one-hot + zero-shot 似然)混合基线（FLIP2/Didi et al. bioRxiv 2026-02-25 验证的蛋白侧最强基线，encoder 型用 masked marginal 口径）——"LM − 最强基线"口径自此成立；② C1 措辞条件化（微调收益 = f(切分偏移 × 任务 × 模型)）+ 评测阶梯重述为六级（one-hot ridge → zero-shot 似然 → 混合 ridge → frozen → LoRA → full FT）；③ 引言动机升级为"蛋白侧公开争议"叙事（Schmirler 微调有利 vs FLIP2 困难切分下微调失效）；④ FLIP2 列入必引。**明确不进口**：FLIP2 五类切分体系——判定依据：fitness 离散档与多骨架文库结构在 RNA 数据集中不存在等价物（用户 2026-09-15 决策"缺什么补什么"）；我们自有的"随机 vs 家族级"体系不变，DMS 的 number/mutation 细分切分列为 T3.3 可选项（标签分辨率预检查通过才做））
> 版本：1.4（2026-09-15 修订四：模型池 15 正式——mRNABERT（Nat Commun 2025-11）并入跨语料组；E2 代表模型改 RiNALMo micro/giga 同家族两档 + RNA-Sc 受控重复（等价线对比改为公平的同源设计）；补上 v1.2 时静默未命中的 E2 full FT 参照臂措辞）
> 版本：1.3（2026-09-15 修订三【用户决策变更】：执行策略由"姊妹篇·串行"改为**并行执行、本篇先发表**——两课题同时推进，微调策略论文优先投稿；启动条件删除"机理篇 arXiv 后"，时间线提前至 2026-10；资产移交改分批交付；风险表对应更新）
> 版本：1.2（2026-09-14 修订二【红队评审后】：任务池 8→10（每任务类 ≥2 数据集，免疫"单点拼盘"质疑）；模型池 16→14（3UTRBERT/RNAErnie 降附录）；预算重算 500-1100 GPU 时 + E1 分 Tier 执行；新增 §3.4 切分单元定义表、§3.5 统计计划预注册节、§7 决策树规则预注册；E2 增补 full FT 参照臂、E6 增补重评噪声带；良渚描述精确化。依据：红队评审报告_20260914.md R1-R11；同日勘误【红队二轮 R12/R13】：模型池计数统一为 14 正式 = Tier-A 8 + Tier-B 6（RNA-FM-26M 与 CodonFM 降附录，共 4 附录）；任务池标题"每类 ≥2"收窄为"结论承载类"——免疫 R9 口径混乱复发）
> 版本 1.1（2026-09-14 修订一：模型池补充 AIDO.RNA/HydraRNA/RiboSpan 等最新主流模型并修正"最大模型"表述；任务池扩充至 8 任务，新增 m6A 修饰预测与 RBP 结合位点两个主流任务；任务选取依据补充"主流度核验"小节）
> 版本 1.0（2026-09-14 定稿，基于三轮调研 + 用户三项决策确认）
> 用户决策（2026-09-14 定，2026-09-15 变更①）：① 与机理篇定位为**姊妹篇·并行**——两课题同时执行，**本篇（微调策略）先发表**（原为"串行"，用户 2026-09-15 变更）；② 实验深度**完整 Schmirler 式**（含 PEFT 横评/成本/配方）；③ 发表渠道**综合大刊**（Nat Commun / Nat Mach Intell）。
> 性质：冻结的科学问题、claim 边界、实验设计与验收标准。修改需经导师确认并升版本号。

---

## 1. 项目定位

- **不做**："第 N 个 RNA 基准"（该赛道 8+ 工作，两篇顶会被拒——见机理篇备忘录第 3 节尸检）；
- **做**：**RNA 版 Schmirler**——受控回答"RNA 语言模型该微调还是用冻结 embedding、LoRA 还是全参、花多少算力"，产出实践配方。实践指南导向，机制解释引用姊妹篇。
- **对标锚点（双锚）**：
  - Schmirler, Heinzinger & Rost, *Fine-tuning protein language models boosts predictions across diverse tasks*（Nat Commun 15:7407, 2024, DOI: 10.1038/s41467-024-51844-2）——方法论直接模板（615 个预测器 = 8 pLM × 8 任务 × 微调/冻结两臂 + LoRA/DoRA/IA3/Prefix 横评 + 资源实测 + 实践配方）；
  - 机理篇《RNA_LM_迁移学习机理研究》（本目录姊妹项目）——机制证据来源与基建供给方。
- **领域空白证据（2026-09 调研快照，四源一手核验）**：

| 工作 | 冻结 embedding | 全参微调 | LoRA/PEFT | 受控策略对比 |
|---|---|---|---|---|
| BEACON（NeurIPS 2024 D&B） | ❌ | ✅ 仅此一臂 | ❌ | ❌ |
| Zablocki et al.（arXiv 2410.16212） | ✅ 仅此一臂 | ❌ | ❌ | ❌ |
| 深圳湾 zero-shot（BIB 2026） | ✅ zero-shot | ❌ | ❌ | ❌ |
| 良渚（Nat Commun 2025-12，11 gLM × 4 任务） | ❌ | ✅ 统一微调 | ❌ | ❌ |

**"同一模型在冻结/LoRA/全参三种适配策略下的受控对比"在 RNA 侧至今无人做**——这正是 Schmirler 的方法论核心。RNA 侧模型规模谱系覆盖 0.5M-1.6B（RiNALMo 651M、AIDO.RNA 1.6B）+ 标注数据小 1-2 个量级 + 家族级分布偏移，预示答案与蛋白侧不同。

### 1.1 与机理篇的分工线（两篇论文都写死，防自我撞车）

| 维度 | 机理篇（在执行） | 本篇（本课题） |
|---|---|---|
| 科学问题 | 协议作为**科学轴**：协议/切分选择如何颠覆结论、与 scaling 的交互、涌现规律 | 适配策略作为**工程对象**：实践者该选哪条路线、花多少算力、何时微调有害 |
| 协议覆盖 | zero-shot / linear probe / full FT（**LoRA 已按 Q8 决议裁剪**） | frozen+头 / **LoRA/PEFT（独占）** / full FT + PEFT 方法横评 |
| 独有 claim | 涌现分析、S12 解耦指数、pretraining time 轴 | C3 小数据阈值、C5 PEFT 横评+小大模型权衡、C6 成本/遗忘/配方 |
| 泄漏轴 | Δ(随机−家族) 按模型报告（Q7 核心实验） | Δ 按策略分报告（泄漏×策略交互，C4） |
| 叙事关系 | "为什么协议影响结论" | "所以实践者应该怎么做"——机制→实践故事弧 |
| 互引义务 | 本篇引机理篇作机制解释来源 | 机理篇引本篇作实践落地出口 |

**关键事实（写进两篇相关工作）**：机理篇 Q8 决议裁剪 LoRA 的直接效果是 LoRA/PEFT 轴**干净地归本篇所有**，无撞车之忧。

### 1.2 Claim 措辞边界（冻结）

- **可以写**：截至 spec 定稿日，没有任何 RNA 工作把 2 种以上适配策略放进同一受控实验做策略隔离对比（四源核验：BEACON/Zablocki/深圳湾/良渚各单臂）；
- **不可写**："RNA 侧无人研究微调"（良渚做统一微调、BEACON 全微调评测、RNAscope rebuttal 有 frozen 观察）——措辞永远是"**无策略受控对比**"；
- **必引并差异化**：Schmirler et al. 2024（蛋白模板·微调有利）；**FLIP2（Didi et al. bioRxiv 2026-02-25，蛋白模板·困难切分下微调常输简单模型）**——两者构成蛋白侧公开争议，我们引言动机 = "该不该微调在蛋白侧已有条件性答案，RNA 侧需受控回答"；差异化 = FLIP2 的微调是未分化单臂，无策略隔离，无 RNA；BEACON（全微调单臂，我们补策略维度）；Zablocki/深圳湾（冻结单臂）；良渚（统一微调的排名结论，我们检验其对策略选择的敏感性）；Vishniakov et al. ICLR 2026（DNA 域 tokenizer 视角）；
- "受控"一词仅修饰策略对比协议本身（同数据/同切分/同指标/仅换策略）；模型间差异一律称"观察性比较"。

## 2. 科学问题（冻结）

**主问题**：给定 RNA 任务、有限标注（10^1–10^4 条）与有限算力（单卡级），实践者应选冻结 embedding + 浅头、LoRA、还是全参微调？微调何时提升、何时无益、何时在家族级分布偏移下有害？

**六个 claim（每个对应论文一节）**：

| # | Claim | 对标 Schmirler | RNA 特有性 |
|---|---|---|---|
| C1 | 微调收益是条件函数：f(切分偏移强度 × 任务类型 × 模型)——随机切分下的"总体有益"被 E4 显式存疑（v1.5 条件化，对齐 FLIP2 发现） | 主结论（其 Fig.1） + FLIP2 负结果 | — |
| C2 | 结构类任务微调增益薄（预训练已编码结构，涌现早） | 二级结构无增益发现 | 与机理篇涌现分析交叉互证 |
| C3 | **小数据阈值**：10^1/10^2/10^3/10^4 学习曲线下冻结/LoRA/全参的分界与翻转点 | 数据量影响观察（其 Fig. S10） | RNA 标注小 1-2 个量级，主战场 |
| C4 | **家族级切分下的策略分化**：随机切分的"微调收益"中泄漏占比；策略间泄漏敏感度差异 | 无此轴 | qYsy "simply cheating" 的策略维度深化 |
| C5 | **PEFT 横评 + 小大模型权衡**：LoRA/DoRA/IA3/Prefix/head-only 相对位次；"小模型全参 vs 大模型 LoRA"等价线 | LoRA≈DoRA>IA3/Prefix + ESM2-150M 全参≈大模型 LoRA | RNA 模型 ≤651M，PEFT 参数效率卖点是否消失的实证回答 |
| C6 | **成本-收益配方 + 灾难性遗忘检查**：GPU 时/显存实测曲线；遗忘度量（S0 held-out NLL 口径）；终端用户决策树。**结构涌现指标保持度归机理篇**（本篇仅交叉互证引用，不承担该实验——§1.1 分工线） | 16GB 配方 + 速度/显存实测（其 Fig.5） | 受控策略对比下的成本/遗忘/配方轴——本篇独有；涌现分析为机理篇独有 claim |

**负结果预案**：若 C1 在 RNA 上不成立（微调普遍无益），叙事切换为"RNA 与蛋白的分界条件"（配 C3 数据量解释），机理篇的语料/涌现结论作机制解释——两种结果均可发，选题结构低风险。

## 3. 实验设计规格（E1–E6，冻结）

| 实验 | 规格 | 检验 |
|---|---|---|
| **E1 主矩阵（v1.2 分层执行）** | **Tier-A 核心层**：受控家族 4 模型 + 通用组 4 模型（RiNALMo 三档+ERNIE-RNA）= 8 模型 × 10 任务 × 3 策略 × 2 切分 × 3 种子（结论主载体）；**Tier-B 观察层（v1.8 勘误：15 口径下为 7 模型——mRNABERT 并入，8+7=15）**：其余 7 模型（RNA-FM-96M/AIDO/HydraRNA/RiboSpan/SpliceBERT/UTR-LM/mRNABERT）× 2 代表任务（ncRNA 分类+二级结构）× 3 策略 × 2 切分 × 3 种子（附录观察性表格）。full FT 仅 ≤100M 模型 | C1/C2 |
| **E2 PEFT 横评（v1.7 方案 X·双家族同源等价线，含 full FT 参照臂）** | 等价线 A：RiNALMo micro-33M（全参端）↔ giga-651M（LoRA 端，官方同源）；等价线 B：RNA-Sc 1M ↔ 100M（受控同配方）；HydraRNA-84M 单点架构观察臂（B11，不入等价线）；六臂 {LoRA, DoRA, IA3, Prefix, head-only, full FT 参照} × rank {4/8/16} × 2 任务 × 3 种子 | C5 |
| **E3 小数据 regime** | 4 任务 × {10^1/10^2/10^3/10^4} 标注量 × 3 策略 × 3 种子（簇级分层降采样，seed 固定） | C3 |
| **E4 泄漏×策略交互** | E1 双切分结果按策略分报告 Δ(随机−家族)；probe 零重叠断言全程生效 | C4 |
| **E5 资源实测** | 每策略记录 wall-clock / 峰值显存 / 检查点体积（对标 Schmirler Fig.5 协议：长度 1024 序列，单卡实测） | C6 |
| **E6 灾难性遗忘（v1.2 增补对照臂）** | 微调前后：S0 held-out 困惑度（本篇口径）；**结构涌现指标保持度不在本篇**（归机理篇 §T3，本篇仅交叉互证）；未微调任务保持度为本篇 v2；**新增重评噪声带对照**：同一未微调模型评估两次（或 3 种子评估方差），遗忘声明 = 变化量 − 噪声带，超带才报 | C6 |

**策略定义（口径冻结）**：
- **评测六级阶梯（v1.5 重述，表征来源系统学）**：one-hot ridge（不用 LM）→ zero-shot 似然（LM 当打分器）→ ridge(one-hot+zs)（混合信号，FLIP2 冠军基线）→ frozen+浅头（LM 当特征提取器）→ LoRA（LM 定向改造）→ full FT（LM 重写）——相邻两级为"多用了 LM 的某一种方式，值不值"的配对比较；
- frozen+浅头：冻结 backbone，头 = 单隐层 MLP（隐宽 32，对齐 Schmirler）；序列级用注意力池化/CLS（禁 mean-pool——TokBench 教训）；
- LoRA：rank=8 默认（E2 扫 4/8/16），alpha=rank/2，目标模块 q/k/v/o，仅训 adapter；
- head-only：仅训头（E2 横评成员，也是 frozen 的训练版对照）；
- full FT：~~仅 ≤100M 模型（651M 档不做，limitation 明写——对齐 Schmirler 对 Ankh 混合精度的处理方式）~~ → **变更（0928 用户决策，待 T0.3.1 补签，详 §10.7-①）**：**废除 full-FT ≤100M 门槛**，任何参数量模型均跑全参微调；大模型 full 沿用 tuned-LR 家族规则、bs 按显存实况下调（AIDO/RiboSpan 1.6B：bs2；RiNALMo-650M：bs8）——limitation 措辞相应改为「大模型 full 的 bs 因单卡显存下调，属协议内标注项」；
- 优化器 AdamW，LR 按策略分网格 {1e-5, 3e-5, 1e-4, 3e-4, 1e-3}（tuning seed=101 上选定后冻结，对齐 BEACON 协议）。

### 3.4 切分单元定义表（v1.2 新增，R5 防线——E4 全部结论的地基）

| 任务粒度 | 切分单元 | 家族表映射规则 |
|---|---|---|
| per-seq（分类/MRL/DMS） | 整条序列 | 家族簇（cluster_id_8080）整簇归一侧 |
| per-base 位点级（m6A/m1A/RBP） | 宿主转录本 | 同一转录本的全部位点整条归一侧；映射：位点 → 转录本 ID → 家族簇 |
| per-base 窗口级（剪接位点） | 宿主基因 | 同一基因的全部窗口归一侧；映射：窗口 → 基因 ID → 家族簇 |
| per-base 全序列级（二级结构/接触图） | 整条序列 | 家族簇整簇归一侧（与 per-seq 同） |

生成切分时的运行时断言：任何位点/窗口与其宿主（转录本/基因）不得分属 train/test 两侧。

### 3.5 统计计划（v1.2 新增，预注册式，R2 防线）

1. **口径统一**：run = 一次训练执行；格 = 模型×任务×策略×切分的 3 种子聚合单元。全表约 480 格（Tier-A）；
2. **配对原则**：一切策略间比较在"同模型×同任务×同切分"内配对进行，禁止跨链非配对比较；
3. **多重比较校正**：全表性陈述（C1 总体结论、C5 位次、C3 翻转点、C4 策略分化）一律 Benjamini-Hochberg FDR（q=0.05）校正后报告；格子级 CI 仅作展示；
4. **方向一致性门槛**：3 种子间方向不一致的格标记为"不定"，不进入任何结论图；
5. **种子协议**：formal 17/29/43 只覆盖训练随机性；数据切分随机性由固定切分文件消除（不作为种子维度）；
6. **C5 位次降级**：E2 规模（2 模型 × 2 任务）有限，位次结论表述为"参考性观察"，正文一句话 + 附录全细节；
7. **预注册检查点（R6）**：每策略列完成 20% 时做检查点分析——若 frozen 相对最强传统基线的增益中位数 <2%（BH 校正后无任何格显著），触发方案复审会议（重估 LoRA/full FT 列的必要性并记录决策）。

## 4. 模型矩阵与任务池

**模型池（15 个正式 + 4 附录级，v1.4：mRNABERT 并入跨语料组——浙大侯廷军/谢昌谕组 Nat Commun 2025-11-24，18M 全长 mRNA、双分词+ALiBi，与我们 5 任务对口（MRL 0.962 超 UTR-LM / 降解 0.89 超 CodonBERT / RBP 13 种最佳 / m6A 第二 / 全长预测 R² 高出次优 1.6-10.4 倍））**：

| 类 | 模型 | 参数 | 角色 | 混杂分层（R4 防线） |
|---|---|---|---|---|
| 通用 ncRNA（同语料组：RNAcentral 系） | RiNALMo micro/mega/giga | 33M/148M/651M | 规模轴主力（giga 只 LoRA/probe） | 组内比较可谈"架构/规模效应（观察性）" |
| 通用 ncRNA（同语料组） | AIDO.RNA-1.6B | 1.6B | 最大 RNA LM，规模轴上限（只 LoRA/probe） | 同上 |
| 通用 ncRNA（同语料组） | HydraRNA | ~0.9B | 非 Transformer（SSM+MHA）架构代表 | 同上（与 Transformer 组的架构对照） |
| 通用 ncRNA（同语料组） | RNA-FM | 96M（正式） | 老牌对照（26M 档降附录） | 同上 |
| 通用 ncRNA（同语料组） | ERNIE-RNA | 86M | 预训练目标多样性 | 同上 |
| 长上下文 | RiboSpan | 1.61B | 10K nt 长上下文代表 | 同语料组（RNAcentral 系） |
| 任务专用（跨语料组） | SpliceBERT / UTR-LM | 19M/1.2M | 特化语料代表 | 跨组比较只谈"语料域效应（观察性）" |
| mRNA 全长（跨语料组，v1.4 新增） | mRNABERT（Nat Commun 2025-11） | ~86M（12 层×768） | 权威期刊代表；MRL/降解/RBP/m6A/全长五任务对口 | 同上 |
| 受控家族 | 机理篇 RNA-Sc-1M/10M/30M/100M | 1M-100M | 同配方规模轴 | **唯一可谈"受控"的组** |
| 附录级（v1.2 降级，同日勘误后 4 个） | RNA-FM-26M / CodonFM-80M / RNAErnie / 3UTRBERT | 26M/80M/105M/86-98M | 附录观察性数据点（CodonFM 为 mRNA 语料代表，观察性引用） | 附录呈现，不进主图 |

**混杂分层规则（R4，写作期强制）**：C1 主图的模型维度按"同语料组（8 席：RiNALMo×3/AIDO/HydraRNA/RiboSpan/RNA-FM-96M/ERNIE-RNA）/ 跨语料组（3 席：SpliceBERT/UTR-LM/mRNABERT）/ 受控家族（4 席：RNA-Sc）"三块分面板呈现，不混排；任何跨层比较语句禁止出现。（8+3+4 = 15 正式）

**v1.1 模型池修正说明**：① 修正 v1.0 的"RiNALMo 651M 为最大 RNA LM"过时表述——AIDO.RNA-1.6B（42M 序列）更大且公开，纳入后规模轴覆盖 0.5M→1.6B，"小模型全参 vs 大模型 LoRA"等价线检验（C5）在 1.6B 端更锐利；② HydraRNA 填补 v1.0 模型池纯 Transformer 的架构单一缺口（Schmirler 用 Ankh 填架构多样性的同款逻辑）；③ ~~651M/1.6B 档统一只跑 frozen/LoRA，full FT 上限维持 ≤100M 不变（预算与显存测算不变）~~ → **变更（0928，详 §10.7-①）**：651M/1.6B 档解锁 full FT（补跑 60+ runs，含 AIDO/RiboSpan 1.6B full——RNA 侧首见数据点）；预算增量 ~100-200 GPU 时，由共享集群夜间窗口吸收。

**0929 增补（P2 接入完成度）**：模型池实际接入 **16 个正式架构**（v1.4 的 15 + NucleicBERT——2026-09 Nat Mach Intell 404M ncRNA 专训，作为 C4 崩溃带第 13-14 个复现对象，角色=外部架构臂）：UTR-LM ✅、mRNABERT ✅、AIDO.RNA-1.6B ✅、RiboSpan-1K-40 ✅、NucleicBERT ✅（54/54）。

**0930 增补（HydraRNA 接入闭环，P2.8）**：第 16 个架构 HydraRNA（SSM+MHA 混合，84M，Genome Biol 2025-11）全链路接入完成——用户提供 Google Drive 权重 zip（3 ckpt md5 核验一致）→ `hydrarna` 独立 conda env（torch 2.3.1+cu118 + mamba-ssm 源码编译 + fairseq fork）→ **跨 env RPC vendored loader**（fairseq fork 与主流水线 torch 版本不可同进程）→ B20 门禁 [UNK]=0 → B11 MHA-only LoRA 目标 → 54-run frozen 观察臂队列在飞（首格收敛中）。**至此 16/16 正式架构全部有权重并可评测**；HydraRNA 角色 = SSM 架构观察臂（不入等价线）；其 lora/full 训练策略需进程内 env 融合（梯度回传跨进程），列为后续工程项。

**任务池（10 任务，v1.2 红队修订【同日勘误收窄表述】：结论承载类（结构/功能）每类 ≥2 数据集——C2 类结论由双数据集互证；工程/互作/变异类各 1 代表任务，不承载类级结论（正文按单任务依据表述）；全部复用已验证数据源——NABench 尸检纪律：不自策展、不碰 SELEX）**：

| 任务类 | 任务 | 数据 | 切分 | 主流度证据 |
|---|---|---|---|---|
| 结构（per-base） | 二级结构预测 | bpRNA-1m/ArchiveII（BEACON 复用） | 家族级（cluster_id_8080） | Zablocki/RiNALMo/RNA-FM/深圳湾/良渚全员使用——领域第一任务 |
| 结构（per-base） | **接触图预测**（v1.2 新增，R1） | BEACON ContactMap 任务（非冗余 RNA 3D 结构集） | 家族级（结构聚类） | BEACON 13 任务之一；AIDO.RNA 评测项——与二级结构同源不同输出形态，互证结构类结论 |
| 结构（per-base） | 剪接位点预测 | SpliceAI 数据（BEACON 复用） | 染色体级 | SpliceBERT/RiNALMo/良渚使用 |
| 功能（per-base） | m6A 修饰预测（v1.1 新增） | MultiRM/BEACON Modification 任务 | 转录本级 | 良渚 4 任务之一；AIDO.RNA 26 任务含修饰；mRNA-LM/DRFormer 使用——表观转录组学核心任务 |
| 功能（per-base） | **m1A 修饰预测**（v1.2 新增，R1） | MultiRM 同源子集（数据现成） | 转录本级 | 与 m6A 同族不同修饰类型——功能类互证，免疫"单修饰类型特性"质疑 |
| 功能（per-seq） | ncRNA 家族分类 | Rfam/NoncodingRNAFamily（BEACON） | 家族级 | RiNALMo/RNA-FM/ERNIE-RNA/深圳湾/良渚全员使用 |
| 全局（per-seq） | 核糖体负载 MRL | BEACON 复用 | 随机/家族双切 | UTR-LM/RiNALMo/良渚使用 |
| 工程相关（per-base） | mRNA 降解预测 | OpenVaccine（BEACON） | 官方切分 | RNA-FM/RiNALMo/AIDO.RNA 使用——mRNA 疫苗设计任务 |
| 互作（per-base） | **RBP 结合位点**（v1.1 新增） | BEACON/RBP-24/eCLIP 衍生 | 转录本级 | RiNALMo 评测项；良渚用 eCLIP；DRFormer 专项任务——RNA 生物学中心问题 |
| 局部变异（per-seq） | DMS fitness 子集 | RNAGym（按 assay 家族分组） | 家族级 | RNAGym/NABench/机理篇 |
| 传统基线（每任务全配，v1.5 扩至 5 个） | k-mer(1-6)+logistic、k-mer+LightGBM、one-hot CNN、random-embedding+头、**ridge(one-hot + zero-shot 似然)**（FLIP2 最强基线，encoder 型 masked marginal 口径） | — | 同切分 | NABench 审稿人 EUvA 点名要求；良渚核心发现依据 |

**任务选取核验（v1.1，2026-09-14 补）**：以"至少 3 个主流模型/基准工作使用过"为主流度门槛，8 任务全部达标（核验来源：BEACON 13 任务清单、良渚 4 任务、RiNALMo/AIDO.RNA 评测集、Zablocki/深圳湾/RNAGym）。任务类覆盖结构/功能/互作/工程/变异五类，恰好对齐 BEACON 的大类而数量收窄（免疫"任务堆叠"死因）；DMS 与 m6A/RBP 补齐了 v1.0 缺失的修饰与互作两类主流任务。**取舍说明**：CRISPR on/off-target（BEACON 有）不纳入——属 RNA 工程小众场景且家族级切分协议不成熟；contact/distance map 与二级结构高度共线，由二级结构代表，避免任务冗余。

## 5. 预算与算力（v1.2 红队重算，诚实区间）

按 v1.2 矩阵（Tier-A 8 模型 × 10 任务 × 3 策略 × 2 切分 × 3 种子 + Tier-B 7 模型 × 2 任务 × 3 策略，v1.8 勘误）：

| 层 | 覆盖 | 实测单位成本估算 | 小计 |
|---|---|---|---|
| frozen/probe/head-only | Tier-A 80 格 + Tier-B 12 格，embedding 抽取为主（大模型共享抽取） | 30-60 GPU 时 | 30-60 |
| LoRA | Tier-A 480 runs + Tier-B 72 runs（含 651M/1.6B bf16，20-40 分钟/run） | 184-368 GPU 时 | 184-368 |
| full FT | 仅 ≤100M 模型（Tier-A 6 模型 × 10 任务 × 2 × 3 = 360 runs，30-80 分钟/run） | 180-480 GPU 时 | 180-480 |
| E2-E6 深化 | PEFT 横评（+full FT 臂）/小数据/泄漏/资源/遗忘 | 60-120 GPU 时 | 60-120 |
| **合计** | — | — | **约 454-1028 GPU 时（报 500-1100）** |

**执行红线（R3/R6）**：① Tier-A 未完成不得启动 Tier-B；② 优先级序：frozen 列 → LoRA 列 → full FT 列 → 深化（每列 20% 检查点）；③ 若第 2 月末 LoRA 列进度 <60%，Tier-B 模型池再砍 2 个（CodonFM/SpliceBERT 降附录）保 Tier-A 完整；④ 旧版"150-250 GPU 时"作废，全部对外表述以本表为准。

## 6. 工程纪律（全部继承机理篇已验收资产）

- **切分/家族表**：cluster_id_8080 全局家族分配表（机理篇 T0.2.2 交付物）直接复用——跨任务家族唯一归属，防任务间泄漏（Z1）；
- **零重叠断言**：微调/评测数据集重叠运行时断言（TokBench P 臂教训）；
- **ledger**：model×task×strategy×seed×split 全组合 registry（机理篇 T0.2.3 模式，新增 strategy 维度）；
- **种子协议**：formal 17/29/43，tuning 101；
- **评测口径**：S0 held-out 困惑度（复用机理篇 split）；encoder 型 zero-shot 用 masked marginal 口径（若引用对照）；
- **月度监控**：机理篇 M1-M4 清单继承执行，**新增 M5：BEACON/良渚/深圳湾团队是否补 LoRA/PEFT 臂**（每轮 30-60 分钟，结果直接喂相关工作）。

## 7. 验收标准（冻结）

1. 每张图对应一个 claim（C1-C6 映射表为准；表外实验不做）；
2. "受控"仅修饰策略对比协议；模型间比较一律标注观察性；
3. E1 每格 ≥3 种子，报告均值 ±95% CI（bootstrap）；翻转性结论（C3/C4）需种子间方向一致；
4. 传统基线全任务配齐——预训练收益一律以"LM − 最强基线"口径报告（机理篇 Q4 决议）；
5. 微调代码零重叠断言生效记录进 ledger；
6. E5 数据覆盖每策略 wall-clock/显存/检查点体积三项；
7. 与机理篇分工线（1.1 节表格）在两篇论文 related work 互引落实；
8. **决策树规则预注册（v1.2，R7）**：增益 >2% 且 BH 校正显著 → "推荐"；0-2% 或种子方向不定 → "中性"；<0（BH 校正显著下降）→ "不推荐"。规则在 T4.3 决策树构建前冻结，与统计分析同步定稿，不得事后调整；
9. 一切"类结论"（如 C2 结构类）必须由 ≥2 个数据集共同支撑（R1）；
10. 模型间比较按 §4 混杂分层规则分面板呈现，跨层比较语句禁止（R4）。

## 8. 交付与时间线（冻结，串行启动）

**启动条件（v1.3 变更）**：**立即启动**（第 0 月 = 2026-10）——两课题并行执行、本篇先发表。frozen/LoRA 臂零机理篇依赖先行；机理篇资产（家族切分表/S0 split/已训 RNA-Sc 各档）按训练进度**分批交付**并入 Tier-A 对应列。发表顺序：本篇先投 Nat Commun/NMI（实践指南独立成文，机制解释暂引机理篇在投版本）；机理篇随后投稿，互引结构不变。

```
第 0 月(2026-10)   spec v1.3 冻结 + Schmirler/PEFT 文献 + frozen/LoRA 框架先行 + 机理篇已训资产接入
第 1-2 月          E1 主矩阵（frozen/LoRA/fullFT 全量）+ ledger 跑满
第 2-3 月          E3 小数据 + E4 泄漏×策略 + E2 PEFT 横评
第 3-4 月          E5 资源实测 + E6 遗忘 + 配方决策树；★ arXiv 预印本（完整核心实验）
第 4-6 月          大刊格式写作（生物学动机前置）→ 投 Nat Commun / Nat Mach Intell
贯穿              月度监控 M1-M5（每月 1 日）
```

**发表渠道（已决）**：综合大刊（Nat Commun / NMI）；写作风格按大刊调——引言实践者困境前置，方法学细节进 Methods/附录。

## 9. 风险基线（快照 2026-09-14）

| 风险 | 等级 | 对冲 |
|---|---|---|
| 与机理篇自我撞车 | 低 | 1.1 分工线 + Q8 裁剪 LoRA 事实 + 两篇互引义务 |
| BEACON/良渚团队补策略对比臂 | 中 | M5 月度监控；若触发 → arXiv 窗口从 4 个月压缩至 3 个月 |
| "蛋白复刻"审稿质疑 | 中 | C3/C4/C5/C6 四个 RNA 特有轴 + 配方输出 + 机理篇机制互证 |
| full FT 651M 缺失被攻击 | 低 | 预设分层说明（对齐 Schmirler 处理 Ankh 方式）+ LoRA 大模型臂 |
| 并行执行的人力/GPU 竞争（v1.3 替换"机理篇延期"） | 中 | 人力以本篇为主、机理篇维持档推进；A100 集群共享排期（本篇优先）；frozen/LoRA 臂零依赖先行，受控家族按机理篇训练完成分批并入 |


## 10. 执行状态（滚动节，与 STATUS_SNAPSHOT_20260916.md 联动）

> 本节为唯一非冻结节（执行状态同步），每次 STATUS_SNAPSHOT 更新后同步。冻结口径以上文 §1-§9 为准。

### 10.1 进度对照（2026-09-16 Day 2，快照 20:45）

| spec 冻结计划 | 计划时间 | 实际状态 | 偏差 |
|---|---|---|---|
| 第 0 月：框架先行 | 2026-10 | ✅ Day 0-1 完成（3 runner + ledger + 家族切分 + 5 基线 + 冒烟矩阵） | **提前 1 个月** |
| E1 主矩阵（C1/C2） | 第 1-2 月 | 🟢 5 模型 × 3 任务 × 2 切分 80%（ledger 201 runs/196 done） | 大幅提前 |
| E4 泄漏×策略（C4） | 第 2-3 月 | ✅ **主结论锁定**：per-seq 5/5 崩溃 vs per-base 0/4 | 提前约 2 月 |
| E2 PEFT 横评（C5） | 第 2-3 月 | ✅ 五臂三种子齐（full 0.938 ≥ DoRA 0.934 ≈ LoRA 0.928 ≫ IA3 0.860 > head-only 0.817） | 提前约 2 月 |
| A8 LR 网格 | 第 0 月末 | ✅ 16 格 + tuned 协议臂三种子（m6A 0.30→0.968） | 按期 |
| E5 资源实测 | 第 3-4 月 | ✅ 185/186 覆盖 | **提前 2 月** |
| E3 小数据（C3） | 第 2-3 月 | ⏳ 未启动 | **明确范围外**（预印本 v1 范围外，见 10.3） |
| E6 遗忘（C6） | 第 3-4 月 | ⏳ 未启动（依赖 E1 全量） | 按依赖 |
| arXiv 预印本 | 第 3-4 月 | 🟢 v0.2.1 全文可评审（15 节 ~2100 词） | **提前 2-3 月** |

### 10.2 三大执行期发现 × 预注册 claim 对照（防事后归纳纪律）

| 发现 | 对应预注册位置 | 性质判定 |
|---|---|---|
| ① 任务粒度是微调崩溃判别器（ncRNA per-seq 家族切分 5/5 崩至 0.06-0.10；m6A/SSP per-base 0/4 崩溃） | C4（泄漏×策略交互）预注册预期"Δ_fullFT > Δ_LoRA > Δ_frozen" | **预注册方向一致的更强版**——粒度维度是预注册未写入的自变量分解，写作时如实标注"执行期发现" |
| ② LR×规模×策略三重交互（full 甜区左移 10M:3e-5→33M:1e-5；默认 3e-4 全参崩溃；LoRA 同 LR 稳定） | C1 条件化 f(切分×任务×模型) | **新增自变量**（LR 协议）——A8 LR 网格是预注册任务，发现本身在任务验收范围内；tuned 协议臂已按预注册流程补三种子 |
| ③ BEACON 官方 split 泄漏（m6A random 臂 27.2% test 窗口与 train 同宿主簇） | E4/R5（切分单元定义 + 宿主断言） | **E4 防线的第三方实证**——泄漏审计脚本 export_leakage.py 可复现，直接支撑 C4 引言叙事 |

### 10.3 范围变更声明（预印本 v1）

预印本 v0.2.1 收敛为：E1（5 模型）+ E4 + E2 + A8 + E5 核心结论（§10.1 表中 ✅/🟢 项）；**E3 小数据、E6 遗忘、配方决策树为 v2 范围**——与 spec §2 claim 列表的关系：C1/C4/C5 完整支撑，C3/C6 推后。此为范围收窄（非设计变更），投稿时在论文 scope 声明中如实呈现。

### 10.4 在跑与队列（2026-10-03 16:30 快照 · 全局缺口总账收官期）

**服务器真态（本轮 SSH 实测，唯一口径）**：ledger **1769 行**（1003b 去重 330 重复行后口径：done 1757 / pending 8 / running 4 心跳行）。HEAD `2c71bd3`。GPU：0-4 各有 7-12G 碎片空闲（共享用户 100% 占用）；GPU5 37G 被外部进程占用；6/7 MIG。**执行原则不变：有显存即抢、共享卡锁自动竞争、不设策略 gate**。

**已收口（程序化 0-miss 终审计，唯一口径 = ledger done+lr 匹配）**：
- **E1 全矩阵 8 个 P2 plan 全 0 miss**：aido 24/24、ribospan 24/24、nucleicbert 54/54、utrlm 36/36、mrnabert 18/18、formal_rerun 60/60、rerun2 72/72（tuned-LR 口径累计 132 runs 全落地）；
- **s101 网格 76/76**（0929 审计的 RERUN 3 + PENDING 28 已全部由 rerun2/grid_fill 闭环）；
- **E6 遗忘全谱 88 unique 格全 done（全项目收官，1003b）**：micro 19 / 10M 20 / 30M 16 / 100M 6 / 1M 6 / rnasc650m 6 / rinalmo650m 6 / mega 9——650M 谱 lora ΔNLL {0.017, 0.017, 0.044} vs full {0.098, 0.124, 0.154}；
- random-init 36/36 ✅、E2-ext 24/24 ✅、E6-v3 18/18 ✅、collapse 10/10 ✅、HydraRNA 18/18（frozen 观察臂，**口径纠错：18 格非 54 runs**）。

**进行中（1003 16:30）**：
| 队列 | 内容 | 进度 |
|---|---|---|
| **fullbig formal**（6-shard） | 1.6B full 大端：AIDO 6 格 @1e-05（网格翻转口径）+ RiboSpan 3 格 @3e-05 | 3 done + 2 在飞 + 9 等卡（34G 门） |
| **tunedmissing**（4-shard，1003d 新派） | TUNED-MISSING 6 格（NB mod/mrl/ncRNA/SSP + Sc-650M mrl/SSP）× 2 切分 × 3 种子 = 36 runs @grid-best 1e-05 | 等卡轮询 |
| **e6v2_fill**（1003c 新派） | E6-v2 补位 3 格（micro lora s17 在跑 epoch 0 / 30M lora s29/s43 待跑） | 首格在跑 |

**工程里程碑（0930-1003 服务器端全链，详 TRAINING_LOG）**：HydraRNA 全链路接入（用户权重 md5 核验 + hydrarna conda env + 跨 env RPC loader，2bb8d4a）；stale-running 毒化根治（claim >2h 自动降级 + epoch 心跳，d7ec463）；claim dedup + ledger 330 重复行清理（830435e）；aido/ribo plan max_len 参数 bug 修复（24 mod 格从 0926 起秒败，8f227c8）；1.6B lora bs4 实测峰值 11.03G（bs8=31.85G）；AIDO full bs1+34G 门（bs2 峰值 30.3G）。

**preprint 状态**：v0.96 仍为现行评审版；P4 v1.0 并入清单 = E6 88 格终判读 + AIDO/RiboSpan 1.6B 等价线大端 + NB tuned-LR 修复值 + E6-v2 完整 18 格 + tuned-missing 36 格 + random-init 36（部分已在 v0.96）；全部落格后一次并入 + 全文对账 + C 组红队自查。

**E6 受控系 36 格全谱（0926 已收口，口径不变）**：1M 轻微 → 10M 负 → 30M 峰值（full 均值 +17.7、最差 +26.2；lora 尾部压缩 ~8×）→ 100M 回稳 → 650M 再负；forget_ratio 1M +0.24× / 10M +1.89× / 30M +11.86× / 100M −0.04× / 650M −0.44×；噪声带 <2.5e-8 全格显著（export_e6.py 全谱 + fig_e6_spectrum）。

### 10.5 执行期发现登记（滚动，防事后归纳纪律）

| 发现 | 对应预注册位置 | 性质判定 |
|---|---|---|
| ④ 148M LoRA family 三种子击穿崩溃带（0.139-0.334，带内其余 0.06-0.12） | C4/C5b（崩溃带"规模无关"表述） | **已判读定性（v0.6.1）**——famlora_audit：1M-100M 带内、148M 三种子全越带、1M/650M 单种子越带；「大体规模无关 + LoRA×预训练充分度部分逃逸」，修订已入 preprint/摘要/中文摘要/fig_c5b |
| ⑤ 崩溃需要骨干更新（head-only family 0.68-0.70 / frozen family 0.72-0.73 不崩，同任务 LoRA/full 才崩） | C4（泄漏×策略交互的机制细化） | **执行期发现（2026-09-22）**——家族切分下崩溃的必要条件是骨干参数更新；纯头训练/冻结特征不受家族记忆拖累。已入摘要（3bcab01） |
| ⑥ 双系方向在所有尺度上完全相反（受控系 full 5/5 全胜同尺度 LoRA：0.700>0.639…0.896>0.855；官方系 LoRA 处处胜 full：0.969>0.957）；受控系交点 10M-30M 且**大端不回吐**（30M full 0.862 ≈ 650M LoRA 0.855） | C5b（等价线家族依赖性） | **已判读定性（v0.7，0924）**——存在性反例大端检验完成：受控系 650M full 0.896/lora 0.855（+0.040）；两系方向相反获全谱支持。v0.6.4 的严谨口径（单家族存在性反例，非普适规律）不变，反例完整表述升级为「30M full（1/20 参数）打平家族最大尺度 LoRA 且优势保持到 650M」。已入 preprint v0.7（ed895bd）/中文摘要（678e5c2）/fig_c5b v2 |
| ⑦ random-init 对照臂（35/36 格时点判读；预注册问题「崩溃带是预训练表征的属性，还是 BERT 训练动力学的属性？」） | C4/A8（崩溃带归因） | **已判读（0928-29）**——家族切分下 random-init backbone **同样落 0.06-0.08 崩溃带（pretrained gap ≈ 0）** → 崩溃带的**位置由任务结构（多成员家族 × per-seq）决定、不依赖预训练**；random 切分下 pretrained 优势巨大（10M full 臂 gap **+0.56**）→ 预训练表征价值 = 同分布记忆（与 C4 泄漏结论闭环）；random-init lora 0.54 vs full 0.11 → 无预训练时 A8 动力学效应更致命 |
| ⑧ E6-v2 任务起点差分（18/18 全落） | C6（遗忘的起点面普遍性——「换任务起点结论变吗」） | **已判读（0927 晚）**——10M 两臂 m6A 起点遗忘更负（full −1.63→−2.45、lora −0.86→−2.13）；30M full 峰值带 +17.7→+9.4 且首种子完全逃逸（−2.7）；方向：**per-base 起点遗忘 ≤ per-seq 起点**（标签密度稀释 backbone 扰动假说） |
| ⑨ E6-v3 跨任务保持度（17/18，probe-style） | T4.2.3 后半（本篇 v2 扩展） | **部分判读（0927 晚）**——受控系跨任务 retention 分化大（MRL 0.22-0.50 @30M full/lora；m6A 多数 ≥1.0 反升）；micro full SSP retention 0.30 为最重跨任务损失；**诚实标注**：probe 头 2k/1ep 为表征可迁移性近似（≠完整微调性能），PPT/正文按「probe-style retention」措辞 |
| ⑩ collapse 时间轴（6/10；30M/SpliceBERT/10M 已判读） | A8（机制故事的时间维度补强） | **已判读（0927 晚）**——30M full family acc 起点 0.084 → **ep1 即 0.076 → 全程 0.06-0.09 震荡：崩溃在第 1 个 epoch 内完成**（与 diag_a8 的 5-10 步秩坍缩一致）；10M lora 反例（0.09→0.13 缓升）构成对照 |
| ⑪ 等价线官方系全谱闭合（fullbig 大端，0928 落格） | C5b | **已判读（0929）**——mega full@1e-5 = 0.945 vs lora 0.949（lora 首次**追平**全参）；RiNALMo-650M full 0.957 < lora 0.969 → 官方系「LoRA ≥ full」自 33M 一路保持到 650M 全谱成立；受控系 full 全尺度胜（650M 0.896 > 0.855）→ 两系方向相反结论全谱闭合；family 崩溃带 13 模型全谱成立（mega full 0.081 不逃逸 → 「部分逃逸 = LoRA × 预训练充分度」判读强化） |
| ⑫ **LoRA 灾难性遗忘优势跨尺度闭合（E6 全谱收官，1003b）** | C6 | **已判读（1003）**——E6 全项目 88 unique 格全 done；650M 谱 lora ΔNLL {0.017, 0.017, 0.044} vs full {0.098, 0.124, 0.154}——**LoRA 遗忘比 full 少 5-9×，与 30M 峰值带的 ~8× 尾部压缩一致，跨尺度（1M→650M + 官方 micro→650M）稳定**；E6 核心结论（C6 遗忘轴）全谱闭合 |
| ⑬ **AIDO 1.6B 网格 LR 翻转（1003b，重要科学信号）** | C1/A8（LR×规模×策略三重交互的大端延伸） | **已判读（1003）**——s101 网格 1e-05=0.720 vs 3e-05=0.520（+0.20，远超种子噪声）；1.6B full-FT 需要**更小** LR；与"published LM 用 1e-5"家族先验一致、与 A8 发现（full 甜区随规模左移）同向外推到 1.6B；formal 12 格已全部切 1e-05（grid-best 语义），已跑 3e-05 family17 (0.0596) 保留为副对照 |

### 10.6 后续交接工作（2026-09-26 下午启动，滚动节）

> 本节记录「后续交接工作」四条工作线的定义、口径与进度。是 §10 的非冻结节的一部分，随执行滚动更新。

**对账结论**：交接文档此前落后于执行进度（tasks.md 多处未勾选，但据 ledger/status 产物实际已完成，如 E4/E2/A8/E5/T4.2）。本轮已按服务器真实态逐项核对回填。

| 线 | 内容 | 类型 | 状态（0929 回填） |
|---|---|---|---|
| **P1** | **E1 矩阵缺口补齐**——程序化盘点 4 任务 × 已接入模型 × {frozen,lora,full} × {random,family} × {17,29,43} 的缺口 | GPU | ✅ **v1 口径收口**（37 组/111 runs 全落，0927 核验）；**v2 口径扩展**——门槛废除后大模型 full + tuned-LR 网格补全（见 P2/grid_fill） |
| **P2** | **剩余架构接入**——spec §4 模型池尚未接入的 5 个架构 + NucleicBERT + HydraRNA | GPU + 下载 | ✅ **7/7 完成（0930 HydraRNA 闭环）**：UTR-LM ✅（36/36）、mRNABERT ✅（18/18）、AIDO.RNA-1.6B ✅（24 计划在飞）、RiboSpan-1K-40 ✅（24 计划在飞）、NucleicBERT ✅（54/54）、**HydraRNA ✅（0930：权重 md5 核验 + hydrarna env + RPC loader + 54-run frozen 队列在飞）——16/16 架构全部接入** |
| **P3** | **终端交付物**——T4.1 E5 资源汇总 + T4.3 决策树/配方（★） | 非 GPU | 🟢 资源矩阵/成本收益图 ✅ + 决策树引擎 ✅（4 任务覆盖）；配方 CLI ✅；覆盖度扩展与复现 notebook 待 P1/P2 收口后自动重算 |
| **P4** | **预印本 v1.0**——v0.96 + 新数据（NB/random-init/grid/fullbig/e6-650M/E6-v2/v3/collapse）→ 导师评审版 | 写作 | ⏳ 待新数据落齐后一次并入（纪律：全部落格 + 全文对账 + C 组红队自查） |

**P1 明细（ledger 实测口径，共 37 组 × 3 种子 = 111 runs）**：
- `mrl × RNA-Sc-1M`：{frozen,lora,full} × {random,family}（6 组）；
- `modification × {RiNALMo-mega frozen, RNA-Sc-1M frozen/lora/full, RNA-Sc-30M frozen, RNA-Sc-100M frozen}`（7 组）；
- `secondary-structure × {RiNALMo-mega frozen/lora, RNA-Sc-1M frozen/lora/full, RNA-Sc-30M frozen/lora/full, RNA-Sc-100M frozen/lora/full}`（24 组）。

**P1 口径（沿用各 runner 既有协议，禁自创）**：
- frozen / LoRA 用默认 LR（3e-4）；
- full FT 用家族 tuned LR：**RiNALMo 系 1e-5**（micro/mega/650M 一致），**受控 RNA-Sc 系 3e-5**；full 的 run_id 追加 `_lr<val>` 标签以与默认口径区分；
- 训练超参：ncRNA `epochs 10 / bs 32`；modification `epochs 3 / n-train 20000 / bs 32`；SSP `epochs 3 / n-train 3000 / n-test 500 / bs 4 / max-len 192`；MRL `epochs 3 / bs 32 / max-len 64`；
- 并行方式：多 GPU worker + 逐卡原子锁 + done-skip + 失败清 pending 重试 ×2 + 真 CUDA 断言（沿用 q_e6_ext_d.sh 模式）。

**P2 明细**：UTR-LM（`multimolecule/utrlm-mrl`）、mRNABERT（候选 `YYLY66/mRNABERT`，需核实体量/是否权威发布）、AIDO.RNA-1.6B（`genbio-ai/AIDO.RNA-1.6B`，已核 HF 200）、HydraRNA（HF 无；GitHub 单 ckpt）、RiboSpan（`SII-GAIR-NLP/RIBOSPAN-FM/1K-*`）。五步：**checkpoint 可达性 → 加载器适配（ModelSpec + 必要时 custom_loader）→ forward smoke-test → ledger 记录 → 入 E1**；任一步失败如实登记（不静默、不硬跑）。

**纪律（全四线通用）**：开工前对照 §3 实验规格与 §7 验收标准；smoke test / proxy 指标 / 训练集结果**不得**写成最终科学结论；GPU 训练与验证必须真 CUDA（不可用或 CPU 静默降级即停并保留证据）；每个任务结束把确认好的代码及时提交 GitHub；代码留 `/home/cunyuliu/rna-ft-eval`、大型数据/权重/artifacts 留 `/mnt/cunyuliu`。

### 10.7 设计变更与新增臂登记（2026-09-27~29，滚动节，按 T0.3.1 流程记录）

> 纪律：设计变更一律显式登记（依据 / 影响面 / 待签状态），不做静默修改；新增实验臂一律带**预注册问题**（「每图一问」）。

| # | 变更 / 新增臂 | 依据 | 状态与口径 |
|---|---|---|---|
| ① | **废除 full-FT ≤100M 门槛（B7 防线）** | 用户 0928 决策：任何参数量模型都跑全参；动机 = 等价线大端补齐 + 1.6B full-FT 是 RNA 侧从未有过的数据点 | 队列在跑（fullbig v4：AIDO/RiboSpan bs2+22G+3 轮重试）；**待 T0.3.1 导师会议正式补签**；§3/§4/§5 已就地标注 |
| ② | **random-init 对照臂**（36 格；NucleicBERT 表 1 同构设计） | 预注册问题：「崩溃带是**预训练表征**的属性，还是 **BERT 训练动力学**的属性？」；random-init × 同协议微调若同样崩 → 动力学解释占优；若不崩 → 预训练表征是必要条件 | 29/36 落格（已判读，发现⑦）；7 格重派中；默认 LR 3e-4 与 pretrained 臂同口径可比 |
| ③ | **E6-v2 任务起点差分**（18 runs） | 响应用户「假设证明牵强」反思：C6 遗忘全部 36 格都以 ncRNA 为起点 → 补 m6A 起点 | 18/18 ✅（发现⑧） |
| ④ | **E6-v3 跨任务保持度**（18 runs，probe-style） | C6「其他任务保持度」——ncRNA 微调前后各做 m6A/MRL/SSP probe（2k 样本/1 epoch 轻量头），retention = post/pre | 17/18（发现⑨）；缺 1 格重派中；**诚实口径：probe 近似 ≠ SOTA** |
| ⑤ | **collapse_tl 崩溃时间轴**（10 runs） | A8 机制故事的时间维度：逐 epoch family acc 记录「崩在第几 epoch」 | 6/10（发现⑩）；4 格重派中 |
| ⑥ | **s101 tuned-LR 网格补全**（76 格 × LR{1e-5, 3e-5}，全模型全任务） | 用户「模型都得过一遍 tuned LR」审计：7 模型完全无网格、其余缺大量任务格；网格只在 VL0 选优（B1 防线），formal 种子另跑 | 4 shard 在跑（20/76）；**网格落齐后若 formal 默认-LR 行与网格最优不一致 → 重跑 formal**（预计影响 RiNALMo-650M 4 任务、RNA-Sc-100M 等） |
| ⑦ | **E2-ext 五臂横评扩臂**（24 runs） | 「C5a 只有 2 模型、外推性弱」——ERNIE-RNA/RNA-FM × {dora,ia3} × ncRNA/m6A | **24/24 ✅**（五臂横评 2 → 4 模型） |
| ⑧ | **NucleicBERT 接入**（P2.7，54 runs） | 2026-09 见刊 404M ncRNA 专训模型（KIT+Jülich，Zenodo 权重）——C4 崩溃带理想新复现对象（外部架构臂角色） | **54/54 ✅**；U→T 字符级 tokenizer 过 B20 门禁；LoRA 目标 out_proj+ffn.0（torch MHA in_proj 打包）+ peft shim |
| ⑨ | **e6 官方臂协议修正**：mega lora 原跑 1e-5（与 micro/受控系 lora@3e-4 不一致）→ 补 3 格 `_lr3e-04` | 协议一致性审计（独立思考项） | 3 格重派中；**P4 决定是否切换口径**（新数据以 `_lr3e-04` 后缀另存，不动既有行；export_e6 口径届时同步评估） |
| ⑩ | **队列共享卡锁 + 重试制**（工程加固） | 根因：各队列独立锁目录 → 多队列同卡叠加 OOM 竞卡（e6 650M 6/6 从未落格、fullbig AIDO/RiboSpan 0/60、grid 单 worker 串行） | 已实施：`/tmp/rnaft_shared_locks`（双 slot；slot1 需 1.8× 余量；抢锁后复核）；q_fill.py + 全部新队列接入；大格降 bs 换落地率 |
| ⑪ | **TUNED-MISSING 补臂**（36 runs，1003d 派发） | grid 审计遗留：NB 4 任务 + Sc-650M mrl/SSP 的 formal tuned-LR 行从未跑过（NB full@默认 3e-4 在 m6A/SSP/ncRNA 上 A8 式崩溃 0.50/0.008，需 @1e-05 grid-best 口径） | 4-shard 在飞（p2_tunedmissing_plan.json）；**NB 的崩溃格不得写入结论——tuned 口径落齐后以 1e-05 行为准** |
| ⑫ | **E6-v2 补位 3 格**（1003c 派发） | 0927 单轮循环 OOM 失败从未落地（micro lora s17 / 30M lora s29/s43）；**纪律教训：单轮循环队列 = 「循环 DONE」≠「格落地」，补位一律走共享卡锁+多轮重试模板** | q_e6_v2_fill.sh 在飞；落齐后 E6-v2 = 18/18 完整口径（当前 15/18，e6v2_table [PENDING] 3 格） |

**影响面声明（写作期必须如实呈现）**：① 门槛废除后，651M/1.6B 的 full 臂 bs 低于小模型（1.6B bs2 / 650M bs8 或 4），属**协议内标注项**（Schmirler 对 Ankh 混合精度的同款处理）；② 网格补全可能触发 formal 重跑——重跑后所有相关图表以「网格最优 LR 口径」统一刷新并记录在 TRAINING_LOG；③ random-init/E6-v2/3/collapse 均为**预注册问题驱动**，判读前不得写入结论。

### 10.8 项目反思与叙事链改进登记（2026-10-06 新增，非冻结节）

> 依据：用户四点指令（叙事证明力再思考 / PPT 数据严核 / 项目问题反思 / 课题→论文主线）。全文详《项目反思与叙事链改进_20261006.md》。本节为登记摘要。

**① 叙事主线重构方案（P4 预印本 v1.0 写作骨架）**：从六 claim 平铺改为「幻觉→机制→条件→路线→代价→配方」六幕因果链——主命题 = *微调 RNA-LM 的收益大部分是泄漏的幻觉；真收益由粒度 × LR 决定；LoRA 是真收益场景的默认最优路线*（C4 揭穿 → 骨干更新/random-init/秩坍缩/ep1 机制闭环 → A8 LR 协议 + E3 安全窗 → C5 等价线 + 官方系 LoRA ≥ full → C6 遗忘 5-9× 压缩 → 决策树收口）。摘要 = 一条主命题 + 四个支撑发现。

**② 证据强度审计**（12 个叙事环节 ★3-5 评级，详反思文档 §1.2）：核心链证据闭合；薄弱点 = head-only 对照仅 2 模型、random-init 仅受控系 3 模型、E6-v2 标签密度假说未直接测——写作期如实标注，不超证据表述。

**③ 系统性问题 P1-P8 与流程防再错新纪律**：
- P1 假完成死亡链 → rc=75 协议（已根治，1006b）；
- P2/P3/P4 审计与标定口径错位 → **新纪律：need 标定必须同 bs 语境引用 ledger peak_mem_mb；审计导出器判定规则必须与 plan 落地口径逐字段对齐**；
- P5 PPT 手抄数字两次同类错误 → **新纪律：P4 写作期 PPT 数据表程序化生成（从 status/*.csv 渲染）**；
- 其余（文档滞后/收敛审计误报/stale-running）双保险在岗。

**④ 收口路径**：NB ncRNA 6 格 + ranksweep 11 格落齐 → final_close_monitor 自动全链重刷 → 导出表 [PENDING] 清零 + grid_audit TUNED-MISSING=0 → P4 预印本 v1.0 按新叙事骨架重写。


### 10.9 P4 预印本 v1.0 完成与假完成第三层根治登记（2026-10-07 新增，非冻结节）

> 依据：v3.16 回填 F 项「P4 preprint v1.0 按新叙事骨架重写」落地 + 本轮第 3 遍全文数字对账。详 paper/preprint_v1.0.md（服务器）与 TRAINING_LOG 1007 段。

**① P4 v1.0 交付**（commit e63f3c5 起 9 commits）：六幕骨架全文重写——Abstract 主命题+四支撑；章节重排（幻觉 2.1-2.2 → 机制 2.3 LR → 条件 2.4 标签预算 → 路线 2.5 PEFT+rank → 审计/统计 2.6-2.7 → 代价 2.8 遗忘）+ 三处过渡句焊接。新增：rank sweep 表 / 1.6B LR 二次翻转 / E6 官方谱（ledger ncRNA-start 权威口径）/ E6-v2 稀释 14/18 / §2.1a 外部臂全收口。头部附数据对账声明。

**② 第 3 遍全文对账修正（v0.96 错误口径 12+ 处）**：16 FT 架构崩溃口径（HydraRNA frozen-only 出计数；3 部分逃逸 UTR-LM 0.15 / mega-lora 0.21 / RNA-FM tuned-full 0.53）/ frozen 家族带 0.11–0.89（ERNIE 0.887、RNA-FM 0.860、窄配方 0.11-0.20——预训练语料广度结论）/ E6 87 格（51+18+18）非 124 / "5-9×" → 危险带条件性（1M 处 LoRA 种子 +3.76 反超 full +2.50）/ E3 旧表作废改 e3_table 权威口径（tuned full 小 n 全线最优）/ m6A 默认崩溃 2/5 非 3/5 / RiNALMo 家族 grid-best 口径 0.944/0.945/0.956 / §2.1 LoRA 行 3-seed 精确均值。

**③ 假完成第三层（P1 延伸）**：q_fill.is_done 不排除 smoke 行——NB 3 缺格（lora random s29 / frozen random s17 / m6A lora s29）各自只有 smoke done 行 → 补跑被假 skip。修复：is_done 加 `not r.get("smoke")`。伴随盲区：OOM exit 1 后 running 心跳行残留 → 自锁 claim-block 死循环；修复 clear_pending 扩展清 pending+running。NB 3 格补跑落地中（lora s29 random 0.9429 已入 v1.0 终值）。

**④ E6 导出器口径冲突根因（P2 延伸）**：export_e6 / export_e6_official 的 collect() 按 (model, strategy, seed) 索引不过滤微调任务——E6-v2 m6A-start artifacts 后跑按 seed 覆盖 v1 ncRNA-start 行（表间 +4.12 vs +11.23 等冲突的根因）。修复：两导出器排除 task=modification。表已重刷与 ledger 逐值一致；v1.0 官方谱表按 ledger 裁决终值化（micro full +0.157 / lora +0.118）。

**⑤ M5 第 2 轮（超期补救）**：无触发；近邻信号登记（NVIDIA BioNeMo Evo2 DNA-LoRA 单任务教程 / NLP "Fine-Tuning Trap" sub-1B 负迁移——与 A8/E2 结论跨域同向，related-work 候选）。

**⑥ 纪律第四条（v3.17）**：论文/PPT 数字写入前必须先过 ledger 原始行检索（不走导出表中转），写入后回对；导出表冲突 = 立即停用该表并回源裁决。

### 10.10 PPT 1008 修订 + 补测队列派发登记（2026-10-08 新增，非冻结节）

> 依据：用户 7 项 PPT 问题审查（结论①/②/③/④/⑤ 图、E4/E5/E6 补图、自训模型收敛质疑）。本地 PPT 13 页交付 + 服务器 2 条补测队列在飞。

**① PPT 修订（11→13 页，结果版主交付已更新）**：
- s3 结论①：fig_ppt_16arch v2——16 架构 × 4 柱（frozen random/family + 微调 random/family），frozen vs 微调对照融入一图（问题1）
- s5 新增 E4 页（04b）：Δ(随机−家族) × 3 策略 × 3 任务分面图 fig_ppt_e4_delta（问题4a）
- s6 结论②：fig_ppt_a8_3task——7 模型（含 AIDO 1.6B / NucleicBERT 404M）× 3 任务（ncRNA/m6A/MRL）分图 + LR 差异复核文字（问题2：改变量系 tuned vs default 真实 gap，SpliceBERT ×12 / ERNIE MRL ×28 实证）
- s7 结论③：fig_ppt_ranksweep v2——m6A r8 lora 补齐（主行=默认 rank8 口径：LoRA 0.970/DoRA 0.979）+ SSP 第三面板（问题3）+ 参数量标注
- s9 结论④：fig_ppt_c5b_v2——横轴改数字标注（1/10/30/100/650/1600M）+ AIDO/RiboSpan 1.6B 并入官方系 + 100M 复测判读（0.803/0.822/0.847 三种子一致，非单调为真信号）+ N=3/6/12 说明（图内标注 3-seed mean）+ 300M 档补测说明（问题5）
- s10 结论⑤：fig_ppt_e3_curves v2——n=3000 档已落（tuned full@3000=0.731 > full@1000=0.707，曲线上行；lora@3000=0.583 反降）+ 5000 档在飞 + 等价线探索结论（full@1000 0.707 ≈ lora@3000 0.696；full@3000 > 全档 lora）（问题6）
- s11 新增 E5 页（09b）：fig_ppt_e5_resources——峰值显存 + wall 双面板（问题4b）
- s12 结论⑥：banner 补 E6 全谱 87 格口径 + collapse 时间轴（问题4c）
- lint PASS + CRC PASS + 四遍结构检查（无越界/无重叠/全 YaHei/行距≥1.2）
- 备份 ppt/work/before_fix_1008.pptx

**② 补测队列派发（问题2/3/5/6 的数据补全）**：
- p2_e3_5000_1008_plan（24 runs）：micro/Sc-10M × {full tuned, lora, frozen} × n∈{3000,5000} × 3 种子——E3 档位加密（3000 已落 3 格：full 0.724/0.744/0.724）
- p2_rnasc300m_1008_plan（18 runs）：**RNA-Sc-300M 首次接入**（models/__init__.py 注册 + run_map + CUDA smoke 通过 302.1M）× ncRNA 双切分 × {frozen,lora,full@3e-05} × 3 种子——受控系等价线 100M→650M 之间插值点（问题5/6 参数量上探 + 收敛审计容量假说验证）
- q_fill.py 两处扩展：--n-train 传参支持 + is_done 精确 e3 档位匹配（修 3000 done 被误判为 5000 done 的假 skip）

**③ 自训模型收敛审计成文（问题7）**：docs/自训模型收敛审计_20261008.md——13 个自训 run 全部收敛平台（val_loss 末 3 档降幅 <1.2%）；scaling 谱单调无离群；两系结论相反归因 = 语料广度 + 配方差异（非欠训）；300M 补测为容量插值假说验证。

**④ AIDO 3e-05 formal 3 种子补跑**：worker 在飞（等 32G 卡窗口，aido_close_monitor cron 自动收口）。

**⑤ 图脚本教训（入踩坑清单）**：fig 过滤 `"_ri" in rid` 会误杀 `_rinalmomicro/_ribospan...` 前缀——random-init 标记必须按 `_` 分段精确匹配（`seg == "ri"`）；`_e310` 子串匹配误匹配 `_e3100`——e3 档位必须 endswith 或分段。

### 10.11 二轮修订 + 300M 收口 + E3 崩溃临界点登记（2026-10-09 新增，非冻结节）

> 依据：用户二轮 6 项问题（问题2/3/5/6/7/9）+ 1008 派发队列全部落地。详 tasks v3.20 回填 + 巡检日志 1009 段。

**① 300M 收口与容量假说验证**：18/18 全落（full random 0.888/0.881/0.867 @3e-05）——介于 100M 0.824 与 650M 0.896 之间 → **受控系 full 非单调（30M 峰→100M 回落→650M 回升）为容量轴真信号，非数据错误**；受控系等价线升六尺度全谱（1/10/30/100/300/650M）。

**② E3 崩溃临界点发现（重要科学信号）**：micro full@5000 = 0.064（崩溃）vs full@3000 = 0.73（正常）——**家族记忆崩溃临界点在 3000-5000 条标注之间**；frozen@5000 = 0.68 不受影响（崩溃仅打微调臂）。此发现细化 C3：小数据全参最优的「安全窗」上界为 ~3000 条。

**③ 二轮图修订（PPT 14 页）**：A8 v3（数值+倍数直标）/ rank v3（SSP+异架构在飞）/ why_opposite（两系归因：语料广度 frozen family 0.65-0.89 vs 0.15-0.52 + full−LoRA gap 反号）/ E3 三任务并排（per-seq vs per-base 类型学）/ E3 等价线交叉图（新页 09c：full@1000≈lora@3000）/ E5 重画（24GB 参考线）/ E6 重画（双面板语义化）。

**④ 用户 PPT 批注处置**：3 处手写批注（「没看懂」/「不要加 aido 了」/「太丑了，看不懂」）按内容修改后删除，处置留痕巡检日志。

**⑤ 新派 78 runs**（p2_e3rank_1009_plan）：异架构 rank sweep 24 + MRL/m6A E3 3000/5000 24 + Sc-30M/300M E3 24——问题3/5/6 的数据补全（rank 结论跨架构验证 + 任务类型区分 + 大参数量等价线）。

### 10.12 第四层假完成根治 + 1016 队列 + 预印本 v1.0 增量 + 配额事故登记（2026-10-13 新增，非冻结节）

> 依据：本轮 SSH 真态（HEAD 5d9af17）+ 两轮 ledger 对账。详 STATUS_SNAPSHOT_20261013.md + tasks v3.22 回填 + 巡检日志 1013 段。

**① 第四层假完成变体（is_done 双格式）**：MRL/m6A runner 落地 e3 run_id 为 `_e3<n>_lr<lr>`（e3 在前），q_fill.is_done 只认 `_lr<lr>_e3<n>` → 1011 六 worker 在已完成格上 claim-blocked 死循环数小时；q_plan_need 台账误报（1010 报缺 5 实为 68）。修复：双格式匹配 + audit_1016.py 权威审计器 + keepalive_1016 cron。**假完成 4 变体共同根因 = run_id 构造逻辑分散在 4 个 runner 无统一函数**（checklist B24 候选）。

**② 调度解锁**：1010 worker 全卡 33-34G 大格（need 过标定违反同 bs 语境纪律的存量）→ 拆 1016 双 plan（mega_e3 27 + bigtail 41）+ need 重标定（650M frozen 34→8G）+ 清 kill -9 残留的 10 个陈旧卡锁 → 6 训练立即启动。教训：杀 worker 用 SIGTERM 或杀后必清锁。

**③ 配额事故（经用户确认）**：home 100% 满（tar_stage 111G 多课题 tar 分片无活跃写入）→ mv /mnt/cunyuliu/tar_stage_1013。巡检纪律新增：`df /home/cunyuliu` 检查项。

**④ 预印本 v1.0 增量（5d9af17）**：Abstract 过渡带 + 六尺度；§2.4 过渡带五模型表（3500/4000/4500 加密 + ERNIE 不稳定窗后恢复 + frozen 平线 + 崩溃跨策略）；§2.5 300M 插值 + 100M 六种子复测 + b59 语料宽度消融终判（语料宽度→frozen 侧 / full−LoRA 方向→配方侧，双因素分离）。对账修正 300M lora family 0.076→0.079。

**⑤ 叙事链第 3 轮审计（详《叙事链证据审计_第3轮_20261013.md》）**：1006 第 2 轮全部薄弱点闭合——head-only 2 模型 → frozen 平线 5 模型全谱（120 格）替代；100M 数据嫌疑 → 六种子 + 300M 双审计洗清；语料宽度假说 → b59 直接检验。残余 2 处表述层风险（A8 网格稀疏 / 机制语言边界）有写作期对策。逻辑链无断环判定在案。

### 10.13 新集群 RTX5090 迁移与 8 任务扩展登记（2026-10-18~23，非冻结节）

> 依据：docs/tasks_v3.23_增量.md（服务器）+ tasks v3.24 回填 + 巡检日志第 28 轮。集群 = px2-jcy.matpool.com:29375（matpool 容器，单卡 RTX 5090 32G，16 核 60G RAM，无 cron/crontab，/ 300G overlay，/teams fx 网络盘）。

**① 硬件换档与复现基准（纪律第八条）**：A100-40G×8 → RTX5090-32G×1（torch 2.11+cu128，Blackwell sm_120 必需）。**跨集群数值对比必须先过单格复算基准**：micro frozen s17 random ACC 0.7366 ≈ 老集群 0.739 ✅（2026-10-18 建立在案）。

**② 8 任务矩阵扩展（用户 2026-10-18 拍板，spec §4 任务池的执行扩展）**：4 类 × 2 = 8 任务——序列级分类（ncRNA + crispr-off-target）/ 序列级回归（MRL + 备选 crispr 连续）/ 碱基级分类（m6A + spliceai 3 分类）/ 碱基级回归（degradation + structural-score-imputation）。RBP 撤回（beacon_raw 无此目录）；crispr 实测为连续 cleavage 分数（PR-AUC 主指标 + 二分类口径）。新 runner：finetune_clf / finetune_spl / finetune_regbase（回归 TokenHead MSE + OpenVaccine scored-window 口径）。**属 v1.0 之外的扩展臂，判读口径 = 执行期发现登记（3 种子 + B23 双证后入正式结论）**。

**③ 工程修复链（10-18~10-23）**：seed 全局化 + per-epoch shuffle（1022b，修 crispr 3 种子同值 bug）/ 跨队列中心仲裁 q_master（1021a，E6/AIDO 排他 + drain 门）/ ledger claim key 修复 + 47 行假 running 清理（1023，容器无 cron 的系统性盲区——reset_stale_cron 已并入 monitor_loop v2 每 15min）/ q_master Phase3 AIDO 协议修正（1023：epochs 3 + 12h timeout，对齐成功先例）/ monitor_loop v2（stale 清理 + 10 车道 respawn + GPU 占满纪律告警 + q_master 守护）。

**④ 执行状态（10-23 12:00）**：ledger 2633 行（done 2578）；GPU 31.6G/32G 99% 占满（10 车道）；audit_1016=1（AIDO mrl s43，q_master Phase3 修正版等 drain）；E6 官方 15 格 + spliceai 尾格排队中。新任务首批信号（登记口径）：spliceai lora 0.54-0.61 / frozen 0.33-0.44（微调增益存在）；crispr 家族切分崩溃带第 4 任务复现（mega full 0.0125-0.154）；degradation NB full 0.375-0.406。

**⑤ 通道**：GitHub 推送 = git bundle → Mac ssh-key 中转（集群无凭据）；大文件备份 = /teams/HoulabData_1788502323/liucunyu/rna-ft-eval/（ledger+status+logs 129M 首批）。**SSH 端口纪律（第九条）**：px2-jcy:29375 高频连接即 reset——合并命令 / 失败等 3-5 分钟。

**⑥ 缺失资产（待用户）**：HydraRNA 3 权重（orico 08_hf_home，Mac 端 TCC 被闸——需授权完全磁盘访问后传集群，16 架构第 16 席，不阻塞主线）。

### 10.14 科学完整性复审与 B20/E6 纠正协议（2026-10-24，非冻结节）

> 触发：本轮对当前 HEAD `a2f1442`、ledger、17 条车道、runner 和日志做交叉审计。16:28 实测 ledger 2711 行 / done 2651；单卡 RTX 5090。以下只登记已实测事实，不把旧文档的“DONE”当作科学验收。

**① 受影响队列的即时处置**：spliceai / degradation / SSI 与 official E6 已暂停，CRISPR per-seq 保留。旧 monitor 与 q_master 停止自动复活。受影响旧结果先备份再隔离，不删除证据；修正版使用独立 RID，严禁新旧协议混算。

**② 已确认的实现错误与影响边界**：

| 问题 | 实测证据 | 影响范围 | 不得使用的口径 |
|---|---|---|---|
| B20 token/label 错位 | HF 模型自动加入 `<cls>/<eos>`；NucleicBERT 加入 `[CLS]/[SEP]`；旧 runner 从 token 0 填 per-base 标签 | spliceai、degradation、SSI 中所有使用这些 tokenizer 的旧训练/评估；k-mer 模型不允许进入 per-base | 旧分数不得进入 PPT、预印本、决策树或“8 任务已完成”计数 |
| official E6 目标泄漏 | `nll_eval` 对未掩码 `ids` 前向并读取同位置 target，与注释的 leave-one-out 不符 | RiNALMo-micro/mega/650M、ERNIE-RNA、RNA-FM 的旧 official E6 NLL 及派生遗忘倍数 | 旧 official ΔNLL、5–9×等结论冻结，待 `_mlm15fix` 重跑 |
| 调度与旧入口 | v2.1 无 monitor/lane 生命周期锁；q_master drain 可永久等待；q5090 曾用 ncRNA runner 调 MRL | 双开、假 DONE、错误 runner 与长期饿死风险 | 不再以日志 DONE、进程数或 pending 行数作为完成证据 |

RNA-Sc tokenizer 无特殊 token，B20 错位不影响其既有 per-base 对齐；controlled causal shift NLL 与 NB hidden-state drift 也不与 official MLM 泄漏混为一谈，但导出时仍须分协议报告。

**③ 纠正实现与验收**：

1. **B20**：训练和评估共用监督 mask，排除 special tokens/PAD；以全长度 tokenization 断言单碱基映射，k-mer 直接失败；支持 degradation scored window 与确定性右截断；RID 含 `_b20fix` 及非默认 LR/rank/n_train/epochs。旧行标记 invalid/cancelled，旧 result 文件改名隔离。
2. **E6**：official 改为固定 15% masked-position MLM NLL；每序列掩码由 eval seed + 原始序列 index 独立决定，跨 batch/order 可复现；pre/post 共用 seed 201，pre_b 用 seed 707，noise band 明示为独立掩码/顺序重评差异；RID 含 `_mlm15fix`。canonical 重跑范围 = 5 个 official 模型 × {LoRA, full} × 3 种子 = 30 格；历史 mega LoRA@1e-5 变体若保留须另带独立协议标签。
3. **工程**：clf/spl/E6 claim-blocked 必须真实返回非零；clf/spl device 改关键字传参；主指标必须 finite；result.json 原子写；q5090 的 AIDO MRL 只准 `finetune_mrl` + 3 epochs + bs1 + 12h；旧 P2 计划禁止 glob 自动复活。
4. **恢复门禁**：本地 focused tests、真实 tokenizer smoke、真实 CUDA smoke、监控故障注入、ledger/result 双证逐项通过后才能恢复对应队列。smoke 只证明实现，不进入科学结论。

**④ 8 任务唯一注册口径**：ncRNA/ACC、CRISPR/PR-AUC、MRL/Pearson r、modification/AUC、spliceai/macro-F1、degradation/PCC、SSI/PCC、secondary-structure/F1。CRISPR 当前正式臂是 per-seq 二分类；其他回归或离散化设想均属未来独立实验臂。

**⑤ 收敛与对照公平**：既有 fixed-epoch 结果保留为 legacy 协议，不把“循环结束”写成“已收敛”。B20 修复重跑先保持原训练预算以隔离实现纠错；每格另做 validation-loss 平台审计，未达到预设 `min_delta + patience` 的格不得标 final，需以独立 `valplateau_v1` continuation 记录续训，且不得把不同选择协议静默并入同一均值。若最终采用 best-val/early-stop 作主协议，必须在新 RID 下重跑整个对应对照集。

**⑥ 结果发布冻结**：在纠正格通过 B23 与收敛门禁前，PPT/预印本不得加入 8 任务新数值；现有 PPT 的 official E6 面板不得作为已确认证据引用。后续所有图表必须显式区分 legacy、`_b20fix`、`_mlm15fix` 与 `valplateau_v1`，并由 ledger 原始行重新生成。

**⑦ 本轮恢复事实（18:15 后）**：三层验证通过后，294 条受影响旧记录与 245 个旧 result 文件已在 `/teams` 备份并隔离；monitor v2.2 单实例与 lane 生命周期锁在岗，corrected dispatcher 和 CRISPR 已恢复，E6 micro 6 格已启动。上述为执行状态，不代表 corrected 结果已达标或可发布。

**⑧ E6-v2 补充隔离与首批 corrected 证据**：后续复核发现 `e6_forget_task` 复制同一未掩码实现，official micro m6A-start 6 行及 6 个 artifacts 已追加隔离，累计 300 行、251 个 result 文件。E6-v2 corrected 6 格已启动。E6-v1 micro 首批 3 格通过 ledger+result+protocol 三证；pre NLL=1.3968、独立 mask/order noise=0.0037，旧口径不得比较。导出器只接收 controlled 或对应 `_mlm15fix` 协议，防止旧值回流。

**⑨ E6 阶段自推进**：E6-v1 micro 已 6/6 双证收口，模型清单自动推进到 ERNIE-RNA/RNA-FM。`e6_phase` 逐格验证并原子更新；E6-v2 6 格与 corrected 342 格均有只读 verify-complete，未完成不得标 DONE，完成后禁止 monitor 空跑复活。遗留 `bash -s` 旧父进程及其 q_splmore/q_master 已清剿。

**⑩ AIDO 协作式独占窗口**：`exclusive_aido` 以原子标志协调 corrected/E6/CRISPR 在新 cell 前等待，当前 child 自然结束后执行 AIDO MRL s43，finally 清标志并恢复队列。排空判据允许等待 parent 的小型 CUDA context，但要求实际训练进程清空且总显存≤512MiB。完成必须 `finetune_mrl` 的 PEARSON_R 双证 + `audit_1016=0`；未达前仍为在途，不得写完成。

### 10.15 导师汇报扩展与证据修复计划（2026-10-26，非冻结执行登记）

> 依据：用户本轮逐页批注及实验扩展要求。先修实现、冻结矩阵、恢复真实 GPU 执行，再刷新图和 PPT。历史 fixed-epoch 或 legacy 数值只作背景对照，不能当作本轮完成证明。用户确认：8 任务介绍采用本节最终注册表的真实粒度，不为了形式上的“每类两个”改变任务定义。

**① 8 任务最终分类与统一比较轴**：序列级分类 = ncRNA 家族分类（ACC）+ CRISPR 脱靶二分类（PR-AUC）；序列级回归 = MRL（Pearson r）；碱基级分类 = m6A（AUC）+ SpliceAI 三分类（macro-F1）+ 二级结构（F1）；碱基级回归 = mRNA 降解（PCC，MCRMSE 辅助）+ 结构得分插补 SSI（PCC，MCRMSE 辅助）。§10.13 中“4 类×2”和“CRISPR 备选连续”是历史未定稿，均由 §10.14 及本节取代。所有扩展统一 random/family 两种切分、17/29/43 正式种子、frozen/LoRA/full 三策略，并优先官方模型；RNA-Sc 自训系列只用于同源受控等价线和后续补充对照。

**② P0：真实 validation 收敛与八任务验收器**：当前代码 `valplateau.py` 读取 `epoch_train_losses`，与 §10.14 的 validation-loss 合同不符；在远程新批次启动前必须改为独立 held-out validation 子集、每 epoch 持久化 `epoch_val_losses`、source=validation，并把该证据与 ledger done、result.json、tokenizer/CUDA smoke 一起纳入验收。SpliceAI、degradation、SSI 的官方 train/test 数据必须先从 train 中确定性划分 validation，不能拿 test 调参、选 checkpoint 或判断停止。新协议 RID 加 `_valplateau_v2`；已有 fixed-epoch 和 train-loss plateau 均不能冒充 v2。验收器覆盖全部 8 任务及 CRISPR，不得以 342 格三任务子验收替代全项目验收。

**③ 八任务结论图与任务扩展**：结论①a 后增加与前三张同构的四柱图（frozen random/family、微调 random/family），按任务分别给出主指标，禁止跨指标共用一个未经说明的纵轴。结论②给出 8 任务 default-LR 与 tuned-LR 的配对差值及真实 LR；先在 seed101 验证集选 LR，再以三种子正式臂检验，禁止全量网格代替正式复测。结论③扩展 LoRA/DoRA/full/rank 对照至 8 任务，并优先复测 RiNALMo-micro rank8 的同协议值，检查 metric、split、checkpoint、LR、数据代际和测评实现，而不是因“太低”定向追求高分。

**④ 同源数据量等价线**：只用 RNA-Sc 同配方规模谱与 RiNALMo 官方 micro/mega/giga 两个家族分面；每任务每家族绘制 small-full(n) 与 large-LoRA(m) 两条学习曲线，横轴为标注量、纵轴为同任务主指标，closest 等价点和误差带以逐种子配对结果计算。必须直接回答“小模型 full 在 n 条数据时达到大模型 LoRA 在 m 条数据的表现”；不在曲线覆盖区插值时标“未观测到等价点”，不得强行制造交点。训练/评估预算一致，结论限于被检验模型、任务、split 与 LR 协议。旧 33M/30M 名称不混用。

**⑤ 结论⑤、机制与异常复核**：

| 工作包 | 预注册问题与最小范围 | 通过条件 |
|---|---|---|
| C5 任务效应 | 8 任务补同协议学习曲线；MRL/m6A 扩展其他可接入官方模型，检查“未见同类坍缩”是否跨模型成立 | 模型×任务×策略×split×种子完整，主指标/数据代际一致 |
| ncRNA 坍缩归因 | 核查类别/家族映射、训练/测试标签覆盖、随机与家族 split 的基线、预测熵/混淆矩阵、head 与 backbone 更新、序列长度/GC 混杂；random-init 与 frozen 为对照 | 先排除实现/评测问题，再区分表征、分类头和数据结构解释；不预先接受“分类头坍缩” |
| 机制 t-SNE | 8 任务×random/family×pre/Post-LoRA/Post-full；同一样本同一坐标拟合，点按真实类别/家族着色，标集合/样本数/模型/随机种子；RiNALMo 以 CLS 表征为参照，同时保留预测头前 embedding，必要时追加 head 后 logit 图 | 表征抽取与 GPU 证据齐全，统一 perplexity/random_state；t-SNE 仅作可视化，轮廓系数和 ACC 另列，不把投影距离当因果证明 |
| C5d 大模型 | 逐 run 核查 mega/650M 缺点的 ledger、result、失败原因和 RIDs；补缺失档，不能通过删点或连线掩盖 | 每个显示点均可回溯源 result，pending 单独标记 |
| C5c 标注预算 | 在 1000–3000 之间固定 {1500, 2000, 2500} 三个补充档，8 任务补齐；RiNALMo micro、mega（官方约148M，用户所称180M档）、giga（约650M）分别复测 | 各档同 split 同采样协议，逐种子结果+95% CI，不把固定 epoch 当收敛 |
| C5b 资源 | ERNIE-RNA 的 LoRA/full 复测并扩展到 8 任务；时间×性能图按任务分面，统一模型、split、n、batch、GPU 和停止协议 | wall/peak/checkpoint 三证，实测值直接关联 run_id，不用跨协议倍数概括 |

**⑥ 执行顺序与门禁**：远程 CUDA、代码、数据与当前队列盘点 → 修复 validation/导出/验收并跑 focused tests → 隔离冲突协议且保留证据 → 官方模型的小模型高价值缺口（micro rank8、MRL/m6A、ncRNA 诊断、表征抽取）与 corrected 任务并行 → mega/giga 和数据量加密 → 自训同源等价线 → 三轮 ledger/result 对账 → 刷新 8 任务图和 PPT。单卡以共享卡锁和按 batch 实测 need 的多 worker 填充显存，禁止无锁重复启动；只在一个连接内执行远程检查，避免高频 SSH。所有新训练均保存配置、命令、git SHA、CUDA/GPU、随机种子、逐 epoch train/val、停止原因、资源与结果路径。每批次代码验收后及时提交 GitHub；代码留 `/home/cunyuliu/rna-ft-eval`，大型数据/权重/artifacts 留 `/teams/HoulabData_1788502323/liucunyu/rna-ft-eval/`。

**⑦ PPT 边界**：在原第 3 页后插入任务地图；结论①a 后插入任务扩展页，其他既有页面不重排、不改用户手调样式。删除已执行的批注框，修正与图不匹配或证据过强的文字，图注说明样本、模型、策略、split、指标及前后页关系。PPT 正文统一 Microsoft YaHei、1.5 倍行距，表格遵循既定紧凑排版。未经上述门禁的 8 任务数值不得进入最终结论页；阶段性交付可包含“待复核/在测”的明确标记，不冒充全量完成。

### 10.16 BEACON modification 任务语义纠错（2026-10-27，覆盖相关旧口径）

> 直接证据：官方 BEACON 论文 Modification Prediction 与 `terry-r123/RNABenchmark/downstream/train_modification.py`；远程 parquet 逐条核查为 101nt sequence + 12 维 label。官方实现为 sequence-level multi-label，12 维 BCE，逐修饰类型 AUC；m6A 对应标签索引 7，另有 mean AUC。

**① 正确的任务分类**：本项目的 `modification` 是**序列级多标签分类**，不是 per-base 任务，也不是单独的 m6A 位点预测。8 任务因此按实际输出粒度为：序列级分类 3（ncRNA、CRISPR、modification）、序列级回归 1（MRL）、碱基级分类 2（SpliceAI、SSP）、碱基级回归 2（degradation、SSI）。此前的 2+1+3+2 注册表和“m6A per-base 免疫”均不是官方任务语义，予以废止。后续若需要真正 per-base m6A，必须另找数据源、独立注册任务与 RID，不能拿本文件替代。

**② 实现与隔离**：旧 `finetune_base` 将 12 维标签误填到 101 个碱基位置，属于任务实现错误，不是 tokenizer 单纯偏移。527 条历史 modification done 行已标 invalid 并保留 quarantine manifest；历史 m6A 数值不得支撑“免疫”“家族切分稳定”“PEFT/rank 稳定”“E3 数据量不敏感”“E6-v2 per-base 起点差异”等结论。传统 per-base baseline 与相应 E6 m6A-start 也须按新任务语义重审，不能借 controlled 结果掩盖该问题。

**③ 新实现与验收**：`finetune_base` 已改为序列级 12 维多标签 head + BCE；m6A AUC 用索引 7，mean AUC 为辅助；validation 使用真实 held-out 集，训练/验证/测试三方无重叠，runtime 与 convergence 证据保留。新正式结果使用 `_seqmlfix` 独立 RID；`_b20fix` smoke 仅作工程验证，不作为科学结果。序列级多标签允许单碱基/3-mer 模型时，仍需 tokenizer 无 [UNK] 和输入语义审查，不再用 per-base token 对齐当作通过条件。

**④ 科学影响**：m6A 不再用于证明“逐碱基任务不崩/免疫”。所有相关 PPT、preprint、图集、决策树、统计检验与旧结论须冻结，待 `_seqmlfix` 的 3 seeds × 双 split × 三策略 × 官方模型复测后重新判读。当前只确认实现与 smoke 验证通过，不宣称 m6A 已复测完成或已恢复旧结论。MRL、SpliceAI、SSP、degradation 与 controlled causal E6 的证据不因此自动失效，但各自仍按对应验收协议执行。

### 10.17 过拟合分支与 best-val 协议（2026-10-27，执行登记）

1. rank8/部分 MRL 的 val2 长训中观察到 train loss 持续下降、validation 早期最低后回升，不能把“训练到末轮”当作泛化最优，也不能把未达 plateau 的结果强行标为正式完成。诊断批次均保留曲线，不作为正式均值。
2. 对这类格新增独立 `bestval_v1` 分支：validation 实质改善时保存最佳 backbone+head；连续 `patience=3` 个 epoch 改善不超过 `max(best×0.02,0.008)` 时 early-stop，恢复最佳 checkpoint 后只在 test 评估一次。best-val 是训练选择协议，不是 plateau 收敛的替代包装；结果须带 best_epoch、stale_epochs、stop_reason、曲线、best checkpoint 路径与 runtime。
3. `bestval_v1` 与 `valplateau_v2` 使用不同 RID、结果目录和报告口径，不与 legacy/fixed-epoch 混均值。需要比较时须同模型、任务、split、seed、训练预算和采样协议成套复跑；旧 cancelled/failed 格不可复用为完成。early-stop 条件满足可标该协议收敛，未满足不得标完成。
4. 对长时间无改善的旧 val2 格可停止并保留 RUNNING/诊断证据，切换 bestval 独立分支；不为了显存占用而无限延长已明确过拟合的格。所有新 bestval 也须真实 CUDA、tokenizer/split 证据和 result+ledger+checkpoint 验收，不允许只记录“best epoch 数字”而没有恢复 checkpoint。

### 10.18 best-val、统一调度与机制诊断验收（2026-10-27）

1. **checkpoint 证明**：`best.ckpt` 必须以 `weights_only=True` 可读，包含非空 backbone/head tensor state；`epoch/best_epoch/best_val` 与 result 一致。result、plateau、ledger 的曲线、停止原因、best 元组和 checkpoint 引用必须一致，CUDA/tokenizer、`acceptance_eligible` 与 split evidence 不可缺失。
2. **执行边界**：统一调度器只接受显式 jobs registry，按唯一 job key/RID/result_dir、显存预算、model/cell 生命周期锁执行；rc=75 跳过而非完成，rc=0 但证明不全仍失败。registry 只描述待执行矩阵，不能充当科学完成清单。
3. **modification-E6**：旧 per-base 训练入口禁用；新臂为序列级 12 标签 BCE，强制 `_seqmlfix` 与独立 validation。遗忘评价继续使用固定 15% masked-position NLL，任务收敛协议与 `forgetting_protocol` 分列。29 条旧记录保持 invalid。
4. **ncRNA 诊断**：同一 test manifest 比较 pre/Post-LoRA/Post-full；post 恢复 best-val 后导出 CLS、head.pool、logits、预测熵、margin、混淆矩阵及 length/GC/family。pre 的随机参考头 seed=201，仅用于参考，其 ACC 不是 zero-shot 能力。联合 t-SNE 只拟合一次，silhouette 用原始高维 embedding；图只作描述性诊断。
5. **当前验收事实**：远程 151 项 focused tests、本地 196 项全仓 tests 通过；ncRNA LoRA、modification LoRA、MRL full 和 modification-E6 LoRA 的真实 CUDA smoke 通过，均 `acceptance_eligible=false`。rank8 random 已有 2 个、MRL random LoRA 已有 3 个正式 best-val 结果通过三证，但仍不是完整矩阵；正式结果与图表须逐格核验。

### 10.19 C5c dense 数据档与全任务波次（2026-10-27）

1. **整簇嵌套采样**：ncRNA family 使用 `prepare_e3_dense.py` 生成 {10,100,1000,1500,2000,2500,3000} × seeds 17/29/43/101 的 28 个子集。每个 seed 只排列一次簇顺序，逐档整簇累加；不截断簇内行，较小档是较大档的子集。旧 E3 文件保持不变。
2. **训练与证据**：dense 子集文件名和 RID 均带 `_dense`；`finetune_one --dense-clusters` 仅用于 family 且要求 n_train>0，读取子集后不再做第二次行级 sampling。result 同时保存 `requested_n_train` 与实际 `n_train`，绘图不得把整簇 overshoot 隐去。
3. **波次范围**：C5c 共 **2016 格 = 8 任务 × 3 个 RiNALMo 档 × LoRA/full × random/family × 7 数据档 × 3 正式 seeds**。ncRNA family 的 126 格使用 dense，其余任务使用各自既定 seed 采样。全量点复用主矩阵，不重复训练；giga full/SSP 等按任务限制 batch 和显存预算。
4. **执行门禁**：28 个子集已逐档验证并备份 `/teams/data/e3_subsets_dense/`；2016 格 dry-run 唯一性通过，但尚未形成结果。主矩阵和资源窗口优先，C5c 队列不得与专用 lane 重格。调度器必须显式传 `--task`，MRL/SSP 的 split-evidence protocol 与 best-val 一致。

### 10.20 七任务机制诊断范式与 SSP pair 对齐门禁（2026-10-27）

1. **诊断必须服从真实输出语义**：CRISPR 使用序列级二分类概率与 PR-AUC；MRL 保存连续预测、残差和 Pearson r，不能对连续标签直接套分类 silhouette；modification 保存独立 `[N,12]` logits/sigmoid/标签，m6A 为索引 7，不能把 12 标签当 softmax 单分类。SpliceAI 使用监督 mask 内的 per-base hidden 与 TokenHead 隐层；degradation/SSI 使用同一 per-base 表示并保存逐位置预测与残差。
2. **SSP 是 pair-level 实现**：当前正式 runner 使用 `PairHead` 和上三角 `(i,j)` 碱基对分数，主指标为 pair-level precision/recall/F1。任务注册表和主指标不变，但机制诊断必须使用 `(sequence_id,i,j)` 的 pair features、gold、score、pair distance 与各状态独立 validation threshold；不得套用 SpliceAI 的 per-base 三分类 head 或混淆矩阵。
3. **SSP token/pair 对齐修复**：2026-10-27 代码核查发现旧 `finetune_ssp` 将原始碱基下标直接用于 tokenizer 输出；对自动加入 CLS/EOS 的官方 tokenizer，这会把 pair target 与 hidden 错位。新实现必须验证全长单碱基映射、排除 special/PAD、保证确定性右截断，并将每个碱基对 `(i,j)` 映射为 `(base_token_pos[i],base_token_pos[j])` 后再计算 loss 和提取分数。不得只修评估而保留训练错位。
4. **隔离与恢复**：新 SSP 运行统一使用 `_pairalign` RID，旧 RID 不覆盖、不混均值。互补 registry 中 90 个 SSP 格在修复验收前不得进入正式训练或图表；已完成旧格按 tokenizer 和 artifact 逐项盘点、备份后隔离，不能只凭模型名批量删除。RNA-Sc 无特殊 token 的历史结果也须保留对齐证据后再判断可否作为 legacy 对照。修复须通过 unit tests、真实 tokenizer 对齐和真实 CUDA best-val smoke；smoke `acceptance_eligible=false`，通过后才恢复 3 seeds 正式格。
5. **机制工程边界**：采用共享 manifest/best-val/联合投影核心，加 sequence/token/pair 三类 adapter，避免七份训练循环漂移。三状态必须在同一 state-independent manifest 上提取；full-test 指标与 t-SNE 采样指标分列。SSP 仅保存抽样 pair features，禁止落盘完整 `L×L×D`。CRISPR family 是 pair-sequence cluster，不是 guide-disjoint；modification 是 window cluster proxy；SpliceAI 不是 gene/chromosome split；degradation family test 不是 leaderboard blind test。
6. **绘图与推断**：`plot_mechanism` 需支持 sequence/token/pair representation、离散或连续着色和可选 silhouette。连续回归不计算分类 silhouette；multi-label 不伪造单标签；token/pair 坐标必须保留 base/pair ID。pre 的 backbone 是真实预训练表示，但 pre 预测来自 seed=201 的随机参考头，不得写成 zero-shot 任务性能。
7. **优先复用 checkpoint**：其余任务机制诊断优先读取已通过 proof 的 best-val checkpoint，不重复训练。post 必须在完整 test 上复算主指标并与源 result 对账，再从同一测试集按与预测无关的确定性规则抽样做三状态联合投影；full-test 指标和 sampled-manifest 指标分列。MRL 先实施该路径，保存 y_true/y_pred/residual，连续标签不计算分类 silhouette。若源格缺失或 full-test 对账失败，不得用重训或抽样指标掩盖。
8. **modification 多标签对账**：保存完整 `[N,12]` labels/logits/sigmoid probabilities，m6A 固定为索引 7。逐标签同时保存 ROC-AUC、positive/negative support 和 valid mask；无双边支持的标签 AUC 记为 null，不伪造 0.5 为真实测量。为复现源 result，另计算 source-compatible 数组（无效标签以 0.5 补齐）及其 mean AUC；同时单列 valid-only mean AUC，二者不得混写。t-SNE 仅以 m6A 标签视图着色，不把 12 标签转成单任务分类。
9. **CRISPR 不平衡诊断**：主指标为 PR-AUC，ROC-AUC 为辅；0.5 阈值 confusion 仅作辅助。post 必须在完整 test 上复算并与源 result 对账。t-SNE 样本在看任何状态预测前，按 sequence hash 选择至多 256 个正例，再以负例 hash 顺序补足 1024；若正例不足则全部纳入。该抽样用于可视化，属于正例富集，不得据此计算或展示 sampled PR-AUC/患病率代替 full-test。family 仅称 pair-sequence cluster split，不宣称 guide-disjoint。
10. **per-base split 证据边界**：SpliceAI、degradation、SSI 的当前 runner 均从 train 内重新 holdout validation，不能写成 official validation；部分 best-val result 没有 `data_evidence` 字段。机制诊断必须独立重建 test 和 split，记录实际 generator、source hash、序列/cluster 零重叠和缺失源证据，不得伪造 `data_evidence` 一致性。SpliceAI family 是 100nt window sequence cluster，不是 gene/chromosome split；degradation family test 仍不是 leaderboard blind test。post 仍以源 checkpoint 的 full-test macro-F1/PCC 对账。
11. **per-base best-val 源格波次**：SpliceAI、SSP、degradation、SSI 各建立 RiNALMo-micro、seed17、LoRA/full、random/family 共 16 格，使用 `bestval_v1` 和当前 B20/SSP pairalign 代码。独立 state-dir=`mechanism_source_perbase`，单 worker、每格预算 8GiB；其他既有队列继续运行，显存不足等待，不双开同 RID。旧 valplateau_v2、legacy 和 smoke 均不算源格。16/16 result/plateau/checkpoint/runtime 验收后才进入对应机制图；C5c 2016 格仍未启动。
12. **SpliceAI token 诊断**：主图使用 B20 监督 mask 内有效碱基位置的 per-base hidden，不把 CLS 当作剪接位点表示。类别语义固定为 `0=negative、1=acceptor、2=donor`。源 result 的主对账指标为 `MACRO_F1/value` 与 `MICRO_F1/value2`；ROC-AUC 仅作 full-test 辅助诊断，不与 `value2` 对账，也不得写成源 AUC。完整 test 同时保存 base_position、token_position、label、三分类 logits/probabilities；full-test 哈希绑定 task、max_len、B20 版本、sequence/base/token/label，不用 sampled 指标代替 full-test。可视化在预测前按 token_id 对 negative/acceptor/donor 各类确定性选择至多 512 个位置，三状态共享相同 token_id；类别均衡仅用于显示，不计算 sampled macro-F1、ROC-AUC 或患病率。
13. **per-base manifest 与源格准入**：SpliceAI、SSP、degradation/SSI 的 post 必须先从 16 格 registry 唯一定位 RID，要求 `proof_state=complete`，且 registry `result_dir` 与 ledger `out_dir` 的 realpath 一致，再恢复 checkpoint。三状态须共享 manifest hash、样本 ID、base/token（或 pair）位置和标签；缺失或篡改 manifest、source proof、full-test 对账任一失败即中止。失败后的未完成 diagnostic/predictions/embeddings/aligned 可清理重试；已有成功产物禁止覆盖或删除。
14. **源格执行修复**：SpliceAI/Regbase 在 test result 已写出后曾因 `metric/value` 重复关键字导致 ledger 未完成，修复 runner 后只允许凭原 result、plateau、best.ckpt 和 runtime 补写 ledger，不重训。SSP registry 不得向 `finetune_ssp` 传不支持的 `--out-suffix _pairalign`；`_pairalign` 已由 runner 的 `_run_extra` 固定写入 RID。修改 registry 必须归档原文件，并在旧 parent 安全退出或切换后再进入 SSP，禁止带着旧内存参数继续执行。
15. **单格辅助 lane 并行门禁**：主 `mechanism_source_perbase` 仍保持单 worker。仅在主 parent 已被非目标活动子进程占用时，才可从原 16 格 registry 原样抽取尚未完成的目标格，建立单格辅助 registry 和独立 state-dir。启动前必须同时确认：目标 `proof_state=runnable`、目标及同名 lane 无活动进程、主 parent/子进程真实存活、单格 dry-run 唯一、按每格 8GiB 预算后仍保留至少 1GiB 安全余量。其他模型的非同 RID 任务不算冲突，但必须计入实时显存。主 parent 恢复派发后须凭 ledger running/done 与完整 proof 跳过辅助 lane 格，禁止双开或覆盖结果。辅助 lane 只改变并行调度，不改变数据、RID、训练参数、收敛协议或验收标准。
16. **SSI random 同序列记录合同**：official SSI train=14,049、test=3,095；train/test 内分别有 15/2 条同序列额外记录，24 个重复序列组均存在不同标签，禁止 dedup 或只保留首条。train holdout 必须以 canonical sequence hash 为 cluster 整组切分，使同序列不同标签记录永不跨 train/val；official test 全量保留。当前 seed17 重建为 train/val/test=12,645/1,404/3,095，train+val=14,049，test 唯一序列 3,093，三侧 sequence-hash 零重叠。诊断以 `sequence_hash:occurrence` 作为记录级 ID，token ID 必须唯一，MCRMSE 按记录等权，PCC 仍拼接全部有效 token。source 与 reconstructed `data_evidence` 必须逐字段一致；post 还必须满足 `source_data_evidence_present=true`、`source_data_evidence_note=matched_reconstructed_sequence_grouped_split` 和记录级 identity proof，缺任何一项均拒绝三状态对齐，不能仅凭 full-test 指标相同复用旧 checkpoint。degradation 和 SSI family 的既有 manifest/hash 不得因此改变。首次 lane6/7 的 overlap 失败发生在训练前且不得写成结果；修复提交为 `5862cd7`，强制证据门禁补充提交为 `362a0f3`。
17. **通用单格辅助 lane**：辅助启动器可从 complementary 或其他正式 registry 原样抽取一个 runnable 格，但不得修改命令、RID、训练参数或验收标准。仅当主 busy child 真实存在且非僵尸时启动，目标 `proof_state=runnable`，不存在同目标或同 lane 的 `expansion_queue.py` 进程，单格 dry-run 唯一，并保证实时可用显存大于该格 `need_gb+1GiB`。辅助 registry/state-dir 必须独立且保留原始记录；主队列恢复后凭 ledger/proof 跳过，不得以辅助 lane 启动数充当完成数。通用 launcher 的自身命令行不得被误判为同 lane 进程，进程匹配必须限定真实 runner/queue。
18. **best-val 异常种子与早停敏感性**：同一模型/任务/split 的正式种子出现明显性能差异时，先逐格核对 `plateau.json`、`best.ckpt`、best_val/best_epoch、validation/train 曲线、test 样本数和主指标，不得直接归因于模型坍缩或评测错误。`bestval_v1` 的 `min_delta=0.02`、`abs_floor=0.008`、`patience=3` 是该批结果的既定合同：即使后续 epoch 出现低于阈值的 validation 改善，也必须保留原 best_epoch 和停止原因，不得事后重选 checkpoint 或修改结果。正式三种子补齐前，不用单种子高低点写跨模型结论。若需检验早停敏感性，必须另设明确标记的诊断协议和 RID，预先冻结停止规则，与原 bestval_v1 分表展示，绝不混入正式均值或冒充同协议复测。
19. **MRL LoRA/full artifact 物理迁移与复用**：`/root/rnaft/artifacts` 与 `/teams/HoulabData_1788502323/liucunyu/rna-ft-eval/artifacts` 是不同物理位置；teams registry 下的 `ledger done but result_dir missing` 必须先与 root registry 对照，不能直接判为科学结果缺失或重训。2026-10-28 对 60 格 MRL LoRA/full 矩阵完成双 registry 审计：54 格 complete（LoRA 30、full 24），6 格 runnable，且六个缺口仅为 RiNALMo-650M full 的双 split 三种子。54 个 complete 中，41 格由 root 逐文件复制到 teams，12 格原已是 root→teams symlink，1 格为 teams 原生完成；实际迁移 31,252,133,777 bytes。复制后先重算逐文件 SHA256 并要求 teams `proof_state=complete`，通过后才移除 root 实体目录并建立绝对 symlink；运行格和 runnable 格不得进入复制或删除流程。独立三轮审计分别验证 60 格唯一对账、53 个 root symlink 与 82 项 result/checkpoint 哈希、teams 54 complete+6 runnable 及全部 CUDA/acceptance proof。迁移 manifest 与 audit 保存于 `/teams/.../status/migrations/mrl_lora_full_root_to_teams_20261028.json` 及同名 `.audit.json`；这些证明只确认结果可复用，不把尚缺的 650M full 写成完成，也不自动生成跨模型科学结论。

### 10.21 2026-10-28 导师汇报续接与防返工执行总账

1. **现行 PPT 基底**：用户指定的 20 页本地文件早于 10 月 27 日阶段交付。当前续接采用已验收的 28 页导师讨论修订版（SHA256=`26a6fdd7b030bd3789ffa83952ec20a8df59d4f7e08e18665186f7f1fd5878e2`），原 20 页文件保留不覆盖。28 页版第 4 页已含任务地图，第 9–16 页已含 8 任务机制图；不得重复插入。
2. **已完成且不得重跑**：8 任务 random/family × pre/Post-LoRA/Post-full 机制图已在 RiNALMo-micro、seed17 范围完成，源 checkpoint 与 full-test 对账齐全；micro ncRNA rank8 已完成双 split × 3 seeds 六格正式 best-val 验收。机制图不替代三种子主矩阵，rank8 旧低值未复现也不自动证明旧测评错误。
3. **当前可复用结果**：MRL/modification 的 micro/mega/ERNIE-RNA/RNA-FM frozen 双 split 三种子共 48 格已验收；MRL LoRA/full 60 格中 54 complete、6 runnable，真实缺口仅为 RiNALMo-650M full 双 split 三种子。其余任务、模型、策略必须以实时 registry+ledger+result proof 重新计数，不能用 registry 大小或启动进程数充当完成数。
4. **实验顺序**：P0 先核 CUDA、git、数据、registry 与活跃 RID，保留在训格并去重；P1 闭合 8 任务官方模型主矩阵及 MRL/modification 跨模型矩阵，650M 大格只在满足实测显存门后启动；P2 闭合结论② default/tuned LR 和结论③ LoRA/DoRA/full/rank；P3 在主矩阵与同协议资源记录稳定后执行 C5c 2016 格、C5d 缺点与 C5b 八任务时间×性能；P4 最后完成 RNA-Sc 与 RiNALMo 同家族 small-full(n) vs large-LoRA(m) 等价线。全量点复用主矩阵，严禁与专用 lane 重格。
5. **并行与停止规则**：单卡多 worker 共享唯一调度与生命周期锁，按同 batch 实测 need 填充空闲显存并保留 1GiB 余量；不得为“占满显存”绕过门禁、启动冲突格或无限延长已过拟合任务。CUDA 不可用、发生 CPU 静默降级或证据链失败即停并保留日志；best-val 按既定 early-stop 合同结束并恢复最佳 checkpoint，valplateau 任务须达到 validation 平台。
6. **图表与页面映射**：任务地图解释后续所有结果页的任务与指标；结论①a 使用每任务独立主指标的同构四柱图；结论②使用 seed101 validation 选 LR、17/29/43 正式复测的 default/tuned 配对；结论③分列 best-val 与 legacy rank；结论④只呈现同家族数据量等价点及 CI；结论⑤、⑤b、⑤c、⑤d 仅画可追溯 run_id 的点。未观测等价点、pending、n<3 与协议差异必须显式标注。
7. **记录、归档与同步**：每批保存命令、git SHA、GPU/CUDA、seed、数据 manifest、逐 epoch train/val、best/stop、wall/peak/checkpoint、result/RID 与结论；图同时保留 CSV/JSON、脚本、metadata、PNG/PDF。旧文档和废弃数据先核引用再归档，不删除隔离证据。确认后的代码留 `/home/cunyuliu/rna-ft-eval` 并及时提交 GitHub，大文件与权威 artifacts 留 `/teams/HoulabData_1788502323/liucunyu/rna-ft-eval/`。

### 10.22 2026-10-28 八任务逐结论全覆盖复核

> 本节将用户本轮逐页意见转成不可遗漏的执行矩阵。八任务固定为 3+1+2+2：ncRNA、CRISPR、modification；MRL；SpliceAI、SSP；degradation、SSI。official RiNALMo 档为 micro 33M、mega 148M（用户所称“180M 档”）、giga 650M。已完成资产只复用，不重跑；本登记不表示任何开放矩阵已完成。

| 页面/结论 | 必须覆盖的实验与证据 | 图与验收边界 |
|---|---|---|
| 任务地图 | 介绍上述四类八任务、输出粒度和主指标 | 28 页版第 4 页已存在，只核语义和排版，不重复插入 |
| 结论①a | 八任务 frozen/LoRA/full × random/family × 17/29/43，优先官方模型 | 与既有三张四柱图统一风格；每任务独立主指标，放在结论①a 后 |
| 机制可视化 | 复用八任务双 split × pre/Post-LoRA/Post-full 的 RiNALMo-micro、seed17 表征、坐标与 full-test 对账 | 参照 RiNALMo 的 CLS、真实标签、独立测试集和标注方式；可重排视觉但不重复已验收抽取，不作因果证明 |
| 结论② | 八任务 seed101 validation 选 LR，17/29/43 default/tuned 正式配对 | 真实 LR、split、rank、n_train、协议入表；tuning seed 不进正式均值 |
| 结论③ | 八任务 LoRA/DoRA/full 与 rank4/8/16 | micro ncRNA rank8 六格复用；best-val 与 legacy 分列，旧低值只作协议归因 |
| 结论④ | RNA-Sc 与 RiNALMo 两家族 × 八任务 small-full(n) 与 large-LoRA(m) | 横轴为标注量；逐 seed closest 等价点与 CI，直接回答“小 full@n ≈ 大 LoRA@m”；无交点写未观测到 |
| 结论⑤ | 八任务同协议学习曲线；MRL/modification 增测其他官方模型；ncRNA 归因 | 先排除标签、家族映射、测评与 checkpoint 问题，再判断真实坍缩；不以单模型外推任务免疫 |
| 结论⑤d | 对 mega/giga 每个显示点回查 RID/result，分类未跑、失败、未导出、路径缺失、协议隔离 | 真实缺点优先补；pending/NA 不补零、不用插线掩盖 |
| 结论⑤c | 八任务 × micro/mega/giga × LoRA/full × 双 split × {10,100,1000,1500,2000,2500,3000} × 3 seeds | 加密 1000–3000；逐 seed+95% CI，全量点复用主矩阵；沿用 C5c 2016 格唯一账目 |
| 结论⑤b | 八任务时间×性能，补 ERNIE-RNA LoRA/full | 同模型、split、n、batch、GPU、停止协议；wall/peak/checkpoint 三证直接关联 RID |

**执行与交付门禁**：先完成实时 registry+ledger+result+checkpoint+runtime 对账，再按主矩阵与异常归因 → LR/rank → C5d/C5c/C5b → 同源等价线推进。单卡多 worker 必须服从唯一调度、生命周期锁和同 batch 实测 need+1GiB；complete 不重训、running 不双开，CUDA 不可用或 CPU 静默降级立即停止并留证。不得以占用率为由绕过 proof 或无限延长已过拟合格。每批记录训练命令、git SHA、数据 manifest、逐 epoch train/val、best/stop、资源与结论边界；通过三轮对账后才更新图和 PPT。PPT 只改目标页并另存，保留用户手调内容、Microsoft YaHei 和正文 1.5 倍行距；交接文档与绘图原数据按 current/archive 整理，废弃项先核引用再归档，隔离证据不删除；确认代码提交 `/home` 并推送 GitHub，大文件留在 `/teams`。

### 10.23 ncRNA family 训练顺序伪影隔离与重测合同

1. **事故证据**：当前与 orico 的 family parquet SHA256 完全相同，排除换数据；train 标签仅 134 个 run/6859 行、最长同类连续段 375，旧 runner 无逐 epoch shuffle。旧 micro LoRA-family seed17=0.084112，现行 shuffled best-val 三种子为 0.894860/0.905374/0.900701。严格 `finetune_one/max_len512` A/B 已完成且 proof=complete：仅关闭 shuffle 即得 ACC=0.095794，而 shuffled=0.894860；`finetune_clf/max_len128` 的 0.059579 仅作跨 runner 支持证据。
2. **即时隔离范围**：所有由 pre-shuffle runner 产生的 ncRNA family 性能，及其派生的“家族坍缩/崩溃带”、random−family Δ、模型规模谱、E3 数据量曲线、small-full(n)↔large-LoRA(m) 等价点和总结措辞，暂停科学判读。受影响 PPT 至少包括第 2、5、17、20–24、27–28 页及对应源图；第 25 页仅显存测量可保留，任何性能解释仍需 corrected RID。旧文件移入 quarantine/archive 索引，不删除原始 ledger/result/checkpoint。
3. **可保留证据**：现行 `bestval_v1` 且有独立 validation、best checkpoint、runtime、序列/cluster 零重叠和明确 runner 参数的格；micro rank8 六格及其 corrected 机制图不因旧事故失效。`finetune_clf` 与 `finetune_one` 诊断必须分别标注 max_len、batch、runner、epoch_shuffle，禁止把不同 runner 的差值写成单变量因果效应。
4. **重测顺序**：优先完成官方 micro/mega/ERNIE-RNA/RNA-FM 的 corrected ncRNA 主矩阵，再补 650M；自训 RNA-Sc 后续复测。旧 E3、⑤c/⑤d 与同源等价线只有在对应 corrected 曲线闭合后重绘，缺格保留 NA，不用 legacy 点回填。
5. **表述门禁**：严格 A/B 已验收，可写“该受控设置下，未 shuffle 足以复现近随机表现”；不得外推为所有模型/任务的唯一机制，也不得把 corrected 高值直接推广为所有模型均不存在跨家族泛化问题。t-SNE 继续只作描述性诊断，旧“分类头坍缩”不得恢复。

### 10.24 C5c micro/mega 五档闭合与29页阶段交付（2026-10-29）

1. **已闭合范围**：ncRNA random split × LoRA rank8 × corrected `bestval_v1`，RiNALMo-micro 33M 与 RiNALMo-mega 148M 的 {1000,1500,2000,2500,3000} 五档均已三种子闭合，合计30个唯一RID。micro 五档 mean=0.780885781/0.818570319/0.842657343/0.834498834/0.871406371，mega=0.836052836/0.856254856/0.875679876/0.884615385/0.904428904。148M 在五档均高于33M，33M在2500档回落，mega当前五档均值递增；上述只描述该任务、split、策略与协议，不能外推650M、full-FT、family或其他任务。
2. **图和PPT唯一续接基底**：`c5c_ncrna_lora_micro_mega.png/.pdf` 与 `_data.csv` 已登记，合并图源共10行30个唯一RID。当前阶段PPT为29页 `RNA_LM微调策略评测-导师讨论修订版_20261029_C5c五档更新.pptx`，新页位于演示顺序第22页（结论⑤后、⑤d前）；原有28页slide XML/rels不变，后续不得重复插入该页。微软雅黑、1.5倍行距、markitdown、layout Issues=0、独立字体渲染和29页PDF已验收。
3. **源数据与代码**：当前 `bestval_ledger_export_20261029.csv` 为385个唯一RID，旧379行逐字段保留，新增仅为mega 2500/3000档6格；4个拒绝项仍均为smoke test。源包 revision=`20261029_bestval_ledger_385_v10`，101个登记文件的本地及teams副本哈希一致。绘图 `/home` 提交为 `621ea49`，GitHub `rnaft-expansion-20261027` 为 `e186390`，全仓385 tests通过。旧快照和远端独立重绘证据均已归档，不得用旧pre-shuffle或中间态点回填。
4. **后续顺序**：先补齐 micro full-FT 五档三种子，再在650M真实满足28+1GiB门禁时补同协议LoRA；只有 small-full(n) 与 large-LoRA(m) 对应曲线均闭合后，才能按逐seed最近性能与95% CI计算等价点，未覆盖区间写“未观测到等价点”。650M、其余任务/split/strategy、八任务结论②③④⑤及⑤b/⑤d仍未完成；当前29页版仅为已闭合组的阶段更新，不是全目标完成声明。

### 10.25 六柱任务扩展与⑤d状态校正（2026-10-29）

1. **扩展图口径**：SpliceAI、degradation、SSI 的 B20-corrected 阶段表改为 frozen/LoRA/full × random/family 六柱，取消“LoRA 优先、缺失时 full”的混合微调柱。原表只有聚合 mean 与 n_seeds，因此不绘制未记录的 SD；n<3 用斜线、NA 表示未闭合，不能将本页解释为8任务终版。
2. **PPT 当前续接版**：`RNA_LM微调策略评测-导师讨论修订版_20261029_六柱扩展与状态校正.pptx` 共29页，仅修改演示页2、8、23：进度页登记33M/148M ncRNA random×LoRA 五档闭合；第8页换六柱图；第23页图内状态与页脚同步区分已闭合五档和650M/full/family/其他任务缺口。其他页 XML/rels 语义无差异。PPT SHA256=`acbb01c5ba4b501eb492ee885ca6e2b20367cefb781238f655221c0e98be6157`，PDF SHA256=`0c2afab83ba9331ff836e599dff5d3f9be9e137b98207f46e5e30b0a0b4651ea`。
3. **复现与待办边界**：源包 revision=`20261029_extension_sixbar_status_v11`，101个登记文件全部哈希通过；旧三任务四柱图与源表移入 `archive_20261028/绘图数据/obsolete_fourbar_20261029/`。绘图代码经108/108单元对账和385项测试后推送 GitHub `7a24117f064a2493ff8ae1d1a269ec33abe6c595`。v11 尚未同步 teams。连接恢复后已按 registry+result+checkpoint proof 确认 micro full-FT 五档15格全部 complete，正在刷新完整 best-val 导出；实时 GPU 与后续矩阵仍须按 proof 复核，不以进程数代替完成。

### 10.26 ncRNA 五档 full-FT 闭合与逐 seed 等价候选（2026-10-29）

1. **400 行正式导出**：micro full-FT 的1000/1500/2000/2500/3000五档15格全部 proof=complete，mean 分别为0.790986791/0.812742813/0.836052836/0.856254856/0.879953380。新 best-val 导出为400个唯一RID、4个smoke-only拒绝项；旧385行逐字段不变，新15行仅为上述 micro-full，全部具有 CUDA 证据。
2. **等价判读边界**：同任务 ncRNA random、同 `bestval_v1` 协议下，逐 seed 最近实测对为 s17 full@2500↔LoRA@1500（Δ=0.006993）、s29 full@2000↔LoRA@1000（Δ=0）、s43 full@2500↔LoRA@1500（Δ=-0.004662）。因此 full@2500≈LoRA@1500 为2/3 seeds候选，full@2000≈LoRA@1000 为1/3 seeds候选；不得写成唯一等价点或跨任务定律。图只连接实测预算，不插值，保留30个源RID、逐seed配对与25组预算对差值。
3. **当前 PPT 与源包**：第20页改为 `equivalence_ncrna_microfull_megalora`，当前文件 `RNA_LM微调策略评测-导师讨论修订版_20261029_等价线更新.pptx`，SHA256=`3a7d737706fbaae9fe36cd746b1d18675af7ce1b2be656c8716b315cbd784d18`；PDF SHA256=`1f3789308f5d13e10773bc21f9bb6fd6b0f4826cb1693812b4e1694c81b6415a`。源包 revision=`20261029_bestval_ledger_400_equivalence_v12`，104个登记文件，manifest SHA256=`628b95bbd68ecdadb29210c358e0a02d0c50015de6db7903d46fb7edf6a7b938`；旧协议示意图归档，两个 teams 副本与本地哈希一致。
4. **代码与后续顺序**：`/home` 提交 `f870f8cc4a31af420938848745050e387009c935`，GitHub `rnaft-expansion-20261027` 提交 `9aee3d4a6edfab5535c4cc7134a51ca3414002d4`，385 tests通过，teams独立重算的 data/pairs/meta 哈希一致。后续继续8任务主矩阵与结论②③，再补650M及其他 C5c 臂；650M仍需28+1GiB真实窗口，不能用 micro-full 的完成替代其他任务、split或模型规模。

### 10.27 八任务 PEFT/rank 注册表与协议去重（2026-10-30）

1. **注册范围**：`peft_rank_jobs_20261030.json` 覆盖8任务×5官方模型×{LoRA rank4/8/16 + DoRA rank8}×random/family×17/29/43，共960格；每任务120格，LoRA 720、DoRA 240。注册表仅是执行清单，不代表启动或许可完成。
2. **实时 proof**：960格 RID/result_dir 均唯一，102 complete、858 runnable、0 conflict；complete 全部为 LoRA，DoRA 尚未形成正式完成格。后续只复用 complete，主矩阵仍在运行的同 RID 不得双开，PEFT/rank 波次须待主矩阵门禁后启动。
3. **rank8 协议边界**：既有 micro ncRNA rank8 六格使用 `_fixedsplit` RID；新注册表的无后缀 rank8 属于主矩阵 `bestval_v1` 协议，二者不是同一实验，不能覆盖、混均值或误标重复。legacy rank、fixedsplit 与主矩阵 rank sweep 在图和统计中分列。
4. **代码与验收**：`scripts/expansion_jobs.py --wave peft-rank` 在本地和 teams 均生成960个唯一任务，385 tests通过；`/home` 提交 `a700ed6`，GitHub `rnaft-expansion-20261027` 提交 `b57abfc`。完整 proof 摘要保存为 `peft_rank_jobs_20261030.audit.json`。
