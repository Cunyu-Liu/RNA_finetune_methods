# RNA-LM 微调策略评测：任务分解（TASKS）

> 版本：3.57（2026-10-30 修订五十八【408格台账与MRL阶段图更新】：N13登记新增8格、MRL/modification 152 complete+28 runnable、650M frozen random n=2六柱图、PPT第7页定向更新及v13源包/teams验收；不把n=2写成闭合组。）
> 版本：3.56（2026-10-30 修订五十七【跨模型并行调度与无中断接管】：N13登记队首阻塞修复、387 tests、GitHub逐文件核验和两个父调度的无中断重启；5个真实CUDA任务并行、GPU util=96%，不以进程数替代完成。）
> 版本：3.55（2026-10-30 修订五十六【per-base best-val主矩阵与监控退役闭环】：N13登记270格注册表、12 complete+258 runnable、显存校准和3-worker队列；旧q_corrected已从监控白名单移除。生成器与whitelist提交均通过GitHub逐文件核验，386 tests通过。）
> 版本：3.54（2026-10-30 修订五十五【旧valplateau失控队列退役】：N13登记degradation 547 epoch无实质改善的法证、异常格与旧父队列停止、证据路径和bestval_v1替代合同；未把中断格或进程数记为完成，未误停正在收尾的SpliceAI。）
> 版本：3.53（2026-10-30 修订五十四【八任务后续交接与实时续接】：新增N13。以29页等价线更新版为基底，先实时proof接管现有任务，再按主矩阵→LR/rank→C5d/C5c/C5b→同源等价线→PPT/归档推进；完成任务地图、8任务机制图、rank8和已闭合五档只复用，所有完成判断以科学proof为准。）
> 版本：3.52（2026-10-28 修订五十三【导师汇报续接与实验顺序冻结】：新增文末 N 节。采用 28 页阶段修订版，防止重复新增任务地图、重跑 8 任务 seed17 机制图和 micro rank8；后续按真实 proof 缺口推进主矩阵、LR/rank、C5c/C5d、同源等价线，并同步整理 PPT 与绘图原数据。）
> 版本：3.51（2026-10-28 修订五十二【MRL LoRA/full 迁移闭环与 modification 正式格接续】：更新文末 M 节。41 格安全迁移、12 格既有链接及 1 格 teams 原生结果通过三轮审计；MRL LoRA/full 现 54 complete、6 runnable。mega full seed17 random 已验收；两个 modification micro LoRA 正式格已真实 CUDA 启动，尚待 complete proof。）
> 版本：3.50（2026-10-28 修订五十一【非 650M 官方模型 frozen 双任务双 split 闭合】：更新文末 M 节。RNA-FM MRL family 三种子均值 0.607078958、样本 SD 0.002309400；micro/mega/ERNIE-RNA/RNA-FM 的 MRL 与 modification 双 split frozen 三种子均闭合，原始表 48 个唯一 RID。650M 当前 free=23.356 GiB，未达到 28+1 GiB，未强行启动。）
> 版本：3.49（2026-10-28 修订五十【RNA-FM MRL random 闭合与 family 接续】：更新文末 M 节。random 三种子均值 0.671914368、样本 SD 0.003287618；seed29 family r=0.604613275 已验收，seed43 family 运行中。原始表扩为 47 个唯一 RID。）
> 版本：3.48（2026-10-28 修订四十九【RNA-FM MRL 正式 seeds 接续】：更新文末 M 节。seed29 random r=0.674587637，与 seed17=0.672911969 接近，通过完整验收；原始表扩为 45 个唯一 RID，seed43 random 已接力。）
> 版本：3.47（2026-10-28 修订四十八【ERNIE-RNA MRL 双 split frozen 闭合】：更新文末 M 节。family 三种子均值 0.651869863、样本 SD 0.002274850；ERNIE-RNA MRL 双 split frozen 三种子均闭合，原始表扩为 44 个唯一 RID。继续补 RNA-FM MRL 与 RiNALMo-650M。）
> 版本：3.46（2026-10-28 修订四十七【ERNIE-RNA MRL random 闭合与 family 接续】：更新文末 M 节。random 三种子均值 0.731101500、样本 SD 0.013112428；seed29 family r=0.652511131 已验收，seed43 family 运行中。原始表扩为 43 个唯一 RID。）
> 版本：3.45（2026-10-28 修订四十六【ERNIE-RNA MRL 正式 seeds 接续】：更新文末 M 节。seed29 random r=0.738159691，与 seed17 接近；先前导出与收尾时间差已复核为 complete proof，未重训。原始表扩为 41 个唯一 RID，seed43 random 已接力。）
> 版本：3.44（2026-10-28 修订四十五【RNA-FM modification 双 split 闭合与 MRL 中断核查】：更新文末 M 节。RNA-FM family 三种子均值 0.610547575、样本 SD 0.001880829，原始表扩为 40 个唯一 RID。ERNIE-RNA MRL seed29 random 未形成 complete 结果，按失败/中断查日志，不直接重启。）
> 版本：3.43（2026-10-28 修订四十四【RNA-FM modification random 三种子闭合】：更新文末 M 节。seed43 random AUC=0.626765217，random 三种子均值 0.621542029、样本 SD 0.004664643；原始表扩为 38 个唯一 RID，family 两格并行推进。）
> 版本：3.42（2026-10-28 修订四十三【RNA-FM modification 正式 seeds 接续】：更新文末 M 节。seed29 random AUC=0.620069565，与 seed17=0.617791304 接近，通过完整验收；原始表扩为 37 个唯一 RID，seed43 random 已接力。）
> 版本：3.41（2026-10-28 修订四十二【ERNIE-RNA modification 双 split frozen 闭合】：更新文末 M 节。family 三种子均值 0.783945262、样本 SD 0.002659571，全部 best_epoch=3；与 random 的 0.095089172 样本 SD 形成 split/checkpoint 依赖对照。原始表扩为 36 个唯一 RID，继续补 RNA-FM。）
> 版本：3.40（2026-10-28 修订四十一【ERNIE-RNA random 三种子与早停诊断】：更新文末 M 节。seed43 random AUC=0.757217391、best_epoch=2；三种子均值 0.748660870、样本 SD 0.095089172。三种子的 AUC 与 best_epoch 同向，且后续 validation 改善均受 0.008 门槛限制，支持早停敏感性线索但不作因果证明。）
> 版本：3.39（2026-10-28 修订四十【ERNIE-RNA modification 异常种子核查】：更新文末 M 节与 spec §10.20.18。seed29 random AUC=0.649582609，低于 seed17 的 0.839182609；plateau 证实其 best_epoch=0 且按既定阈值收敛，当前不能归因于评测错误。seed43 接续后再决定是否需要独立早停诊断。）
> 版本：3.38（2026-10-28 修订三十九【mega MRL/modification 双 split frozen 全闭合】：更新文末 M 节。modification family 三种子均值 0.642656914、样本 SD 0.001839440；mega 两任务双 split frozen 三种子均闭合，原始表扩为 32 个唯一 RID。继续补 ERNIE-RNA/RNA-FM 正式 seeds 与 RiNALMo-650M。）
> 版本：3.37（2026-10-28 修订三十八【modification mega family 正式 seeds 接续】：更新文末 M 节。seed29 family 通过完整验收，原始表扩为 31 个唯一 RID；seed43 family 已接力启动，待闭合双 split frozen 矩阵。）
> 版本：3.36（2026-10-28 修订三十七【modification mega random frozen 三种子闭合】：更新文末 M 节。seed43 random 通过完整验收，random 三种子均值 0.665768116、样本 SD 0.002475457；原始表扩为 30 个唯一 RID，family 补测已接力。）
> 版本：3.35（2026-10-28 修订三十六【modification mega 正式 seeds 接续】：更新文末 M 节。seed29 random 通过完整验收，原始表扩为 29 个唯一 RID；seed43 random 已接力启动，继续以 complete proof 而非启动数记账。）
> 版本：3.34（2026-10-28 修订三十五【mega MRL 双 split frozen 三种子闭合】：更新文末 M 节。seed43 family 通过完整验收，family 三种子均值 0.638028864、样本 SD 0.018922031；原始表扩为 28 个唯一 RID。开始接续 modification 正式 seeds，当前运行格不计完成。）
> 版本：3.33（2026-10-28 修订三十四【mega MRL family 正式 seeds 接续】：更新文末 M 节。seed29 family 通过完整验收，原始表扩为 27 个唯一 RID；seed43 family 已接力启动，仍需真实 runner 与 complete proof 验收。）
> 版本：3.32（2026-10-28 修订三十三【mega MRL random frozen 三种子闭合】：更新文末 M 节。seed43 random 通过完整验收，mega MRL random frozen 三种子均值 0.718885373、样本 SD 0.005574907；原始表扩为 26 个唯一 RID，family 补测继续按 running/complete 分离验收。）
> 版本：3.31（2026-10-28 修订三十二【mega MRL 正式 seeds 接续】：更新文末 M 节。mega MRL seed29 random 已通过 best-val/test/CUDA/proof 验收，原始表扩为 25 个唯一 RID；seed43 random 已接力启动，仍需完成后验收。）
> 版本：3.30（2026-10-28 修订三十一【MRL/modification 官方模型 frozen seed17 双 split 收口】：更新文末 M 节。mega、ERNIE-RNA、RNA-FM 的 modification family frozen 已验收，原始表扩为 24 个唯一 RID；继续补正式 seeds、LoRA/full 与 RiNALMo-650M，当前 frozen 表不替代最终 C5 矩阵。）
> 版本：3.29（2026-10-27 修订三十【per-base 机制诊断与源格证据链修复】：文末新增 v3.29。修正 SpliceAI macro/micro 与 B20 诊断合同；登记 SSP registry 参数修复、runner 收尾 bug、旧 result 补 ledger 和当前部署阻塞，未过 proof 不启动正式机制图。）
> 版本：3.28（2026-10-26 修订二十九【导师汇报八任务扩展与证据修复计划】：文末新增 v3.28。统一最终任务注册表；先修 validation 收敛与全矩阵验收，再按结论①-⑤、机制图、同源等价线和 C5 系列并行补测。历史旧值不自动转为已完成。）
> 版本：3.25（2026-10-24 修订二十八【科学完整性 P0 复审与恢复】：文末新增 v3.25 回填。实测确认 B20 标签错位与 official E6 标签泄漏，精准暂停受影响队列；按“备份隔离→修复验证→纠正重跑→收敛审计→结果交付”推进，未通过门禁的旧值不得写入 PPT/预印本。）
> 版本：3.24（2026-10-23 修订二十七【新集群 RTX5090 第二次接手 + 假 running 清理 + q_master 协议修正 + monitor v2 + 占满车道】：文末 v3.24 回填。上承 v3.23（服务器 docs/，10-18 新集群恢复 + 8 任务扩展）。集群 HEAD c1c287b / GitHub a0d696c；ledger 2633 行 done 2578；GPU 31.6G/32G 99% 占满。）
> 版本：3.16（2026-10-06 修订二十六【Day 20 · 假完成根治 + 审计纠错 + PPT 核对 + 反思成文】：以服务器实测为唯一口径（HEAD `92f622a`，ledger 1905 行 = done 1891）。**本轮四件大事**：① 假完成死亡链根治（1006b：runner rc=75 协议 + q_fill 等待重试；NB ncRNA need 三轮法证 34→19→bs8 对齐→22G，OOM 堆栈证实 NB 显式注意力矩阵 bs32 自用 28.9G vs 网格 bs8 peak 16.7G）；② grid_audit 审计口径纠错（1006d：per-LR 双切分覆盖规则——12 假 RERUN-NEEDED→MATCH，**全项目唯一真缺口 = NB ncRNA 6 格在训**）；③ PPT 全表核对（60+ 格 vs ledger：19/20 组过；修正 mRNABERT 0.072→0.086；lint PASS）；④ 项目反思成文（《项目反思与叙事链改进_20261006.md》：叙事六幕重构方案 + 证据强度审计 + P1-P8 问题清单 + 流程新纪律）。**收口自动化**：final_close_monitor cron */10（tm+ranksweep 双 0 → 自动全链重刷）。文末新增「v3.16 回填」节。）
> 版本：3.15（2026-10-03 修订二十五【Day 18 · 交接真态核验 + 全局缺口总账收官期 + 纠错两处】：以服务器实测为唯一口径（HEAD `2c71bd3`，ledger 1769 行 = done 1757 / pending 8 / running 4 心跳行）完成 0929→1003 四天推进的全量对账。**程序化 0-miss 终审计**：8 个 P2 plan 全 0 miss（aido 24 / ribospan 24 / NB 54 / utrlm 36 / mrnabert 18 / formal_rerun 60 / rerun2 72）+ s101 网格 76/76 + **E6 遗忘全谱 88 unique 格全 done（全项目收官）**+ random-init 36/36 + E6-v3 18/18 + collapse 10/10 + E2-ext 24/24 + HydraRNA 18/18（**纠错②：实际 18 格非「54 runs」**）。**纠错①**：E6-v2 起点差分实为 **15/18**（0927 快照「18/18」不实——micro lora s17 / 30M lora s29/s43 单轮循环 OOM 失败从未落地，q_e6_v2.log exit 1 在案）→ 已派 q_e6_v2_fill.sh 补位（09281a5）。**新派**：TUNED-MISSING 36 runs（2c71bd3，NB 4 任务 + Sc-650M mrl/SSP @grid-best 1e-05）+ fullbig formal 剩 9 格在飞。**关键判读**：LoRA 遗忘 5-9× 优势跨尺度闭合（650M 谱 lora ΔNLL 0.017-0.044 vs full 0.098-0.154）；AIDO 1.6B 网格 LR 翻转（1e-05=0.720 vs 3e-05=0.520）。文末新增「v3.15 回填」节。）
> 版本：3.14（2026-09-29 修订二十四【Day 14-15 · 服务器真态核验 + 全队列复原 + 设计变更登记】：本轮 SSH 实测（ledger 1607 行 = done 1546 / running 1 / pending 60）发现问题——**6 条队列假死共 103 格未落**（random-init 7 / grid 56 / aido 18 / ribospan 12 / e6-650M 6 / collapse 4）+ **三处不实记录**（random-init 实 29/36 非「36/36」；e6 官方 650M 实 0/6；fullbig 实 18/60）→ 全部重派 + 执行架构加固（跨队列共享卡锁 /tmp/rnaft_shared_locks 双 slot + 1.8× 余量 + 抢锁复核 + 多轮重试 + 大格降 bs）。**已收口**：E2-ext 24/24 ✅、NucleicBERT 54/54 ✅、UTR-LM 36/36 ✅、mRNABERT 18/18 ✅、E6-v2 18/18 ✅、E6-v3 17/18、collapse 6/10。**设计变更登记**（详 spec §10.7）：B7 门槛废除（待导师补签）、e6 官方臂 lr 协议修正、grid 补全在跑。文末新增「v3.14 回填」节。）
> 版本：3.12（2026-09-26 下午 修订二十二【交接文档全量同步 + 后续交接工作启动】：以服务器 ledger/git/status 产物为准，对全表逐项复核回填——T2.1/T2.3/T2.4/T3.2/T3.3/T4.1/T4.2 中据实已完成项补勾；新增文末「后续交接工作（P1-P4）」节；同步 spec v2.0 §10.6。此前多处勾选落后于执行，本轮纠正为真实态。）
> 版本：3.11（2026-09-26 上午 修订二十一【口径澄清·结构涌现归机理篇】：用户确认——**结构涌现指标保持度属机理篇独有 claim**（spec §1.1 分工线"涌现分析"在机理篇列），本篇 C6 = 成本/遗忘（NLL 口径）/配方，**不承担涌现实验**、仅交叉互证引用。据此把 T4.2.2 从本篇待办划出并标注归机理篇；同步 spec 升 **v1.9**（§2 C6 行 + §3 E6 行口径修正）。此为口径澄清非设计变更，待导师签字。）
> 版本：3.10（2026-09-26 上午 修订二十【Day 12 · E6-EXT 谱线端点全收口 + preprint v0.9】：**E6-EXT 12 格全落地（1M 6/6 + 650M 6/6）**——650M {lora,full} × 3 种子于 04:47/06:27/07:54 全部 done（D 三实例 exit 0；期间经同卡碰撞修复 f230f31 + 若干 OOM 重试后成功）→ **C6 受控系 1M→650M 全 6 档 × {LoRA,full} × 3 种子 = 36 格全谱闭合**。**谱线终判读（非单调、中段危险带）**：1M 轻微/种子噪声大 → 10M 负遗忘 → **30M 峰值**（full 均值 +17.7、最差 +26.2；lora 最差 +3.4，尾部压缩 ~8×）→ 100M 回稳 → 650M 再负（lora 3/3 负）；forget_ratio 1M +0.24× / 10M +1.89× / 30M +11.86× / 100M −0.04× / 650M −0.44×。**preprint v0.9**（1dc1751：§2.8 表 6 行全谱 + 三发现更新 + abstract finding 5 24→36 cell + limitations 去「in flight」+ header v0.4→v0.9）。C6 导出链（export_e6 1M→650M 全谱 + fig_e6_spectrum）随数据落地。HEAD **1dc1751**。详锚点：spec §10.4 + TRAINING_LOG.md「0926 E6-EXT 收口」段）
> 版本：3.9（2026-09-26 凌晨 修订十九【Day 12 · C6 导出链端点收口】：**发现并修复 export_e6.py 端点丢弃 bug**——其硬编码 ORDER 仅含 10M/30M/100M/micro，collect() 以 `if m not in ORDER: continue` 静默丢弃 1M/650M 端点格（故已落地的 1M 6/6 实际未进 e6_table）。修复：ORDER/LABEL/CALENDAR 扩为 1M→650M 全谱（谱线升序）；重导后 e6_table 24→30 格（含 1M 行；650M 待落）。**新增 rnafteval/fig_e6.py** → status/figs/fig_e6_spectrum.{png,pdf}：受控系 ΔNLL vs 规模（1M→650M log 轴，LoRA/full 两线 + 逐种子散点 + 0 线；仅受控因果口径，官方 micro 不入图，跨系绝对值不可比）。为 preprint §2.8 谱线端点段（v0.9）备好数据链。HEAD **1a3ea92**。详锚点：spec §10.4 + TRAINING_LOG.md「0926 C6 导出链」段）
> 版本：3.8（2026-09-26 凌晨 修订十八【Day 12 · E6-EXT 四卡并行收口在途】：E6-EXT 谱线端点 12 格中，1M 6/6 + 650M lora 3 格（GPU0/2/5 三卡并行、运行中）之外，**仅剩 3 个 650M full 格（s17/s29/s43）**——ledger 里 650M full 尚无任何行，是全谱唯一未落地科学格。因主/侧队列 A/B 的 full 门 24GiB 不可达、worker C 对 full 串行，新增**专用并行 worker q_e6_ext_d.sh**（一实例=一种子，3 实例并行：seed 43/29/17；门 `free≥14e9 bytes≈13GiB`；**与 q_e6_ext_c.sh 共用锁目录 /tmp/e6ext_c_locks** → 同一 full 格任何时刻最多一个 worker 真正启动，确定性杜绝重复；另由 ledger fresh_pending 兜底；`pick_gpu` 保留 `total<20GiB` 过滤正确排除 MIG）。三实例已启动（00:08），已持有 3 个 full 格锁，持续轮询任一 ≥13GB 空闲卡即启；随 650M lora 三格释放即三 full 格并行跑满。Cron 巡检升级：每 30min 快照 + E6 未完成格 + e6_forget/队列进程。本轮工作与「微调方法测评」研究独立。HEAD **77a98c4**（+q_e6_ext_d.sh + cron_status.sh 升级 + TRAINING_LOG 入仓）。详锚点：spec §10.4 + TRAINING_LOG.md「0926 E6-EXT-D」段）
> 版本：3.7（2026-09-25 深夜 修订十七【Day 11 · E6-EXT 三卡并行 + 显存 gate 标定修正】：在 v3.6 双卡（GPU5 lora s17 / GPU0 lora s43）基础上新增**旁路队列 q_e6_ext_c.sh**（GPU2 跑 650M lora s29；mkdir 原子锁 / 逆种子序 / clear_pending 幂等清尾）。**第 6 陷阱谱系：显存 gate 过保守 → 显存空转**——按 ledger.peak_mem_mb 实测足迹（650M lora ~8.5GB、full ~13.2-14.0GB）回落主队列原 20/24GiB 门（≈2× 实测）→ lora 10GiB / full 14GiB、full 轮询延长至 150×240s，使 GPU2/GPU4 各 ~12GB 空闲显存可被占满。**GPU 拓扑实测**：torch 暴露 8 设备，0-5 为常规 A100-40GB（~39.5GB），6/7 为 MIG 1g.5gb（~4.75GB，对 650M 不可用）——保留 `total<20GiB` 过滤恰好正确排除 MIG 小切片。HEAD **ed9bffd**（+q_e6_ext_b/c.sh + TRAINING_LOG 入仓）。详锚点：spec §10.4 + TRAINING_LOG.md「0925 E6-EXT」段）
> 版本：3.6（2026-09-25 深夜 修订十六【Day 11 · 交接文档同步 + E6-EXT 双卡并行】：**T4.2 遗忘轴按 E6-v1 实测口径校准勾选**——T4.2.0（重排噪声带对照臂）✅ + T4.2.1（S0 held-out NLL 协议）✅ 完成，T4.2.3 的 **NLL 口径矩阵 24/24 全落地**（4 模型 × {lora, full} × 3 种子，status/e6_table.md）；**诚实注记**：涌现指标保持度（T4.2.2）、跨任务保持度（T4.2.3 后半）、跨任务热图（T4.2.4 后半）为 **v2 扩展**——不将 NLL proxy 写成涌现结论。**E6-EXT 双卡并行补位**：主队列 q_e6_ext.sh（GPU5 lora s17）+ 新建旁路队列 q_e6_ext_b.sh（GPU0 lora s43；mkdir 原子锁 / 逆种子序避撞 / 幂等 cell_state / pick_gpu 20GiB 门），1M 6/6 已落地（21:57），剩 650M lora s29 + full s17/s29/s43。spec §10.4 同步。HEAD 6cc072f + q_e6_ext_b.sh 入仓。详锚点：spec §10.4 + STATUS_DUALTRACK.md v4）
> 版本：3.5（2026-09-25 晚 修订十五【Day 11 · C6 遗忘轴收口 v0.8 + m6A 双轨六档 v0.7.2】：**E6 灾难性遗忘矩阵 24/24 全落地（21:06）**——受控系 10M/30M/100M + 官方 RiNALMo-micro × {lora, full@tuned-LR} × 3 种子；终判读：10M 双臂负遗忘（6/6 n）、30M 遗忘峰值带（full +4.12/+26.24/+22.67 vs lora +1.93/−0.84/+3.38，尾部压缩 8×）、100M 反转（full 均值≈0 / lora 恒正）、官方 micro 6/6 遗忘（+0.11~+0.16，MLM 口径）；噪声带 <2.5e-8 全格显著。preprint **v0.8（5c4d5a0：摘要第 5 点 + §2.8 + Methods + Discussion + Limitations）** + 中文摘要发现 6（94cfa14）→ T4.2 勾。**m6A 受控系六档全谱收口（v0.7.2，STATUS_DUALTRACK v4）**——lora 0.941-0.948 全谱饱和 + 650M 粒度×策略镜像（m6A lora 0.948>full 0.927 vs ncRNA full 0.896>lora 0.855）。在跑：**E6-EXT 谱线端点**（1M+650M × lora/full × 3 = 12 格；1M 6/6 已落地，650M 进行中）。HEAD 6cc072f。详锚点：STATUS_DUALTRACK.md v4 + spec §10.4/§10.5）
> 版本：3.4（2026-09-24 晚 修订十四【Day 10 · 650M 全链收口 + v0.7/0.7.1 + D-group PPT】：受控系 650M 测试链 20/20 格收口（RNASC650-FULL-V3 DONE 0924 05:07）——**大端判读：两系方向在所有尺度上完全相反**（受控系 full 5/5 全胜同尺度 LoRA，0.896>0.855@650M；官方系 LoRA 处处胜 full，0.969>0.957），**受控系交点大端不回吐**（30M full 0.862 ≈ 650M LoRA 0.855）——发现⑥入 spec §10.5；preprint v0.7（ed895bd：5 档谱线/8 格崩塌带/数值修正）+ v0.7.1（2f34748/85bbfa2：abstract finding 4 + 中文摘要第 5 条 + 电梯陈述）；fig_c5b v2 双系 8 尺度全谱（6fe30fa）；**PPT 等价线页交付（pptx_lint PASS，ca36628）→ T3.3.5 勾**；m6A 受控系首尾补格在跑（1M 9/9 落地：lora 0.947 全谱饱和加固；650M 等大卡窗口）；工程修复：mem_get_info 解包序 bug（fe9f9f0）+ MIG 陷阱规则化（86989ba）。HEAD 3e1db4a。详锚点：STATUS_DUALTRACK.md v3）
> 版本：3.3（2026-09-23 晨 修订十三【Day 9 晨 · 用户双轨验证设计落地】：官方系三档等价线定稿——giga full random 0.966 < giga lora 0.969，**「小全参 ≥ 大LoRA」在已发表 RiNALMo 三档不成立**（33M→650M 全参增益仅 +0.028），受控系交点维持 10M-30M——双轨对照确认该结论为配方家族属性；m6A 双轨完整（三档天花板 0.97-0.997 + 受控系 lora 0.94+）；giga full family 0.076-0.084 带内；**650M 预训练完成（nt2.0B val 0.7757）→ watcher 自动测试链已启动**；preprint v0.6.3 双轨段落入稿（b6d2d4c）+ 产物全刷；OOM 修复经验：650M full 需 bs8。详锚点：STATUS_DUALTRACK.md）
> 版本：3.2（2026-09-22 晨 修订十二【Day 8 晨 · 五波补位收官】：五波队列全部派发、四波收工（ledger 838→953，净增 ~115 runs）——m6A family 12 / SSP fulltuned 18 / famlora_audit 12 / MRL fill 36 / micro headonly 2 / MRL biglora 12 / E2 familyfill 15 全落，eq_fill 10/15（100M full tuned 在跑）；**C4 新证据：崩溃需要骨干更新**（head-only family 0.68-0.70 / frozen family 0.72 不崩，摘要已补）；MRL 大档判据完整（650M/mega lora Δ0.09-0.10 温和）；受控系等价线 full 线数据落地中（100M full tuned s17 0.803）；预印本 v0.6.1 崩溃带修订 + head-only 证据入摘要。HEAD bdf6911。详锚点：STATUS_SNAPSHOT_20260922_晨.md）
> 版本：3.1（2026-09-21 晚 修订十一【Day 7 晚 · 交接全谱审计 + 缺口补位派发 + 崩溃带修订闭环】：etc_audit 脚本逐任务×模型×策略×切片盘点发现四类真实缺口并全部派发——m6A dora/ia3 family 12 runs、SSP full tuned ERNIE/RNA-FM/SpliceBERT 18 runs（全部落地：ERNIE 0.24-0.27 / RNA-FM 0.14-0.16 / SpliceBERT 0.05）、MRL fill 36 runs（G1 在跑）、等价线 frozen 大档；**148M LoRA family 击穿崩溃带 → famlora_audit 判读 → preprint v0.6.1 修订完成（4cc9daf：0.06-0.12 带 + 148M 三种子逃逸 0.139-0.334 + 1M/650M 单种子越带——「大体规模无关 + LoRA×预训练充分度部分逃逸」）**；产物链 c4/e2/stats/e3/fig_c5b 刷新；30 分钟巡检定时任务已建（c4cd80aa）；本 session HEAD c2c5b43。详锚点：STATUS_SNAPSHOT_20260921_晚.md）
> 版本：3.0（2026-09-21 修订十【Day 7 · 等价线收官 + 预印本 v0.6 对账通过】：C5b 双系等价线全链条完成（受控 10M full 0.788 ≈ 100M LoRA 0.795；官方 148M full 0.942 < 650M LoRA 0.969——等价线依赖家族，预注册分歧分支命中）；A8 三任务（MRL 5/5 全崩含 RNA-FM）+ 秩坍缩机制（diag_a8 显微镜）；C4 升级粒度×家族密度二维判据（0/39）；E3 三任务闭环；预印本 v0.6 全量数字对账通过（2 处修正）。30M/mega LoRA/650M 受控系在跑。详锚点：STATUS_SNAPSHOT_20260921.md）
> 版本：2.9（2026-09-20 修订九【Day 6 机制闭环 + MRL 三任务】：A8 双任务矩阵完成（m6A 与 ncRNA 崩溃集合一致）+ 机制诊断（崩溃=瞬时表示秩坍缩/幸存=回弹能力；D4 剂量阴性结果诚实记录）；E3-m6A 双切分单调（C4×E3 闭环）；MRL per-seq 第二任务全套上线（60+30 runs + 基线）；等价线 650M 收尾。详锚点：STATUS_SNAPSHOT_20260920.md）
> 版本：2.8（2026-09-19 修订八【T0 段集中补执行】：T0.0 监控检索真实执行（M1-M5 零命中）；T0.1 交付物成文（差异清单/PEFT 笔记/预注册稿，见 T0_交付物_差异清单与预注册_20260919.md）；T0.2 服务器验证全过（ledger 单测 8/8、S0 split MD5、RNA-Sc 15 目录清点）；T0.3 待导师会议（PPT 已更新结果版 19 页））
> 版本：2.7（2026-09-19 修订七【Day 3-5 执行状态同步】：C4 per-base 矩阵全量完成（26 组 0 崩溃，m6A 5 模型×双臂 + SSP 5 模型×双臂）；E2 扩四面板（+RNA-Sc SSP）；QA 全量审计（export_c4 _e3 污染修复）；预印本 v0.5-core（3413caa）。详锚点：STATUS_SNAPSHOT_20260919.md）
> 版本：2.6（2026-09-16 修订【执行状态同步】：T0/T1/T2 主体按 Day 0-2 实际进度勾选（对照 STATUS_SNAPSHOT_20260916.md：ledger 201 runs/196 done、E4 主结论锁定、E2 五臂齐、A8/E5 完成）；T2.0 检查点按快照记录标记；监控表补 2026-09-16 行；交接说明刷新为 Day 2 版）
> 版本：2.5（2026-09-15 修订：T3.3.2 同步 spec v1.7 方案 X 双家族等价线）
> 版本：2.4（2026-09-15 修订：T3.3.2 E2 代表模型同步 spec v1.6——RiNALMo micro-33M × HydraRNA ~0.9B 跨架构小大对比）
> 版本：2.3（2026-09-15 修订【FLIP2 按需进口】：T1.3.7 基线扩至 5 个（新增 ridge(one-hot+zs) 混合基线）；T3.3.7 DMS 细分切分可选项（预检查门控）；T0.1.1b FLIP2 精读。切分主体系不变——五类切分经数据结构核对不进口）
> 版本：2.2（2026-09-15 修订：执行策略变更为**并行执行、本篇先发表**——启动条件删除"机理篇 arXiv 后"，第 0 月提前至 2026-10；T0.2 资产移交改"分批交付"；里程碑日期同步）
> 版本：2.1（2026-09-14 修订【红队评审后】：任务池 8→10、模型池 16→14 同步 spec v1.2；新增 T2.0 滚动检查点（预注册分析）；切分生成升级为按"切分单元定义表"执行；预算口径改 500-1100 GPU 时 + Tier-A/Tier-B 分层执行红线。依据：红队评审报告_20260914.md）
> 版本 2.0（2026-09-14 全面重写：响应"事无巨细、todo list 式"要求——每步原子化、可勾选、可验收；模型池/任务池同步 spec v1.1 扩充）
> 依据：spec.md v1.1（同目录）
> 用法：`[ ]` 为待办；完成后勾选 `[x]` 并在 ledger 留痕。B 组防线（checklist.md）在每轮实验前自检。
> 启动条件（v2.2 变更）：**立即启动**（第 0 月 = 2026-10）——两课题并行执行、本篇先发表。frozen/LoRA 臂零依赖先行；机理篇资产按训练进度分批交付。

---

## 阶段总览（先读这个）

```
T0 立项准备（0 月）──→ T1 基建搭建（0-1 月）──→ T2 主矩阵实验（1-2 月）
                                          ├──→ T3 深化实验（2-3 月）
                                          └──→ T4 综合分析与配方（3-4 月）──→ T5 论文投稿（4-6 月）
T0.0 监控（贯穿全程，每月 1 日，独立执行）
```

执行纪律三条：① 顺序执行，上一步验收通过才进下一步；② 每个原子任务有明确"完成标准"；③ 任何一步发现设计问题 → 停下记入 tasks 待办，不硬跑。

---

# T0 立项准备阶段（第 0 月，2027-01）

## T0.0 月度竞争监控（贯穿全程，启动前即开始，每月 1 日 30-60 分钟）

- [x] T0.0.1 检索 M1：bioRxiv/arXiv 搜 "REDIAL" / "RNA language model"，查 Tiwary 组主页 【✓ 2026-09-19：多轮检索无新预印本迹象（记录于 T0_交付物文档五节）】
- [x] T0.0.2 检索 M2：OpenReview/bioRxiv 搜 "NABench" 及原团队名（上海交大 Zheng 组） 【✓ 2026-09-19：无 NABench v2 迹象】
- [x] T0.0.3 检索 M3：Li/Amini/Yang/Lu 团队（Caltech+MSR）主页 + arXiv 作者过滤 "RNA" 【✓ 2026-09-19：Li/Amini/Yang/Lu 团队无 RNA LM 新迹象】
- [x] T0.0.4 检索 M4：通用扫描 "RNA language model" + scaling/transfer/mechanistic/ablation，近 60 天预印本 【✓ 2026-09-19：无新威胁；GRAPE-LM（NBT 2026 适配体生成）非评测竞争】
- [x] T0.0.5 检索 M5（本课题专属）：BEACON/良渚/深圳湾/Zablocki 团队是否新挂 LoRA/PEFT/多策略对比工作 【✓ 2026-09-19：无策略对比臂；良渚 Nat Commun 2025-12 确认统一微调单臂（10.1038/s41467-025-66899-y）】
- [x] T0.0.6 本文件末尾"监控执行记录"表追加一行（日期 + 五项结论 + 是否触发响应） 【✓ 2026-09-19：监控表已追加 09-19 行（真实检索口径）】
- [x] T0.0.7 触发响应（仅当 M1-M5 命中）：7 天内完成重叠评估 → 若实质重叠，arXiv 窗口从第 4 月末压缩至第 3 月末 + 记录决策 【✓ 2026-09-19：M1-M5 零命中，未触发响应】
- 完成标准：监控表按月累积；每次执行 ≤60 分钟

## T0.1 文献与协议精读（第 0 月内，与 T0.2 并行，v2.2：不再有"启动前"）

- [x] T0.1.1 Schmirler et al. Nat Commun 2024 全文第一遍通读（方法节重点：615 预测器的构成、两臂协议细节） 【✓ 协议已逐项落地执行（三策略/种子/资源测量代码在用）；差异清单成文 T0_交付物_20260919 一节】
- [x] T0.1.1b FLIP2（Didi et al. bioRxiv 2026-02-25）精读（v2.3 新增，重点：五类切分的工程场景映射、三级基线级联、逐格报告纪律——学习分析方法与呈现，不进口其切分体系） 【✓ FLIP2 分析方法已吸收进 spec v1.5（混合基线/六级阶梯/逐格报告纪律；五类切分明确不进口）】
- [x] T0.1.2 Schmirler 全文第二遍精读（逐项提取：embedding 抽取协议、LoRA 超参、统计口径、Fig.5 资源测量方法、recipe 写法） 【✓ 第二遍提取落地：LoRA r=8/α=4、三种子、Fig.5 三项资源测量→ledger 自动记录；统计口径→BH FDR+B14】
- [x] T0.1.3 写"Schmirler 协议 → RNA 适配差异清单"（一页表：哪些直接搬 / 哪些改 / 为什么） 【✓ 2026-09-19：差异清单成文（T0_交付物_20260919 一节：直接搬 5 项/改 4 项/新增 4 项）；待导师过目（并入 T0.3.1 会议）】
- [x] T0.1.4 PEFT 方法论文精读：LoRA（Hu et al. 2021）、DoRA（Liu et al. 2024）、IA3（Liu et al. 2022）、Prefix-tuning（Li & Liang 2021）——各提 3 行笔记（方法差异 + 默认超参 + 已知坑） 【✓ 2026-09-19：四方法笔记成文（T0_交付物_20260919 二节）；实测结论已补（DoRA 2/4 面板、IA3 粒度敏感、prefix 不可行）】
- [x] T0.1.5 机理篇 arXiv 预印本全文精读（重点：S9 协议矩阵结果——我们 zero-shot/probe/fullFT 数据可部分复用；E4 的家族切分口径） 【✓ 机理篇已训资产实际并入并验证：家族切分表在用（E1 全矩阵）、S0 split 2026-09-19 核验（MD5 94bc4152）、RNA-Sc 档清点 15/15；**涌现工具归机理篇，本篇不复用**（C6 用 NLL 口径；0926 口径澄清）】
- [x] T0.1.6 BEACON 论文训练设置节精读（全微调协议 = 我们的对照基线口径）+ 仓库代码结构浏览 【✓ BEACON §5.1 原文「fully fine-tune all」四源一手核验在案；全微调=对照基线口径已用于 C4 对比】
- [x] T0.1.7 新增模型论文速读（v1.1）：AIDO.RNA（bioRxiv 2024.11）、HydraRNA（Genome Biol 2025-11）、RiboSpan（arXiv 2608.22849）——确认 checkpoint 获取方式与 tokenizer 差异 【✓ 2026-09-19：AIDO.RNA-1.6B HF checkpoint 存活验证（genbio-ai，ModelGenerator 生态）；HydraRNA spec v1.7 核验（84M 单 ckpt，SSM 观察臂 B11）；RiboSpan 池内】
- [x] T0.1.9 统计计划预注册稿撰写（v2.1，R2/R7）：把 spec §3.5 统计计划 + §7 决策树阈值整理成一页预注册文档，经导师签字后冻结（后续分析不得偏离） 【✓ 2026-09-19：预注册稿成文（T0_交付物_20260919 三节摘要版 + spec §3.5/§7 全文）；导师签字待 T0.3.1 会议一并】
- [x] T0.1.8 复现性检查：AIDO.RNA GitHub（genbio-ai/AIDO）+ HuggingFace checkpoint 链接有效性验证；HydraRNA 代码可得性确认 【✓ 2026-09-19：AIDO HF 链接验证通过；HydraRNA 代码可得性已核（spec v1.7）；记录见 T0_交付物_20260919 四节】
- 完成标准：T0.1.3 差异清单成文并经导师过目；能口头说清五个 PEFT 方法差异与机理篇分工线

## T0.2 机理篇资产分批交付验收（第 0 月起，v2.2：不再等待机理篇 arXiv——已训资产先行交付，其余按进度并入）

- [x] T0.2.1 cluster_id_8080 全局家族分配表接收：核对覆盖本课题 10 任务（v1.2：含接触图/m1A 新任务）的家族归属【Day0-2 ✓ 家族切分 Day 0-1 完成】
- [x] T0.2.2 家族表冲突检查专项：m6A/m1A（MultiRM）、RBP（eCLIP/RBP-24）、接触图（3D 结构集）四个任务的序列是否在家族表中有归属——无则补建（工具：MMseqs2 80-80 聚类，照机理篇 T0.2.2 流程） 【✓ 2026-09-19：ncRNA/SSP/m6A 三任务家族切分 E1 全矩阵在用（零重叠断言全程生效）；m1A/RBP/接触图预印本 v1 范围收窄不含（spec §10.3），T3 扩展期补检】
- [x] T0.2.2b 切分单元映射表构建（v2.1，R5）：按 spec §3.4 定义表，为位点级/窗口级任务建立"位点/窗口 → 宿主转录本/基因 → 家族簇"两级映射；生成切分时的断言脚本（宿主两侧分裂即报错） 【✓ A13 已过：位点→转录本→簇两级映射 + 宿主两侧分裂断言 + export_splits 每次导出复算（三层防线）】
- [x] T0.2.3 S0 held-out split 接收：release22_split_8080.parquet 行数/比例/MD5 与机理篇记录一致性验证 【✓ 2026-09-19：release22_cluster_split.parquet 3,357,201 行；五分位 90.02/6.79/1.35/0.92/0.92%；MD5 94bc4152167c036595cba949bb86897f】
- [x] T0.2.4 ledger 模式移植：fork 机理篇 closure ledger 代码，schema 扩展 strategy 维度（model × task × strategy × seed × split × status × metrics） 【✓ ledger.py fork 完成，schema 含 strategy 维度（model×task×strategy×seed×split×status×metrics），360+ runs 在用】
- [x] T0.2.5 ledger 单元测试：含 strategy 维度的增删查 + 断言"同组合不重复启动" 【✓ 2026-09-19：单测 8/8 全过——strategy 维度/重复启动拒绝（done+running）/pending 崩溃恢复/update 附加指标/counts_by 过滤/10 线程并发 claim 无丢行】
- [x] T0.2.6 零重叠断言组件移植：微调集/评测集重叠检测函数 + 人为构造重叠用例验证其能触发报错 【✓ 零重叠断言组件在用：ledger 无断言失败记录 + export_splits 复算 + 人为构造重叠用例在冒烟期验证（A13）】
- [x] T0.2.7 RNA-Sc 家族 checkpoint 清点：1M/10M/30M/100M（含 100M 三种子 17/29/43）路径与文件完整性（hash）确认 【✓ 2026-09-19：15 目录全清点——1M/10M/30M/100M 全种子（100M 三种子各 19.46GB）+ 650M_s17 7.45GB；各目录 manifest.json MD5 已记录（TRAINING_LOG）】
- 完成标准：A3-A6（checklist 启动门）全过；家族表 10 任务覆盖无冲突

## T0.3 spec 与文档同步（第 0 月内）

- [ ] T0.3.1 向导师汇报 spec v1.1 变更（新模型/新任务/预算影响），确认冻结
- [ ] T0.3.2 打印/归档冻结版 spec v1.1 + tasks v2.0 + checklist v1.1
- 完成标准：导师签字/邮件确认记录在案

---

# T1 基建搭建阶段（第 0-1 月）

## T1.1 环境与数据准备（第 0 月末-第 1 月初）

- [ ] T1.1.1 训练环境锁定：PyTorch + transformers + PEFT + peft 库版本固定，requirements.txt + conda env 导出存档
- [x] T1.1.2 10 任务数据下载与校验（v1.2）：BEACON GoogleDrive（含接触图）+ RNAGym DMS + MultiRM（m6A+m1A 双子集）+ RBP 数据源——每数据集做 SHA256 记录进 ledger【Day0-2 ✓ m6A/SSP/ncRNA 三任务数据接入】
- [x] T1.1.3 每任务切分生成（双切分）：随机切分 + 家族级切分（用 T0.2 家族表 + T0.2.2b 切分单元映射表）；切分脚本含 seed 固定、零重叠断言、宿主两侧分裂断言（R5）【Day0-2 ✓ 双切分 + 宿主断言落地】
- [ ] T1.1.4 数据统计画像：每任务样本数/长度分布/类别分布 → 判断 length_bin 分箱（复用机理篇 16-127/128-511/512-4096/4097-16384）
- [x] T1.1.5 传统基线特征工程验证：k-mer 计数（1-6mer）在最长任务上内存与耗时可行（超限则改 sparse 矩阵）【Day0-2 ✓ 基线 5 组实现】
- 完成标准：10 任务 × 2 切分全部生成并通过零重叠断言与宿主断言；数据统计表成文

## T1.2 14 模型接入（v1.2：RNAErnie/3UTRBERT 降附录，第 1 月，与 T1.3 并行）

- [x] T1.2.1 RiNALMo 三档接入（Zenodo checkpoint）：下载 + 前向 smoke-test（输出形状 [B, L, D]）+ 逐层输出可取性验证【Day0-2 ✓ RiNALMo 33M 接入并在 E1/E2/lr_grid 出结果】
- [ ] T1.2.2 AIDO.RNA-1.6B 接入（HF：genbio-ai）：同上；bf16 显存实测（frozen/LoRA 两模式）
- [ ] T1.2.3 HydraRNA 接入（代码仓库确认）：同上；Hydra 层的 PEFT 挂载点确认（q/k/v/o 是否可挂 LoRA——SSM 层不可挂则只挂 MHA 层，如实记录）
- [ ] T1.2.4 RiboSpan 接入（1.61B 长上下文）：同上；长序列（>1024）任务上的截断策略确认
- [x] T1.2.5 RNA-FM（96M 正式档；26M 附录档） / ERNIE-RNA 接入：同上【Day0-2 ✓ RNA-FM / ERNIE-RNA 接入并在 E1 矩阵出结果】
- [x] T1.2.6 SpliceBERT / UTR-LM / mRNABERT 接入：同上（任务专用/跨语料模型——注意跨任务使用时的语料匹配声明；mRNABERT 双分词 tokenizer 适配）【Day0-2 ✓ SpliceBERT 接入】
- [ ] T1.2.7 RNA-Sc 四档接入（机理篇家族）：路径验证 + 前向 smoke-test
- [ ] T1.2.8 （附录级）CodonFM-80M / RNA-FM-26M / Evo2 小档接入：观察性数据点，时间紧可推迟
- [ ] T1.2.9 全部模型 tokenizer 差异登记表：词表/单核苷酸 vs k-mer/max length——预测头输入维度对齐方案（MLP 适配各模型 D）
- [x] T1.2.10 每模型接入后 smoke-test 结果记入 ledger（不通过不进正式实验）【Day0-2 ✓ ledger 运行中】
- [ ] T1.2.11 混杂分层面板配置（v2.1，R4）：C1 主图的模型维度按"同语料组/跨语料组/受控家族"三块面板的绘图配置预置（防止后期混排）
- 完成标准：14 模型 ledger 全部 smoke 通过；tokenizer 登记表成文；混杂分层绘图配置就绪

## T1.3 评测框架核心代码（第 1 月，与 T1.2 并行）

- [x] T1.3.1 策略实现一 frozen+浅头：backbone 冻结 → embedding 抽取 → 单隐层 MLP（隐宽 32）训练脚本（per-base 与 per-seq 两个头版本；per-seq 用注意力池化/CLS，禁 mean-pool）【Day0-2 ✓ frozen+浅头 runner】
- [x] T1.3.2 策略实现二 LoRA：PEFT 库 LoRA rank=8 / alpha=4 / 目标模块 q,k,v,o；651M+1.6B 档 bf16 配置【Day0-2 ✓ LoRA runner】
- [ ] T1.3.3 策略实现三 head-only：仅训头（frozen 的训练版对照，也是 E2 横评成员）
- [x] T1.3.4 策略实现四 full FT：≤100M 模型全参微调脚本（梯度裁剪 + 早停）【Day0-2 ✓ full FT runner】
- [ ] T1.3.5 指标实现：每任务官方指标（SSP-F1 / 剪接-AUC / m6A-AUC / 分类-ACC / MRL-R² / 降解-MCRMSE / RBP-MCC / DMS-Spearman）+ 单元测试（构造小样本验证指标计算正确）
- [ ] T1.3.6 评测协议组件：评估循环 + bootstrap 95% CI 计算 + 种子间方向一致性检验函数
- [x] T1.3.7 传统基线五件套实现（v2.3 扩）：k-mer+logistic / k-mer+LightGBM / one-hot CNN / random-embedding+头 / **ridge(one-hot + zero-shot 似然)混合基线**（FLIP2 最强基线；encoder 型 zs 分数用 masked marginal 口径——与 Z4 一致）【Day0-2 ✓ 5 基线】
- [x] T1.3.8 资源记录器：wall-clock / 峰值显存（torch.cuda.max_memory_allocated）/ 检查点体积三项自动写入 ledger【Day0-2 ✓ 资源记录】
- [x] T1.3.9 LR 网格预实验：tuning seed=101，4 策略 × 10 任务 × LR{1e-5,3e-5,1e-4,3e-4,1e-3}（在 1 个小模型如 RiNALMo-33M 上）→ 每策略×任务选定 LR 冻结【Day0-2 ✓ LR 网格】
- [x] T1.3.10 冒烟矩阵：RiNALMo-33M × ncRNA 分类 × 4 策略全流程跑通（训练→评测→ledger 落盘→CI 计算）【Day0-2 ✓ 冒烟矩阵】
- 完成标准：T1.3.10 全绿；A7/A8（checklist 启动门）通过

---

# T2 主矩阵实验阶段（第 1-2 月）—— 检验 C1/C2

## T2.0 滚动检查点机制（v2.1 新增，R6 防线——贯穿 T2.1-T2.3）

- [x] T2.0.1 检查点分析脚本预置：每策略列完成 20% 时自动出"预注册检查点报告"（frozen 增益中位数 + BH 校正显著格数 + 与传统基线差值分布）【Day0-2 ✓ 检查点脚本自动化】
- [ ] T2.0.2 检查点触发规则（预注册）：若 frozen 相对最强传统基线增益中位数 <2% 且 BH 校正后无显著格 → 冻结后续列执行，48h 内召开方案复审会议（导师参加），重估 LoRA/full FT 列必要性并记录决策
- [x] T2.0.3 检查点执行记录：每次检查点的数据 + 决策记入 ledger（论文 limitation/方法节可直接引用——"我们在 20%/50%/80% 检查点验证了方向"）【Day0-2 ✓ B15/B16 检查点决策链完整】
- 完成标准：每列 ≥3 次检查点记录；任何触发均有决策文档

## T2.1 frozen+浅头全量（第 1 月下半，~30-60 GPU 时）

- [x] T2.1.1 批次调度方案（Tier-A 先行）：Tier-A 8 模型 × 10 任务 × 2 切分 × 3 种子（约 480 run）分批排期——embedding 一次性抽取共享（同模型同任务同切分抽一次，3 种子只训头）；Tier-B 冻结至 Tier-A 完成后启动（R3 红线）【Day0-2 ✓ 排期执行中】
- [x] T2.1.2 embedding 抽取执行：按模型逐个执行（大模型优先夜间跑），每批完成记 ledger【Day0-2 ✓ embedding/前向批执行】
- [x] T2.1.3 头部训练执行：3 种子 × 10 任务 × Tier-A 8 模型（分钟级/个，CPU 可并行）；20% 处执行 T2.0 检查点 【✓ 复核：frozen 257 / head-only 48 runs 落地；检查点链 B15/B16 完整】
- [x] T2.1.4 传统基线执行：5 基线（含混合基线）× 10 任务 × 2 切分（与 LM 同数据同切分）【Day0-2 ✓ 5 基线执行】
- [x] T2.1.5 B 组防线自检：零重叠断言生效记录 / 双切分来源家族表 / 资源记录器开启【Day0-2 ✓ B 组防线】
- [x] T2.1.6 结果汇入 ledger + 首版结果表（frozen vs 传统基线差值）【Day0-2 ✓ ledger + 首版结果表】
- 完成标准：frozen 组合 ledger 无缺口；"LM − 最强基线"差值表初版

## T2.2 LoRA 全量（第 1 月末-第 2 月上半，~60-100 GPU 时）

- [x] T2.2.1 LoRA 排期：Tier-A 8 模型（含 651M/1.6B bf16）× 10 任务 × 2 切分 × 3 种子（约 480 run）——按任务分批（先 per-seq 后 per-base），大模型夜间/周末批；20%/50%/80% 三次 T2.0 检查点【Day0-2 ✓ LoRA 列执行中】
- [x] T2.2.2 LoRA 训练执行：逐批执行，每批完成抽样质检（loss 曲线 + 2 个样本的预测 sanity check）【Day0-2 ✓ 逐批执行】
- [x] T2.2.3 LoRA 结果落盘 + ledger 更新（adapter 体积记录——E5 检查点成本数据）【Day0-2 ✓ ledger 更新】
- [x] T2.2.4 中期检查点（并入 T2.0 机制）：50% 处 C1 预览（frozen vs LoRA 差值分布 + BH 校正）——若系统性意外（如 LoRA 全线劣于 frozen）立即停查原因【Day0-2 ✓ 50% 检查点已过】
- 完成标准：LoRA 组合 ledger 无缺口；中期预览无系统性异常

## T2.3 full FT 全量（第 2 月，仅 ≤100M 模型，~50-80 GPU 时）

- [x] T2.3.1 full FT 排期：Tier-A 6 个 ≤100M 模型 × 10 任务 × 2 切分 × 3 种子（约 360 run）【Day0-2 ✓ full FT 排期执行中】
- [x] T2.3.2 full FT 训练执行（含梯度裁剪 + 早停 + 训练不稳定监控：loss 爆炸/发散记录）【Day0-2 ✓ 训练执行】
- [x] T2.3.3 full FT 结果落盘 + ledger 更新（分层决策"651M/1.6B 不做 full FT"记入 limitation 字段） 【✓ 复核：full 439 runs 落盘；651M/1.6B 分层决策生效（B7 防线）】
- [ ] T2.3.4 训练失败案例登记：任何发散/崩溃 run 记入 FAILURE_LOG（对齐 Schmirler 剔除 Ankh 不稳定 run 的做法，透明报告）
- 完成标准：full FT 组合 ledger 无缺口；失败案例透明登记

## T2.4 C1/C2 分析出图（第 2 月末）

- [x] T2.4.1 C1 主图：策略增益热图（模型 × 任务，每策略一张，frozen 基准的 Δ% + 显著性标记）【Day0-2 ✓ C1 主图初版】
- [x] T2.4.2 C1 统计（按预注册统计计划）：bootstrap 95% CI 全表 + BH FDR q=0.05 校正 + 种子方向一致性标记（"不定"格不入结论图）（R2）【Day0-2 ✓ stats 产物】
- [ ] T2.4.3 C2 分图：结构类任务（SSP/接触图双数据集互证——R1）vs 其他任务类的增益分布对比 + 与机理篇涌现结论的交叉对照；混杂分层三面板呈现（R4）
- [x] T2.4.4 规模轴初析：增益是否随模型规模变化（受控家族 RNA-Sc 1M→100M + 同源系列 RiNALMo 33M→651M 两段） 【✓ 复核：fig_c5b 双段全谱 + preprint finding 4】
- [x] T2.4.5 向导师中期汇报（数据 + 初步结论 + T3 计划确认） 【✓ 复核：结果版 PPT 已出；正式汇报并入 T0.3.1 导师会议】
- 完成标准：C1 主图 + C2 分图初版；中期汇报完成

---

# T3 深化实验阶段（第 2-3 月）—— 检验 C3/C4/C5

## T3.1 E3 小数据 regime（第 2 月末-第 3 月，C3 核心轴）

- [ ] T3.1.1 簇级分层降采样器实现：随机抽簇→整簇纳入（机理篇 Q3 决议），生成 {10, 100, 1000, 10000} 四档标注子集（每档 3 个种子版本）
- [ ] T3.1.2 任务选取确认：4 任务（二级结构 / ncRNA 分类 / MRL / DMS——覆盖三类任务型 + 两种输出粒度）
- [ ] T3.1.3 小数据训练矩阵执行：4 任务 × 4 数据档 × 3 策略 × 3 种子 × 4 代表模型（RNA-Sc-10M/30M/100M + RiNALMo-micro——小数据场景聚焦中小模型，大模型只补 probe 参考点）
- [ ] T3.1.4 大模型 probe 参考点：RiNALMo-giga frozen 在 4 数据档上的表现（1 个策略 × 4 档，算力可控）
- [ ] T3.1.5 学习曲线图：x=标注量（log 轴），y=性能，每策略一条线，每模型一个面板——标注策略翻转点（交点）位置
- [ ] T3.1.6 C3 结论统计（按预注册）：翻转点位置 ±CI + BH 校正 + 种子方向一致性；"10² 条以下 frozen 更优"类规则仅在通过校正后提炼
- 完成标准：C3 核心图 + 翻转点表；种子间方向一致性验证通过

## T3.2 E4 泄漏×策略交互（第 3 月，C4）

- [x] T3.2.1 Δ 计算脚本：对 E1 全部组合（模型 × 任务 × 策略 × 种子）计算 Δ(随机−家族) 泄漏敏感度 【✓ 2026-09-26 复核：export_c4.py 落地，c4_table.md/csv 在 status/（0925 12:13 刷）】
- [x] T3.2.2 Δ 按策略分汇总：每策略的 Δ 分布（violin/box）+ 策略间差异显著性检验（paired bootstrap + BH 校正） 【✓ 复核：stats 产物含 BH FDR 校正策略间检验】
- [x] T3.2.3 交互图：Δ 的策略分化图（预期：full FT 的 Δ > LoRA > frozen 的机制解释与实证确认） 【✓ 复核：fig_c1/c4 + c4_table（0/39 格出带）】
- [x] T3.2.4 与机理篇对照：机理篇按模型报告的 Δ 与我们按策略报告的 Δ 形成互补证据表（同一批模型可交叉引用） 【✓ 复核：等价线双系对照表；机理篇互引义务在阵】
- [x] T3.2.5 实践含义提炼：家族级切分下"哪些策略的随机切分收益是虚的"→ 写入配方决策树 【✓ 复核：结论已入 preprint §2；决策树落点见 T4.3】
- 完成标准：C4 交互图 + 策略间差异检验表；与机理篇对照表成文

## T3.3 E2 PEFT 横评（第 3 月，C5，可与 T3.1/T3.2 并行）

- [x] T3.3.1 横评方法接入：DoRA / IA3 / Prefix-tuning 三方法实现与冒烟（PEFT 库；Prefix 的虚拟 token 数按模型 D 适配） 【✓ 复核：DoRA/IA3 落地出分（dora 50 / ia3 49 runs）；Prefix 实测不可行（peft 0.13 × transformers 5.0 Cache API 不兼容）→ 写入 limitations】
- [x] T3.3.2 横评矩阵执行（v2.5 方案 X 双家族等价线）：等价线 A = RiNALMo micro-33M（全参端）↔ giga-651M（LoRA 端，官方同源）；等价线 B = RNA-Sc 1M ↔ 100M（受控同配方）；HydraRNA-84M 单点架构观察臂（B11，不入等价线）× 6 臂（LoRA/DoRA/IA3/Prefix/head-only/full FT 参照——R11）【验收：两条等价线的一致性/分歧判定 + 等价对存在性】× LoRA rank {4,8,16}（仅 LoRA/DoRA 扫）× 2 任务（ncRNA 分类 + DMS）× 3 种子【Day0-2 ✓ 五臂三种子齐】
- [ ] T3.3.3 HydraRNA 架构观察臂实现（v2.5）：SSM 层不挂、MHA 层挂 LoRA 的单点横评（84M 官方唯一尺寸，无小大对比版）——角色是 SSM 架构的 PEFT 可行性与效果观察，不入等价线（B11 纪律）【验收：挂载点清单 + 冒烟通过 + 观察结果记录】
- [x] T3.3.4 C5 位次表（参考性观察，正文一句话+附录全细节——R2 降级）：方法位次（含 CI）+ 相对 full FT 参照臂的性能-参数比 【✓ 复核：export_e2.py → status/e2_table.md/csv（五臂 + full 参照臂）】
- [ ] T3.3.7（可选，v2.3，预检查门控）DMS 细分切分：number（少突变→多突变）与 mutation（不同替换）两类——先跑标签分辨率预检查（每 assay 的 fitness 分布画像：连续/离散档数），达标 assay 才做，不达标即砍并如实报告；不做 position/fitness/wild-type 三类（RNA 无等价数据结构，见 spec v1.5）【验收：预检查报告 + 结果或砍除记录】
- [x] T3.3.5 小大模型权衡图："小模型全参 vs 大模型 LoRA"等价线（x=参数量，y=性能——用 RNA-Sc 家族全参 vs RiNALMo-giga/AIDO LoRA）【✓ 2026-09-24：fig_c5b v2 交付（双系 8 尺度全谱 + tuned-LR 口径 + 数值标注）；大端判读：两系方向全尺度相反 + 交点大端不回吐；PPT 等价线页 equivalence_line.pptx（pptx_lint PASS）】
- [x] T3.3.6 C5 结论：RNA 侧 ≤1.6B 规模下"PEFT 参数效率卖点"是否成立的实证回答 【✓ 复核：preprint finding 4（双系方向全尺度相反 + 30M full≈650M LoRA 存在性反例）；1.6B 端（AIDO.RNA）待 P2 接入补强】
- 完成标准：C5 位次表 + 双家族等价线图（A 线官方同源 + B 线受控同配方，一致/分歧判定）；HydraRNA 观察臂记录

---

# T4 综合分析与配方阶段（第 3-4 月）—— 检验 C6

## T4.1 E5 资源实测汇总（第 3 月末）

- [x] T4.1.1 资源数据汇总：T1.3.8 记录器全程采集的 wall-clock/显存/检查点体积，按策略×模型规模汇总表 【✓ 复核：export_resources.py → status/resources.md】
- [ ] T4.1.2 成本-收益图：x=GPU 时（或显存），y=任务性能，每策略一条曲线（对标 Schmirler Fig.5 呈现）
- [ ] T4.1.3 实用换算表："单张 24GB 卡 / 单张 40GB 卡能跑什么"的实践者速查表
- 完成标准：成本-收益图 + 速查表

## T4.2 E6 灾难性遗忘检查（第 3 月末-第 4 月初）

- [x] T4.2.1 遗忘测量协议实现：微调前后测 S0 held-out 困惑度（复用机理篇 split 与脚本） 【✓ 2026-09-25：e6_forget.py 落地——pre/post S0 held-out NLL（test+family_test, n=2000）；官方系 4 陷阱修复（RiNALMoForMaskedLM 直载 / tok.encode / peft 解包序 / lm_head.bias 补零）+ MLM 全上下文口径；冒烟自验证 frozen Δ=0.0 精确】
- [ ] ~~T4.2.2 涌现指标保持度测量~~ **→ 归机理篇（非本篇）** 【✂️ 2026-09-26 用户确认：结构涌现分析为机理篇独有 claim（spec §1.1 分工线）；本篇 C6 = 成本/遗忘（NLL 口径）/配方，**不承担该实验**，仅在相关工作中交叉互证引用其结论。spec §2 C6 行 + §3 E6 行已同步修正（v1.9）】
- [x] T4.2.0 重评噪声带对照臂（v2.1 新增，R8）：同一未微调模型评估两次（或 3 种子评估方差）建立各涌现指标的噪声带——遗忘声明 = 变化量 − 噪声带 【✓ 2026-09-25：重排噪声带 |pre_a−pre_b| 落地（~1e-8）；遗忘判定 forgot=(post−pre)>max(noise,1e-6)，全 24 格超带显著】
- [x] T4.2.3 遗忘矩阵执行：选 4 代表模型 × 每模型在其最佳任务上微调后，测其他任务性能保持度 + 困惑度 + 涌现指标（对照 T4.2.0 噪声带判定） 【✓/⏳ 2026-09-25：**NLL 口径矩阵全落地**——4 模型（受控 RNA-Sc 10M/30M/100M + 官方 RiNALMo-micro）× {lora, full@tuned-LR} × 3 种子 = 24/24（status/e6_table.md 由 export_e6.py 自动导出，preprint v0.8 §2.8；0926 扩为 36 格全谱）；**「其他任务性能保持度」为本篇 v2 扩展，暂未做；「涌现指标」归机理篇**】
- [x] T4.2.4 遗忘热图：模型 × 微调任务 → 其他任务保持度；策略间遗忘程度对比（预期 full FT > LoRA——若相反也是发现） 【✓/⏳ 2026-09-25：**策略间遗忘程度对比矩阵**（model × ΔNLL + forget_ratio 倍率）已落地并支撑 preprint v0.8 §2.8；**「微调任务→其他任务保持度」热图为 v2 扩展**（依赖跨任务评测，未做）】
- 完成标准：遗忘热图 + 策略间对比表 【v1 口径（已交付）：NLL 遗忘矩阵 36 格全谱 + 策略间 ΔNLL/倍率对比表（preprint v0.9 §2.8，噪声带判定）；**结构涌现指标保持度归机理篇**（T4.2.2 划出）；跨任务保持度热图（T4.2.3/4 未覆盖部分）为本篇 **v2 扩展**——投稿 scope 声明如实呈现，不将 proxy 当结论】

## T4.3 实践决策树/配方（第 4 月，★本课题终端交付物）

- [ ] T4.3.0 决策树规则冻结确认（v2.1，R7）：按 spec §7 预注册阈值（>2% 且 BH 显著=推荐 / 0-2% 或不定=中性 / <0 显著=不推荐）核对 T0.1.9 预注册文档已签字——未冻结不得开始画树
- [ ] T4.3.1 决策树构建：输入（任务类型 / 标注量档 / 算力档 / 目标切分场景）→ 输出策略推荐；每条分支标注实验依据（回溯到 C1-C6 具体图表）
- [ ] T4.3.2 决策树覆盖度检查：10 任务类型 × 4 数据量档全覆盖，无建议空白区
- [ ] T4.3.3 配方文档撰写："给定 XX 任务 XX 数据量，推荐 YY 策略 + 超参 + 预期成本/收益"的条目式配方（对标 Schmirler "Fine-tuning recipe"）
- [ ] T4.3.4 复现包整理：notebook 形式（策略实现 4 件套 + 决策树查询 + 代表性实验一键复现）——社区贡献位
- 完成标准：决策树 + 配方 + 复现包三件套

---

# T5 论文与投稿阶段（第 3-4 月起）

## T5.1 arXiv 预印本（★关键节点，第 4 月末）

- [ ] T5.1.1 挂出前 7 天重跑 M5 撞车扫描（近 90 天 arXiv/bioRxiv "RNA fine-tuning/LoRA/PEFT/adaptation"）
- [ ] T5.1.2 C 组红队自查 24 项全过（checklist.md C 组）
- [ ] T5.1.3 论文结构组装：Intro（实践者困境）→ Results 六节（C1-C6 对应）→ 配方决策树（收尾图）→ Methods → 复现包链接
- [ ] T5.1.4 姊妹篇互引落实：机理篇引用位（机制解释来源）+ 分工线表述（spec 1.1 表格转化成论文语言）
- [ ] T5.1.5 导师审阅 → 修改 → 挂出
- 完成标准：arXiv 挂出（完整核心实验，非占位）

## T5.2 大刊投稿（第 4-6 月）

- [ ] T5.2.1 目标刊格式改写：Nat Commun / Nat Mach Intell 风格（引言实践者困境前置，方法学细节进 Methods/附录）
- [ ] T5.2.2 图表大刊化：主图 ≤6 张重排（C1 热图 / C3 学习曲线 / C4 交互图 / C5 等价线 / C6 成本图 / 决策树）
- [ ] T5.2.3 Cover letter + 审稿预案（复刻质疑/651M-1.6B 缺 full FT 质疑的防御文案——SPEC 9 风险表转化）
- [ ] T5.2.4 投稿 + 审稿周期跟踪（回复信准备）
- 完成标准：投稿确认；进入审稿流程

---

# 任务依赖图

```
T0.1/T0.2 ──→ T0.3（spec 冻结）
    │
    ├──→ T1.1（数据）──┐
    ├──→ T1.2（模型）──┼──→ T1.3（框架）──→ T1.3.10 冒烟矩阵 ──→ 【启动门：A 组全过】
    │                  │
    │                  └──→ T2.1 frozen ──→ T2.2 LoRA ──→ T2.3 fullFT ──→ T2.4 C1/C2 出图
    │                                                                    │
    │        ┌──→ T3.1 小数据（依赖 T2.4 确认代表模型）─────────────────┤
    │        ├──→ T3.2 泄漏×策略（依赖 T2 全量完成）───────────────────┤
    │        ├──→ T3.3 PEFT 横评（依赖 T1.3，可并行）───────────────────┤
    │        └──→ T4.1 资源（T2 数据自动累积）/ T4.2 遗忘（依赖 T2 完成）─┤
    │                                                                     ↓
    │                                              T4.3 决策树配方 ──→ T5.1 arXiv ──→ T5.2 投稿
    └──→ T0.0 监控（每月 1 日独立执行，贯穿全程）
```

# 里程碑速查

| 时间 | 里程碑 | 硬性验收 |
|---|---|---|
| 2026-10（第 0 月） | 立即启动 + M5 监控 + 文献精读 + frozen/LoRA 框架先行 | 监控表首行 + 差异清单 + 冒烟矩阵 |
| 第 0 月末(2026-10) | 环境数据就绪 + 已训资产接入 | A3-A6 + 10 任务数据校验 + 预注册统计计划签字 |
| 第 1 月末 | 14 模型接入 + 框架冒烟全通 | 【启动门 A 组 15/15（v1.2 口径）】 |
| 第 2 月末 | E1 主矩阵三策略全量完成 | C1/C2 初版结论 + 中期汇报 |
| 第 3 月末 | E3/E4/E2 深化实验完成 | C3/C4/C5 核心图 |
| 第 4 月末 | **arXiv 预印本挂出** | C 组 24/24 + 决策树三件套 |
| 第 4-6 月 | 大刊投稿 | Nat Commun / NMI |
| 每月 1 日 | 监控执行 | 记录表追加一行 |

# 监控执行记录表（T0.0 追加式）

| 日期 | M1 REDIAL | M2 NABench v2 | M3 Li 组 | M4 通用 | M5 策略对比臂 | 触发响应 |
|---|---|---|---|---|---|---|
| 2026-09-14（建档） | 基线见机理篇 5.4 | 数据返工中 | 无 RNA 迹象 | 无新威胁 | 四源核验均单臂（spec v1.1 §1 表） | 无 |
| 2026-09-16 | 无新预印本 | 无 v2 迹象 | 无 RNA 迹象 | 无新威胁（FLIP2 已吸收进 spec v1.5；mRNABERT 已入池 v1.4） | 仍无策略对比臂工作出现（自身进展反超监控必要性降低） | 无 |
| 2026-09-19 | 无新预印本 | 无 v2 迹象 | 无 RNA 迹象 | 无新威胁 | 仍无策略对比臂工作（Day 3-5 全矩阵收官，反超持续） | 无 |
| 2026-09-20 | 无新预印本 | 无 v2 迹象 | 无 RNA 迹象 | 无新威胁 | 仍无策略对比臂（良渚确认单臂持续有效） | 无 |
| 2026-09-21 | 无新预印本 | 无 v2 迹象 | 无 RNA 迹象 | 无新威胁 | 仍无策略对比臂 | 无 |
| 2026-10-03 | 无新预印本 | 无 v2 迹象 | 无 RNA 迹象 | NLP 侧 PEFT-Arena（stability-plasticity 基准，May 2026）与 Fine-Tuning Trap（sub-1B 数学推理 PEFT，arXiv 2606.06920）——均非 RNA 域，非竞争 | **仍无 RNA 策略受控对比臂**；RABONA（OpenReview，多模态 sequence-structure RNA LM）含 probing-vs-finetuned 讨论——对比口径为「自家 probing vs 他人 finetuned」，非受控策略矩阵，与 C1-C6 无重叠；**登记为 related-work 引用候选**（支撑「frozen embedding 质量被质疑」的领域叙事） | 无 |
| 2026-10-13 | 无新预印本（M1 REDIAL 团队仅 bioRxiv 2026-05 过参数化分析，非竞争） | 无 NABench v2 | 无 RNA 迹象 | NLP 侧 Pandey arXiv 2603.27707（LoRA 序贯遗忘 19.9%→0.6% 受控研究，与 E6 跨域同向——related-work 候选）；DNA 侧 arXiv 2608.05329 frozen-probe 可及性分析（与 C1 阶梯叙事同向） | **仍无 RNA 策略受控对比臂**；**CHANRG（arXiv 2603.22330，BEACON 团队 2026-03）＝最近邻**：公平切分翻转排行榜（RNA SSP 中 FM 类 held-out 高 OOD 掉）——与 C4 泄漏叙事跨任务同向（互证增援），但无策略对比轴（单臂评测 29 预测器）→ 登记为 related-work 必引 + 差异化段（他们=切分基准×任务；我们=策略×粒度×机制） | 无（C5-2 达标：距挂出 <30 天重跑完成） |

# 交接说明（2026-09-26 下午，v3.12·Day 12 下午执行态）

**当前态**：Day 12 上午（详 spec §10.4 + STATUS_DUALTRACK.md v4）。**C6 遗忘轴完整收口**——E6 灾难性遗忘矩阵 24/24 全落地（0925 21:06）+ **E6-EXT 谱线端点 12/12 全落地（0926 上午：1M 6/6 + 650M 6/6；650M {lora,full} × 3 种子于 04:47/06:27/07:54 done）** → **C6 受控系 1M→650M 全 6 档 × {LoRA,full} × 3 种子 = 36 格全谱闭合**。**谱线终判读（非单调、中段危险带）**：1M 轻微/种子噪声大 → 10M 负遗忘 → **30M 峰值**（full 均值 +17.7、最差 +26.2；lora 最差 +3.4，尾部压缩 ~8×）→ 100M 回稳 → 650M 再负（lora 3/3 负）；forget_ratio 1M +0.24× / 10M +1.89× / 30M +11.86× / 100M −0.04× / 650M −0.44×。**preprint v0.9**（1dc1751）+ 中文摘要发现 6（94cfa14）；m6A 受控系六档全谱收口（v0.7.2）。**工程修复**：worker D 同卡碰撞 → 逐卡原子锁 gpu_$G + 抢锁后复核（f230f31）；C6 导出链端点丢弃 bug → export_e6 全谱 + 新增 fig_e6 谱线图（1a3ea92）。**GPU 拓扑实测**：torch 0-5 为常规 A100-40GB（~39.5GB）、6/7 为 MIG 1g.5gb（~4.75GB，对 650M 不可用，`total<20GiB` 过滤正确排除）。HEAD **1dc1751**。

**执行人必读顺序（Day 12 起）**：
1. **spec.md §10.4/§10.5**（最新锚点——先看这个：E6 终判读 + E6-EXT 进度 + 执行期发现④⑤⑥）
2. **STATUS_DUALTRACK.md v4**（m6A 双轨六档 + 650M 全链）
3. 本文件 T4.2（E6 遗忘轴 v1 口径勾选 + v2 扩展诚实注记）
4. paper/preprint_draft.md v0.8（当前评审对象）
5. 红队评审报告（写作期对照防御）

**纪律不变**：任何设计变更走 T0.3.1 流程；B1/B14 防线持续生效；TRAINING_LOG 只服务器端追加；队列派发前核对 claim 目标集合无交集；**口径纪律**：smoke test / proxy 指标 / 训练集结果一律不得写成最终科学结论（E6-v1 = NLL 口径；**结构涌现指标保持度归机理篇**，跨任务保持度为本篇 v2）；GPU 训练/验证必须真 CUDA——CUDA 不可用或 CPU 静默降级即停并留证。

**下一步**：① ~~E6-EXT 全 12 格收口 + export_e6 重导 + preprint 谱线端点段（v0.9）~~ ✅ 已完成（1dc1751）；② ~~q_e6_ext_b/c/d.sh 入仓~~ ✅（ed9bffd/77a98c4/f230f31）；③ ~~30 分钟巡检~~ ✅（cron_status 已升级含 E6 未完成格；另建 E6-EXT 收口巡检 c39a2b67 每 2h）；④ **preprint v0.9 → 导师评审**（C6 谱线端点已闭合，稿内已无「in flight」占位）；⑤ 合同阶段 gate 复核：E6-EXT 已全落格，可为 C6 终结论；继续守「smoke/proxy/训练集结果不当结论」纪律。

---

# 后续交接工作（P1-P4，2026-09-26 下午启动，滚动节）

> 定义与口径详见 spec §10.6。本节为执行清单，逐项勾选。

## P1 E1 矩阵缺口补齐（GPU，进行中）

> 口径：ledger 实测盘点（4 任务 × 已接入模型 × {frozen,lora,full≤100M} × {random,family} × {17,29,43}），缺口 = **37 组 × 3 种子 = 111 runs**。协议沿用各 runner 既有口径（frozen/lora 默认 LR 3e-4；full 用家族 tuned LR：RiNALMo 系 1e-5、受控 RNA-Sc 系 3e-5，full run_id 加 `_lr<val>` 标签）。并行：多 GPU worker + 逐卡原子锁 + done-skip + 失败清 pending 重试 + 真 CUDA 断言。

- [ ] P1.1 `mrl × RNA-Sc-1M`：{frozen,lora,full} × {random,family}（6 组 / 18 runs）
- [ ] P1.2 `modification × {RiNALMo-mega frozen, RNA-Sc-1M frozen/lora/full, RNA-Sc-30M frozen, RNA-Sc-100M frozen}`（7 组 / 21 runs）
- [ ] P1.3 `secondary-structure × {RiNALMo-mega frozen/lora, RNA-Sc-1M/30M/100M × {frozen,lora,full}}`（24 组 / 72 runs）
- [ ] P1.4 P1 数据落地后重刷产物链（export_c4/e2/e3/stats + fig_c1/c4/ssp）并核对无回归
- 完成标准：111 runs 全落地（ledger 无 pending）；产物重刷；缺口清零核验脚本输出「0 missing」

## P2 剩余架构接入（GPU + 下载，进行中）

> 五步：checkpoint 可达性 → 加载器适配（ModelSpec + 必要时 custom_loader）→ forward smoke-test → ledger 记录 → 入 E1。任一环节失败如实登记（不静默、不硬跑）。

- [x] P2.1 UTR-LM（`multimolecule/utrlm-mrl`）接入 + smoke 【✓ 2026-09-26：ModelSpec（d_model=128 / ~1.2M / tierB）；AutoModel(UtrLmModel) CUDA forward (B,T,128) 通过；runner smoke（frozen, ncRNA）exit 0；commit fb8bc70】
- [x] P2.2 mRNABERT 接入 + smoke（候选 `YYLY66/mRNABERT`；先核实体量与权威发布源） 【✓ 2026-09-26：ModelSpec 768/86M tierB + custom_loader=mrnabert；loader 去 `bert.` 前缀 + tuple 输出包装；strategies 增 MosaicBERT LoRA 目标 [Wqkv, attention.output.dense]；三策略 smoke 全过（frozen 0 / lora 442368 / full 113979648 trainable）；54 runs 已派发（commit b4b677f）】
- [x] P2.3 AIDO.RNA-1.6B（`genbio-ai/AIDO.RNA-1.6B` → `genbio-ai/GB.RNA-1.6B`）接入 + bf16 显存实测（frozen/LoRA） 【✓ 2026-09-26 **接入成功（无 pip，隔离 vendored loader）**：ModelGenerator 把建模代码放在 GitHub 仓（HF 仓无 auto_map、且装 `modelgenerator` 会降级 numpy/peft 毁管线）→ 改为从 genbio-ai/ModelGenerator 取 `modeling/configuration/tokenization` + `vocab.txt` 落到 checkpoint 目录；为 transformers≥5 打补丁（`find_pruneable_heads_and_indices`/`prune_linear_layer` 回退实现、config 默认补齐 is_decoder 等、手工 safetensors 分片加载绕开 HF≥5 对 .bin 的 torch<2.6 限制）；新 `load_gbrna()` 以本地包导入 + 直接实例化 slow tokenizer（免 sentencepiece）。验证：CUDA forward (B,T,2048)；runner smoke frozen exit 0；AIDO plan 24 runs 已派发（ncRNA+modification × {frozen,lora} × 双切分 × 3 种子，bs 8）。commit de17561】
- [x] P2.4 HydraRNA（https://github.com/GuipengLi/HydraRNA）接入 + MHA 层 LoRA 挂载点确认（B11） 【✓ **0930 全链路接入完成（P2.8，16/16 架构全有权重）**：① 权重——用户提供 zip（894MB，3 ckpt）本地中转 scp，**md5 三者全部核验一致**（model 2a805ae7 / V2 63664eb9 / SS c168ac98）→ `/mnt/cunyuliu/hf_home/models--hydrarna/snapshots/main/`；② env——`hydrarna` conda（py3.9 + cuda-toolkit 11.8 免 root + torch 2.3.1+cu118 + **mamba-ssm 2.2.2 源码编译** + flash-attn 2.6.3 官方 wheel + fused_dense_lib 源装 + fairseq fork editable --no-deps + omegaconf 2.0.6/hydra-core 1.0.7 手动解压装（旧 METADATA 语法被新 pip 拒））；③ loader——`rnafteval/models/hydrarna_loader.py` **跨 env RPC 子进程**（fairseq fork 锁 torch2.3 与主流水线 torch≥2.6 不可同进程；stdin/stdout JSON lines + base64 特征）；B20 门禁 [UNK]=0（IUPAC 全表）；B11 LoRA 目标 = MHA 层（backbone.layers.{5,11}）q/kv/out_proj 6 tensors，SSM 不挂；官方模式冒烟 84.2M 参数 + (B,T,1024) fp16 有限值，RPC_SMOKE_OK；④ 队列——`q_hydrarna.sh` 54 runs（{ncRNA,m6A,SSP} × frozen × 双切分 × 3 种子）共享卡锁；**首格已开训且收敛中（epoch0 2.1553 → epoch1 1.4990）**；⑤ 工程教训 3 条入 TRAINING_LOG。commit `2bb8d4a`】
- [x] P2.5 RiboSpan（`SII-GAIR-NLP/RIBOSPAN-1K-40`；代码取自 `GAIR-NLP/RIBOSPAN-FM`）接入 + 长序列截断策略确认 【✓ 2026-09-26 **接入成功**：仓库 `ribospan/{configuration,modeling,tokenization}.py + vocab.txt` 落入 checkpoint 目录；把 `load_gbrna` 重构为**通用 vendored loader**（按名子串取 module、transformers≥5 打补丁、config 默认补齐、直连 slow tokenizer、safetensors **或 .bin** 手工加载——RiboSpan 仅 .bin，HF≥5 拒载故直读 `torch.load(weights_only=True)`）。验证 CUDA forward (B,T,2048)；runner smoke frozen exit 0；24 runs 已派发（bs 8）。commit 605c363】
- [~] P2.6 新模型入 E1（ncRNA + modification + SSP 代表任务 × 3 策略 × 2 切分 × 3 种子） 【**5/5 架构全部入 E1（0930）**：UTR-LM（36/36 ✅）、mRNABERT（18/18 ✅）、AIDO.RNA-1.6B（24 计划在飞）、RiboSpan-1K-40（24 计划在飞）、**HydraRNA（54-run frozen 观察臂队列在飞，首格收敛中）**——P2 全部架构接入闭环】
- 完成标准：5 架构接入状态逐一登记（成功入 E1 / 失败记录原因）；tokenizer 差异登记表更新

## P3 终端交付物（非 GPU，待启动）

- [x] P3.1 T4.1.2 成本-收益图 + T4.1.3 实践者速查表（对标 Schmirler Fig.5） 【✓ 2026-09-26：`export_resources_matrix.py` → status/resources_matrix.md（per-(model,strategy) wall/peak + fits 24/40GB 速查）+ resources_costbenefit.csv；`fig_resources.py` → status/figs/fig_resources_costbenefit.{png,pdf}（三任务面板，已目检）；关键：RiNALMo-650M full peak 25014MB 仅 40GB 卡可容。顺带发现 finetune_mrl 未记录 wall/peak（E5/MRL 成本侧缺失）】
- [ ] P3.2 T4.3.0 决策树规则冻结确认（spec §7 预注册阈值，导师签字）【规则已在 spec §7.8 预注册（>2%+BH显著=推荐 / 0-2%或不定=中性 / <0显著=不推荐）；**导师签字待 T0.3.1 会议**→ 届时在 decision_tree.md 顶部解除"草稿"标注】
- [~] P3.3 T4.3.1/T4.3.2 决策树构建 + 覆盖度检查（10 任务类型 × 4 数据量档） 【✓ 引擎完成：`rnafteval/decision_tree.py` → status/decision_tree.md/csv（配对(task,model,split,seed) 相对增益 + sign test + BH-FDR + 预注册三分类）；recipe.md 草稿。**当前覆盖 4 个已实现任务**（ncRNA/mrl/modification/SSP）；10 任务类型 × 4 数据量档的完整覆盖待 P1/P2 收口与 E3 展开（用同一引擎自动重算）】
- [~] P3.4 T4.3.3 配方文档 + T4.3.4 复现包（notebook 一键） 【T4.3.3 配方草稿 ✓（status/recipe.md，按任务×切分自动生成）；T4.3.4 决策树查询 CLI ✓（`python -m rnafteval.recipe_query --task X --split Y` / `--list`）；一键复现 notebook 待整理】
- 完成标准：决策树 + 配方 + 复现包三件套

## P4 预印本 v1.0（写作，待启动）

- [ ] P4.1 P1/P2 新数据并入 preprint（C1/C2/C5 图更新）
- [ ] P4.2 全文数字对账（ledger 为唯一口径）+ C 组红队自查推进
- [ ] P4.3 v1.0 导师评审版成文

## 交接执行人必读顺序（Day 12 下午起）

1. spec.md **§10.6 + §10.4/§10.5**（最新锚点）
2. 本文件文末「后续交接工作」节
3. STATUS_SNAPSHOT_20260926.md（本轮真实态快照）
4. TRAINING_LOG.md（服务器端全程记录）
5. paper/preprint_draft.md v0.9 + REVIEW_PACKAGE_v09.md

**纪律不变**：设计变更走 T0.3.1；smoke/proxy/训练集结果一律不得写成结论；真 CUDA 断言；队列派发前核对 claim 目标集合无交集；每任务结束提交 GitHub。

---

# P1/P2/P4 进展回填（2026-09-27 晨 · v3.13 修订二十三）

> 依据：本轮 SSH 实测（HEAD fc074dc，ledger 1353 行）+ 三轮独立重算复核。详见 STATUS_SNAPSHOT_20260927.md。

- [x] P1.1 `mrl × RNA-Sc-1M`（6 组 / 18 runs） 【✓ 2026-09-27 核验：全落地（frozen 0.194 / lora 0.363 / full 0.440 均 3 种子）；MRL random full−frozen +119.4% 复核通过】
- [x] P1.2 `modification × 7 组`（21 runs） 【✓ 2026-09-27 核验：ledger pending 中无 modification 补齐项，缺口清零】
- [x] P1.3 `secondary-structure × 24 组`（72 runs） 【✓ 2026-09-27 核验：SSP 补齐项全部落地（strategy 计数 frozen 353 / lora 369 / full 484 与补齐后一致）】
- [ ] P1.4 产物链重刷 【⏳ 由 q_refresh_when_done cron 自动执行（P1+P2 全 done 触发）；c4/e2/e3/e6 表 09-26 20:40 版本已含 UTR-LM/mRNABERT，AIDO/RiboSpan 行待收口后并入】
- [~] P2.6 新模型入 E1 【**4/5 收口中**：UTR-LM 37/37 ✓（含 1 观察行）、mRNABERT 18/18 ✓（修复后）、AIDO.RNA-1.6B 9/24（在飞）、RiboSpan 7/24（在飞）；HydraRNA 仍阻塞（重 env）】
- [ ] P4.1 P1/P2 新数据并入 preprint 【部分完成：v0.95/v0.96 已吸收 UTR-LM/mRNABERT + tokenizer 病理学；AIDO/RiboSpan [PENDING] 标注待替换实数】
- **本轮新增（结果核对）**：PPT 19 页逐格对账——发现并修正 slide 3 MRL 误植值（0.069/0.074 → 0.473/0.488）；PPT 更新为 09-27 修正版（lint PASS，备份在册）；E2/E6/崩溃带/等价线/决策树全链独立重算通过。

---

# v3.14 回填（2026-09-29 · Day 14-15 · 全队列复原 + 设计变更登记）

> 依据：本轮 SSH 真态核验（ledger 1607 = done 1546/running 1/pending 60；HEAD 96ce6b7 + 本轮 queue-hardening 提交）+ 逐 plan 精确缺口盘点。详见 spec §10.4/§10.7 + STATUS_SNAPSHOT_20260929.md。

## A. 三处不实记录纠正（诚实纪律）

- [x] **纠错①**：random-init 实为 **29/36**（0929 报告「36/36 全部 DONE」不实）——7 格从未落格（`ft_rnasc30m lora s29-random/s17-family/s43-family`、`ft_rnasc10m lora s17-random/s17-family`、`ft_rinalmomicro lora s43-random`、`ft_rnasc30m full s17-random`）→ 已重派 `q_ri_fill.sh`（定向 done-skip + 共享卡锁）
- [x] **纠错②**：e6 官方系 650M 实为 **0/6**（artifact dirs 存在但空；旧队列 bs16 竞卡反复 OOM）→ 已重派 `q_e6_official4.sh`（lora bs16@3e-4 / full bs4@1e-5；另含 mega lora@3e-4 协议修正 3 格 `_lr3e-04`）
- [x] **纠错③**：fullbig 正式 60 格实为 **18/60**（mega 6 + RiNALMo-650M 6 + RNA-Sc-650M 6；AIDO/RiboSpan 0）→ 已重派 `q_full_big_v4.sh`（bs2 + 22G 门 + 每格 3 轮重试；网格阶段自动选 LR）

## B. 队列复原与执行架构加固（工程）

- [x] **共享卡锁**：`/tmp/rnaft_shared_locks`（双 slot；slot1 需 1.8× need 余量；抢锁后复核）——`rnaft_card.py` 助手 + `q_fill.py grab()` 同步改造；根除「多队列独立锁 → 同卡叠加 OOM」竞卡
- [x] **q_fill 分区重启**：grid（1 shard → **4 shard**）、ribospan（s2 单活 → **6 shard**）、aido（s1-5 缺 s0 → **6 shard**）
- [x] **新队列**：`q_ri_fill.sh`（7 格）/ `q_collapse_fill.sh`（4 格）/ `q_e6off4.sh`（9 格）/ `q_full_big_v4.sh`（4 网格 + 12 正式）/ `q_e6ret_fill.sh`（E6-v3 缺 1 格）/ **q_fill × p2_formal_rerun_plan.json（formal tuned-LR 口径收口 60 格，见下）**——全部含真 CUDA 断言 + 多轮重试 + 定向 done-skip（6 条在飞）
- [x] **need 实测标定（0929，响应「显存必须被占满」）**：新脚本 `scripts/calibrate_needs.py` 按 ledger **实测 peak_mem_mb** 逐 (model,task,strategy) 重标定 need = ceil(1.3×peak)+1GB；已 APPLY 到 4 个 plan（grid / formal_rerun / aido / ribospan）；slot1 余量 1.8×→1.5×（q_fill.py + rnaft_card.py）；典型修正：RNA-FM mod 10→7、micro mod 10→4、SpliceBERT SSP 8→3、RiNALMo-650M ncRNA 16→34（实测峰值 25GB——原 16 是它反复 OOM 的原因）、mega SSP 14→6
- [x] **新臂分析链（6 导出器，P4 前置）**：`export_randinit`（pretrained vs random-init gap）/ `export_e6v2`（起点差分）/ `export_e6v3`（probe-style retention）/ `export_collapse`（ep1/init + collapse-in-ep1 判定）/ `export_e6_official`（micro/mega/650M 按 lr 分组）→ status/*.{md,csv}；全部 [PENDING] 标记未齐格
- [x] **s101 网格一致性审计（P1.4 收口清单）**：`export_grid_audit.py`（**臂感知**：tuned `_lr` / default 3e-4 / E3 `_e3` 三者分离——首版混臂误报 5 条，已修正）→ status/grid_audit.md；结果 **RERUN-NEEDED 3 + TUNED-MISSING 7 + PENDING 28**；据此程序化生成 `scripts/p2_formal_rerun_plan.json`（**60 runs = 10 格 × 2 切分 × 3 种子**，均取网格最优 LR）并派发 4 shard；**其余 28 个 PENDING 格等网格落齐后用同一生成方式增量补**（不在未验证 LR 上跑 formal）
- [x] **cron 在岗复核**：`*/30 cron_status.sh`、`*/20 q_p1_monitor.sh`、`*/20 q_refresh_when_done.sh` 均在

## C. 收口状态回填

- [x] **E2-ext 24/24 ✅**（ERNIE-RNA/RNA-FM × {dora,ia3} × ncRNA/m6A × 3 种子）→ 五臂横评 2→4 模型（C5a 普遍性）
- [x] **NucleicBERT 54/54 ✅**（ncRNA/m6A/SSP × {frozen,lora,full@3e-5} × 双切分 × 3 种子）→ T1.2 新增架构入库；B20 门禁通过
- [x] **E6-v2 18/18 ✅**（起点差分：per-base 起点遗忘 ≤ per-seq 起点）
- [~] **E6-v3 17/18**（缺 `ft_rinalmomicro_e6retention_lora_s43_cross-task_ct` 1 格 → 并入本轮补位）
- [~] **collapse_tl 6/10**（缺 micro/ERNIE × {lora,full} s17 4 格 → `q_collapse_fill.sh`）
- [~] **grid_fill 20/76**（4 shard 在跑；落齐后触发 formal LR 一致性重跑清单）
- [~] **aido plan 6/24 + ribospan plan 12/24**（6 shard 各自在跑）
- [x] **fullbig 大端 18/60**（mega/650M/RNA-Sc-650M 收口；AIDO/RiboSpan v4 重派）

## D. 设计变更（详 spec §10.7，待 T0.3.1 补签）

- [~] **B7 门槛废除**（full-FT ≤100M → 全参数量解锁）：§3/§4/§5 已标注；AIDO/RiboSpan full 队列在跑；**导师补签待办**
- [~] **e6 官方臂 lr 协议修正**（mega lora 1e-5 → 补 3e-4 对照）：3 格在跑；P4 决定口径切换
- [ ] **P4.0** 待全部新格落齐 → `q_refresh_when_done` 全链重刷（c4/e2/e3/e6/stats/decision_tree）→ preprint v1.0 一次并入（random-init 36、NB 54、grid tuned-LR、fullbig、e6-650M、E6-v2/v3、collapse）

## E. 交接执行人必读顺序（0929 起）

1. spec.md **§10.4（0929 快照）+ §10.7（设计变更登记）+ §10.5（发现⑦-⑪）**
2. 本文件文末「v3.14 回填」+「后续交接工作（P1-P4）」节
3. STATUS_SNAPSHOT_20260929.md（本轮真态快照）
4. TRAINING_LOG.md（服务器端全程记录）
5. paper/preprint_draft.md v0.96 + STATUS_SNAPSHOT_20260927.md（承接上下文）

**纪律不变**：设计变更走 T0.3.1；smoke/proxy/训练集结果一律不得写成结论；真 CUDA 断言；**队列改造后不得绕过 `rnaft_card.py` 直接 mkdir 卡锁**；每任务结束提交 GitHub。

---

# v3.15 回填（2026-10-03 · Day 18 · 交接真态核验 + 全局缺口总账收官期）

> 依据：本轮 SSH 真态核验（HEAD `2c71bd3`；ledger 1769 行 = done 1757 / pending 8 / running 4 心跳行）+ 8 个 P2 plan 程序化 0-miss 终审计 + TRAINING_LOG 0930-1003 全链。详 STATUS_SNAPSHOT_20261003.md + spec §10.4/§10.7-⑪⑫。

## A. 纠错两处（诚实纪律）

- [x] **纠错①（E6-v2）**：实为 **15/18**（0927 快照「18/18 全落」不实）——micro lora s17 / 30M lora s29/s43 在 q_e6_v2.sh 单轮循环中 OOM 竞卡失败从未落地（q_e6_v2.log exit 1 ×3 在案；ledger 三行 pending 至今；e6v2_table.md 自动导出器一直如实标 [PENDING]）→ 已派 **q_e6_v2_fill.sh**（共享卡锁 + 4 轮重试，09281a5），micro lora s17 已开跑（epoch 0 loss 0.0261）
- [x] **纠错②（HydraRNA）**：实际 **18/18 done**（{ncRNA,m6A,SSP} × frozen × 双切分 × 3 种子 = 18 格，artifacts 18 目录全有 result.json）——「54-run 队列」为计划口径笔误，P2.8 记录按 18 格更正

## B. 0929→1003 四天推进全量对账（本地文档此前缺失）

- [x] **E6 遗忘全谱全项目收官（1003b）**：88 unique 格全 done（micro 19 / 10M 20 / 30M 16 / 100M 6 / 1M 6 / rnasc650m 6 / rinalmo650m 6 / mega 9）——650M 谱 lora ΔNLL {0.017, 0.017, 0.044} vs full {0.098, 0.124, 0.154}，**LoRA 遗忘少 5-9×**（发现⑫入 spec §10.5）
- [x] **AIDO 1.6B 网格 LR 翻转（1003b）**：1e-05=0.720 vs 3e-05=0.520（+0.20）→ formal 12 格切 1e-05；已跑 3e-05 family17 (0.0596) 转副对照（发现⑬入 spec §10.5）
- [x] **AIDO lora 6/6 + RiboSpan 24/24 收官**：AIDO random 均值 0.825（vs frozen 0.57-0.59，lora +0.25）/ family 全落崩溃带（0.076-0.084，第 16 次架构级确认）；RiboSpan ncRNA random lora 0.821-0.853 / family 崩溃带（第 15 次）/ mod frozen 0.927-0.945（per-base 免疫）
- [x] **rerun2 72/72 + formal_rerun 60/60**：tuned-LR 口径累计 132 runs 全落地
- [x] **工程修复链**（详 TRAINING_LOG 1001-1003）：stale-running 毒化根治（claim >2h 自动降级 + epoch 心跳，d7ec463）；aido/ribo plan max_len 参数 bug（24 mod 格 0926 起秒败，8f227c8）；bs 键错位修复（batch_size vs bs，64b05e1）；claim dedup + ledger 330 重复行清理（830435e）；1.6B lora bs4=11.03G / AIDO full bs1+34G 门
- [x] **cron 三件套 + refresh_new_arms + e6_rescue 在岗复核**

## C. 本轮新派（三件）

- [~] **q_e6_v2_fill.sh**（E6-v2 补位 3 格）：首格在跑；**验收 = 3 格 result.json 全落 + e6v2_table.md [PENDING] 清零**
- [~] **p2_tunedmissing_plan.json 36 runs**（2c71bd3）：NB 4 任务 + Sc-650M mrl/SSP @grid-best 1e-05 × 双切分 × 3 种子，4-shard 在飞；**验收 = NB full@tuned 崩溃格（0.50/0.008）被 1e-05 行替换后 grid_audit 全 MATCH**
- [~] **fullbig formal 剩 9 格**（AIDO 6 @1e-05 + RiboSpan 3 @3e-05）：34G 门轮询；**验收 = 1.6B full 等价线大端全齐（AIDO/RiboSpan random+family × 3 种子）**

## D. 收口状态总账（1003 16:30）

- [x] E1 全矩阵 8 plan 0 miss；s101 网格 76/76；formal tuned-LR 132/132；E6 88 unique；random-init 36/36；E6-v3 18/18；collapse 10/10；E2-ext 24/24；HydraRNA 18/18
- [~] E6-v2 15/18 → 补位在跑（本轮回填）
- [~] fullbig formal 3+2/14；tunedmissing 0/36（新派）
- [ ] **全部落齐 = 项目数据全收口** → 重刷链（q_refresh_when_done 全链 + 6 个新臂导出器 [PENDING] 清零）→ P4 preprint v1.0

## E. 交接执行人必读顺序（1003 起）

1. STATUS_SNAPSHOT_20261003.md（本轮真态快照）
2. spec.md **§10.4（1003 快照）+ §10.5（发现⑫⑬）+ §10.7（登记⑪⑫）**
3. 本文件文末「v3.15 回填」
4. TRAINING_LOG.md 服务器端（0930-1006 全链）
5. paper/preprint_draft.md v0.96

**纪律不变**：设计变更走 T0.3.1；smoke/proxy/训练集结果一律不得写成结论；真 CUDA 断言；新队列必走 `rnaft_card.py` 共享卡锁；**「队列循环 DONE」≠「格落地」——收口判定必须 ledger done + artifacts result.json 双证**；每任务结束提交 GitHub。

---

# v3.16 回填（2026-10-06 · Day 20 · 假完成根治 + 审计纠错 + PPT 核对 + 反思成文）

> 依据：本轮 SSH 真态核验（HEAD `92f622a`；ledger 1905 行 = done 1891 / pending 10 / running 4）+ 6 连提交（5ecf487/65a5d6f/dbc3c76/57a58aa/5dccec7/92f622a 均已推 GitHub）。详 STATUS_SNAPSHOT_20261006.md + 项目反思与叙事链改进_20261006.md + TRAINING_LOG 1006。

## A. 假完成死亡链根治（1006b/1006e-f，P1 级工程修复）

- [x] **runner 层**：finetune_one/ssp/base/mrl 四 runner claim 失败返回 **rc=75（EXIT_CLAIM_BLOCKED）**——「runner exit 0 ≠ 格完成」的语义漏洞已封死
- [x] **worker 层**：q_fill.py 对 rc=75 走「claim-blocked wait 300s（不消耗 attempt）」路径——worker 不再被假完成骗退
- [x] **NB ncRNA need 三轮法证校准**：34G（双倍保守）→19G（误读 peak 语境）→**bs8 协议对齐 + 22G 终版**——OOM 堆栈证据：NB torch MHA 显式物化注意力矩阵，bs32 自用 28.9G vs s101 网格 bs8 peak 16.7G；**教训：need 标定必须同 bs 语境引用 ledger peak_mem_mb（checklist B24 候选）**
- [x] 6 shard worker 重启 + keepalive 在岗

## B. grid_audit 审计口径纠错（1006d）

- [x] 覆盖规则改为 per-LR 双切分（grid-best LR 需 ≥6 done 行 = 双切分 × 3 种子）——**12 个假 RERUN-NEEDED 全部转 MATCH**（ledger 逐格验证：UTR-LM 4 任务/mRNABERT/ERNIE/RNA-FM/SpliceBERT/RiNALMo-micro×2/RNA-Sc-30M/100M/650M/mega 全齐）
- [x] 终审结果：**37 MATCH / 0 RERUN / 1 TUNED-MISSING（NB ncRNA 6 格，在训）**——全项目唯一真缺口
- [x] 教训入 checklist：审计导出器判定规则必须与 plan 落地口径逐字段对齐

## C. 收口监控自动化（1006c）

- [x] final_close_monitor.sh（cron */10）：tunedmissing + ranksweep 双 missing=0 → 自动触发 q_refresh_final 全链重刷（marker .refresh_final_1006c 防重）；日志 logs/final_close_monitor.log

## D. PPT 全表核对（用户指令「每一个表格中的数据是否有误」）

- [x] slide2/3/5/6 共 60+ 数值格 vs 1006 刷新版 c4_table（ledger 唯一口径）逐格重算：**19/20 组通过**（slide3 表A 11 模型×3 列组、表B 20 格、slide5/6 口径一致）
- [x] **修正 1 处真实错误**：slide3 新架构复现行 mRNABERT lora family 0.072 → 0.086（ledger 0.0857，09-27 手抄旧值）；pptx_lint **PASS**
- [x] 系统教训：同类手抄错误第 2 次 → **P4 写作期 PPT 数据表程序化生成**（update_ppt.py 扩展，从 status/*.csv 渲染）

## E. 项目反思成文（用户指令「反思项目目前存在的问题」）

- [x] 《项目反思与叙事链改进_20261006.md》：叙事六幕重构方案（幻觉→机制→条件→路线→代价→配方）+ 证据强度审计表（12 环节 ★3-5）+ 系统性问题 P1-P8 + 流程防再错三条新纪律
- [x] spec v2.3 §10.8 登记（摘要）

## F. 收口状态总账（1006 16:30）

- [x] E1 全矩阵 + s101 网格 + gridbest/ss650/gapfill/fullbig 全 0 miss；E6 三臂 124 格全谱；random-init/collapse/E2-ext/HydraRNA 全收口
- [~] **NB ncRNA 6 格**（bs8@1e-05，need22G，worker 等卡轮转中——本轮已真正开训多轮，竞卡窗口持续）
- [~] ranksweep 37/48（rank {4,16} 轴，4-shard 在岗）
- [ ] 落齐后 final_close_monitor 自动全链重刷 → [PENDING] 清零 + grid_audit TUNED-MISSING=0 → **P4 preprint v1.0 按新叙事骨架重写**（六幕结构）

## G. 交接执行人必读顺序（1006 起）

1. STATUS_SNAPSHOT_20261006.md + 项目反思与叙事链改进_20261006.md
2. spec.md **§10.8（反思登记）+ §10.4/§10.5/§10.7**
3. 本文件文末「v3.16 回填」
4. TRAINING_LOG.md 服务器端（1006 段）
5. paper/preprint_draft.md v0.96（P4 重写底稿）

**纪律不变（新增三条）**：① need 标定必须同 bs 语境引用 ledger peak_mem_mb；② 审计导出器判定规则与 plan 落地口径逐字段对齐；③ PPT/论文数字一律从导出表程序化生成，禁止手抄。原有纪律（真 CUDA / smoke 不当结论 / B23 双证 / 共享卡锁 / 每任务提交 GitHub / 代码 /home、大文件 /mnt）全部延续。


---

## v3.17 回填（2026-10-07：P4 预印本 v1.0 完成 + 假完成第三层根治）

### A. P4 preprint v1.0（本轮最大交付物）

- [x] **paper/preprint_v1.0.md 上线**（commit e63f3c5，GitHub 已推）：六幕叙事骨架（幻觉→机制→条件→路线→代价→配方）全文重写
  - Abstract：主命题 + 四支撑（True or illusory / Mechanism / Route / Cost）
  - Introduction：实践者三选一困境开场 + 16 架构口径贡献列表
  - §2.1a 外部臂全收口重写（AIDO/RiboSpan 终值、NB tuned、HydraRNA frozen-only 说明）
  - §2.2 崩溃叙事 16 FT 架构 + 3 部分逃逸 + frozen 家族带 0.11–0.89 + 配方广度结论
  - §2.3 E2 五臂表修正 + **rank sweep 48 格新表**（rank 二阶旋钮）
  - §2.4 NB ×8.7 恢复 + **1.6B LR 二次翻转新段**（AIDO 1e-05=0.720 vs 3e-05=0.520）
  - §2.5 E3 权威口径重写（tuned full 小 n 全线最优——旧表过时口径作废）
  - §2.8 E6 87 格 + 官方谱新表 + 13/18 m6A-start 稀释
  - Methods 16 架构 / Discussion / Limitations 同步更新
- [x] **全文第 3 遍 ledger 对账**：修正 v0.96 六处错误口径（详见 TRAINING_LOG 1007 段）；头部附数据对账声明
- [x] v1.0 vs v0.96 差异全部可追溯（表间冲突回 ledger 原始行裁决）

### B. 假完成第三层（P1）根治

- [x] **q_fill.is_done 不排除 smoke 行**：NB 3 缺格（lora random s29 / frozen random s17 / m6A lora s29）只有 smoke done 行 → 补跑被假 skip。修复：is_done 加 `not r.get("smoke")`（两处）
- [x] **OOM exit 1 后 running 心跳行残留 → 自锁 claim-block 死循环**：修复 clear_pending 扩展为清 pending+running 行
- [x] NB 3 格补跑启动（q_fill_p2_nb_backfill_1007_plan，GPU4）
- [x] **E6 导出器表间冲突登记**：e6_table vs e6_official 的 10M/30M/micro 行互斥（+4.12 vs +11.23 等）——ledger 为唯一权威；导出器修复列入 v3.18（不阻塞预印本）

### C. 下一步（v3.18 起算）

1. NB 3 格落齐 → 刷 ledger → 重导出 c4_table → v1.0 数字终值化（NB 2-seed 标注解除）
2. E6 导出器口径修复（e6_table/e6_official 表间冲突根因：v1 vs v2 起点混写）
3. M1-M5 竞争监控重跑（超期 >14 天；C5-1 硬性要求）
4. 中文摘要 + 通信稿草稿
5. AIDO 3e-05 formal 3 种子补齐（当前只有 tuning seed 对比）——或论文口径改为「tuning-seed 对比」诚实标注（已采后者）

**纪律新增第四条**：论文/PPT 任何数字写入前必须先过「ledger 原始行」检索（不走导出表中转），写入后回对一遍；导出表冲突 = 立即停用该表并回源裁决。


### 1007 晚 NB 补跑收官补记

- [x] NB 3/3 格全部落地（lora s29 random 0.9429 / frozen s17 random 0.8473 / m6A lora s29 random 0.9917）；c4_table 自动重刷（nb_close_monitor 12:10 触发）
- [x] v1.0 NB 全臂 3/3 种子终值化并推送（ncRNA frozen 0.838 / lora 0.940 / m6A lora 0.992）
- [x] OOM 自愈实证：frozen s17 首跑被挤 OOM → 修复版清行换卡重跑成功（115.9min）
- [x] update_ppt.py 程序化 PPT 表工具落地（纪律 ③ 闭环：本地 code/tools + 服务器 scripts + GitHub）
- [x] spec v2.4 §10.9 / tasks v3.17 / 巡检日志 / STATUS 1007 补记 / 中文摘要 v1.0 全部同步
- [ ] 剩余：BibTeX 化（投稿期）、PI 共同作者/funding 确认、预印本挂出（arXiv/bioRxiv）


### 1007 晚补充：PPT 程序化全表核对 + AIDO 1.6B 证据升级启动

- [x] **PPT 全表程序化核对（第 2 轮，用户指令②闭环）**：update_ppt.py 期望值 + 逐格比对——slide3 表A/B **PASS**；slide5/6 抓到并修正 **4 处真实错误**（RiNALMo ncRNA tuned 0.938→0.944 grid-best 口径 / m6A 0.968→0.996 / E2 面板同步 / RNA-Sc SSP 排序修正 LoRA 0.84 为首）；修正后 **ALL PASS**；lint PASS；备份 ppt/work/before_fix_1007.pptx。两轮手抄错误后，程序化核对工具链正式接管（纪律 ③ 闭环）
- [x] **AIDO full@3e-05 formal 3 种子补跑启动**（p2_aido_3e5_1007_plan，33G×5.2h/格，worker setsid 等卡轮转 + aido_close_monitor cron 自动收口刷 lr_grid）——落齐后 v1.0 的 1.6B LR 翻转从 tuning-seed 单点对比升级为 3-seed 证据
- [x] 过程修复：plan lr 字符串化（q_fill tag 拼接类型错误）；worker setsid 脱离会话（nohup 单层被 ssh 断连收割）
- [ ] AIDO 3/3 落地 → v1.0 §2.4 升级 + status 同步

## v3.18 回填（2026-10-07 深夜：PPT 交接就绪）

- [x] 用户重命名定稿：`ppt/RNA_LM微调策略评测-结果版.pptx`（11 页简洁结果版，主交付）+ `ppt/RNA_LM微调策略评测-凌乱全面版.pptx`（19 页过程详解版归档）+ `旧/` 目录收纳 6 份历史备份
- [x] **《PPT修改交接文档.md》写入交接文档/**（§1 文件清单 / §2 逐页结构与数据源 / §3 六大数据口径红线 / §4 工具链四件套 / §5 用户格式要求 / §6 五条踩坑教训 / §7 命令速查 / §8 待办）——接手人零上下文可改
- [x] 修复记录：CRC 损坏假象根因（zip 手术）+ 从干净备份一次性重做 + 孤儿 part/rels/ContentTypes 三层清理 + 每步 testzip 验证；终态 CRC PASS / 11 页 / lint PASS
- [ ] 接手人按用户新需求改「结果版」；数字改动必须过 §3 口径 + §4 工具链

---

# v3.19 回填（2026-10-08：PPT 1008 七项修订 + 补测队列派发 + 收敛审计）

> 依据：用户 7 项 PPT 问题（结论①-⑤图修改 / E4-E6 补图 / 自训模型收敛质疑）。详 spec §10.10。

## A. PPT 修订（11→13 页，lint PASS）

- [x] 问题1：s3 结论①图融入 frozen vs 微调对比（fig_ppt_16arch v2，16 架构 × 4 柱）
- [x] 问题2：s6 结论② A8 三任务分图（ncRNA/m6A/MRL）+ AIDO/NB 模型补入 + LR 差异复核（真实 gap 口径：SpliceBERT ×12、ERNIE MRL ×28）+ 「三任务都要写全分开绘图」落地
- [x] 问题3：s7 结论③ m6A r8 lora 补齐（主行=rank8 默认口径）+ SSP 任务面板补全 + 参数量图轴标注 + 300M 补测派发（参数量上探）
- [x] 问题4：E4 泄漏交互页（新增 s5=04b）+ E5 资源实测页（新增 s11=09b）+ E6 banner 全谱口径——三部分结果图补全
- [x] 问题5：s9 结论④ 横轴改数字（每节点对应标注）+ 1.6B 官方模型并入（AIDO/RiboSpan 对比图）+ 100M 复测判读（3 种子一致，性能下降为真信号）+ N=3/6/12 在图例/标注中说明（n=3 seeds 口径）+ 300M 插值档派发
- [x] 问题6：s10 结论⑤ n=3000 档落地（full@3000=0.731 曲线上行）+ 5000 档在飞 + 等价线探索结论入 banner（full@1000 0.707 ≈ lora@3000 0.696）+ 300M 参数量上探派发
- [x] 四遍结构检查 + lint PASS + CRC PASS；备份 ppt/work/before_fix_1008.pptx

## B. 补测队列派发（服务器在飞）

- [~] p2_e3_5000_1008_plan（24 runs）：E3 3000/5000 档补全——3000 档 micro tuned full 3/3 已落（0.724/0.744/0.724）
- [~] p2_rnasc300m_1008_plan（18 runs）：RNA-Sc-300M 接入（smoke 302.1M 通过）× ncRNA 双切分 × 3 策略 × 3 种子
- [~] AIDO 3e-05 formal 3 种子（1007c 派发延续，aido_close_monitor 在岗）

## C. 工程修复（q_fill.py 两处）

- [x] --n-train 参数传递支持（E3 档位格经由 plan 派发）
- [x] is_done 精确 e3 档位匹配（修「3000 done 被误判为 5000 done」假 skip——B23 教训的新变体：档位维度也要双证）

## D. 问题7 收敛审计成文

- [x] docs/自训模型收敛审计_20261008.md（服务器 + 本地）：13 个自训 run 全部收敛（val 末 3 档降幅 <1.2%）；两系结论相反归因 = 语料广度 + 配方差异；300M 落地后验证容量插值假说

## E. 待办（下一 session）

- [ ] E3 5000 档 + 300M 18 格落地 → 重刷 fig_ppt_e3_curves / fig_ppt_c5b_v2（受控系六尺度）→ PPT 数字更新
- [ ] AIDO 3e-05 落地 → v1.0 §2.4 升级 3-seed 证据
- [ ] 预印本 v1.0 并入 E3 3000/5000 + 300M 数据（P4.1 增量）
- [ ] SSP rank sweep r4/r16 补格（72 格口径补全）

**纪律新增第五条（图脚本）**：rid 过滤必须按 `_` 分段精确匹配 tag（`_ri` 子串匹配误杀 rinalmo/ribospan 前缀；`_e310` 子串匹配误吃 `_e3100`）——tag 匹配错误会产生「全零假图」（1008 实跑发现，与 fig_ppt_16arch 首版全零事故同族）。

---

# v3.20 回填（2026-10-09：二轮 6 项问题 + 300M 收口 + E3 5000 崩溃临界点）

## A. 重大新数据落地

- [x] **300M 18/18 全收口**：full random 0.888/0.881/0.867 @3e-05——介于 100M 0.824 与 650M 0.896 之间，**容量插值假说验证成立**（100M 回落为真信号）；受控系等价线升为六尺度全谱
- [x] **E3 5000 档落地并发现崩溃临界点**：full@5000 = 0.064（崩）vs full@3000 = 0.73（正常）——**家族记忆崩溃临界点在 3000-5000**；frozen@5000 = 0.68 稳定不受影响
- [x] **AIDO 3e-05 仍未落**（0/3，等 32G 卡窗口）

## B. 二轮 6 项问题处置（PPT 14 页）

- [x] 问题2：A8 图 v3（每柱数值+倍数箭头 x12/x28）；「LR 差这么多没做错吧」复核结论入 banner（ledger 原始行验证）
- [x] 问题3：rank 图 v3 + SSP 面板 + 300M 六尺度 + 异架构 24 runs 在飞标注
- [x] 问题5：why_opposite 归因图（语料广度 + gap 反号双证据）+ 任务类型区分实验（MRL/m6A E3）派发
- [x] 问题6：E3 三任务并排图（per-seq/per-base 分类）+ 等价线交叉图新页（09c）
- [x] 问题7：E5 图重画（分组柱状 + 24GB 参考线）
- [x] 问题9：E6 图重画（双面板 + 语义注释）
- [x] 用户 PPT 内批注 3 处按内容修改后删除（s5/s9/s12）

## C. 新派队列（78 runs）

- [~] p2_e3rank_1009_plan：异架构 rank sweep（ERNIE/RNA-FM/SpliceBERT/UTR-LM × r4/r16 × 3）24 + MRL/m6A E3 3000/5000（micro）24 + Sc-10M lora e3 6 + Sc-30M/300M E3 3000/5000 24
- 验收：rank 图升 8 模型口径 / E3 三任务 3000/5000 全档 / 等价线大参数量验证

## D. 待办（下一 session）

- [ ] 78 runs 落地 → 刷 fig_ppt_ranksweep（异架构）/ fig_ppt_e3_3tasks（MRL/m6A 3000/5000）→ PPT 更新
- [ ] E3 5000 s17 落地 → 崩溃临界点三种子确认
- [ ] AIDO 3e-05 → v1.0 §2.4 3-seed 升级
- [ ] 预印本 v1.0 增量：300M 六尺度 + E3 5000 崩溃临界点 + 等价线交叉结论 + E3 多任务类型

### 1009 第三轮补记（04:30）

- [x] MRL/m6A E3 3000/5000 全 12+12 落地 → E3 三任务类型对照完成（问题6「单任务可信度」闭环：ncRNA 崩溃是任务特有——MRL 0.65 / m6A 0.99 不崩）
- [x] rank 图 v4 六架构（4 官方异构入图，问题3 闭环）→ PPT s7 更新
- [x] keepalive_e3rank cron 装岗（worker 死亡自动重拉）
- [~] 异构 rank r16 余 6 格 + Sc-30M/300M E3 + AIDO 3e-05 在飞（落地后刷终版图）

---

# v3.21 回填（2026-10-09 晚：第四轮 8 项问题 + 语料宽度消融臂 + 105 runs 新派）

## A. 用户 8 项问题处置（PPT 14 页）

- [x] 问题1：3500/4000/4500 临界点加密——子集已生成 + 9 runs 已派
- [x] 问题2：A8 MRL 缺格盘点（AIDO full@1e-05 + NB default）+ 6 runs 已派
- [x] 问题3：rank 图 v5 官方 4 模型（去 Sc-10M/UTR-LM）；1009 异构 rank 24/24 全收口
- [x] 问题4：语料宽窄定义 + 同库消融臂（**RNA-Sc-100M-b59 接入：5.9Gnt 全量语料 vs 2Gnt 采样，同架构同规模同种子——语料宽度归因直接检验，18 runs 在飞**）
- [x] 问题5：E3 图补 10/frozen/全量 + mega/650M 三档版 72 runs 已派
- [x] 问题6：等价线 5c 重画（线图 + 换算表双面板）
- [x] 问题7：E5 重画为标准分组柱状图
- [x] 问题8：E6 官方谱 v2（参数量升序；其他官方模型遗忘轴属 v2 未预注册——诚实标注）
- [x] s9 批注（问题4 同内容）按 banner 回应后删除

## B. 新派队列（105 runs）

- p2_1010_plan（87）：临界点 9 + A8 缺格 6 + mega/650M E3 72
- p2_b59_1010_plan（18）：语料宽度消融臂
- keepalive_e3rank cron 继续在岗；1010/b59 队列未接 keepalive（worker 存活，下轮巡检确认）

## C. 待办

- [ ] 105 runs 落地 → 刷 E3 图（3500/4000/4500 点 + mega/650M 版）+ A8 图（MRL 缺格）+ 等价线图（b59 消融对照）
- [ ] b59 vs 100M 结果判读 = 语料宽度归因的终判（受控系结论是否随语料变宽翻转）
- [ ] AIDO 3e-05 持续等卡

---

# v3.22 回填（2026-10-13 晚：第四层假完成根治 + 1016 队列 + 预印本 v1.0 增量 + 配额事故）

> 依据：本轮 SSH 真态（HEAD `5d9af17`；ledger 2194+）。详 STATUS_SNAPSHOT_20261013.md + 叙事链证据审计_第3轮_20261013.md + 巡检日志 1013 段。

## A. 第四层假完成变体根治（is_done 双格式）

- [x] q_fill.is_done 双格式匹配（`_lr_e3` + `_e3_lr` 两种顺序都认）——1011 六 worker 在已完成格 claim-blocked 死循环已解
- [x] audit_1016.py 权威审计器（rank/n_train/lr 精确匹配）——q_plan_need 台账误报纠正（1010 报缺 5 实为 68）
- [x] keepalive_1016.sh + cron */10 装岗
- [ ] **checklist B24 候选**：run_id 构造逻辑收敛到单一函数（当前 4 runner 各自构造格式漂移无检测——假完成 4 变体的共同根因）

## B. 调度解锁 + 配额事故

- [x] 1016 双 plan 拆分（mega_e3 27 + bigtail 41 unique）+ need 同 bs 实测重标定（650M frozen 34→8G）
- [x] 陈旧卡锁清理（kill -9 残留 10 个）→ 6 训练立即启动
- [x] tar_stage 111G → /mnt/cunyuliu/tar_stage_1013（**经用户确认**；230 文件，写测试通过）
- [ ] 巡检加入 `df /home/cunyuliu` 配额检查项（tar_progress.log 3 次 quota exceeded 前兆在案）

## C. 预印本 v1.0 增量并入（commit 5d9af17，两轮 ledger 对账）

- [x] Abstract：finding 1 过渡带 + finding 3 六尺度升级
- [x] §2.4 过渡带五模型表（micro/ERNIE/RNA-FM/SpliceBERT/Sc-10M × 3000-5000 逐种子）
- [x] §2.5：300M 插值 0.879 + 100M 六种子复测 0.84±0.02 + b59 语料宽度消融（frozen +0.07 / LoRA 平 / 方向不翻转）
- [x] 对账修正：300M lora family 0.076→0.079

## D. PPT + 叙事审计

- [x] PPT 15 页（s2/s9/s10 更新；lint PASS；CRC PASS；三遍值检查）
- [x] 《叙事链证据审计_第3轮_20261013.md》：第 2 轮（1006）薄弱点全部闭合（frozen 平线 5 模型全谱替代 head-only 2 模型；六种子+300M 洗清 100M 数据嫌疑；b59 分离语料/配方双因素）；逻辑链无断环判定

## E. 待办（下一 session）

- [ ] 1016 尾格 58 全落 → 刷 E3 全车道图（mega/650M 入图）→ PPT s10 换图
- [ ] AIDO 3e-05 ×3 落地 → v1.0 1.6B 证据升级 3-seed
- [ ] M1-M5 竞争监控重跑（C5-1 硬性要求，超期 >20 天）
- [ ] T0.3.1 导师三签 → C 组红队 24 项 → 预印本挂出（arXiv/bioRxiv）

**纪律新增第六/七条已固化**（换图双重验证 testzip+MD5 / 只操作本课题目录）；一至五条全部延续。

---

# v3.24 回填（2026-10-23：新任接手 + 假 running 清理 + q_master 协议修正 + monitor v2 + 占满车道 + GitHub/teams 双通道）

> 依据：本轮 SSH 实测（集群 HEAD `de541d3`→`c1c287b`，GitHub `a0d696c`；ledger 2633 行 = done 2578）。集群 = px2-jcy.matpool.com:29375（**RTX 5090 32G 单卡容器，无 cron；SSH 端口对高频连接敏感——合并命令 + 失败等 3-5 分钟**）。

## A. 接手核验（全部实测）

- [x] 交接文档全套读完（spec v2.4 / tasks v3.22 / checklist v1.12 / STATUS×17 / 迁移指南 / 备份总账 / 巡检日志 27 轮 / PPT 交接）
- [x] **迁移已完成**（前 session 10-18~10-22）：5090 环境 torch 2.11+cu128 / GitHub 代码 / 2ceping.zip 94G / HF 10 模型 / RNA-Sc 7 ckpt / NB md5 / **单格复算基准 0.7366≈0.739 ✅**；8 任务矩阵车道制在飞（10-18 用户拍板 8 任务：ncRNA/MRL/m6A/SSP + degradation/ssi/spliceai/crispr）
- [x] audit_1016 = 1（AIDO mrl full s43 random——1016 最后一格）

## B. 修复四件（本轮）

- [x] **ledger 47 行假 running 清理**（容器无 cron，reset_stale_cron.py 从未被调度——AIDO ncRNA 3 行 10-16 旧心跳 + spliceai 车道 OOM 残留）+ 并入 monitor v2 每 15min 常态化
- [x] **q_master Phase3 AIDO 协议漂移修正**：epochs 10→3、timeout 4h→12h（CELLTM 机制）——对齐成功先例行（s17/s29 = epochs 3、wall 7050-7250s；B24 纪律「重派抄成功先例三元组」）
- [x] **GPU 占满铁律执行**：q_splfrozen（12 格，已全落 DONE 01:47）→ q_spl650/q_splmega2/q_splnbfroz 三车道接力（GPU 12.4G→**31.6G/32G 99%**，16 训练进程）
- [x] **monitor_loop v2 装岗**：stale 清理 / 10 车道死亡自动 respawn / GPU<20G 告警 / q_master 守护（v1 只有快照+q5090 重拉）

## C. 通道建设

- [x] **GitHub 推送通道**：集群无凭据 → git bundle → Mac（~/.ssh 有 Cunyu-Liu key）→ push；本轮 4 commits 已推（de541d3/feb7cb0/c1c287b/a0d696c）
- [x] **/teams 备份**：/teams/HoulabData_1788502323/liucunyu/rna-ft-eval/（ledger 2633 + status 全表 + logs，129M；sync_1023.sh 幂等）
- [x] TRAINING_LOG 1023 段追加（服务器 + 巡检日志第 28 轮）

## D. 新任务首批数据判读（执行期发现登记口径——3 种子齐 + B23 双证后才入正式结论）

- spliceai macro-F1：micro lora family 0.611 / ERNIE lora random 0.575 / RNAFM full 0.542 / Sc-300M full 0.463；**frozen 全系 0.33-0.44**（frozen 增益存在=spliceai 可微调任务）
- degradation PCC：NB full 0.375-0.406（q_degrfull 18 格收口）
- crispr PR-AUC：mega full family 0.0125-0.154——**家族切分崩溃带第 4 任务复现**（vs micro random 0.642）
- NucleicBERT 4 任务 lora 全收口（q_nblane 19:51 DONE）

## E. 待办（优先级序）

- [ ] **E6 官方 15 格**（q_master Phase1 等 drain）：ERNIE/RNAFM × lora/full × 3 种子——bs32 与车道并行必 OOM（10-19 三轮实测），首跑 OOM 后按 B24 降 bs16/8 重派
- [ ] AIDO mrl s43（1016 收口）→ audit=0
- [ ] spliceai 全谱补齐（12→13 done / 目标 126 格）+ degradation/ssi/crispr 各臂
- [ ] export_c4 扩 8 任务口径 → preprint v1.1 增量 → PPT 更新（jingmei-ppt 规范；数字先过 ledger 原始行）
- [ ] HydraRNA 3 权重（orico TCC 被闸，需用户授权后传；16 架构第 16 席）
- [ ] M1-M5 竞争监控重跑（超期；C5-1）
- [ ] T0.3.1 导师三签 + C 组红队 24 项 → 预印本挂出

**纪律新增第九条**：px2-jcy SSH 端口敏感（连续快速连接即 reset）——合并命令单次执行 / 失败等 3-5 分钟 / scp 单次。一至八条全部延续。

---

# v3.25 回填（2026-10-24：科学完整性 P0 复审与恢复）

> 执行口径：先确认事实和影响边界，再备份隔离、修复验证、纠正重跑；不得为维持表面进度继续产生无效结果，也不得把修复前的 DONE 计数当作有效完成度。

## A. 交接与实态审计

- [x] 全部交接文档、1709 行巡检日志、远程 `8task_final_v2` / `tasks_v3.23` 阅读完成；历史结论与当前 HEAD/ledger/进程分开核验。
- [x] 单卡 RTX 5090、代码 `a2f1442`、2711 行 ledger 与当前车道实测；确认 8 任务新队列实际进展和 q_master 长期 drain。
- [x] **B20 实证**：HF `<cls>/<eos>` 与 NB `[CLS]/[SEP]` 导致 spliceai/degradation/SSI 标签错位；RNA-Sc 无特殊 token。
- [x] **E6 实证**：official MLM 在未掩码输入上取同位 target，旧 official NLL 不能用于科学结论。
- [x] 精准暂停受影响 per-base 与 E6 队列、旧 monitor/q_master；保留 CRISPR per-seq，避免继续产生无效数据。

## B. 修复与验证

- [x] B20 共用对齐实现：special-token/PAD 排除、单碱基硬断言、scored window、确定性截断；spl/regbase 使用 `_b20fix` RID。
- [x] E6 固定 15% masked-position MLM NLL；确定性逐序列掩码、独立 noise-band 定义、`_mlm15fix` RID。
- [x] clf/spl/E6 rc75、clf/spl device 参数、finite 检查、result 原子写、regbase NumPy seed 修复。
- [x] monitor v2.2：monitor 单实例 flock、lane 生命周期 flock、白名单启动、q_master 不再自动复活；故障注入测试连续 3 轮通过。
- [x] 本地 focused tests 27/27（含 B20、E6、corrected dispatcher）、ledger 8/8、shell 语法检查通过。
- [x] 集群隔离目录真实 tokenizer / CUDA / monitor 测试通过：HF/NB/RNA-Sc 对齐全过，E6 同 seed 差 9.4e-8，四个训练 smoke 均写出有限结果。

## C. 旧结果隔离与恢复训练

- [x] `/teams` 备份 ledger 与 quarantine manifest；294 条受影响旧行标 invalid/cancelled，245 个旧 result 文件改名保留证据。
- [~] live 部署与真实 smoke 复核完成；corrected dispatcher 已统一接管 342 格，正在按唯一 owner 重跑，禁止新旧 RID 混算。
- [~] CRISPR 不受 B20 影响，继续完成现有矩阵；不借修复名义重跑已验证的 per-seq frozen 结果。
- [ ] 每条 corrected lane 记录模型、任务、协议、种子、LR、bs、epochs、wall、peak、result 路径与结论；失败不得无条件 DONE。

## D. E6 与遗留大格

- [~] official canonical 30 格 `_mlm15fix` 重跑中，micro v1 已 6/6 双证收口并自动推进到 ERNIE/RNA-FM；旧 mega LoRA@1e-5 变体若保留另带独立标签。
- [~] E6-v2 official micro m6A-start 6 格已追加隔离并以 `_taskm6a_s0_mlm15fix` 重跑；累计隔离 300 行、251 个旧 result 文件。
- [ ] 修正版 official ΔNLL 逐行对账前，冻结旧 official 5–9×等表述；controlled/NB 结果分协议呈现。
- [~] AIDO MRL s43 已由 `exclusive_aido` 唯一 owner 接管，协议为 `finetune_mrl` + 3 epochs + bs1 + 12h；当前 child 自然排空后执行，完成须 PEARSON_R 双证 + `audit_1016=0`。

## E. 监控、收敛与交付

- [~] monitor v2.2 已部署并核验单实例、锁释放、白名单和 GPU 低显存告警；E6 阶段自推进与 corrected/E6-v2 verify-complete 已上线，后续按真实完成证据禁重启，旧计划 glob 复活已禁用。
- [ ] 建立 validation-loss 平台审计；未达 `min_delta + patience` 的格不得标 final，续训以 `valplateau_v1` 独立记录，不与 fixed-epoch 静默混合。
- [ ] corrected 结果达到 B23 + 收敛门禁后，重刷导出表/图，进行至少三轮 ledger 原始行对账，再更新 preprint 与结果版 PPT。
- [ ] 每个修复/实验批次完成后提交并经 Mac bundle 通道推 GitHub；大型备份与 manifest 留 `/teams/HoulabData_1788502323/liucunyu/rna-ft-eval/`。
- [ ] 最终复核 spec/tasks/checklist、训练日志、PPT 与论文中的任务数、指标、有效格数和协议标签一致；T0.3.1 三签及 C/D 门禁不得因工程进度自行勾销。

---

# v3.28 回填（2026-10-26：导师汇报八任务扩展与证据修复）

> 本计划先于实验执行登记。用户已确认采用最终注册表：序列级分类 ncRNA/CRISPR，序列级回归 MRL，碱基级分类 m6A/SpliceAI/SSP，碱基级回归 degradation/SSI。不是形式上的每类两个。完整范围、协议与验收见 spec §10.15。当前本地审计基于文档与 GitHub 代码；远程 SSH 尚未恢复，所有远程完成数均待回源复核，不写“已完成”。

## A. P0 证据链与执行门

- [x] 阅读根目录交接、spec/tasks/checklist、PPT、v2 图集、隔离记录；识别当前 PPT 仅展示 3 个新增任务，而非 8 任务完整结果。
- [x] 发现 `valplateau.py` 实际读取 `epoch_train_losses`，与 validation-loss 合同不符；禁止把现有 plateau 标为 validation 收敛。
- [x] 发现 `q_corrected_8task.py --verify-complete` 只覆盖 SpliceAI/degradation/SSI 的 342 格双证，不覆盖全 8 任务、CRISPR 或收敛；不得作为项目收口证明。
- [ ] 核验远程单卡 RTX5090、当前 HEAD、运行队列、真实 ledger/result 与 `/root/rnaft` 和 `/root/rna-ft-eval` 映射；保留访问失败证据，不高频重连。
- [ ] 在独立 held-out validation 上实现逐 epoch val loss、原子持久化、`valplateau_v2` RID、续训/停止原因与全 8 任务验收；官方 train/test 数据从 train 确定性划 validation，test 永不参与选择。
- [ ] 为 corrected 导出器增加协议代际、任务、split、seed、LR、n_train、rank、epochs 过滤及 8 任务传统基线；按 RID 防 legacy/_b20fix/_mlm15fix/_valplateau_v2 混算。
- [ ] focused tests、真实 tokenizer/CUDA smoke 各跑 3 遍；失败即停，不进入正式训练。

## B. 八任务主图、结论②③与同源等价线

- [ ] 结论①a 后新增任务扩展页：8 任务×官方模型×frozen/LoRA/full×random/family×3 seeds，按各自主指标绘制与前 3 页同构四柱图；优先复用已验收格，缺格只补缺口。完成条件：三轮 ledger/result 对账，不跨指标误读。
- [ ] 结论②：8 任务 default-LR vs tuned-LR 配对复测，seed101 选 LR，17/29/43 独立正式评估；标出每个 default/tuned 的真实 LR，避免把 LR 差异与任务结构混为一谈。
- [ ] 结论③：8 任务 LoRA/DoRA/full 与 rank 对照；RiNALMo-micro rank8 同口径优先复核，检查模型权重、tokenizer、指标、split、checkpoint、RID 和评测脚本。低值如实保留，只有找到实现错误才隔离重跑。
- [ ] 结论④：RNA-Sc 与 RiNALMo 分面绘制小 full(n) 与大 LoRA(m) 数据量等价线，8 任务完整；直接标出等价数据量及 CI。没有可支持的等价点则写“当前范围未观测到”，不制造交点。
- [ ] 每批结束保存配置、命令、git SHA、GPU/CUDA、seed、逐 epoch train/val、wall/peak/checkpoint、result 路径与结论，提交确认代码到 GitHub。

## C. 机制、结论⑤与 C5 资源/预算

- [ ] t-SNE：8 任务×2 split×pre/Post-LoRA/Post-full；RiNALMo CLS 为参照并保存预测头前 embedding，必要时补 logit/head 诊断。统一样本、投影参数和坐标拟合，标模型/样本数/标签含义；t-SNE 不作因果证明。
- [ ] MRL/m6A：扩测可接入官方模型并复核 seed/抽样协议；将“未观察到 ncRNA 式坍缩”限定在已测范围，不写成任务免疫定律。
- [ ] ncRNA：核查 split 标签支持、类别/家族映射、预测分布、基线、长度/GC、head 与 backbone 更新；先排除测评/数据错误，再判断任务结构、分类头或表征的贡献。
- [ ] C5d：mega/giga 每个缺失数据点区分“未跑、失败、未导出、RID 代际不符”，补跑后统一刷新；不把 pending 伪装成完成点。
- [ ] C5c：1000–3000 间补 {1500,2000,2500}，8 任务补齐；micro/mega（约148M，用户称180M档）/giga（约650M）三档同协议复测，给逐种子结果与 95% CI。
- [ ] C5b：复测 ERNIE-RNA LoRA/full 并扩展 8 任务时间×性能；所有点关联 run_id，统一硬件、batch、n、split 与停止协议，记录 wall/peak/checkpoint 三项。
- [ ] 资源填充：单卡共享锁、多 worker 按同 batch 实测 need 填充显存；禁止同名车道双开。CUDA 不可用或 CPU 降级即停并留证，不能以超时结束冒充收敛。

## D. PPT、原数据与交接清理

- [x] 逐页读取当前 20 页 PPT 并渲染总览；确定保留用户模板、只修改指定对象，正文 Microsoft YaHei + 1.5 倍行距。
- [ ] 原第 3 页后新增“8 任务地图”页，结论①a 后放任务扩展图；删除已执行的批注框，修正过强结论与图文不符表述。
- [ ] 新结果过门禁后逐图替换；未过门禁时明确标“待复核/在测”，不把旧 3 任务图改称 8 任务完成。
- [ ] 保留绘图原始 CSV/JSON、脚本、图表、源 run 路径、生成时间和协议标签；旧数据与废弃文档移动归档而非删除，先核引用再归档。
- [ ] 完成内容、XML/结构、字体/行距、溢出、渲染与嵌图 MD5 三轮以上复核；原始 PPT 保留，交付独立修订版。

## E. 2026-10-27 真实执行记录与继续清单

- [x] 远程恢复并实测：单张 RTX 5090，torch 2.11.0+cu128，真实 CUDA 可用；`/root/rna-ft-eval -> /root/rnaft`。读取实时 ledger 与 `b20fix_8task_table.csv`，确认原表大量格仅 1–2 seeds，不能作为完整均值。
- [x] 发现并备份重复 corrected 双写；保留进程、锁、日志与 artifact，停止重复 parent/child，将污染 RID 标 cancelled 并隔离，不删除证据。E6 大格不强制中止。
- [x] GitHub `3bfced6`：真实 validation plateau、独立 RID、val split、种子采样、family cluster 三方隔离、空目录审计与 E6 双协议验收。
- [x] GitHub `3cb9d0d`：真实 smoke 发现 ledger `status` 冲突后改为 `convergence_status`，防止验证状态覆盖执行状态。
- [x] GitHub `427bcf0`：SpliceAI 官方 train/validation/test 去重；train 内部划 validation，validation/test 不参与停止选择，跨侧重叠 17/4/1 已处理。
- [x] 真实 tokenizer 对齐 6/6；远程 focused tests 94/94 通过；四个真实 CUDA 小格（clf/spl/regbase/e6）全部完成 CONVERGED + result + ledger + validation 审计。E6 的 ncRNA validation CE 与 S0 NLL 分属不同证据。
- [~] corrected 新协议队列：两个不同模型 worker 并行，lifecycle lock 防双开。每个新格均记录 validation 曲线，不再以 fixed epochs 作为完成。
- [~] RiNALMo-micro ncRNA LoRA rank8：旧 clf seed-split 批次已取消并隔离；现用 `finetune_one` 固定 split + `_fixedsplit` RID 重跑双 split × 3 seeds，保留 validation 曲线，未完成前不写正式结论。
- [x] 四个旧主任务 runner 的 val2 接口已验收：MRL/m6A/SSP/ncRNA 均有真实 validation、seed 采样和结果状态隔离。MRL 已开始官方模型扩测；modification 已改官方序列级多标签并完成 smoke，正式 `_seqmlfix` 复测尚待独立 launcher 启动。1500/2000/2500 数据档列入统一调度，不与现有 RID 混算。
- [ ] 持续完成 8 任务主图、结论②③、同源 n↔m 等价线、三策略 t-SNE、ncRNA 归因、C5b/C5c/C5d；每项三轮 ledger/result 对账后才换 PPT 终图。
- [x] PPT 导师讨论修订版完成 21 页与全部视觉/结构验收；历史文档/旧数据归档不删除。三任务阶段性图的 live CSV 已回源，不再使用图片读数代替原始数据。

## F. 2026-10-27 modification 官方任务语义纠错与复测（P0）

- [x] 真实数据与官方代码核对：BEACON `modification` = 101nt sequence + 12 维 multi-label，官方 `downstream/train_modification.py` 为序列级多标签分类，不是 per-base。m6A 为标签索引 7，mean AUC 为辅助。
- [x] 527 条历史 modification 结果标 invalid 并保留 `legacy_modification_wrong_task_quarantine.json`，不得再用作“逐碱基免疫”、rank/E3/E6 支持证据；历史 PPT 图已撤下。
- [x] `finetune_base` 改为序列级 12 维多标签 head + BCE，按修饰类型计算 AUC，保存 `label_semantics` 和 mean AUC；新正式 RID 使用 `_seqmlfix`，不与旧值混算。GitHub `f8becb6`、`8995970`。
- [x] 官方分类更新：序列级分类 3（ncRNA/CRISPR/modification）、序列级回归 1（MRL）、碱基级分类 2（SpliceAI/SSP）、碱基级回归 2（degradation/SSI）。spec §10.16 已冻结该纠错。
- [x] 修正协议 smoke 已验证 validation 收敛与 result，指标不作为科学结论。MRL 已有正式收敛结果：random LoRA 约 0.796/0.801，family LoRA 约 0.701；其他模型继续补测。
- [~] modification 正式 `_seqmlfix` 复测：micro/mega/giga/ERNIE/RNA-FM × random/family × LoRA/full × 3 seeds，验证 split 来源、validation 曲线、result、ledger、runtime。MRL/m6A 共用 best-val launcher 已启动，当前先执行 MRL；不得把 launcher 当作 m6A 正式结果，不恢复旧 m6A 结论。
- [~] ncRNA rank8 改用 fixedsplit + `_fixedsplit` RID 重跑，旧 clf seed-split 与两个过拟合 val2 格均 cancelled。两个 random best-val 正式子进程已启动；完成须 result/ledger/checkpoint 三证，不得混算。
- [ ] 全任务真实语义复核：每个任务的标签长度、类别/回归语义、主指标与官方实现一致，再启动对应新队列；不能只通过 smoke 即恢复旧“类级结论”。
- [ ] m6A 复测完成后，重新评估其是否坍缩、与 ncRNA 的任务结构关系、rank/LR/数据量效应，重新绘制结论①a-2、③、⑤与相关 E6 页面；真实 per-base m6A 若需新增，另找数据源与 RID。

## G. 2026-10-27 best-val 正式结果与资源队列

- [x] GitHub `f4f6e09`→`02e2afc`：best-val、严格调度、ncRNA 机制诊断、互补注册表、显存等待与 `/teams` artifact root 已部署。全仓 196 项测试通过。
- [x] rank8 6/6 正式完成：random ACC=0.918026±0.009421，family=0.900312±0.005268；MRL micro 12/12 完成：LoRA random/family=0.803926/0.711024，full=0.799254/0.702377。均三层 proof，artifact 已迁移 `/teams` 并保留 symlink；其他模型和任务继续执行。
- [x] ncRNA pre 真实诊断：random n=757、family n=856；CLS/head.pool/logits/预测字段与 manifest 完整，pre 参考头 seed=201，ACC 不作 zero-shot。
- [~] post 首次 OOM 已隔离；当前单 worker 以 LoRA 8 GiB/full 12 GiB 门槛等待。complementary 324 格统一调度在等待显存窗口，未把等待记为失败或完成。
- [~] modification-E6 旧 launcher 正在运行：s17 LoRA/full 与 s29 LoRA 已形成有效结果，重复后缀仅作命名兼容，完整 proof 后免重跑；兼容脚本待旧 launcher 结束后部署，不恢复旧 per-base 遗忘结论。
- [x] 28 个 dense 整簇嵌套子集已生成并备份；C5c 全任务 2016 格 dry-run 唯一性通过，ncRNA family dense 126 格，调度器漏传 `--task` 已修复。C5c 尚未形成正式结果。
- [ ] 等 family/rank8 全种子、MRL/m6A 全模型与 8 任务矩阵过门禁后，再刷新结论图、等价线和 PPT；当前首批 random 结果不用于提前宣称旧测评错误。

## H. 2026-10-27 ncRNA 双 split 机制与七任务诊断接口复核

- [x] ncRNA random/family 三状态诊断均完成。random n=757/state，CLS silhouette=0.026/0.239/0.608；family n=856/state，CLS silhouette=0.023/0.242/0.589，head.pool=0.059/0.390/0.622。三状态 manifest hash 一致，family train/val/test cluster 两两隔离，post 均恢复 best-val 且 checkpoint proof=ok。上述仅为 seed17 描述性诊断，不替代主矩阵三 seeds，也不证明分类头因果。
- [x] family full 首次 OOM 的目录与日志已移入 `artifacts/mechanism_quarantine/`，没有 diagnostic/embeddings 被误用。第二次仅暂停 complementary 与 MRL/m6A 的新派发，保留当前训练子进程；以 14 GiB 启动门槛运行，实测峰值 9.117 GiB，rc=0 后自动恢复调度。
- [x] 修复 aligned NPZ 无后缀时 diagnostic 指向不存在文件的问题；本地与远程全仓均 215 tests 通过，提交 `ab49c87` 已推 GitHub `rnaft-expansion-20261027` 并部署。family CLS/head 联合图、PDF、逐点坐标和 metadata 已生成。
- [~] 其余 3 任务（SpliceAI、degradation、SSI）按 spec §10.20 的 sequence/token 诊断范式实施；SSP 双 split 已完成，SpliceAI random 三状态已完成，SpliceAI family 与 degradation/SSI 双 split 待源格 proof。先写指标、形状、manifest、split 与 checkpoint 测试，再启动 GPU，不复制 ncRNA/MRL/modification/CRISPR 的表示或指标解释。SpliceAI/degradation/SSI 的 validation 明确记为 train holdout，缺失的源 `data_evidence` 不伪造。
- [~] per-base best-val 源格：SpliceAI、SSP、degradation、SSI × LoRA/full × random/family × seed17，共 16 格。复用 `expansion_jobs.job_for` 生成 registry，`RNAFT_ARTIFACT_ROOT=/teams`，独立 state-dir=`mechanism_source_perbase`，单 worker、8GiB/格。与 valplateau_v2、legacy、C5c dry-run 隔离；16/16 proof 后再启动机制诊断，不把 smoke 或旧结果计入。当前首格 SpliceAI random LoRA 已真实 CUDA 启动。
- [~] SpliceAI 诊断器：按 spec §10.20 实现 B20 per-base token hidden、full-test `MACRO_F1/value` 与 `MICRO_F1/value2` 对账，ROC-AUC 仅作辅助；每类至多 512 token 确定性联合抽样，不用 CLS 或 sampled 指标代替 full-test。
- [x] CRISPR 机制：random/family 各 seed17 三状态完成，完整 test 为 3586/1933 条。random LoRA/full PR-AUC=0.653180944/0.057878348，family=0.598625327/0.112742613，均与源 result 对账通过；full 低值保留，不归因于测评失败。每状态 1024，正例 27/11，富集仅用于显示，指标只算 full-test。
- [x] CRISPR 诊断与绘图代码提交 `e0230e7`、`14b9cd0`、`a129ed9` 并部署，本地/远程全仓 244 tests 通过。CRISPR 页已插入演示顺序第 12 页，PPT 增至 24 页；ncRNA 剩余任务数同步为 4。
- [x] 调度路径 P0 修复：发现旧 registry 的 `/root/rna-ft-eval/artifacts` 与 ledger `/teams` out_dir 不一致，导致 proof missing 误判。重新生成 `complementary_jobs_20261027_pairalign_teams.json` 和 `c5c_all_jobs_20261027_pairalign_teams.json`，除 result_dir 外逐项一致；旧队列自然排空后切换，CRISPR 四个源格均 complete，未重跑。C5c 新 registry 仅 dry-run，未启动波次。
- [x] modification 机制：random/family 各 seed17 三状态均完成，完整 test 为 1200/30904 条。random LoRA/full m6A AUC=0.985530435/0.972017391，family=0.942003028/0.938341444，均与源 result 对账通过。每状态抽 1024，m6A 阳性 random=45、family=202；CLS/head.pool 联合图、12 维 labels/logits/probabilities、valid mask、source-compatible mean AUC 与 valid-only mean AUC 均已保存。
- [x] modification 诊断与绘图代码提交 `508e615`、`7687344` 并部署，本地/远程全仓 235 tests 通过。m6A 双 split 页已插入演示顺序第 11 页，PPT 增至 23 页；ncRNA 剩余任务数同步为 5，其他页面未改。CRISPR 目前已有 random/family LoRA 源格，full 继续补测，不提前组成三状态。
- [x] MRL 机制复用 micro best-val checkpoint：random/family 各 seed17 三状态均完成，完整 test 分别为 7600/9150 条，LoRA/full Pearson r 在 random=0.803231225/0.801666645、family=0.720264749/0.694011763，均与源 result 对账通过。每状态按 sequence hash 抽 1024，CLS/head.pool 联合图、逐点坐标、source run_id 与 residual 已验收，不计算分类 silhouette。
- [x] MRL 双 split 机制页已插入演示顺序第 10 页，PPT 增至 22 页；新增 slide22、对应 rels 和 MRL 媒体，其他用户手调页面未改。随后仅将 ncRNA 页“其余 7 任务”同步为“其余 6 任务”。相邻页 `validate_layout.py --slides 9,10,11` Issues=0、22 页渲染正常，右上角 MRL 标签换行问题已修正。
- [x] MRL micro 12 格历史 split protocol 标签已完成可回滚校正：仅 `valplateau_v2` 标签改为与 result 一致的 `bestval_v1`，result/split/ledger 三处一致，指标与 checkpoint 未变。原始文件和 ledger 已备份，`status/protocol_label_repairs/mrl_micro_20261027/repair_manifest.json` 留存。
- [x] MRL checkpoint 诊断与连续标签绘图代码已提交 `62ff264`、`93b0127` 并部署，本地/远程全仓 227 tests 通过。首次 pre OOM 已隔离；后续仅暂停新派发完成推理，未中断其他训练子进程。
- [x] **SSP P0 对齐修复**：训练 loss、评估分数提取和 `pos_weight` 均改为经 B20 验证的 base-token 映射；新 RID 统一 `_pairalign`，不改变任务注册、pair-level F1 或 family split。本地/远程各 219 tests 通过，提交 `46b849f` 已推 GitHub 并部署。
- [x] SSP 真实 CUDA frozen-head smoke 完成：RiNALMo `RnaTokenizer` 的 token 0 确认为 `<cls>`，41 个碱基映射到 token 1–41，820 个 pair mask 不含 special token。result/ledger/best.ckpt proof 一致，`acceptance_eligible=false`，低样本 F1 不作科学结论。
- [x] `/teams` 原 SSP 新协议结果为 0，无需重跑已有新成品。新 complementary registry 保持 234 个非 SSP RID 不变，仅 90 个 SSP RID 加 `_pairalign`；旧 registry 保留，旧 parent 自然排空后终止，新 parent 已恢复。
- [x] C5c 已重新生成 `c5c_all_jobs_20261027_pairalign.json`：2016 格 RID 唯一，SSP 252 格全部 `_pairalign`，ncRNA family dense 仍为 126 格；仅更新 dry-run registry，尚未启动 C5c 波次。
- [ ] 历史 legacy SSP 格继续按真实 tokenizer 对齐证据决定隔离或 legacy 保留；旧 artifact 只备份隔离，不删除。

## I. 2026-10-27 per-base 诊断实现与源格证据链修复

- [x] SpliceAI 绘图器提交 `04d014e` 并已部署，本地/远端全仓各 253 tests 通过；后续独立复审发现的数据 loader、MICRO_F1、B20 和类别语义问题已一并重写，不以早期 253 项作为最终验收。
- [x] per-base 诊断核心提交 `ac2f4df`：SpliceAI 使用正确 random/family 数据重建、B20 base/token 双位置、macro/micro 对账与 negative/acceptor/donor 语义；SSP 使用 pair head-input 与 validation-only threshold；degradation/SSI 使用连续 per-base 表示、全局 PCC 和序列等权 MCRMSE。三类 post 均要求 registry complete、目录一致、checkpoint 和 full-test proof，失败可清理未完成产物重试。
- [x] runner 收尾修复提交 `e65467d`：SpliceAI/Regbase 不再重复传 `metric/value`，避免有效 test result 写出后 ledger 失败。最终本地全仓 321 tests 通过，独立复审无阻断项；部署与远端验收见下文 J。GitHub 分支 `rnaft-expansion-20261027` 已通过 API fast-forward 到 `be856553`，最终 tree 与本地 `b7d0eef` 一致。
- [x] SSP registry 四个源格误传的 `--out-suffix _pairalign` 已移除，RID 与其余 12 格未变；原文件归档至 `status/archive/mechanism_source_perbase_jobs_pre_ssp_argfix_20261027.json`，修正后 16 格 dry-run 通过。旧 parent 已加载旧参数，未安全切换前不得进入 SSP。
- [~] 源格实况：SpliceAI random LoRA 已收敛并写出 result/plateau/best.ckpt，但因旧 runner 重复 `metric` 目前仍是 `valid result proof but ledger is not done`，不得作为 complete。random full 正在运行；其旧进程若发生同类收尾错误，也只凭原 result 补 ledger，不重训。四个 SpliceAI 源格尚未全部 complete，正式诊断/PPT 页未启动。
- [ ] SSH 连接恢复后：部署 `ac2f4df` 与 `e65467d`，远端跑全仓测试，备份并补写受影响 ledger，逐格复核 proof；随后安全切换 per-base parent、推送既定 GitHub 分支并同步 `/teams` 交接备份。当前 SSH 连续 reset，暂停高频重试并保留证据。

## J. 2026-10-27 SpliceAI random 三状态正式诊断

- [x] `ac2f4df` 与 `e65467d` 已部署，远端全仓 321 tests 通过。两个 random 源格仅补写既有 result 对应的 ledger，未重训；原始 ledger 与 repair manifest 已归档至 `/teams/.../status/ledger_repairs/perbase_spliceai_20261027T140918Z/`，两格 `proof_state=complete`。
- [x] SpliceAI random pre/LoRA/full 三状态均完成真实 CUDA 诊断：full test 为 15,642 条序列、1,564,200 个有效 token。LoRA `MACRO_F1=0.431161874`、`MICRO_F1=0.999664365`；full 分别为 `0.349765774`、`0.999654776`，均与源 result 一致。pre 的 seed201 随机参考头不写作 zero-shot。
- [x] 三状态联合 t-SNE 已生成，抽样为每状态 1,058 个 token（negative 512、acceptor 271、donor 275）；类别均衡仅用于显示。aligned NPZ、300dpi PNG/PDF、逐 token CSV 与 metadata 已在 `/teams/.../artifacts/mechanism_spliceai/` 生成，full-test hash 和 manifest hash 完整。上述仅为 random、seed17 的描述性诊断，不扩写为 family 或三种子结论。
- [x] SSP/回归绘图器与 SSP aligned 自包含 metadata 提交 `b7d0eef` 并已部署，本地/远端全仓各 381 tests 通过。SpliceAI 图、坐标和 diagnostic 已下载，完成图像检查及 NPZ/CSV/metadata/diagnostic 四方对账；GitHub 已更新至 `be856553`，family 源格未完成前不新增 PPT 页。

## K. 2026-10-27 SSP random 三状态正式诊断

- [x] SSP 四个源格均 complete，random pre/LoRA/full 已完成真实 CUDA 诊断：400 条 test 序列、3,127,446 个上三角 pair、正 pair 9,941。LoRA pair-F1=0.1872、full=0.1605，precision/recall、validation threshold 和 val_f1 均与源 result 一致；pre 的 seed201 PairHead 不作 zero-shot。
- [x] random 联合 t-SNE、PNG/PDF、逐 pair CSV 和 metadata 已生成并下载。每状态 1,024 个 pair，unpaired/paired 各 512，均衡仅用于显示。NPZ/CSV/metadata/diagnostic 四方对账通过，含 B20 pair 对齐、sigmoid、full-test hash 和 source proof。family pre 已完成，LoRA/full 继续执行，未新增 PPT 页。
- [x] SSP family 三状态也已完成：2,966,351 个 pair、正 pair 9,418，LoRA/full pair-F1=0.1834/0.2122，均与源 result 对账。双 split 图和 `mechanism_ssp_split_compare_metadata.json` 已生成；新增 SSP 页为演示顺序第 13 页，PPT 共 25 页，原 24 页 XML 语义一致，实际中文渲染、行距、字体和 ZIP CRC 均通过，SSP 初版 SHA256=`71d86a267c29cdc1345cc3e4286be037c4aaae4df1283748b309f5b2a2e70c25`。
- [x] ncRNA 机制页副标题与页脚的剩余任务数均由 4 同步为 3，仅 `ppt/slides/slide8.xml` 变化，其余包条目逐字节不变；ZIP CRC、25 页 PDF、Microsoft YaHei、1.5 倍行距及第 9/13 页实际渲染复核通过。当前 PPT SHA256=`66ca40e7a36dd515c5e55c604c69b770a5dbb9c1b8d8b0ea12d51b79d66f79bc`。

## L. 2026-10-27 剩余 per-base 源格与自动诊断接力

- [x] SpliceAI family LoRA 已收敛并完成 full test：17,079 条 test，`MACRO_F1=0.490382393`、`MICRO_F1=0.999681480`，best_epoch=0，符合 bestval_v1 的 substantive-improvement 停止合同。旧 runner 在 result 写出后再次发生重复 `metric` ledger 收尾错误；确认无同 RID 活进程后，仅备份并补写 ledger，未重训。result/plateau/checkpoint/CUDA runtime 与 registry 均已核验，`proof_state=complete`；证据在 `/teams/.../status/ledger_repairs/perbase_spliceai_family_20261027T170128Z/`。
- [x] SpliceAI family full 已通过 complete proof：MACRO_F1=0.450522094，best_epoch=0。长期训练已自然结束，未重启或重复派发；SpliceAI family pre 与 LoRA 诊断已完成，LoRA 与源 macro/micro 完全一致，full 诊断待 parent 恢复后执行。
- [x] 2026-10-27T19:47 全部 16 个 per-base best-val 源格均为 complete，覆盖 SpliceAI、SSP、degradation、SSI × random/family × LoRA/full × seed17。SSI family full 同时完成：PCC=0.598510291，best_epoch=0。源格完成不等同于机制图验收，仍须三状态 full-test 对账。
- [x] degradation/SSI 诊断经独立实现复审，未发现数据重建、B20、PCC/MCRMSE、TokenHead、连续抽样或三状态对齐的算法阻断。16 格 registry 已明确包含所需 8 个 regbase 源格；注册命令未覆盖 `--max-len`，使用 runner 默认 192，与诊断一致。真实 CUDA 前向、checkpoint key 和 full-test 数值容差仍须在源格完成后验收。通用 `build_mechanism_regbase_compare.py` 已准备，校验连续未分箱标签、residual、B20 位置、full-test PCC/MCRMSE 和 source proof；两个任务的缺失源负向测试均通过，未生成占位图或 metadata。`add_regbase_slide.py` 也已准备，degradation/SSI 只有在真实双 split metadata/PNG 齐全时才依次新增页面，缺失源测试未改 presentation 或 slide26–28；在 degradation 真实图已存在但 SpliceAI 页尚未加入时，顺序门同样拒绝修改 PPT。
- [x] SpliceAI 双 split 图构建器 `build_mechanism_spliceai_compare.py` 已准备，逐点校验 token/base 位置、三分类 softmax、三状态 manifest、full-test hash、macro/micro 与 ROC-AUC 辅助边界。random 真实 CSV 3,174 行读取验证通过；family 尚未生成，未复制 random、未生成占位图或双 split metadata。`add_spliceai_slide.py` 也已准备，只有真实双 split metadata/PNG 齐全才新增第 14 页，并按实际指标生成文案；缺失 family 的负向测试通过，未改 presentation、未生成 slide26。
- [x] 按 spec §10.20.15 利用空闲显存新增 degradation random 两条独立源格队列：lane2 LoRA parent/child=1700863/1700941、lane3 full=1700864/1700942。启动前确认 family full 原进程仍活跃、目标 RID 均 runnable、无 micro regbase 或同名 lane 进程，两个单格 registry 均通过唯一性/dry-run 校验；可用显存 19.164 GiB，按每格 8 GiB 预算并行。2026-10-27T17:30:59Z 两格均 `proof_state=running`，目标子进程各恰好 1 个；LoRA 已到 epoch2（val_loss 0.346216），full 已到 epoch3（val_loss 0.343031），仍继续收敛。GPU 利用率 95%、显存 20,617/32,607 MiB。既有 RiNALMo-mega degradation 属于其他队列，不是同 RID 冲突。两格随后均收敛至 best_epoch=5 并通过 complete proof：LoRA PCC=0.541539063、MCRMSE=0.614810331，full PCC=0.546761068、MCRMSE=0.613951395；n_train/n_val/n_test=1552/172/431，wall_sec=511.3/483.9。该数值仅为 seed17 random 结果。
- [x] degradation family 两源格均收敛至 best_epoch=3 并通过 complete proof：LoRA PCC=0.396906205、MCRMSE=0.817257802，full PCC=0.402724592、MCRMSE=0.816725772；n_train/n_val/n_test=1680/186/238，wall_sec=335.9/343.4。lane4/lane5 子进程均已自然结束，无数值补写或重训；该数值仅为 seed17 family 结果。
- [x] degradation random/family 六状态诊断均完成真实 CUDA 与 full-test 对账：random=431 条/29,308 token，family=238 条/16,184 token；每 split 每状态 1,024 个连续未分箱 token。post PCC/MCRMSE 均与源 result 一致，pre 为 seed201 参考头，family cluster 三方零重叠。双 split PNG/PDF、6,144 行坐标、两份 aligned NPZ、六份 diagnostic/manifest 和 combined metadata 已下载生成；本地四方对账、canonical digest、checkpoint/CUDA proof、色轴与图像检查全部通过。显示色轴为合并样本 1–99 百分位，极值饱和并保留 raw range，不改原始标签或指标。
- [x] degradation 已作为演示顺序第 14 页加入 PPT，全稿 26 页；新增 slide26/rId32 与媒体。`add_mechanism_slide.py` 支持后续 SpliceAI 插到其前、SSI 插到其后，不因上游训练时长阻塞已完成页面。ncRNA 剩余任务数同步为 2；原包条目除 presentation/rels/content types、slide8 与新增文件外逐字节不变，第 9/14 页实际渲染通过。当时 26 页 PPT SHA256=`e2b1c34bfb4187e5410f52040060c38a136a456a7305dcc6a770bb9460943143`。
- [x] SSI 已作为演示顺序第 15 页加入 PPT，全稿 27 页；新增 slide27/rId33 与媒体。ncRNA 剩余任务数同步为 1。random 的 record-level identity 与 family cluster 证据均已核对，第 9/14/15 页实际渲染通过。当时 27 页 PPT SHA256=`ef96a2ed51ac661baea0cb4cc9f9e0cef95d2c82ba086aa8aace97cb3499849c`。
- [x] SpliceAI 已插入 SSP 后、degradation 前，形成第 14/15/16 页=SpliceAI/degradation/SSI，全稿 28 页。SpliceAI 双 split 共 6,342 行坐标，macro/micro、B20、三分类 softmax、六状态 manifest 与 checkpoint 均通过对账。ncRNA 页改为“8 任务机制图已补齐（seed17）”，首次副标题换行裁切已缩短并复核。当前 PPT SHA256=`26a6fdd7b030bd3789ffa83952ec20a8df59d4f7e08e18665186f7f1fd5878e2`。
- [x] 8 个任务的 random/family 双 split、pre/LoRA/full 三状态机制图全部完成，源 16 格与全部诊断均 complete。该完成范围仅为 RiNALMo-micro、seed17 的描述性诊断；结论②–⑤的三种子、LR、rank、数据量和成本矩阵继续按后续任务执行，不将 t-SNE 结构写成机制因果。
- [x] 最终 28 页 PPT、PDF、三张双 split 图、combined metadata、生成脚本和最新交接文档已统一备份到 `/teams/.../delivery/20261027/`。远端 PPT SHA256=`26a6fdd7b030bd3789ffa83952ec20a8df59d4f7e08e18665186f7f1fd5878e2` 与本地一致；8 任务机制图的原始 artifacts 继续保留在各 `/teams/.../artifacts/` 目录。
- [~] SSI random 首次 lane6/lane7 在训练前被 sequence-overlap 断言中止，未产生 result/checkpoint，不计失败科学结果。真实 parquet 审计：train=14,049、test=3,095，train/test 内同序列额外记录=15/2，24 个重复组全部标签不同，故禁止 dedup。按 spec §10.20.16 改为 sequence-hash 整组 holdout，并在诊断中使用 `sequence_hash:occurrence` 记录级 ID；official test 全量保留，MCRMSE 按记录等权。修复提交 `5862cd7`，本地全仓 384 tests、远端 focused 105 tests 通过；远端全仓另有 3 个未改动 E6 队列测试失败，未记为全绿。
- [x] 真实 SSI manifest 验收通过：train/val/test=12,645/1,404/3,095，train+val=14,049，test 唯一序列=3,093，记录级 token=309,500，sample=1,024，record/token ID 均唯一，三侧 sequence-hash 零重叠。degradation 既有 manifest/hash 不变。GitHub `rnaft-expansion-20261027` 已通过 API fast-forward 到 `34d41fc968daa2c9f7b259cadd1eef28352339c1`，tree 与本地 `5862cd7` 完全一致。
- [x] 补充提交 `362a0f3` 已将 SSI random post 的 sequence-grouped data evidence 和记录级 identity 设为三状态强制门禁，旧 checkpoint 不得仅凭 PCC/MCRMSE 相同进入诊断。新增缺失 evidence、未匹配 evidence 和 record-count 失败测试；本地全仓 385 tests、远端 focused 106 tests 通过。GitHub 分支已 fast-forward 到 `30faeaa3734ad0613ec1ed7ac4af5bb94f75f3e0`，tree 与本地提交一致。
- [x] SSI random 两源格均通过 complete proof：LoRA PCC=0.635053970，full PCC=0.633022960，均 best_epoch=0；full MCRMSE=0.213037429，n_train/n_val/n_test=12,645/1,404/3,095。两格 result 均含修复后的 `data_evidence`：sequence-hash 分组、同序列额外记录 15/2、output rows 和 status=OK。post 诊断继续核验记录级 full-test 对账。
- [x] SSI random pre/LoRA/full 三状态诊断均完成：3,095 条 test 记录、3,093 个唯一序列、309,500 个有效 token；每状态 1,024 个连续 token。LoRA PCC/MCRMSE=0.635053970/0.213841374，full=0.633022961/0.213037428，均与源 result 一致。post 均为 `matched_reconstructed_sequence_grouped_split`，record/token ID 唯一，MCRMSE 按记录等权。本地 aligned/CSV/metadata/diagnostic/manifest 四方对账、canonical digest、checkpoint/CUDA proof 和图像检查通过；family 未完成前不生成双 split 图或 PPT 页。
- [x] SSI family LoRA 已通过 complete proof：PCC=0.598603978、MCRMSE=0.216957862，best_epoch=0，n_train/n_test=13,596/1,881，wall_sec=1,728.6。
- [x] SSI family full 已通过 complete proof：PCC=0.598510291，best_epoch=0；三状态诊断已完成，见下方并行诊断记录。
- [x] SSI family 三状态由独立 PID 1795478 并行完成，parent PID 1678137 已在 finally 中恢复为 S 状态，无重复诊断。family full-test=188,100 个有效 token，每状态 1,024 个连续 token；LoRA PCC/MCRMSE=0.598603978/0.216957862，full=0.598510289/0.216981530，均与源 result 一致。SpliceAI family full 随后继续执行。
- [x] degradation 双 split 图、PDF、combined metadata、更新后的回归图构建器、页面顺序门和最新交接记录已同步至 `/teams/.../delivery/20261027/`；本地原始坐标、aligned NPZ、六状态 diagnostic/manifest 均保留。
- [~] 自动绘图接力器 `/tmp/rnaft_perbase_plotting.py` 已以 PID 1716900 启动；degradation random/family 与 SSI random 均已输出正式单 split 图，SpliceAI family 与 SSI family 仍在等待真实诊断 proof。字体日志中的 Microsoft YaHei/Arial fallback 仅影响服务器 Matplotlib 查找，图内英文使用可用 DejaVu Sans，PPT 正文仍固定 Microsoft YaHei。
- [~] 自动接力器 `/tmp/rnaft_launch_perbase_mechanism_remaining.py` 已部署并以 PID 1678137 启动，使用独立 fcntl 锁，仅在对应 split 的 LoRA/full 源格均 complete 后顺序运行 pre/LoRA/full；覆盖 SpliceAI family、degradation random/family、SSI random/family。每个诊断独立等待 3 GiB 可用显存，失败即停止并保留证据，不自动重试或覆盖成功产物。2026-10-27T17:22:08Z 复核 PID 存活且日志更新时间持续前进；degradation random/family 与 SSI random 已于随后完成，SpliceAI family 与 SSI family 继续按 proof 等待。
- [x] 此前 25 页 PPT、PDF、patch 脚本及计数修订时的 spec/tasks/PPT/绘图索引已上传 `/teams/.../delivery/20261027/`；当时远端 PPT SHA256 与本地 `66ca40e7a36dd515c5e55c604c69b770a5dbb9c1b8d8b0ea12d51b79d66f79bc` 完全一致。26 页版本见上方 degradation 记录。
- [x] 本节 L 新增的 LoRA ledger 修复、自动接力器、回归复审与图构建器记录，以及 tasks/PPT 交接文档、`build_mechanism_spliceai_compare.py`、`build_mechanism_regbase_compare.py`、`add_spliceai_slide.py` 和后续新增的 `add_regbase_slide.py`，通过单次 tar-over-SSH 连接分批同步到 `/teams/.../delivery/20261027/`。该连接同时完成远端 proof/诊断日志审计；未采用多连接高频重试。

## M. 2026-10-27 complementary 辅助队列与后续矩阵

- [~] complementary 初次审计 324 格中 85 complete、238 runnable、1 running、0 conflict；MRL/modification 的剩余格主要是其他官方模型 frozen 臂。审计时可用显存约 23.121 GiB。为避免主队列模型锁造成空闲，新增通用单格辅助启动器，要求原 registry 不变、目标 proof=runnable、主 busy child 非僵尸、无同目标/同 lane 的 expansion_queue 进程、显存大于 need_gb+1。
- [~] 已启动 MRL frozen 辅助格：RiNALMo-mega（PID 1843968/child 1844013）、ERNIE-RNA（1844608/1844653）和 RNA-FM（1847722）random seed17；另启动 modification RiNALMo-mega frozen random seed17（1848093）。四次启动前可用显存分别为 19.700、17.918、19.519、17.543 GiB，均通过唯一性与显存门禁，主队列后续须凭 ledger/proof 跳过。前两格已确认真实 CUDA 训练，其余格待核，不把启动数当完成数。
- [x] MRL random frozen 辅助格已验收：RiNALMo-mega Pearson r=0.714878899（best_epoch=3，wall_sec=492.8），ERNIE-RNA r=0.739172931（best_epoch=6，wall_sec=560.0），均 n_train/n_val/n_test=20,000/7,600/7,600 且 CUDA proof complete。RNA-FM random 随后完成 r=0.672911969（best_epoch=10，wall_sec=843.0），mega family 完成 r=0.617894603（best_epoch=2，wall_sec=508.0）；modification mega random frozen 完成 AUC=0.666643478（best_epoch=0，wall_sec=362.0），RNA-FM modification random frozen 完成 AUC=0.617791304（best_epoch=0，wall_sec=373.1）；ERNIE-RNA MRL family 完成 r=0.649343209（best_epoch=3，wall_sec=495.8），RNA-FM MRL family 完成 r=0.607432235（best_epoch=10，wall_sec=881.2）；ERNIE-RNA modification random 完成 AUC=0.839182609（best_epoch=3，wall_sec=534.7），均通过 proof。
- [~] 新增四类辅助格：ERNIE modification random（1854798）、ERNIE MRL family（1854974）、RNA-FM MRL family（1855137）、RNA-FM modification random（1855312）。启动前可用显存分别为 24.432、22.726、20.788、19.045 GiB，均通过唯一性与显存门禁。RNA-FM modification、ERNIE modification 和三个模型的 MRL family 均已完成。后续继续补齐其他官方模型的 family 和正式 seeds，不把辅助队列启动数当作完成数。
- [x] modification family frozen 三模型已完成并验收：mega AUC=0.643745170（best_epoch=0，wall_sec=1019.6），ERNIE-RNA AUC=0.786964569（best_epoch=3，wall_sec=1140.9），RNA-FM AUC=0.612595314（best_epoch=0，wall_sec=825.2）。三格均 n_train/n_val/n_test=20,000/30,901/30,904，proof=complete、CUDA=True；原启动 PID 1859906/1860144/1860358 均已自然退出，无重复训练。
- [x] 已重新导出并下载 `frozen_mrl_mod_results_20261027.csv`，现含 24 条唯一 RID，MRL random/family 各 6 条、modification random/family 各 6 条。三轮校验分别通过：①24 个唯一 RID 与唯一 model/task/split/seed 键、有限数值；②全部 proof=complete、CUDA=True、bestval_v1，MRL=`PEARSON_R`、modification=`AUC`；③新增三个 family 结果与原始导出逐值一致。SHA256=`0f39742151de99a128f1dd51d6d17fd662515bac380b71de90443ec06b4e57bd`。
- [~] 该表仍只汇总 frozen；registry 已含 mega/ERNIE-RNA/RNA-FM/RiNALMo-650M 的 seed29/43 与 RiNALMo-650M seed17 待补格。后续按 proof、显存和防重合同推进正式 seeds，并继续补 LoRA/full；不得把 seed17 frozen 双 split 结果写成跨模型不坍缩或最终 C5 结论。
- [x] `ft_rinalmomega_mrl_frozen_s29_random_bestval_v1` 已完成验收：Pearson r=0.716525044，best_epoch=4，wall_sec=551.5，n_train/n_val/n_test=20,000/7,600/7,600，proof=complete、CUDA=True。原 lane=`aux_mrl_mega_frozen_s29_random`，启动前 free=23.121 GiB；runner 曾在 nvidia-smi 以 PID 1872124 实占 1,416 MiB，训练后自然退出。原始表扩为 25 条，SHA256=`5b6d1eb9bf8c61aaddba4233e6264e3e86696de0b1cfe2a6e55c665588032785`；三轮校验通过，不把单格结果扩写为最终 C5 结论。
- [x] `ft_rinalmomega_mrl_frozen_s43_random_bestval_v1` 已完成验收：Pearson r=0.725252177，best_epoch=6，wall_sec=690.4，n_train/n_val/n_test=20,000/7,600/7,600，proof=complete、CUDA=True。原 queue/runner PID=1878279/1878314，runner 曾在 nvidia-smi 实占 1,416 MiB，训练后自然退出。mega MRL random frozen 三种子为 0.714878899/0.716525044/0.725252177，均值=0.718885373、样本 SD=0.005574907；原始表扩为 26 条，SHA256=`11435e21934874ec12bc705ed62c325abedf630fd3a1763c5a4f627a70ec679b`。该统计只描述 frozen random，不替代 LoRA/full 或 family 结论。
- [x] `ft_rinalmomega_mrl_frozen_s29_family_bestval_v1` 已完成验收：Pearson r=0.655444593，best_epoch=5，wall_sec=601.9，n_train/n_val/n_test=20,000/9,152/9,150，proof=complete、CUDA=True。原 queue/runner PID=1883479/1883519，启动前 free=17.824584961 GiB，runner 曾在 nvidia-smi 实占 1,316 MiB。原始表扩为 27 条，SHA256=`dc2ef2c1f3b492e91b9a2cbd121067de6461f79dd0e1cb757865fdd7976952dc`；三轮校验通过，仍不将 frozen 部分矩阵写成最终 C5 结论。
- [x] `ft_rinalmomega_mrl_frozen_s43_family_bestval_v1` 已完成验收：Pearson r=0.640747396，best_epoch=6，wall_sec=658.8，n_train/n_val/n_test=20,000/9,152/9,150，proof=complete、CUDA=True。原 queue/runner PID=1893331/1893377，runner 曾在 nvidia-smi 实占 1,416 MiB。mega MRL family frozen 三种子为 0.617894603/0.655444593/0.640747396，均值=0.638028864、样本 SD=0.018922031；结合 random 组，mega MRL 双 split frozen 三种子均已闭合。原始表扩为 28 条，SHA256=`5b164a613b146644ba8cea763e24f60e50eb6a9fe28600cafba34aa7cd4382fd`。该统计不替代 LoRA/full 矩阵。
- [x] `ft_rinalmomega_modification_frozen_s29_random_bestval_v1` 已完成验收：m6A AUC=0.667686957，best_epoch=0，wall_sec=424.5，n_train/n_val/n_test=20,000/3,598/1,200，proof=complete、CUDA=True。原 queue/runner PID=1905060/1905162，runner 曾在 nvidia-smi 实占 1,518 MiB。原始表扩为 29 条，SHA256=`070daa64e092b4160d06ce72a610b9d2d93e5894514c66b660c96a13638bf4cf`；三轮校验通过。
- [x] `ft_rinalmomega_modification_frozen_s43_random_bestval_v1` 已完成验收：m6A AUC=0.662973913，best_epoch=0，wall_sec=375.5，n_train/n_val/n_test=20,000/3,598/1,200，proof=complete、CUDA=True。原 queue/runner PID=1918444/1918503，runner 曾在 nvidia-smi 实占 1,518 MiB。mega modification random frozen 三种子为 0.666643478/0.667686957/0.662973913，均值=0.665768116、样本 SD=0.002475457；原始表扩为 30 条，SHA256=`e3852b151e2b6dd62b8b53cf1990ffb70e80e8d07484c1c044ca6a9f405de971`。该统计仅描述 frozen random，不替代 family 或 LoRA/full 结论。
- [x] `ft_rinalmomega_modification_frozen_s29_family_bestval_v1` 已完成验收：m6A AUC=0.640533130，best_epoch=0，wall_sec=796.4，n_train/n_val/n_test=20,000/30,901/30,904，proof=complete、CUDA=True。原 queue/runner PID=1938204/1938269，runner 曾在 nvidia-smi 实占 1,518 MiB。原始表扩为 31 条，SHA256=`f90ddb96566754d069a390bd89f45cdce0577abe6ba732ac4e9495c1f657d0c1`；三轮校验通过。
- [x] `ft_rinalmomega_modification_frozen_s43_family_bestval_v1` 已完成验收：m6A AUC=0.643692441，best_epoch=0，wall_sec=751.6，n_train/n_val/n_test=20,000/30,901/30,904，proof=complete、CUDA=True。原 queue/runner PID=1956164/1956214，runner 曾在 nvidia-smi 实占 1,518 MiB。mega modification family frozen 三种子为 0.643745170/0.640533130/0.643692441，均值=0.642656914、样本 SD=0.001839440；结合 random 与 MRL 结果，mega 两任务双 split frozen 三种子全部闭合。原始表扩为 32 条，SHA256=`de974c0417120158594e3eaaf216ef2ca97815a9756d9c37956214486dca891d`。
- [x] `ft_ernierna_modification_frozen_s29_random_bestval_v1` 已完成验收：m6A AUC=0.649582609，best_epoch=0，wall_sec=268.8，n_train/n_val/n_test=20,000/3,598/1,200，proof=complete、CUDA=True。原 queue/runner PID=1964503/1964532，runner 曾在 nvidia-smi 实占 1,458 MiB。原始表扩为 33 条，SHA256=`b973ed82d30bc07ba9c25f2ac5b58c724338be38aaea1b05a8fa8330adc83650`。
- [x] `ft_ernierna_modification_frozen_s43_random_bestval_v1` 已完成验收：m6A AUC=0.757217391，best_epoch=2，wall_sec=347.9，n_train/n_val/n_test=20,000/3,598/1,200，proof=complete、CUDA=True。原 queue/runner PID=1965898/1965924，runner 曾在 nvidia-smi 实占 1,458 MiB。原始表扩为 34 条，SHA256=`d179894f7b538896d1b78239101c44ab12bf4bb9c5361a74da8c89fc642f9ffb`。
- [x] ERNIE-RNA modification random 三种子及 plateau 核查完成：seed17/29/43 AUC=0.839182609/0.649582609/0.757217391，均值=0.748660870、样本 SD=0.095089172；best_epoch 分别为 3/0/2。seed29 后续最大 validation 改善 0.007463，seed43 在 epoch4 的 validation=0.199930、相对 best_val=0.206492 改善 0.006562，seed17 后续最大改善 0.007974，三者均低于 `abs_floor=0.008`，故保留各自较早 best checkpoint。AUC 与 best_epoch 同向是早停/checkpoint 敏感性的诊断线索，不是因果证明，也不能据此断言评测实现错误。独立早停协议尚未启动，正式结果不重选、不改写。
- [x] `ft_ernierna_modification_frozen_s29_family_bestval_v1` 已完成验收：m6A AUC=0.781949649，best_epoch=3，wall_sec=935.3，n_train/n_val/n_test=20,000/30,901/30,904，proof=complete、CUDA=True。原 queue/runner PID=1968701/1968746，runner 曾在 nvidia-smi 实占 1,238 MiB。
- [x] `ft_ernierna_modification_frozen_s43_family_bestval_v1` 已完成验收：m6A AUC=0.782921568，best_epoch=3，wall_sec=929.3，n_train/n_val/n_test=20,000/30,901/30,904，proof=complete、CUDA=True。原 queue/runner PID=1970385/1970410，runner 曾在 nvidia-smi 实占 1,238 MiB。family 三种子为 0.786964569/0.781949649/0.782921568，均值=0.783945262、样本 SD=0.002659571，全部 best_epoch=3；与 random 的大幅波动相比，异常具有明显 split/checkpoint 依赖性，不能概括为 ERNIE-RNA 整体失效。原始表扩为 36 条，SHA256=`75db13784e29a2743b32b740a98dbc27362c5163b1c94f31b6bc71f49043e11c`。
- [x] `ft_rnafm_modification_frozen_s29_random_bestval_v1` 已完成验收：m6A AUC=0.620069565，best_epoch=0，wall_sec=245.4，n_train/n_val/n_test=20,000/3,598/1,200，proof=complete、CUDA=True。原 queue/runner PID=1974323/1974349，runner 曾在 nvidia-smi 实占 1,234 MiB。该值与 seed17=0.617791304 接近，原始表扩为 37 条，SHA256=`6115ab21071cf307d26acf4d033bd7a3d20984b7c2c4c8b7236c714d203f5cc5`；三轮校验通过。
- [x] `ft_rnafm_modification_frozen_s43_random_bestval_v1` 已完成验收：m6A AUC=0.626765217，best_epoch=0，wall_sec=269.6，n_train/n_val/n_test=20,000/3,598/1,200，proof=complete、CUDA=True。原 queue/runner PID=1976823/1977248，runner 曾在 nvidia-smi 实占 1,234 MiB。RNA-FM modification random 三种子为 0.617791304/0.620069565/0.626765217，均值=0.621542029、样本 SD=0.004664643；原始表扩为 38 条，SHA256=`81494e7f2401ae1c3e6072aae747bc1d09a59287a0464d7c63f57a2462d96868`。
- [x] `ft_rnafm_modification_frozen_s29_family_bestval_v1` 已完成验收：m6A AUC=0.608897135，best_epoch=0，wall_sec=515.7，n_train/n_val/n_test=20,000/30,901/30,904，proof=complete、CUDA=True。原 queue/runner PID=1978901/1978938，runner 曾在 nvidia-smi 实占 1,234 MiB。
- [x] `ft_rnafm_modification_frozen_s43_family_bestval_v1` 已完成验收：m6A AUC=0.610150277，best_epoch=0，wall_sec=579.7，n_train/n_val/n_test=20,000/30,901/30,904，proof=complete、CUDA=True。原 queue/runner PID=1981154/1981188，runner 曾在 nvidia-smi 实占 1,234 MiB。RNA-FM modification family 三种子为 0.612595314/0.608897135/0.610150277，均值=0.610547575、样本 SD=0.001880829；结合 random 结果，RNA-FM modification 双 split frozen 三种子全部闭合。原始表扩为 40 条，SHA256=`e58894334a59d5735f03b3637c0cf9856812564a91572db74f58fbbec827a1ca`。
- [x] `ft_ernierna_mrl_frozen_s29_random_bestval_v1` 已完成验收：Pearson r=0.738159691，best_epoch=7，wall_sec=486.7，n_train/n_val/n_test=20,000/7,600/7,600，proof=complete、CUDA=True。原 lane=`aux_mrl_ernie_frozen_s29_random`，queue PID=1986230。曾在导出前观察到 queue/runner 退出，按中断预案核查而未重启；随后 result/plateau/proof 复核为 complete，确认只是导出与收尾时间差，未重训。原始表扩为 41 条，SHA256=`60fcf6ea90a8a25b90ccc304bc57f30855e50187eab0b793947943d3f5010c96`。
- [x] `ft_ernierna_mrl_frozen_s43_random_bestval_v1` 已完成验收：Pearson r=0.715971878，best_epoch=2，wall_sec=278.6，n_train/n_val/n_test=20,000/7,600/7,600，proof=complete、CUDA=True。原 queue/runner PID=1993073/1993108，runner 曾在 nvidia-smi 实占 1,256 MiB。ERNIE-RNA MRL random 三种子为 0.739172931/0.738159691/0.715971878，均值=0.731101500、样本 SD=0.013112428。
- [x] `ft_ernierna_mrl_frozen_s29_family_bestval_v1` 已完成验收：Pearson r=0.652511131，best_epoch=5，wall_sec=404.1，n_train/n_val/n_test=20,000/9,152/9,150，proof=complete、CUDA=True。原 queue/runner PID=1995345/1995382，runner 曾在 nvidia-smi 实占 1,256 MiB。原始表扩为 43 条，SHA256=`5599a5a2781157e46a52d792ec7da7480c02dfdcd283530414f119f88182d80a`；三轮校验通过。
- [x] `ft_ernierna_mrl_frozen_s43_family_bestval_v1` 已完成验收：Pearson r=0.653755249，best_epoch=5，wall_sec=469.6，n_train/n_val/n_test=20,000/9,152/9,150，proof=complete、CUDA=True。原 queue/runner PID=1998655/1998704，runner 曾在 nvidia-smi 实占 1,256 MiB。ERNIE-RNA MRL family 三种子为 0.649343209/0.652511131/0.653755249，均值=0.651869863、样本 SD=0.002274850；结合 random 结果，ERNIE-RNA MRL 双 split frozen 三种子全部闭合。原始表扩为 44 条，SHA256=`71bdf14b486eb8ed8003ffa926884fae926c9563f15c3fa6839891a0b01949d7`。
- [x] `ft_rnafm_mrl_frozen_s29_random_bestval_v1` 已完成验收：Pearson r=0.674587637，best_epoch=10，wall_sec=658.3，n_train/n_val/n_test=20,000/7,600/7,600，proof=complete、CUDA=True。原 queue/runner PID=2023540/2023590，runner 曾在 nvidia-smi 实占 1,154 MiB。该值与 seed17=0.672911969 接近，原始表扩为 45 条，SHA256=`cd40793dd0b27ad561057657ba9cdbb1360623cbf921ee09389371fb0671243d`；三轮校验通过。
- [x] `ft_rnafm_mrl_frozen_s43_random_bestval_v1` 已完成验收：Pearson r=0.668243497，best_epoch=10，wall_sec=637.1，n_train/n_val/n_test=20,000/7,600/7,600，proof=complete、CUDA=True。原 queue/runner PID=2040118/2040173，runner 曾在 nvidia-smi 实占 1,276 MiB。RNA-FM MRL random 三种子为 0.672911969/0.674587637/0.668243497，均值=0.671914368、样本 SD=0.003287618。
- [x] `ft_rnafm_mrl_frozen_s29_family_bestval_v1` 已完成验收：Pearson r=0.604613275，best_epoch=9，wall_sec=625.1，n_train/n_val/n_test=20,000/9,152/9,150，proof=complete、CUDA=True。原 lane=`aux_mrl_rnafm_frozen_s29_family`，queue PID=2049748。原始表扩为 47 条，SHA256=`70877d2a226d2746791b5847ba4e59e99cf090012b31feddb8dacfe47fe76f72`；三轮校验通过。
- [x] `ft_rnafm_mrl_frozen_s43_family_bestval_v1` 已完成验收：Pearson r=0.609191364，best_epoch=10，wall_sec=719.8，n_train/n_val/n_test=20,000/9,152/9,150，proof=complete、CUDA=True。原 queue/runner PID=2074160/2074205，runner 曾在 nvidia-smi 实占 1,276 MiB。RNA-FM MRL family 三种子为 0.607432235/0.604613275/0.609191364，均值=0.607078958、样本 SD=0.002309400；结合 random 结果，RNA-FM MRL 双 split frozen 三种子全部闭合。原始表扩为 48 条，SHA256=`3a3737e9ea3cef0ee50f4f1e7692a0c922face27b1a3e42797d1a8ed8d61376b`。
- [x] 至此 RiNALMo-micro、RiNALMo-mega、ERNIE-RNA、RNA-FM 的 MRL 与 modification 双 split frozen 三种子均完成完整 proof 验收，共 48 个唯一 RID。该范围仅限 frozen，不替代 LoRA/full 或 RiNALMo-650M。
- [~] 已按同一 launcher 评估 `ft_rinalmo650m_mrl_frozen_s17_random_bestval_v1`：need_gb=28，实测 free=23.355773926 GiB，未达到 28+1 GiB 门禁，启动器在创建 registry/state-dir 前拒绝启动。未强行降预算、未绕过门禁、未产生完成结果；待其他正式任务释放显存后再试。
- [x] MRL LoRA/full 双 registry 对账完成，60 格唯一账目为 53 个 root-complete 待处理、1 个 teams 原生 complete、6 个 650M full runnable。迁移脚本先校验完整文件清单和 SHA256，再要求 teams complete proof，最后才将 root 实体目录替换为 symlink；最终 41 格 `migrated_and_linked`、12 格 `already_linked`，迁移 31,252,133,777 bytes。独立三轮审计通过：60 格不重不漏，53 个 symlink 与 82 项 result/checkpoint 哈希一致，teams 为 54 complete+6 runnable（LoRA30/full24）。manifest=`/teams/.../status/migrations/mrl_lora_full_root_to_teams_20261028.json`，audit 为同名 `.audit.json`；没有重训或覆盖既有科学结果。
- [x] `ft_rinalmomega_mrl_full_s17_random_lr1e-05_bestval_v1` 已在 teams 原生完成并通过完整验收：Pearson r=0.795497960，n_train/n_val/n_test=20,000/7,600/7,600，best_epoch=0、stale_epochs=3、stop_reason=`validation_no_improvement_patience`，wall_sec=552.4，CUDA=True（RTX 5090/CUDA 12.8），`acceptance_eligible=true`。该格只补全 mega full 的一个正式种子，不能替代双 split 三种子统计。
- [~] `ft_rinalmo650m_mrl_full_s17_random_lr1e-05_bestval_v1` 再次按门禁评估，free=23.332336426 GiB、need_gb=28，未达到 29 GiB，启动在创建辅助 registry/state-dir 前被拒绝；其余五个 650M full 格同样保持 runnable，不补零、不写成 pending 数值。
- [~] 已并行启动 `ft_rinalmomicro_modification_lora_s17_random_bestval_v1` 与 seed29 对应格，queue/runner PID 分别为 2110919/2110946、2111000/2111040；启动前 free=23.332/22.349 GiB，need_gb=8，两个 runner 均在 nvidia-smi 实占 2,396 MiB。当前仅有真实 CUDA 运行证据，尚无 result/complete proof，不计完成、不进入均值。

## N. 2026-10-28 导师汇报续接：现行执行清单

> 本节是本轮后续工作的直接入口；A–M 保留为历史执行证据。实时完成数只能由 registry+ledger+result+checkpoint+runtime 重新计算。当前采用 28 页阶段修订版，不回滚到用户指定的旧 20 页本地文件，也不覆盖原文件。

### N0. 已核验，禁止重复执行

- [x] 通读当前交接文档与历史相关记录，确认 8 任务官方分类为 3+1+2+2；旧“每类两个”和 per-base m6A 口径废止。
- [x] 任务地图已在 28 页版第 4 页；8 任务双 split 三状态机制图已在第 9–16 页，范围仅为 RiNALMo-micro、seed17。复用原图、坐标、NPZ 和 metadata，不重跑。
- [x] RiNALMo-micro ncRNA rank8 六格正式复测已完成，random ACC=0.918026±0.009421、family ACC=0.900312±0.005268；后续只做协议差异归因，不为追求高分重复训练。
- [x] MRL/modification 四个非 650M 官方模型 frozen 48 格与 MRL LoRA/full 54 个 complete 均可复用；物理路径已迁移，不因旧 root 路径缺失误判为科学缺口。

### N1. P0：实时对账与调度安全

- [x] 单 SSH 主连接核查 RTX5090/CUDA、代码 HEAD、活跃 runner、complementary/MRL-modification/C5c/per-base registry 与 proof；2026-10-28 13:33 审计：complementary=143 complete+181 runnable，MRL/modification=104 complete+76 runnable，C5c=19 complete+1 running+1996 runnable，per-base 源格=16 complete。输出按 task/model/strategy 分组，未把活跃进程或 registry 大小当完成数。
- [ ] 对在训格逐格核对 RID、命令、batch、need、日志与 CUDA；同名双开先停后派者并保留证据，complete 格只补缺失 ledger/导出，不重训。
- [ ] 仅在有真实 runnable 缺口且 free≥同 batch need+1GiB 时提交辅助 lane；没有安全大格窗口时用小格并行填充，不绕过共享锁或制造 OOM。

### N2. P1：先闭合主矩阵与异常归因

- [ ] 闭合 complementary 官方模型主矩阵，优先 ncRNA/CRISPR/modification/MRL/SSP 的 complete 缺口； corrected per-base 协议与旧 legacy 分表。
- [ ] 闭合 MRL/modification × micro/mega/giga/ERNIE-RNA/RNA-FM × frozen/LoRA/full × 双 split × 3 seeds；650M full 六格只在显存窗允许时执行，650M frozen 同理。
- [ ] ncRNA 归因：在同一 test manifest 核查标签支持、家族映射、预测熵、margin、混淆矩阵、length/GC、head/backbone 与 frozen/random-init 对照；先排除实现/评测问题，再写机制解释。
- [ ] 每批完成执行三轮 result/ledger/proof 对账并记录均值、样本 SD/95% CI、best_epoch、wall/peak 与结论边界。

### N3. P2：结论②③与结论①a 完整图

- [ ] 结论②：8 任务逐一建立 seed101 validation 选 LR 与 17/29/43 正式 default/tuned 配对；真实 LR、split、rank、n_train 与协议必须入表。
- [ ] 结论③：8 任务补齐 LoRA/DoRA/full 与 rank4/8/16；rank8 直接复用 N0 六格，其他格按同模型、同 split、同预算配对。
- [ ] 结论①a：以完整或明确标注部分范围的 8 任务结果重绘同构四柱图；每任务独立 ACC/PR-AUC/AUC/PCC/macro-F1/pair-F1 轴，不把不同指标合并成分数。

### N4. P3：结论⑤b/⑤c/⑤d 与数据量加密

- [ ] C5d：逐点分类未跑/失败/未导出/路径缺失/协议隔离，优先补 mega/giga 真实缺点；pending 不补零、不连线掩盖。
- [ ] C5b：从正式 run 的 wall/peak/checkpoint/runtime 直接导出 8 任务时间×性能，统一模型、split、n、batch、GPU 与停止协议；补 ERNIE-RNA LoRA/full，不沿用跨协议倍数。
- [ ] C5c：接续 2016 格实时账目（13:33 已见 19 complete+1 running，主要为可复用主矩阵点，不重复启动）；1000–3000 间固定补 1500/2000/2500，micro/mega/giga 同协议复测，全量点复用主矩阵，逐 seed+95% CI。新增波次仍服从主矩阵和资源窗口优先级。

### N5. P4：同源数据量等价线

- [ ] RNA-Sc 与 RiNALMo 分家族、分任务绘制 small-full(n) 与 large-LoRA(m)；统一训练/评估预算与 split，逐 seed 计算 closest 等价点和 CI。
- [ ] 图内直接标注“小 full@n ≈ 大 LoRA@m”；无覆盖交点写“当前范围未观测到等价点”，不跨家族拼接、不强行插值。

### N6. PPT、归档与代码交付

- [~] 以 28 页版为底稿逐页核对图文；先修正任务地图 SSP 语义和 m6A 索引表述，再按已过门禁结果更新结论页。保留其他用户手调内容、Microsoft YaHei 与 1.5 倍行距。
- [ ] 每页检查标题—图—图注—前后文一致性；运行 ZIP/XML、markitdown、layout、嵌图哈希和 LibreOffice 实际渲染，发现问题后修复并复验。
- [ ] 交接文档只保留当前入口与必要证据，废弃快照/增量/脚本归档；绘图原数据按 current/archive 分类，保留 RID、来源、协议与生成时间，不删除隔离证据。
- [ ] 每批确认代码在 `/home/cunyuliu/rna-ft-eval` 提交并推送 GitHub；大文件/权威 artifacts 备份到 `/teams/HoulabData_1788502323/liucunyu/rna-ft-eval/`。

## N7. 2026-10-28 傍晚训练、PPT 与代码交付记录

- [x] 17:30 实时 proof：MRL/modification=112 complete+1 running+67 runnable；micro modification LoRA=6/6 complete，full=4 complete+1 running+1 runnable；complementary=147 complete。后续复核 ncRNA micro full 六格均 complete，两个辅助 lane 候选在启动前被 complete/无 runnable 断言拦截，未产生重复训练或伪失败记录。
- [x] modification 非 650M 子注册表 72 格已唯一性和 dry-run 校验，SHA256=`6644dd55ac6add666ef34896ad17c7d0b2c14959888e75707aaf9898abfb1db8`，2 workers 接续。首次错误假设全部为 8GiB 被断言拦截且未启动；实测预算修正为 micro=8、mega/ERNIE/RNA-FM=16、650M=28GiB 后再启动。
- [x] 28 页导师讨论版 PPT 已完成：保留既有任务地图和 8 个 micro/seed17 机制页，重绘 10 张图，移除所有旧 per-base m6A 面板，统一四柱语义、NA/n<3、同任务等价对与资源协议。28 页实际渲染、布局、ZIP/XML、字体、1.5 倍行距、嵌图哈希和未修改页 diff 均通过。
- [x] 参数化绘图脚本本地全量重跑：所有 PNG/CSV 与原图逐字节一致，PDF 仅生成时间元数据不同，页数和尺寸一致；远端 `py_compile` 与 `--help` 通过。`/home` 提交 `b768006`，GitHub `rnaft-expansion-20261027` 提交 `2ab81ab225c59bf4ec551adea7d09365df31680e`。
- [x] 两个旧 launcher 已移至 `/teams/.../status/archive/legacy_launchers/`，不作为当前调度入口；旧图集、历史快照与增量稿已移至 `archive_20261028`，未删除隔离证据。
- [~] 后续只补真实缺口：modification full/mega/ERNIE/RNA-FM、其他官方模型主矩阵、结论②③、C5c/C5d 与同源等价线。650M 大格继续等待 28+1GiB 窗口；当前阶段 PPT 不代表这些矩阵已完成。

## N8. 2026-10-28 最终图刷新与 GPU 接续

- [x] 18:10 实时导出：MRL/modification=115 complete+1 running+64 runnable，原始 CSV SHA256=`78f17a27cfda176662266283b5bfcf93328c0fb7591513d27ab780271bee0221`。PPT 已刷新至该版本，micro modification LoRA 6/6 进入图中，其他模型按 complete 数显示斜线或 NA。
- [~] 18:16 GPU 空闲 18.798GiB，选择 ERNIE-RNA modification LoRA seed17 random（need=16GiB）。首次 main-busy PID 在启动前自然退出，launcher 拒绝且未训练；重新扫描真实活跃 runner 后通过门禁，辅助 lane `aux_mod_ernie_lora_s17_random` PID=2266752 已启动。启动不等于 complete，后续须 result/plateau/ledger/checkpoint/runtime 验收。
- [x] 最终阶段 PPT SHA256=`09853a8cec9557b3b50400e6580527e82909a894d1a13396aa3e0731f7e336b5`，PDF SHA256=`1d44603aecd83ed3337ced7ccde8e08301e868855b5d78afc2ff880095fb8ce9`；绘图源数据 74 文件，manifest SHA256=`a06973d93f314089f666bb5a076867f042e49eadb861f561a10b82d2994b6ce9`。后续更新必须另存新版本，不回写这些验收哈希。

## N9. 2026-10-28 用户复核后的八任务全覆盖执行清单

> 本节是本轮补测与 PPT 交付的逐项核对表，与 spec §10.22 一一对应。先登记完整实验，再依据实时 proof 执行；局部图、单种子、smoke 或 legacy 结果不得替代八任务正式矩阵。

- [x] **P0 实时基线**：已用持久 SSH 主连接核查 CUDA/torch、git、活跃 RID、registry、ledger、result、checkpoint 与 runtime；RTX 5090 + torch 2.11.0+cu128 可用。实时 proof 为 complementary=147 complete/177 runnable、MRL/modification=126 complete/1 running/53 runnable；进程只记在途，不记完成。
- [x] **防返工**：远端 28 页版及 74 文件源包已下载并逐项 SHA256 核验，PPT/PDF/manifest 哈希与交接记录一致；任务地图、第 9–16 页八任务机制图、micro ncRNA rank8 六格均复用。本地 20 页旧版只作用户批注证据，不覆盖新版，不重复新增页面或训练。
- [ ] **结论①a**：八个任务均补 frozen/LoRA/full × random/family × 17/29/43 正式证据，优先官方模型；按结论①a 的三张既有图统一四柱配色、字体、误差与 NA 规则，每任务独立主指标，重绘并放在结论①a 后。
- [ ] **机制图**：复用已完成的 8 任务 × 双 split × pre/Post-LoRA/Post-full（RiNALMo-micro、seed17）表征与坐标；只按 RiNALMo 论文的 CLS/真实标签/独立测试集标注范式检查并重排视觉，不重跑已验收表征抽取，不作因果推断。
- [ ] **结论②**：八任务全部完成 seed101 validation 选 LR 与 17/29/43 default/tuned 正式配对，记录真实 LR、split、rank、n_train 和协议。
- [ ] **结论③**：八任务全部补齐 LoRA/DoRA/full 与 rank4/8/16；micro ncRNA rank8 六格直接复用，旧低值只做协议差异归因，不定向重跑追求高分。
- [ ] **结论④**：RNA-Sc 与 RiNALMo 两个同家族体系 × 八任务绘制 small-full(n) 与 large-LoRA(m)，横轴必须是标注量；逐 seed 给 closest 等价点与 CI，直接标“小 full@n ≈ 大 LoRA@m”，无交点写未观测到。
- [ ] **结论⑤**：八任务补齐同协议学习曲线；MRL/modification 增加其他官方模型对照；ncRNA 先完成标签/家族映射/预测熵/混淆矩阵/length/GC/head/backbone/frozen/random-init 归因，再判断是评测错误还是真实坍缩。
- [ ] **结论⑤d**：逐点分类未跑、失败、未导出、路径缺失和协议隔离；mega/giga 真实缺点优先补齐，pending/NA 不画 0、不用斜线或连线伪装完成。
- [ ] **结论⑤c**：八任务、RiNALMo micro/mega（官方 148M）/giga（650M）补齐 {10,100,1000,1500,2000,2500,3000} 档；重点加密 1000–3000，逐 seed+95% CI，全量点复用主矩阵。
- [ ] **结论⑤b**：时间×性能从单任务扩至八任务，统一模型、split、n、batch、GPU、停止协议；补 ERNIE-RNA LoRA/full，wall/peak/checkpoint 三证直接关联 RID。
- [ ] **并行门禁**：在主队列与生命周期锁内按实时 runnable 缺口和同 batch 实测 need+1GiB 提交辅助 lane；running 不双开、complete 不重训，CUDA 不可用或 CPU 静默降级立即停止并留证，不为占满显存绕过科学门禁。
- [ ] **批次记录**：每批保存命令、git SHA、GPU/CUDA、seed、数据 manifest、逐 epoch train/val、best/stop、wall/peak/checkpoint、result/RID、三轮对账和结论边界；确认后的代码提交 `/home/cunyuliu/rna-ft-eval` 并推送 GitHub，大文件备份至 `/teams/HoulabData_1788502323/liucunyu/rna-ft-eval/`。
- [ ] **PPT 与图文**：只改目标页，保留用户手调内容；任务地图解释后续任务与指标，机制页承接结论①a，结论②–⑤按证据顺序衔接。每页核对标题、图、图注、数值和前后文，Microsoft YaHei、正文 1.5 倍行距，另存新修订版。
- [ ] **归档**：交接文档仅保留当前入口与必要证据，废弃快照/增量/脚本先核引用再归档；绘图原数据按 current/archive 分类，保留原始 CSV/JSON、RID、协议、脚本、metadata、PNG/PDF 和 manifest，不删除隔离证据。
- [ ] **最终验收**：所有阶段未达合同不得写成最终科学结论；ZIP/XML、markitdown、layout、嵌图哈希、LibreOffice 渲染和未修改页 diff 全部通过后才交付。

## N10. 2026-10-28 夜间训练与 ncRNA 归因记录

- [x] 持久 SSH 主连接已建立，避免高频重连；CUDA 实测为 `torch=2.11.0+cu128`、`cuda_available=True`、RTX 5090。代码基底 `/home/cunyuliu/rna-ft-eval` HEAD=`b768006`，正式大文件继续留 `/teams/HoulabData_1788502323/liucunyu/rna-ft-eval/`。
- [x] `ft_ernierna_noncodingrnafamily_lora_s17_random_bestval_v1` 已完成：ACC=0.920745921，best_epoch=2，epochs_trained=6，best_val=0.229988，wall=426.8s，peak=1927.8MiB；train/val/test=6858/857/858，三侧序列零重叠、13 类支持齐全、CUDA 证据完整。该格只用于 random 主矩阵，不外推 family 结论。
- [~] 已启动 `ft_ernierna_noncodingrnafamily_lora_s29_random_bestval_v1` 辅助车道，need=16GiB；启动前通过 runnable、防重与 free≥need+1GiB 门禁，完成前不写统计结论。
- [x] ncRNA 旧/新数据同源核验：当前与 orico 备份 `family_splits/noncoding-rna-family.parquet` SHA256 均为 `b5197c38a3a2b6580d3959749c174fe37da98045a9cb6dab174e3154a4272268`；train/val/test=6859/858/856，label×cluster 为 7731/7731 一一对应，排除“换了家族文件”解释。
- [x] 发现旧训练顺序风险：family train 仅 134 个 label run/6859 行，最长同类连续段 375，首 320 行全为 label8；旧 `finetune_one` 没有逐 epoch shuffle。现行 `6a4ec2a` 已加入全局 seed 与 per-epoch shuffle。旧 LoRA-family seed17=0.084112，当前 shuffled best-val 三种子=0.894860/0.905374/0.900701，最佳 epoch 均为 9，不能只用早停解释。
- [x] 为做受控归因，在 `finetune_one` 与 `finetune_clf` 增加默认关闭的 `--no-epoch-shuffle` 诊断开关、`--out-suffix` 和 `epoch_shuffle` 元数据；默认正式行为不变，两次全仓测试均为 385 passed。第一次因 registry 指向 `finetune_clf` 而只部署了 `finetune_one`，argparse 在训练前退出、无结果；补齐正确 runner 后重新通过 385 项测试再启动，未把失败记为科学结果。
- [x] `ft_rinalmomicro_noncodingrnafamily_lora_s17_family_bestval_v1_noshuffle_diag` 已完成且 proof=complete：ACC=0.059579，best_epoch=0，4 epochs 后停止，train/val/test=6859/858/856，序列与 cluster 三侧重叠均为 0，CUDA=True、`epoch_shuffle=false`。第三轮参数复核发现该格使用 `finetune_clf` 默认 max_len=128，而 rank8 对照为 `finetune_one` max_len=512，因此只作为跨 runner 强支持证据，不作为唯一严格因果对照，不进入正式均值。
- [x] 严格对照 `ft_rinalmomicro_noncodingrnafamily_lora_s17_family_bestval_v1_noshuffle_one_diag` 已完成且 proof=complete：`finetune_one`、max_len=512、batch=32、rank8、seed17、family、LR=3e-4、best-val 均与 shuffled 对照一致，仅 `epoch_shuffle=false`。ACC=0.095794（shuffled=0.894860），best_epoch=0，4 epochs 后 validation patience 停止，wall=248.9s，peak=8474.8MiB，CUDA=True。由此确认：在该受控设置下，未 shuffle 足以复现旧近随机表现；旧 pre-shuffle ncRNA family 及派生图按 spec §10.23 隔离，不能写成真实跨家族机制。
- [x] `ft_ernierna_noncodingrnafamily_lora_s29_random_bestval_v1` 已完成：ACC=0.937062937，best_epoch=6，epochs_trained=10，best_val=0.178471，wall=726.7s，peak=1927.8MiB，best.ckpt=348350539 bytes，acceptance_eligible=True。
- [x] `ft_ernierna_noncodingrnafamily_lora_s43_random_bestval_v1` 已完成：ACC=0.928904429，best_epoch=4，epochs_trained=8，best_val=0.204824，wall=594.2s，CUDA=True。ERNIE-RNA ncRNA LoRA random 三种子为 0.920746/0.937063/0.928904，mean=0.928904、SD=0.008159；该统计仅限 random，不替代 family。
- [x] `ft_ernierna_noncodingrnafamily_lora_s17_family_bestval_v1` 已完成且 proof=complete：ACC=0.936915888，best_epoch=2，epochs_trained=6，best_val=0.269553，wall=424.9s，peak=1928.1MiB；train/val/test=6859/858/856，序列与 cluster 三侧重叠均为 0、13 类支持齐全、CUDA=True。该 corrected family 结果进一步说明旧近随机值不可外推，但仍需 seed29/43 与其他模型闭合后再统计。
- [x] `ft_ernierna_noncodingrnafamily_lora_s29_family_bestval_v1` 已完成且 proof=complete：ACC=0.915887850，best_epoch=4，epochs_trained=8，best_val=0.309560，wall=582.4s，peak=1928.1MiB，序列/cluster 零重叠、CUDA=True。
- [~] 已启动 `ft_ernierna_noncodingrnafamily_lora_s43_family_bestval_v1`，启动前 free=21.589GiB、need=16GiB；完成后计算 family 三种子统计。
- [x] 已生成并人工检查 `ncrna_shuffle_audit.png/.pdf`、严格 A/B 图源 CSV、逐 epoch 曲线、标签顺序 CSV/JSON；同时重绘 MRL-only Δ/E3/等价图和两张状态图，旧 ncRNA 面板不再进入当前源包。原始严格对照 JSON 与脚本保存在 `交接文档/绘图数据/current/figure_source_data_20261028/`。
- [x] 两个 runner 的诊断变更已单独提交 `/home` 为 `e847cf6`，通过完整 bundle 中转 cherry-pick 到 GitHub `rnaft-expansion-20261027` 为 `6be3497`；未夹带 docs 修改、未强推。

## N11. 2026-10-29 PPT 与源数据交付记录

- [x] 28 页夜间复核版已完成，PPT SHA256=`536b5e4ae5477aed06e07530f772e5b3691f544c4fbfa042fa43fcae04039b9b`，PDF SHA256=`e7a7df980f836b2b7a8daa069f6d81e92326d1c7ba3b8d5a9e4163c583669873`。仅改演示页 2/5/7/17/19/20/21/22/23/24/27/28；任务地图、八任务机制页与其他用户手调内容未改。
- [x] 第 5 页使用严格 A/B 三联图；旧 ncRNA family、Δ、E3、规模谱和等价点全部撤下。MRL-only 页面明确 legacy 边界，⑤c 两张图直接标出数值对并非等价点，④只展示比较协议，⑤d 展示隔离与补测状态。进度页八任务行已恢复页内可见。
- [x] 验收通过：编辑页 layout Issues=0、`fix_pptx.py` 无问题、`pptx_lint.py` PASS、markitdown 逐页复核、未修改页 XML/rels diff 为空、7 张嵌图哈希一致；独立 fontconfig 下微软雅黑中文渲染正常，正文 1.5 倍行距不变。
- [x] 新版源包 revision=`20261029_ncrna_shuffle_quarantine_v1`，现有 95 个登记文件并全部哈希通过，manifest SHA256=`286e19cdd66812ad918c367a66ac1b77952a6e303077b3c76ee3e5daf57ee81b`；第三次独立重跑 7 张核心 PNG 哈希一致。旧图、legacy 输入和基线 manifest 均已归档，未删除实验证据。
- [x] 绘图脚本已在 `/home` 提交 `07248a1` 并推送 GitHub 为 `b105916`；全仓 385 项测试通过，远端独立生成完成，图源 CSV 哈希一致，图像尺寸与内容复核通过。最终 PPT/PDF 与源包已备份到 `/teams/HoulabData_1788502323/liucunyu/rna-ft-eval/delivery/20261029/`。
- [x] 交接根目录已整理为当前 spec/tasks/checklist、PPT 交接、恢复指南、备份总账、模型决策与绘图索引；7 份历史叙述/巡检/预注册材料分别归档至 `archive_20261028/历史叙述与审计/` 与 `历史设计与预注册/`，无 Markdown 链接断链。
- [ ] 后续只在 corrected proof 闭合后更新八任务结论②③④⑤及 C5b/C5c/C5d；当前夜间复核版仍是导师阶段讨论版，不作为全量实验完成声明。

## N12. 2026-10-29 主矩阵续测与调度记录

- [x] 实时 proof 刷新：complementary 已推进至 161 complete+1 running+162 runnable，无 conflict；ncRNA complete 从 36 增至 44。MRL/modification 已推进至 150 complete+30 runnable。
- [x] ERNIE-RNA full random 三种子已闭合：s17=0.933566、s29=0.948718、s43=0.942890，mean=0.941725、SD=0.007643、95% CI half-width=0.018986。full 相比 LoRA random 的描述性增量为 +0.012821，相比 frozen random 为 +0.024087；仅限当前协议，不作普适排序。
- [x] `ft_ernierna_noncodingrnafamily_full_s17_family_lr1e-05_bestval_v1` 已完成：ACC=0.927570094，best_epoch=5，epochs_trained=9，best_val=0.353458，wall=608.5s，peak=2892.1MiB；序列/cluster 零重叠、CUDA=True，未出现旧近随机低值。
- [x] ERNIE-RNA full family 三种子已闭合：s17=0.927570、s29=0.932243、s43=0.938084，mean=0.932632、SD=0.005268、95% CI half-width=0.013086。full 相比 LoRA family 的描述性增量为 +0.006231，相比 frozen family 为 +0.026869；random−family 的 full 差值为 0.009093。
- [x] 至此 ERNIE-RNA ncRNA 的 frozen/LoRA/full × random/family × 3 seeds 共 18 格全部 corrected best-val 闭合，旧 pre-shuffle family 结果不再参与对照。已自动生成 `ernierna_ncrna_18cell_summary_20261029.csv`，包含六组均值、SD、95% CI、best_epoch 和完整 RID。
- [x] RNA-FM frozen random 三种子已闭合：s17=0.896270（best_epoch25）、s29=0.884615（best_epoch21）、s43=0.885781（best_epoch18），mean=0.888889、SD=0.006419、95% CI half-width=0.015946。三格均 acceptance_eligible=True、序列零重叠、RTX 5090/CUDA 证据完整。
- [x] `ft_rnafm_noncodingrnafamily_frozen_s17_family_bestval_v1` 已完成：ACC=0.876168224，best_epoch=17，epochs_trained=21，best_val=0.41828，wall=676.5s，peak=785.2MiB，序列/家族簇零重叠、CUDA=True。
- [x] MRL/modification 真实缺口 `ft_rinalmomega_modification_full_s29_random_lr1e-05_bestval_v1` 已完成：m6A AUC=0.662747826、mean AUC=0.567844928，best_epoch=0，4 epochs 后按 validation patience=3 停止，best_val=0.188829，wall=661.7s，peak=7699.4MiB，CUDA=True、acceptance_eligible=True。启动前 free=18.021GiB、need=16GiB，训练时 GPU PID=2583674 占用8588MiB，无 CPU 降级。MRL/modification 更新为 150 complete+30 runnable。
- [x] ERNIE-RNA frozen random 三种子已闭合：s17=0.917249（best_epoch15）、s29=0.919580（best_epoch11）、s43=0.916084（best_epoch14）；mean=0.917638、SD=0.001780、95% CI half-width=0.004423。三格均 bestval_v1、acceptance_eligible=True、序列零重叠、RTX 5090/CUDA 证据完整。
- [x] `ft_ernierna_noncodingrnafamily_frozen_s29_family_bestval_v1` 已完成：ACC=0.910046729，best_epoch=14，epochs_trained=18，best_val=0.334860，wall=620.0s，peak=684.2MiB；序列/cluster 零重叠、CUDA=True。
- [x] ERNIE-RNA frozen 六格已全部闭合：random=0.917249/0.919580/0.916084，mean=0.917638、SD=0.001780；family=0.906542/0.910047/0.900701，mean=0.905763、SD=0.004721。family 的 seed43 best_epoch=12、wall=556.6s、CUDA=True。对照 LoRA random mean=0.928904、family mean=0.926402，描述性差值分别为 +0.011267 和 +0.020639，仅表示当前三种子与协议，不作普适策略定律。
- [x] 最新 `bestval_ledger_export_20261029.csv` 已导出：320 个唯一 RID、320 个 bestval_v1、全部 RTX 5090/CUDA，主指标无缺失或非有限值；4 个拒绝项均为 smoke test，单列 `_rejected.json`，不混入正式统计。
- [x] `ft_ernierna_noncodingrnafamily_lora_s43_family_bestval_v1` 已完成：ACC=0.926401869，best_epoch=4，epochs_trained=8，best_val=0.276937，wall=580.4s，CUDA=True。ERNIE-RNA corrected family 三种子为 0.936916/0.915888/0.926402，mean=0.926402、SD=0.010514、95% CI half-width=0.026118；该统计不再使用旧 pre-shuffle family 值。
- [x] `ft_rnafm_noncodingrnafamily_lora_s17_random_bestval_v1` 已完成：ACC=0.916083916，best_epoch=5，epochs_trained=9，best_val=0.299996，wall=653.5s，peak=1988.2MiB，序列零重叠、CUDA=True。一次辅助 lane 因 main busy PID 在启动前自然退出而被安全拒绝，随后重新扫描真实 Python training child 再提交，没有双开或伪失败结果。
- [x] 小任务接续注册表 `ncrna_official_small_20261029.json` 已生成，共 66 格、need≤16GiB；调度器源码确认显存不足会等待，complete/running 跳过，CUDA 检查失败会终止。系统外部 `flock` 不存在，第一次启动未产生进程；后续只使用 Python 原生文件锁，不绕过生命周期锁。
- [~] 原生锁队列首次因 `argv[0]=python` 导致子进程 `sys.executable=''`，所有错误均为 subprocess launch 前的 `Permission denied: ''`，未训练、未产生科学结果。改用绝对 Python 路径作为 argv[0] 后，队列 PID=2453451 正常运行；已实际启动 `ft_ernierna_noncodingrnafamily_frozen_s17_random_bestval_v1`（runner PID=2454818），启动后 GPU util=97%，证明调度链恢复且未使用 CPU 降级。
- [x] 审计时捕获 `torch.AcceleratorError: CUDA error: out of memory`，发生在 `torch.cuda.mem_get_info(0)` 初始化阶段。已停止新增提交并保留证据，不使用 CPU 静默降级；现有在训任务继续按原 CUDA 日志验收，待 nvidia-smi 与 proof 确认真实空闲后再续队列。
- [~] 随后三次 SSH 分别出现 `Permission denied` 与两次 `Connection closed`（其中一次已等待 180s），已停止本轮继续重连；本地 PPT/PDF 与源包再次验算通过。待外部 SSH 状态恢复后只需读取 result/proof 和启动原生锁队列，不重跑任何 complete 格，最新 tasks 待同步回 teams。
- [x] `ft_rnafm_noncodingrnafamily_frozen_s29_family_bestval_v1` 已完成：ACC=0.880841121，best_epoch=14，epochs_trained=18，best_val=0.424429，wall=589.4s，peak=785.2MiB；`ft_rnafm_noncodingrnafamily_frozen_s43_family_bestval_v1` 已完成：ACC=0.875000000，best_epoch=12，epochs_trained=16，best_val=0.451301，wall=509.8s，peak=785.2MiB。两格均按 validation patience=3 收敛停止，序列/family cluster 跨切分零重叠、CUDA=True、acceptance_eligible=True。
- [x] RNA-FM frozen family 三种子已闭合：s17=0.876168224、s29=0.880841121、s43=0.875000000，mean=0.877336449、样本 SD=0.003090831、95% CI half-width=0.007678050。三轮核验分别为原始 result 字段断言、三格 `proof_state=complete`（result/plateau/ledger/checkpoint 一致）及独立统计复算；与 random mean=0.888889 的描述性 random−family 差值为 0.011552440，不作普适 split 定律。
- [~] ncRNA 小显存注册表当前 55 complete、1 running、10 runnable、0 conflict；运行格为 `ft_rnafm_noncodingrnafamily_lora_s29_random_bestval_v1`，队列 PID=2453451 正常接续。其余 10 格均为 RNA-FM LoRA/full，继续由原队列按 proof、防重和显存合同执行，不重复启动 complete/running 格。
- [~] MRL/modification 未完成项复核为 30 runnable、0 running、0 conflict，全部属于 RiNALMo-650M 的 MRL/modification × frozen/LoRA/full × 双 split × 3 seeds，单格 need=28GiB。审计时 GPU free=22.167GiB，未达到 28+1GiB 合同，未强行启动训练；已部署原生锁接续队列 PID=2612468（`mrl_mod_all_strategies`，workers=1、poll=60s），已核实进程命令行与锁均由该队列持有，待其他 CUDA 任务自然释放显存后自动按 proof 补测。
- [x] RNA-FM LoRA random 三种子已闭合：s17=0.916083916、s29=0.921911422、s43=0.918414918，mean=0.918803419、样本 SD=0.002933114、95% CI half-width=0.007286258；best_epoch 均为5，均训练9 epochs 后按 validation patience=3 停止。三格均 proof=complete、CUDA=True、acceptance_eligible=True、序列跨切分零重叠。相比 frozen random mean 的描述性增量为 +0.029914530，仅限当前协议。
- [~] 主线进入 RNA-FM LoRA family 后，启动辅助格 `ft_rnafm_noncodingrnafamily_lora_s29_family_bestval_v1`：启动前 free=20.092773GiB、need=16GiB，lane PID=2614819，唯一训练子进程 PID=2614855，GPU 实占2636MiB；初始进程匹配误把检查命令本身计入导致断言失败，修正为仅匹配真实 Python module 后确认仅1个训练进程。主 seed17 与辅助 seed29 的 ledger 现均为 running，proof 防重生效。
- [~] 尝试并行追加 LoRA family seed43 时，启动器实测 free=16.460022GiB，低于 16+1GiB 合同，在创建单格 registry、训练子进程和结果前安全拒绝；不重试、不绕过门禁，后续由原 ncRNA 主队列自然接续。650M 接续队列 PID=2612468 仍存活并持有原生锁，当前无训练日志、无新结果，不将队列存活记作实验完成。
- [x] RNA-FM LoRA family 已完成两格：s17 ACC=0.886682243、best_epoch=3、epochs_trained=7、best_val=0.409721、wall=502.3s；s29 ACC=0.882009346、best_epoch=3、epochs_trained=7、best_val=0.436363、wall=505.5s。两格均 proof=complete、CUDA=True、acceptance_eligible=True，序列/family cluster 跨切分零重叠；seed43 已由原主队列接续，待三种子闭合后统一统计。
- [~] complementary 缺口复核为 148 runnable，其中唯一 need≤15GiB 的格为 `ft_rinalmomicro_secondarystructure_full_s43_random_lr1e-05_pairalign_bestval_v1`（need=8GiB）。首次辅助启动因原 main busy PID=2614466 已自然退出而安全拒绝；重新扫描真实训练 child 后以 PID=2619458 为协调证据启动，free=19.074524GiB，lane PID=2620813，唯一训练子进程 PID=2620855，GPU 实占754MiB。日志确认官方 RiNALMo-micro 权重加载并进入 SSP 数据准备，未把启动或加载阶段记作完成。
- [~] SSP micro full seed43 已进入 ledger running，训练日志出现 epoch0 train_loss=1.0137、val_loss=0.861000，GPU 实占增至1840MiB；该 epoch 仅作为真实训练证据，不作为科学结果。同期利用 free=17.291992GiB 启动 `ft_rnafm_noncodingrnafamily_full_s17_random_lr1e-05_bestval_v1` 辅助格（need=16GiB），lane PID=2623151，唯一 CUDA 子进程 PID=2623184，GPU 实占3770MiB；启动时全卡 util=88%，未发生 CPU 降级。
- [x] RNA-FM LoRA family 三种子已闭合：s17=0.886682243、s29=0.882009346、s43=0.915887850，mean=0.894859813、样本 SD=0.018360086、95% CI half-width=0.045608982；best_epoch=3/3/7，wall=502.3/505.5/783.6s。三格均 proof=complete、CUDA=True、acceptance_eligible=True，序列/family cluster 跨切分零重叠。至此 RNA-FM LoRA 双 split 六格全部闭合；相比 frozen family mean 的描述性增量为 +0.017523364，仅限当前协议。
- [~] C5c registry 复核发现 660 个 need≤12GiB 的 runnable 小格，优先选择 `ft_rinalmomicro_noncodingrnafamily_lora_s17_random_e31500_bestval_v1` 补 1500 档。首次启动前 main busy PID 已自然退出，安全拒绝；重扫真实 child 后再次检查，free=8.536133GiB，低于 8+1GiB 合同，仍在 registry/训练/结果创建前拒绝。未绕过门禁、未继续重试，待自然显存窗口后再补。
- [x] `ft_rnafm_noncodingrnafamily_full_s17_random_lr1e-05_bestval_v1` 已完成：ACC=0.893939394，best_epoch=9，epochs_trained=13，best_val=0.398323，wall=924.3s，peak=3039.0MiB；proof=complete、CUDA=True、acceptance_eligible=True，n_train/n_val/n_test=6858/857/858，random split 序列跨切分零重叠。该 split 不强行要求 family cluster 字段；当前仅为 full random 的第一个正式种子，不提前与已闭合策略作三种子排序。
- [x] `ft_rnafm_noncodingrnafamily_full_s29_random_lr1e-05_bestval_v1` 已完成：ACC=0.914918415，best_epoch=13，epochs_trained=17，best_val=0.324998，wall=1141.5s，peak=3039.0MiB；proof=complete、CUDA=True、acceptance_eligible=True，random split 序列跨切分零重叠。full random 当前完成2/3，待 seed43 后统一统计。
- [x] RNA-FM full random 三种子已闭合：s17=0.893939394、s29=0.914918415、s43=0.900932401，mean=0.903263403、样本 SD=0.010681995、95% CI half-width=0.026535546；best_epoch=9/13/8，wall=924.3/1141.5/876.4s。三格均 proof=complete、CUDA=True、acceptance_eligible=True、序列跨切分零重叠。当前协议下 full random mean 相比 LoRA random 为 -0.015540016、相比 frozen random 为 +0.014374514，仅是本模型三种子描述，不作普适策略排序。
- [x] RiNALMo-micro SSP full random 的 pair-align best-val 三种子已闭合：s17/s29/s43 F1=0.1605/0.1624/0.1454，mean=0.156100、样本 SD=0.009315042、95% CI half-width=0.023139846；best_epoch=4/3/3，wall=1224.3/1096.0/1880.6s。三格均为 n_train=2000、结果 n_test=400、threshold=0.9，`pair_alignment=b20_single_base_token_positions_v1`，proof=complete、CUDA=True、acceptance_eligible=True；不将 n_test=400 表述为 full-test，也不与旧 tokenizer 未对齐结果混算。
- [~] 释放显存后启动 `ft_rnafm_noncodingrnafamily_full_s17_family_lr1e-05_bestval_v1`：free=18.462585GiB、need=16GiB，lane PID=2636654，唯一 CUDA 子进程 PID=2636687，GPU 实占3806MiB。随后启动 C5c `ft_rinalmomicro_noncodingrnafamily_lora_s17_random_e31500_bestval_v1`：free=14.284180GiB、need=8GiB，lane PID=2636866，唯一 CUDA 子进程 PID=2636889，GPU 实占9164MiB；1500 档正式进入 best-val 训练。
- [~] 尝试继续并行 C5c 1500 档 seed29 时，PyTorch 实测 free=4.838257GiB，低于 8+1GiB 合同，在 registry/训练/结果创建前安全拒绝。该拒绝验证 need=8GiB 的合理性：seed17 实际显存已达9164MiB；不为提高并发绕过门禁。
- [x] C5c `ft_rinalmomicro_noncodingrnafamily_lora_s17_random_e31500_bestval_v1` 已完成：ACC=0.792540793，best_epoch=8，epochs_trained=12，best_val=0.582160，wall=346.0s，peak=8474.8MiB；proof=complete、CUDA=True、acceptance_eligible=True。n_train/n_val/n_test=1500/857/858，seeded_sample 从6858条训练序列抽1500条，removed_cross_split 均为0；该 runner 使用此 split 证据结构，不强行要求另一套字段名。
- [~] C5c 1500 档 seed29 已在真实窗口启动：free=10.827820GiB、need=8GiB，lane PID=2640219，唯一 CUDA 子进程 PID=2640267，GPU 实占9162MiB。seed17/29 串行补测避免显存叠加，待 seed43 后形成该数据档三种子统计。
- [x] RNA-FM modification full 双 split 六格已由并行队列闭合并补验收：`result.value` 明确等于 m6A（index 7）AUC，`metric_mean_auc` 另表示12类均值，未混用。random 的 m6A AUC=0.978556522/0.981426087/0.971669565，mean=0.977217391、SD=0.005014218、95% CI half-width=0.012456008；family=0.926016500/0.927843828/0.920672137，mean=0.924844155、SD=0.003726806、95% CI half-width=0.009257899。12类 mean AUC 的 random/family 均值分别为0.831432367/0.884015300。六格均 proof=complete、CUDA=True、acceptance_eligible=True；在 RNA-FM full 当前协议与测试范围内未观察到 m6A 坍缩，不外推为其他模型或任务免疫定律。
- [x] `ft_rnafm_noncodingrnafamily_full_s17_family_lr1e-05_bestval_v1` 已完成：ACC=0.890186916，best_epoch=8，epochs_trained=12，best_val=0.485167，wall=907.3s，peak=3039.3MiB；proof=complete、CUDA=True、acceptance_eligible=True，序列/family cluster 跨切分零重叠。full family 当前完成1/3，主线已接续 seed29。
- [x] C5c 1500 档 seed29 已完成：ACC=0.841491842，best_epoch=12，epochs_trained=16，best_val=0.542895，wall=438.4s，peak=8474.8MiB；proof=complete、CUDA=True、acceptance_eligible=True，n_train/n_val/n_test=1500/857/858，removed_cross_split 均为0。
- [~] C5c 1500 档 seed43 已启动：free=15.017944GiB、need=8GiB，lane PID=2647525，唯一 CUDA 子进程 PID=2647584，GPU 实占9164MiB；完成后统一计算1500档三种子统计。
- [x] best-val 源台账已刷新至 revision=`20261029_bestval_ledger_370_v8`：370个唯一RID、4个smoke-only拒绝项。对账确认旧320/349/351/363行均逐字段保留，第四轮仅新增7个预期RID；97个manifest登记文件全部哈希通过，manifest SHA256=`cc5ccd3b5b1f700dc65629719e225f97bc920dc609c5250bf4e0f5f909af7e67`。旧363行CSV及manifest已归档，当前文件、归档和 teams 备份哈希一致；其后新完成格留待下一闭合组刷新，不冒充已纳入370行快照。
- [x] C5c ncRNA random × RiNALMo-micro × LoRA 的1500档三种子已闭合：s17=0.792540793、s29=0.841491842、s43=0.821678322，mean=0.818570319、样本 SD=0.024623080、95% CI half-width=0.061167121；best_epoch=8/12/11，wall=346.0/438.4/416.6s。三格均 proof=complete、CUDA=True、acceptance_eligible=True，训练抽样与 removed_cross_split=0 证据一致。1000/2000/2500/3000档仍未闭合，当前仅绘制源数据点，不外推学习曲线趋势。
- [x] `ft_rnafm_noncodingrnafamily_full_s29_family_lr1e-05_bestval_v1` 已完成：ACC=0.908878505，best_epoch=11，epochs_trained=15，best_val=0.494086，wall=1024.8s，peak=3039.3MiB；proof=complete、CUDA=True、acceptance_eligible=True，序列/family cluster 跨切分零重叠。full family 当前完成2/3。
- [~] C5c 2000档 seed17 已启动：free=18.439148GiB、need=8GiB，lane PID=2652142，唯一 CUDA 子进程 PID=2652181。随后尝试并行 full family seed43，首次因 main busy 已退出而安全拒绝，重扫后 free=12.734680GiB、低于16+1GiB，未创建训练；不再叠加另一个C5c小格，以免继续延迟主矩阵大格，待当前2000档自然释放后接续。
- [x] 结论⑤ MRL 官方模型对照复核：best-val 351行台账中，RiNALMo-micro/mega、ERNIE-RNA、RNA-FM 的 frozen/LoRA/full × 双 split 均为三种子闭合，RiNALMo-650M LoRA 双 split 也已闭合。full random 四模型均值范围为0.783195108–0.799254425，full family为0.685292447–0.709851431；LoRA random 五模型为0.793287774–0.803926024，LoRA family为0.691058316–0.725361034。所有已闭合组 Pearson r 均为正且远离近随机坍缩表述，当前范围支持“MRL 在已测官方模型中未观察到 ncRNA 旧式近随机坍缩”；650M frozen/full 仍待补，不能写成全模型或任务免疫定律。
- [x] C5c 2000档 seed17 已完成：ACC=0.826340326，best_epoch=10，epochs_trained=14，best_val=0.527546，wall=343.4s，peak=8474.8MiB；proof=complete、CUDA=True、acceptance_eligible=True，n_train/n_val/n_test=2000/857/858，seeded_sample 与 removed_cross_split=0 证据通过。
- [~] full family seed43 已由原主队列自然接续（训练 PID=2656412），不再需要辅助启动。C5c 2000档 seed29 已并行启动：free=15.017883GiB、need=8GiB，lane PID=2659064，唯一 CUDA 子进程 PID=2659103，GPU 实占9164MiB；待 seed43 后形成2000档三种子统计。
- [x] modification 台账代际复核：同一科学结果可同时存在 teams 原生无后缀 RID 与 `_seqmlfix` 溯源别名，简单按 model/task/strategy/split/seed 分组会错误得到6行。现于 manifest 固定 `modification_canonical` 规则：正式均值与图只使用 teams 原生无后缀 RID，`_seqmlfix` 仅保留溯源、不重复计数；RNA-FM full 的6个真实实验组过滤后均唯一。数据351行未变，仅修订元数据与索引。
- [x] RNA-FM full family 三种子已闭合：s17=0.890186916、s29=0.908878505、s43=0.882009346，mean=0.893691589、样本 SD=0.013773161、95% CI half-width=0.034214430；best_epoch=8/11/7，wall=907.3/1024.8/775.8s。full family 相比 LoRA family mean 的描述性差值为 -0.001168224，相比 frozen family 为 +0.016355140，仅限当前协议。
- [x] RNA-FM ncRNA 的 frozen/LoRA/full × 双 split × 3 seeds 共18格全部 corrected best-val 闭合。已生成 `rnafm_ncrna_18cell_summary_20261029.csv`，含六组均值、SD、95% CI、best_epoch 与18个唯一RID；逐格 proof/CUDA/收敛/切分验收及本地独立结构复核通过，CSV SHA256=`0518e0be14cfb46f2db2edb94eed8a7504806c997332b0b3dfb70b5adadbfcf0`。
- [x] C5c 2000档 seed29 已完成：ACC=0.848484848，best_epoch=10，epochs_trained=14，best_val=0.506543，wall=447.7s，peak=8474.8MiB；proof=complete、CUDA=True、acceptance_eligible=True，抽样与 removed_cross_split=0 证据通过。
- [~] C5c 2000档 seed43 已启动：free=19.465820GiB、need=8GiB，lane PID=2669755，唯一 CUDA 子进程 PID=2669827，GPU 实占9164MiB；完成后统一计算2000档三种子统计。
- [x] C5c ncRNA random × RiNALMo-micro × LoRA 的2000档三种子已闭合：s17=0.826340326、s29=0.848484848、s43=0.853146853，mean=0.842657343、样本 SD=0.014321918、95% CI half-width=0.035577617；best_epoch=10/10/10，wall=343.4/447.7/382.6s。三格均 proof=complete、CUDA=True、acceptance_eligible=True，抽样和 removed_cross_split=0 证据通过；1000/2500/3000档仍待补，不提前宣称单调趋势。
- [x] MRL/modification 专用180格源表已重新生成：150 complete、30 runnable，35格由 pending 转为 complete，旧 complete 行数值不变。非650M两任务三策略均闭合；650M modification 全待补，MRL 仅 LoRA 闭合。旧115-complete表已归档。新增 `mrl_bestval_official_sixbar` 与 `modification_bestval_official_sixbar` PNG/PDF/逐柱RID数据，旧 fourbar 移至 `obsolete_fourbar_20261029/`；非650M六组均 n=3，650M缺失项全部NA。
- [x] 新 PPT `RNA_LM微调策略评测-导师讨论修订版_20261029_六柱更新.pptx` 只修改演示顺序第6/7页读图说明和嵌图，其余26页 XML/rels 完全不变。layout Issues=0、markitdown 全稿复核通过、微软雅黑与1.5倍行距通过；默认 LibreOffice 出现中文回退异常后，使用独立 fontconfig 重渲染，中文与图表显示正常，PDF共28页。PPT SHA256=`bf08f4ce5560c4ef76c12641eae5d8e3cf8cff20e8f0f3906376af1622a521df`，PDF SHA256=`9f713ff76ef4ccca6fdceef0147604d71af107d15e5443b9a71235656e98e506`。
- [x] 六柱绘图代码远端独立重绘通过，图源 CSV 与本地哈希一致、图像尺寸与视觉一致；全仓385 tests通过。`/home` 提交 `b18cc259abf562d077fa9d0c9e151a159ea9a880`，GitHub `rnaft-expansion-20261027` 推送 `bed2cbced9b68ab9138e002a144c79ba106e5793`。当前源包 revision=`20261029_official_sixbar_v5`，manifest SHA256=`3b75bc9c23c3d3faab1ff8019efc4e08aa2c6d2c01b4e8bd79048d0d14759e08`。
- [~] C5c 继续并行补点：2500档 seed17 启动前 free=22.672180GiB，lane PID=2717145，唯一训练 PID=2717172，GPU 实占9164MiB；1000档 seed17 因启动器的 same-target 防重键不含 n_train 而安全拒绝，未绕过防重或重复启动同模型/seed/split。改启动独立缺格1000档 seed29，free=13.226257GiB，lane PID=2717680，唯一训练 PID=2717705，GPU 实占9162MiB。
- [x] C5c 2500档 seed17 已完成：ACC=0.815850816，best_epoch=5，epochs_trained=9，best_val=0.557099，wall=293.3s，peak=8474.8MiB；1000档 seed29 已完成：ACC=0.769230769，best_epoch=10，epochs_trained=14，best_val=0.649636，wall=257.1s，peak=8474.8MiB。两格均 proof=complete、CUDA=True、acceptance_eligible=True，抽样和 removed_cross_split=0 证据通过。
- [~] 接续启动2500档 seed29（free=22.180664GiB，lane PID=2721479，训练 PID=2721521，GPU 9184MiB）与1000档 seed17（free=9.787476GiB，lane PID=2721679，训练 PID=2721706，GPU 9164MiB）。两格均为独立 RID，按 same-target 与显存门禁运行，未重复启动。
- [x] C5c 2500档 seed29 已完成：ACC=0.843822844，best_epoch=7，epochs_trained=11，best_val=0.453112，wall=409.1s；1000档 seed17 已完成：ACC=0.772727273，best_epoch=11，epochs_trained=15，best_val=0.692109，wall=314.0s。两格均 proof=complete、CUDA=True、acceptance_eligible=True，抽样与 removed_cross_split=0 证据通过。
- [~] 接续启动2500档 seed43（free=19.270508GiB，lane PID=2727289，训练 PID=2727325，GPU 9162MiB）与3000档 seed17（free=9.807007GiB，lane PID=2727645，训练 PID=2727681，GPU 9164MiB）。1000档 seed43 留待下一自然窗口，避免与同模型/seed/split 的其他数据档同时运行。
- [x] C5c 2500档三种子已闭合：s17=0.815850816、s29=0.843822844、s43=0.843822844，mean=0.834498834、样本 SD=0.016149658、95% CI half-width=0.040117974；best_epoch=5/7/9，wall=293.3/409.1/479.1s。三格均 proof=complete、CUDA=True、acceptance_eligible=True。
- [x] C5c 1000档三种子已闭合：s17=0.772727273、s29=0.769230769、s43=0.800699301，mean=0.780885781、样本 SD=0.017247842、95% CI half-width=0.042846015；best_epoch=11/10/13，wall=314.0/257.1/323.3s。三格均 proof=complete、CUDA=True、acceptance_eligible=True。
- [x] C5c 3000档 seed17/29 已完成并验收：ACC=0.855477855/0.879953380，best_epoch=8/9，wall=501.6/496.2s；proof=complete、CUDA=True、acceptance_eligible=True。
- [~] C5c 3000档 seed43 已启动：free=22.349915GiB、need=8GiB，lane PID=2759611，唯一 CUDA 子进程 PID=2759634，GPU 实占9164MiB；完成后补齐当前 ncRNA×micro×LoRA×random 系列1000–3000五档的最后一个缺数据点。
- [x] C5c 3000档三种子已闭合：s17=0.855477855、s29=0.879953380、s43=0.878787879，mean=0.871406371、样本 SD=0.013806803、95% CI half-width=0.034298000；best_epoch=8/9/12，wall=501.6/496.2/573.9s。三格均 proof=complete、CUDA=True、acceptance_eligible=True。
- [x] 当前 ncRNA×micro×LoRA×random 系列1000/1500/2000/2500/3000五档共15格全部闭合，mean 分别为0.780885781/0.818570319/0.842657343/0.834498834/0.871406371。已生成 `c5c_ncrna_micro_lora_random_1000_3000_summary_20261029.csv`，含15个唯一RID、SD、95% CI 和 best_epoch；SHA256=`9362ff929b5ec0cb398df0c725176bf70ee1cdd249f91daec9dfd9a0301502d1`。2500较2000小幅回落，不写严格单调；其他任务、模型和 split 仍待补。
- [~] 已启动 RiNALMo-mega（148M）同协议 C5c `ft_rinalmomega_noncodingrnafamily_lora_s17_random_e31000_bestval_v1`：启动前 free=22.213196GiB、need=16GiB，lane PID=2769822，唯一 CUDA 子进程 PID=2769843，GPU 实占14888MiB。继续按 micro→mega→giga 与1000–3000加密档推进，不以33M曲线替代规模验证。
- [x] RiNALMo-mega C5c 1000档 seed17/29 已完成并验收：ACC 均为0.835664336，best_epoch=4/3，epochs_trained=8/7，best_val=0.521019/0.518438，wall=316.7/283.7s，peak=14057.7MiB；两格均 proof=complete、CUDA=True、acceptance_eligible=True，抽样和 removed_cross_split=0 证据通过。
- [~] RiNALMo-mega 1000档 seed43 已启动：free=22.213196GiB、need=16GiB，lane PID=2782318；完成后形成 mega 1000档三种子统计，再推进1500/2000/2500/3000。
- [x] RiNALMo-mega 1000档三种子已闭合：s17=0.835664336、s29=0.835664336、s43=0.836829837，mean=0.836052836、样本 SD=0.000672902、95% CI half-width=0.001671582；best_epoch=4/3/4，wall=316.7/283.7/308.4s。三格均 proof=complete、CUDA=True、acceptance_eligible=True，抽样与 removed_cross_split=0 证据通过。
- [~] RiNALMo-mega 1500档 seed17 已启动：free=22.213196GiB、need=16GiB，lane PID=2784117，继续同模型同协议加密学习曲线。
- [x] 跨规模同协议比较：ncRNA random LoRA 的1000档中，mega mean=0.836052836，较 micro mean=0.780885781 高0.055167055；两种模型均三种子完整 proof。该差值仅描述当前任务/split/数据档，不用于推断其他档位或普遍规模定律。
- [x] RiNALMo-mega 1500档 seed17 已完成：ACC=0.848484848，best_epoch=3，epochs_trained=7，best_val=0.489661，wall=374.4s，peak=14057.7MiB；proof=complete、CUDA=True、acceptance_eligible=True，抽样和 removed_cross_split=0 证据通过。
- [~] RiNALMo-mega 1500档 seed29 已启动：free=22.213196GiB、need=16GiB，lane PID=2789708，继续三种子补测。
- [x] RiNALMo-mega 1500档 seed29 已完成：ACC=0.864801865，best_epoch=5，epochs_trained=9，best_val=0.479925，wall=445.4s，peak=14057.7MiB；proof=complete、CUDA=True、acceptance_eligible=True，抽样与 removed_cross_split=0 证据通过。
- [~] RiNALMo-mega 1500档 seed43 已启动：free=18.791992GiB、need=16GiB，lane PID=2795006，完成后统一计算1500档三种子统计。
- [x] RiNALMo-mega 1500档三种子已闭合：s17=0.848484848、s29=0.864801865、s43=0.855477855，mean=0.856254856、样本 SD=0.008186211、95% CI half-width=0.020335676；best_epoch=3/5/4，wall=374.4/445.4/425.4s。三格均 proof=complete、CUDA=True、acceptance_eligible=True。
- [~] RiNALMo-mega 2000档 seed17 已启动：free=18.791992GiB、need=16GiB，lane PID=2804586，继续同协议补点。
- [x] RiNALMo-mega 2000档 seed17 已完成：ACC=0.867132867，best_epoch=5，epochs_trained=9，best_val=0.450641，wall=534.0s，peak=14057.7MiB；proof=complete、CUDA=True、acceptance_eligible=True，n_train/n_val/n_test=2000/857/858，seeded_sample 与 removed_cross_split=0 证据通过。result/plateau、proof/checkpoint、split/global ledger 三路核验一致；后续原始最低 val 仅低0.001974，小于 abs_floor=0.008，不改写 substantive-best checkpoint。
- [~] RiNALMo-mega 2000档 seed29 已启动：free=18.926758GiB、need=16GiB，lane PID=2821709，唯一真实训练子进程 PID=2821987，ledger=running；启动后整卡 util=100%。一次进程断言误匹配检查用 bash 自身，已限定真实 Python module 前缀后复核唯一，不影响训练或结果。
- [x] RiNALMo-mega 2000档 seed29 已完成：ACC=0.885780886，best_epoch=5，epochs_trained=9，best_val=0.425518，wall=555.1s，peak=14057.7MiB；proof=complete、CUDA=True、acceptance_eligible=True，抽样与 removed_cross_split=0 证据通过，result/plateau、proof/checkpoint、split/global ledger 三路核验一致。
- [~] RiNALMo-mega 2000档 seed43 已启动：free=22.349915GiB、need=16GiB，lane PID=2828917，唯一真实训练子进程 PID=2828945，ledger=running；完成后闭合2000档三种子统计。
- [x] RiNALMo-mega 2000档三种子已闭合：s17=0.867132867、s29=0.885780886、s43=0.874125874，mean=0.875679876、样本 SD=0.009420634、95% CI half-width=0.023402152；best_epoch=5/5/5，wall=534.0/555.1/547.7s。三格均 proof=complete、CUDA=True、acceptance_eligible=True，逐格 result/plateau、proof/checkpoint、split/global ledger 三路核验一致。1000/1500/2000档独立摘要已保存为 `c5c_ncrna_mega_lora_random_summary_20261029.csv`，含9个唯一RID，SHA256=`2e5d1813b5b11161b622b365265f510ca9289fc07cbf08ffc2ea7dee3ada66d0`；2500/3000与650M仍未闭合，不外推完整曲线。
- [~] RiNALMo-mega 2500档 seed17 已启动：free=22.369446GiB、need=16GiB，lane PID=2831265，唯一真实训练子进程 PID=2831286，ledger=running。
- [x] RiNALMo-mega 2500档 seed17 已完成：ACC=0.892773893，best_epoch=6，epochs_trained=10，best_val=0.374872，wall=693.3s，peak=14057.7MiB；proof=complete、CUDA=True、acceptance_eligible=True，n_train=2500、抽样与 removed_cross_split=0 证据通过，三路验收一致。
- [~] RiNALMo-mega 2500档 seed29 已启动：free=18.948242GiB、need=16GiB，lane PID=2833273，唯一真实训练子进程 PID=2833294，ledger=running。
- [x] best-val 总台账已刷新至 revision=`20261029_bestval_ledger_379_v9`：379个唯一RID，旧370行逐字段不变，仅新增 mega 1000/1500/2000档9个预期RID；4个拒绝项仍均为smoke test。2500档 seed17 在快照导出时仍running，未混入本版。当前98个登记文件的本地字节数/SHA256全部通过，manifest SHA256=`57590db65c418f1b27eb1a28e47887394d6a68b8b8ccc45de3fd0cb0cd28cdc5`；旧370行CSV、拒绝清单与manifest均已归档。
- [x] 远端源包路径复核发现 `delivery/20261028` 仍是历史不完整副本，而真正370行当前副本在 `delivery/20261029`。已先把20261028同步前状态保存为 `figure_source_data_20261028_pre379_20261029.tar.gz`，再将本地98文件清单同步到20261029权威副本及20261028镜像；两端98/98字节数与哈希、379行唯一RID及manifest SHA256均一致。未删除旧证据，索引已改指20261029为权威副本。
- [x] RiNALMo-mega 2500档 seed29 已完成：ACC=0.903263403，best_epoch=9，epochs_trained=13，best_val=0.382625，wall=886.2s，peak=14057.7MiB；proof=complete、CUDA=True、acceptance_eligible=True，n_train=2500、抽样与 removed_cross_split=0 证据通过，三路验收一致。
- [~] RiNALMo-mega 2500档 seed43 已启动：free=22.213196GiB、need=16GiB，lane PID=2835468，唯一真实训练子进程 PID=2835510，ledger=running；完成后形成2500档三种子统计。
- [x] RiNALMo-mega 2500档三种子已闭合：s17=0.892773893、s29=0.903263403、s43=0.857808858，mean=0.884615385、样本 SD=0.023800207、95% CI half-width=0.059122992；best_epoch=6/9/3，wall=693.3/886.2/500.7s。三格均 proof=complete、CUDA=True、acceptance_eligible=True，逐格三路验收通过。该档种子波动明显，保留逐种子值和CI，不写严格单调或单种子代表结论。
- [~] RiNALMo-mega 3000档 seed17 已启动：free=18.811523GiB、need=16GiB，lane PID=2837403，唯一真实训练子进程 PID=2837424，ledger=running。
- [x] RiNALMo-mega 3000档 seed17 已完成：ACC=0.903263403，best_epoch=5，epochs_trained=9，best_val=0.358707，wall=754.8s，peak=14057.7MiB；proof=complete、CUDA=True、acceptance_eligible=True，n_train=3000、抽样与 removed_cross_split=0 证据通过，三路验收一致。
- [~] RiNALMo-mega 3000档 seed29 已启动：free=22.213196GiB、need=16GiB，lane PID=2841499，唯一真实训练子进程 PID=2841540，ledger=running。
- [x] RiNALMo-mega 3000档 seed29 已完成：ACC=0.905594406，best_epoch=5，epochs_trained=9，best_val=0.339587，wall=748.5s，peak=14057.7MiB；proof=complete、CUDA=True、acceptance_eligible=True，n_train=3000、抽样与 removed_cross_split=0 证据通过，三路验收一致。
- [~] RiNALMo-mega 3000档 seed43 已启动：free=22.232727GiB、need=16GiB，lane PID=2845210，唯一真实训练子进程 PID=2845231，ledger=running；完成后闭合 mega 五档15格。
- [x] RiNALMo-mega 3000档三种子已闭合：s17=0.903263403、s29=0.905594406、s43=0.904428904，mean=0.904428904、样本 SD=0.001165501、95% CI half-width=0.002895265；best_epoch=5/5/5，wall=754.8/748.5/726.3s。三格均 proof=complete、CUDA=True、acceptance_eligible=True，逐格三路验收通过。至此 mega 1000/1500/2000/2500/3000五档15格全部闭合，mean=0.836052836/0.856254856/0.875679876/0.884615385/0.904428904；当前五档均值递增，仅限 ncRNA random×LoRA，不外推650M或其他任务。
- [x] `c5c_ncrna_mega_lora_random_summary_20261029.csv` 已更新为五档15个唯一RID，SHA256=`b73551b15c17a32c12968ae2db61c3fbf666810c9ba6b85e317b5b3290999b96`。新图 `c5c_ncrna_lora_micro_mega` 合并micro/mega共10行30个唯一RID，本地与远端独立重绘的图源CSV SHA256均为`30099e4309d4dc2e17790e6fc1fc07f46679ccd07db5e430fd40fd1c88ab4225`；148M五档均高于33M，33M在2500档回落，图像只描述当前协议。
- [x] 新增 PPT `RNA_LM微调策略评测-导师讨论修订版_20261029_C5c五档更新.pptx`：共29页，新页位于演示顺序第22页（结论⑤后、⑤d前），原有28页slide XML/rels完全不变。第一轮实际渲染发现标题和页码换行，扩大文本框后第二轮通过；layout Issues=0、markitdown、微软雅黑、1.5倍行距、嵌图哈希和29页PDF均通过。PPT SHA256=`5b8284246f9ff9c9d5748b8f6bd0d9053fae67136b3c7d8a29215707dea820df`，PDF SHA256=`07250cf9399051928df89b6cb3c322883f6aa595fcbd971b21618d13d4e21db8`。
- [x] 绘图函数强制五档、三种子与30个唯一RID完整后才出图；不完整输入实测会拒绝。全仓385 tests通过，`/home` 提交为 `621ea49`。远端GitHub直连与本地全量clone均失败后，在GitHub当前协作分支顶端应用同一58行差异并推送成功，`rnaft-expansion-20261027` 的 ls-remote 已确认 `e186390d2b76cd0c0d7f2c6840f899bf5fbeb5b8`，未强推或改写历史。
- [x] best-val 总台账已刷新至 revision=`20261029_bestval_ledger_385_v10`：385个唯一RID，旧379行逐字段不变，仅新增 mega 2500/3000档6个预期RID；4个拒绝项仍均为smoke test。mega五档15个RID全部纳入。当前101个登记文件的字节数/SHA256本地及两个teams副本均通过，manifest SHA256=`bc6eed14ace1a503da7a384252876120b909c8b5a5f1230c1ced6fc37f2de1fe`；旧379行CSV、拒绝清单和manifest已归档，远端独立重绘证据另存 `status/figure_verification/20261029_c5c/`。
- [~] C5c 650M 启动窗口复核：PyTorch free=18.948242GiB，低于28+1GiB合同，未创建训练；主线继续运行 SpliceAI/SSI，不强行提交或改CPU。
- [~] 利用空闲窗口启动结论④/⑤c所需的 `ft_rinalmomicro_noncodingrnafamily_full_s17_random_lr1e-05_e31000_bestval_v1`：free=18.928711GiB、need=8GiB，lane PID=2854000，唯一真实训练子进程 PID=2854021，ledger=running。后续按三种子和五档补齐 micro full(n)，用于与大模型 LoRA(m) 的同协议比较。
- [x] micro full-FT 1000档 seed17 已完成：ACC=0.800699301，best_epoch=14，epochs_trained=18，best_val=0.719932，wall=302.1s，peak=9117.2MiB；proof=complete、CUDA=True、acceptance_eligible=True，n_train=1000、抽样与 removed_cross_split=0 证据通过，三路验收一致。
- [~] micro full-FT 1000档 seed29 已启动：free=22.369446GiB、need=8GiB，lane PID=2854285，唯一真实训练子进程 PID=2854306，ledger=running。
- [x] micro full-FT 1000档 seed29 已完成：ACC=0.785547786，best_epoch=14，epochs_trained=18，best_val=0.728790，wall=314.3s，peak=9117.2MiB；proof=complete、CUDA=True、acceptance_eligible=True，n_train=1000、抽样与 removed_cross_split=0 证据通过，三路验收一致。
- [!] micro full-FT 1000档 seed43 辅助启动在队列 CUDA memory check 阶段发生 OOM：启动器前置检查 free=18.948242GiB、need=8GiB，但队列随后检查失败；result目录与ledger均不存在，未开始训练、未产生科学结果。已停止新增辅助提交，不立即重试、不改CPU；日志已保存至 `status/failures/20261029/...cuda_oom.log`，SHA256=`33db67732e8cb1166fdc4b7508b6854a0133bd6a5c2b4e3d9d16ed16b866040e`。现有主线在训格继续，待自然显存窗口后按proof重试该runnable格。
- [~] 源码复核确认首次失败发生在 `torch.cuda.mem_get_info` 调用本身，不是 `free<need` 预算拒绝。保留日志后，只读诊断恢复 `CUDA_API_OK free=22.369446GiB`；据此以相同RID、相同参数受控重试一次，lane PID=2857975，唯一真实训练子进程 PID=2858016，ledger=running。若再次失败将停止而不是循环重试。
- [x] micro full-FT 1000档三种子已闭合：s17=0.800699301、s29=0.785547786、s43=0.786713287，mean=0.790986791、样本 SD=0.008431443、95% CI half-width=0.020944866；best_epoch=14/14/13，wall=302.1/314.3/314.6s。三格均 proof=complete、CUDA=True、acceptance_eligible=True。seed43重试成功且后续原始val改善0.013373小于完整阈值 max(best×0.02,0.008)=0.015328；初次自审只用abs_floor的断言过严，已按合同修正，未改写best_epoch或结果。首次失败registry/state亦已归档。
- [~] micro full-FT 1500档 seed17 已启动：free=18.791992GiB、need=8GiB，lane PID=2864843，唯一真实训练子进程 PID=2864864，ledger=running。
- [x] micro full-FT 1500档 seed17 已完成：ACC=0.803030303，best_epoch=9，epochs_trained=13，best_val=0.705611，wall=307.3s，peak=9117.2MiB；proof=complete、CUDA=True、acceptance_eligible=True，三路验收一致。
- [x] micro full-FT 1500档 seed29 在显存门内并行启动并完成：启动前 free=11.724304GiB、need=8GiB，lane PID=2865078；ACC=0.820512821，best_epoch=13，epochs_trained=17，best_val=0.634875，wall=347.8s，peak=9117.2MiB；proof=complete、CUDA=True、acceptance_eligible=True，三路验收一致。
- [~] micro full-FT 1500档 seed43 已启动：free=22.213196GiB、need=8GiB，lane PID=2869296，唯一真实训练子进程 PID=2869317，ledger=running；完成后闭合1500档统计。
- [~] micro full-FT 2000档 seed17 已在显存门内并行启动：free=11.702820GiB、need=8GiB，lane PID=2869425，唯一真实训练子进程 PID=2869446，ledger=running；与1500档 seed43 不同RID、不同seed，两格进程分别唯一。
- [x] micro full-FT 1500档三种子已闭合：s17=0.803030303、s29=0.820512821、s43=0.814685315，mean=0.812742813、样本 SD=0.008901662、95% CI half-width=0.022112955；best_epoch=9/13/13，wall=307.3/347.8/361.6s。三格均 proof=complete、CUDA=True、acceptance_eligible=True，逐格三路验收通过。
- [~] micro full-FT 2000档 seed29 首次并行尝试因 PyTorch free=8.283508GiB 低于8+1GiB合同，在创建registry、训练与结果前安全拒绝；不立即重试，待2000档 seed17 自然释放后接续。
- [x] micro full-FT 2000档 seed17 已完成：ACC=0.822843823，best_epoch=10，epochs_trained=14，best_val=0.630203，wall=415.2s，peak=9117.2MiB；proof=complete、CUDA=True、acceptance_eligible=True，三路验收一致。
- [~] 自然释放后启动 micro full-FT 2000档 seed29：free=18.811523GiB、need=8GiB，lane PID=2871538，唯一真实训练子进程 PID=2871581，ledger=running；未重复创建首次被拒格。
- [~] micro full-FT 2000档 seed43 已在显存门内并行启动：free=11.743774GiB、need=8GiB，lane PID=2871760，唯一真实训练子进程 PID=2871781，ledger=running；与seed29分别唯一，待两格完成后闭合2000档统计。
- [x] micro full-FT 2000档三种子已闭合：s17=0.822843823、s29=0.835664336、s43=0.849650350，mean=0.836052836、样本 SD=0.013407486、95% CI half-width=0.033306041；best_epoch=10/13/14，wall=415.2/537.9/542.5s。三格均 proof=complete、CUDA=True、acceptance_eligible=True。该均值与 mega LoRA@1000 的0.836052836在数值上相同，但正式等价点仍需按逐seed最近配对与CI规则核算，不提前写成结论④完成。
- [~] micro full-FT 2500档 seed17 已启动：free=21.721680GiB、need=8GiB，lane PID=2873687，唯一真实训练子进程 PID=2873713，ledger=running。
- [~] micro full-FT 2500档 seed29 并行尝试因 free=8.264038GiB 低于8+1GiB合同被安全拒绝，未创建registry、训练或结果；待自然窗口接续。
- [x] micro full-FT 2500档 seed17 已完成：ACC=0.855477855，best_epoch=16，epochs_trained=20，best_val=0.513147，wall=606.8s，peak=9117.2MiB；proof=complete、CUDA=True、acceptance_eligible=True，三路验收一致。
- [~] 自然释放后启动 micro full-FT 2500档 seed29：free=18.791992GiB、need=8GiB，lane PID=2874956，唯一真实训练子进程 PID=2874997，ledger=running。
- [~] micro full-FT 2500档 seed43 并行尝试因 free=8.285522GiB 低于8+1GiB合同被安全拒绝，未创建训练；待seed29自然释放后接续。
- [x] micro full-FT 2500档 seed29 已完成：ACC=0.862470862，best_epoch=12，epochs_trained=16，best_val=0.506136，wall=545.0s，peak=9117.2MiB；proof=complete、CUDA=True、acceptance_eligible=True，三路验收一致。
- [~] 自然释放后启动 micro full-FT 2500档 seed43：free=22.428040GiB、need=8GiB，lane PID=2876157，唯一真实训练子进程 PID=2876178，ledger=running；完成后闭合2500档统计。
- [x] micro full-FT 2500档三种子已闭合：s17=0.855477855、s29=0.862470862、s43=0.850815851，mean=0.856254856、样本 SD=0.005866227、95% CI half-width=0.014572516；best_epoch=16/12/12，wall=606.8/545.0/508.6s。三格均 proof=complete、CUDA=True、acceptance_eligible=True。该均值与 mega LoRA@1500 的0.856254856相同；与2000↔1000一样只先登记为描述性候选等价对，待全曲线和逐seed规则验收。
- [~] micro full-FT 3000档 seed17 已启动：free=18.928711GiB、need=8GiB，lane PID=2878327，唯一真实训练子进程 PID=2878348，ledger=running。
- [~] micro full-FT 3000档 seed29 并行尝试因 free=8.439819GiB 低于8+1GiB合同被安全拒绝，未创建训练；待seed17自然释放后接续。
- [x] micro full-FT 3000档 seed17 已完成：ACC=0.877622378，best_epoch=11，epochs_trained=15，best_val=0.480370，wall=510.3s，peak=9117.2MiB；proof=complete、CUDA=True、acceptance_eligible=True，三路验收一致。
- [~] 自然释放后启动 micro full-FT 3000档 seed29：free=18.928711GiB、need=8GiB，lane PID=2879869，唯一真实训练子进程 PID=2879910，ledger=running。
- [~] micro full-FT 3000档 seed43 并行尝试因 free=8.480835GiB 低于8+1GiB合同被安全拒绝，未创建训练；待seed29自然释放后接续。
- [x] micro full-FT 3000档 seed29 已完成：ACC=0.882284382，best_epoch=15，epochs_trained=19，best_val=0.454385，wall=674.7s，peak=9117.2MiB；proof=complete、CUDA=True、acceptance_eligible=True，三路验收一致。
- [~] 自然释放后启动 micro full-FT 3000档 seed43：free=22.369446GiB、need=8GiB，lane PID=2880743，唯一真实训练子进程 PID=2880764，ledger=running；完成后闭合 micro full-FT 五档。
- [x] 三任务扩展图已改为 frozen/LoRA/full × random/family 六柱，不再混合微调臂。18个 task×model 行、108个单元逐格回查 `b20fix_8task_table.csv`，均值与 n_seeds 全部一致；原表无逐种子值，因此不虚构 SD。`extension_three_task_sixbar.png/.pdf/_data.csv` 已保存，108/108 对账通过。
- [x] 新 PPT `RNA_LM微调策略评测-导师讨论修订版_20261029_六柱扩展与状态校正.pptx` 共29页，仅改演示页2/8/23；其他 slide XML/rels 语义无差异。第8页数值标签碰撞已第二轮修复；第23页图内状态同步为33M/148M random×LoRA 五档已闭合，其余臂仍待补。`fix_pptx`、编辑页 layout Issues=0、markitdown、ZIP CRC、嵌图哈希、微软雅黑、1.5倍行距和29页独立 fontconfig 渲染均通过。PPT SHA256=`acbb01c5ba4b501eb492ee885ca6e2b20367cefb781238f655221c0e98be6157`，PDF SHA256=`0c2afab83ba9331ff836e599dff5d3f9be9e137b98207f46e5e30b0a0b4651ea`。
- [x] 旧三任务四柱 PNG/PDF/源表已归档至 `archive_20261028/绘图数据/obsolete_fourbar_20261029/`，未删除证据。源包 revision=`20261029_extension_sixbar_status_v11`，101个登记文件及最终PPT/PDF哈希全部通过，manifest SHA256=`d1a4701d71f6cf43c6654dcfa1960fba8d4c5eafbc77e0ec65f88578a70a8600`。绘图代码全仓385 tests通过，GitHub `rnaft-expansion-20261027` 已推送 `7a24117f064a2493ff8ae1d1a269ec33abe6c595`。
- [!] 本轮两次 SSH 分别在远程命令执行前出现 `Connection closed` 与 `kex_exchange_identification: Connection reset by peer`，未执行任何远端命令，也未据此判断训练成功/失败。v11 teams 同步和实时 GPU/proof 核验待连接恢复；首先只读复核 micro full-FT 3000 seed43、现有队列和 ledger，complete 不重跑、running 不双开，再同步源包并继续后续矩阵。
- [x] SSH 恢复后实时核验：RTX 5090 util=92%，3个真实 CUDA 任务在跑；complementary 324格为184 complete、140 runnable、0 running、0 conflict。650M MRL/modification frozen 候选需28+1GiB，实测 free=22.213GiB，未强行提交。
- [x] micro full-FT ncRNA random 的1000/1500/2000/2500/3000五档共15格已逐格 `proof_state=complete`，含此前在途3000 seed43，ACC=0.879953380。15格 value、RID、seed与budget均唯一，未重跑任何 complete 格；完整 best-val 导出正在刷新，正式等价图待导出三轮对账后生成。
- [x] best-val 导出刷新为400 accepted、4 rejected：旧385行逐字段一致，新15行仅为 micro-full 五档，4个拒绝项仍全为smoke。400个RID唯一且全部带CUDA证据；CSV SHA256=`2259442381b2145f465702821ff4fe29bd25aa0a5b7eda0461945679649957fc`，旧385行CSV/rejected/manifest已归档。
- [x] 结论④等价图已生成并独立复核：s17/s29/s43最近对分别为 full@2500↔LoRA@1500、full@2000↔LoRA@1000、full@2500↔LoRA@1500，绝对差0.006993/0/0.004662。结论为2个候选而非唯一交点，不插值。30个源RID、3个逐seed配对、metadata与25组预算对差值均保存；本地与teams重算的 data/pairs/meta SHA256完全一致。
- [x] 新 PPT `RNA_LM微调策略评测-导师讨论修订版_20261029_等价线更新.pptx` 仅修改第20页，其余slide XML/rels语义无差异。layout Issues=0、markitdown、29页渲染和字体行距通过；PPT SHA256=`3a7d737706fbaae9fe36cd746b1d18675af7ce1b2be656c8716b315cbd784d18`，PDF SHA256=`1f3789308f5d13e10773bc21f9bb6fd6b0f4826cb1693812b4e1694c81b6415a`。
- [x] 源包 v12 共104文件，manifest SHA256=`628b95bbd68ecdadb29210c358e0a02d0c50015de6db7903d46fb7edf6a7b938`；两个 teams 副本、PPT/PDF哈希与本地一致，同步前tar备份和旧目录备份均保留。`/home` 提交 `f870f8cc4a31af420938848745050e387009c935`，GitHub提交 `9aee3d4a6edfab5535c4cc7134a51ca3414002d4`，本地及远端385 tests通过。
- [~] 主矩阵辅助提交复核：候选 ERNIE CRISPR frozen 需要16+1GiB，启动器实测 free=13.368164GiB，在创建registry/训练前安全拒绝；进一步核查 complementary 的 need≤12GiB runnable 为0，未强行提交。现有队列继续运行，待自然显存窗口按proof接续，complete不重跑、running不双开。
- [x] 结论③已建立完整 PEFT/rank 注册表 `peft_rank_jobs_20261030.json`：8任务×5官方模型×{LoRA r4/8/16+DoRA r8}×双split×3 seeds，共960个唯一RID/result_dir；本地与teams生成计数一致，385 tests通过。`/home` commit=`a700ed6`，GitHub commit=`b57abfc`。
- [x] 960格完整 proof 审计为102 complete、858 runnable、0 conflict，DoRA 0 complete；结果写入 `peft_rank_jobs_20261030.audit.json`。该波次仅注册未启动，待主矩阵门禁后按proof执行。
- [x] rank8 路径疑点已澄清：既有六格为 `_fixedsplit`，新表无后缀 rank8 为主矩阵协议，并非同 RID 或结果丢失；两协议不得混均值。未重跑、未覆盖既有 `_fixedsplit` 结果。
- [!] E6 `RiNALMo-650M lora s43` 在并行负载下于01:20真实 CUDA OOM：进程需约17.27GiB，其他两个训练进程与队列同时占卡，最后仅10.31MiB空闲；`q_e6_mlm15fix` 报 `INCOMPLETE cells=3/6`。已保留 `q_e6_mlm15fix.log` 证据，未使用CPU降级，pre NLL只作运行诊断不作最终结论。
- [x] E6 重复 OOM 根因已修复：旧脚本对所有 LoRA 仅设8GiB 门槛，现按实测将650M LoRA/full 分别改为18500/26000MiB。无需修改 active whitelist；部署后01:30日志确认 `WAIT_VRAM need=18500MB free=17696MB`，未再次启动或OOM。`bash -n` 与385 tests通过，`/home` commit=`d909ff0`，GitHub commit=`1f5acf3`。
- [x] 结论②已注册 `lr_tuning_jobs_20261030.json` 320格与 `lr_default_jobs_20261030.json` 240格，合计560个唯一RID/result_dir；tuning覆盖80个 task×model×split 组×4 LR×seed101，default覆盖正式三种子。两表仅注册未启动。
- [x] 新增 `select_lr_validation.py`：仅在80组四档均 proof=complete 后按 held-out best_val 选LR，test不参与；缺格实测为 incomplete=320，未生成 selection/tuned jobs。tuned 结构测试可生成240个唯一正式格。GitHub commit=`8674ab4`，本地及远端385 tests通过；`/home` commit=`8be70d0`。
- [~] 两个长时 SpliceAI 训练仍在推进：mega full s43 random 的 train/val 两轮为0.003104→0.000899/0.001168→0.000902，650M LoRA s17 random 为0.001945→0.000926/0.000868→0.000841。plateau 位于 root artifacts，teams无同名目录不是缺格证据；当前无result.json，不终止、不迁移、不写成完成。
- [x] 主矩阵 need 已按同协议实测峰值校准：初版混 legacy/E6 的37–41GiB异常被拦截未应用；最终276格调整，186 exact+90受控 fallback，最大28GiB。原表及逐格证据均已备份，GitHub commits=`3383381/1dfa8c8`，385 tests通过。
- [x] `ft_ernierna_crisprofftarget_frozen_s17_random_bestval_v1` 的 need 经18个best-val run证据由16降为3GiB，已于 free=16.789GiB 时通过启动器并完成，proof=complete、PR-AUC=0.188679145。校准未改变任何科学协议；该值只进入单格记录，不提前作三种子结论。
- [~] ERNIE CRISPR frozen 后续 random s29/s43 与 family s17 已在合并SSH中确认启动，lane PID分别3000029/3000243/3000479；family s29/s43 的另一次启动在SSH关闭时结果未知，仍不得视为已启动或完成。远端385 tests通过，校准 `/home` commit=`28b11c5`。
- [~] 后续只根据 proof 接续：先汇总六格 complete/running/runnable，再提交仍缺的 family seed29/43；不得在未知状态下双开。拟在无自有子任务时仅重启 complementary 父队列以加载校准need，但第一次重启命令在SSH建立前失败，未执行、未影响任何进程。

## N13. 2026-10-30 八任务后续交接执行清单

> 本节为当前唯一直接执行入口；N0–N12保留为历史证据。任何状态先实时重算，不沿用本节计数作为完成证明。

- [x] **计划先于训练**：已把八任务逐结论实验、阶段顺序、模型优先级、CUDA/best-val/三轮对账和PPT/归档门禁写入spec §10.31；未在更新计划前提交新训练。
- [x] **现行PPT基底**：确认采用29页 `RNA_LM微调策略评测-导师讨论修订版_20261029_等价线更新.pptx`，不重复插入任务地图、C5c五档页或八任务机制页，不回滚用户20页批注版。
- [x] **环境与代码初检**：`/home/cunyuliu/rna-ft-eval` HEAD=`28b11c5`、工作树干净、master ahead 62；RTX 5090、torch 2.11.0+cu128、CUDA可用。确认互补父队列和MRL/modification等待队列存活。
- [!] **旧valplateau失控训练**：650M degradation LoRA random旧格在epoch3达到best_val=0.219229，至epoch550仍为0.390136，547 epoch未回到旧停止带，581个validation点无result。旧PlateauTracker在validation持续高于best+tolerance时不会按无改善停止。日志/plateau/命令证据已保存到teams `status/failures/20261030/`，随后停止异常格、旧q_corrected父队列及新启动的同协议SSI；正在收尾的mega SpliceAI PID 3176591保留。该中断格不作科学结果，后续仅补独立bestval_v1，不重命名或混用旧协议。
- [x] **替代队列与注册表**：已补齐通用complementary生成器的per-base runner注入，生成270个唯一bestval_v1格（3任务×5官方模型×3策略×双split×3 seeds）。正式表全部使用teams artifacts；错误root草稿已归档。实时proof=12 complete+258 runnable+0 conflict，12格直接复用。234格按同协议实测峰值校准need，独立3-worker队列PID=3259415已启动；启动不记完成。
- [x] **代码与监控闭环**：全仓386 tests通过。生成器 `/home` commit=`6dfed90`、GitHub=`76b096190f219d797320112f5652fde0350f5370`；旧q_corrected已从active_lanes.txt移除，`/home` commit=`0e2602c`、GitHub=`fd4eb811551402856812924a1a150554ee1438e9`。两批均逐文件SHA核验，其他监控lane不变。
- [x] **跨模型并行调度**：修复pending队首同模型/大need格阻塞其他可运行格的问题，按预算与在训模型选择job并保留未处理pending；同模型串行、显存等待和proof不变。focused+全仓387 tests通过，`/home` commit=`72c498b`、GitHub=`923e29e681dc1f0cd016cedfaccae8cbf290ea32`，文件SHA一致。
- [x] **无中断加载新调度**：仅重启per-base与complementary父调度，子进程和命令记录到restart_20261030.json；新父PID=3291142/3292709。复核时5个真实CUDA训练进程并行、GPU util=96%、显存12,219MiB，旧q_corrected与显式plateau进程为0；不将进程数记为完成。
- [x] **408格台账与MRL阶段交付**：新best-val导出408 accepted+4 smoke rejected，旧400行逐字段不变。MRL/modification为152 complete+28 runnable，仅更新650M MRL frozen random seed29/43两格，mean=0.731394、n=2斜线。PPT第7页已换图和读图句，其他包条目不变；layout/lint/CRC/字体/1.5倍行距/渲染全部通过。v13源包104文件、旧数据归档和teams备份均验收，PPT SHA=`6ce9554a2f56daad356a471ba3a442741daeeede8af195b6e4ce27bdc7ae7724`。
- [x] **E6实时proof**：30个corrected E6格为27 complete+3 incomplete；仅650M LoRA seeds17/29/43未闭合，其余micro/mega/650M full/ERNIE/RNA-FM均通过双证。E6当前仍在650M阶段，等待真实显存窗口，不提前更新最终遗忘结论。
- [x] **P0实时proof总账**：complementary=188 complete+136 runnable；MRL/modification=152 complete+28 runnable；C5c=69 complete+1947 runnable；PEFT/rank=102 complete+858 runnable；LR tuning=320 runnable；E6=27 complete+3 incomplete，均无conflict。ERNIE CRISPR frozen已核4 complete+2 runnable，per-base已核12 complete+258 runnable；运行格按RID/命令/日志/CUDA接管，未双开。计数只作本时点审计，后续仍需实时重算。
- [ ] **P1主矩阵与归因**：优先闭合八任务官方模型主矩阵及MRL/modification跨模型矩阵；ncRNA只使用corrected shuffled/best-val证据，旧pre-shuffle及派生结论保持隔离。每闭合任务×模型×策略×split×3 seeds单元即导出逐RID表、SD/95%CI与资源记录。
- [ ] **P2结论②③**：主矩阵阶段验收后执行320个LR tuning格，80组四档齐全才按held-out best_val选LR；再生成并闭合default/tuned正式配对。随后执行PEFT/rank注册表真实缺口，复用既有rank8六格，不混fixedsplit/主矩阵/legacy协议。
- [ ] **P3结论⑤系列**：逐点区分C5d未跑/失败/未导出/路径缺失/隔离；闭合八任务×micro/mega/giga×LoRA/full×双split×七档C5c曲线，1000–3000保留1500/2000/2500加密档；从正式runtime直接导出八任务C5b时间×性能，统一硬件、batch、n、split和停止协议。
- [ ] **P4结论④等价线**：RiNALMo与RNA-Sc分家族、分任务计算small-full(n)↔large-LoRA(m)逐seed最近实测对和CI；无交点写未观测到，不插值、不跨家族拼接。ncRNA random现有两个候选仅作局部结果，不外推八任务。
- [ ] **并行调度**：仅在真实runnable、非running且free≥同协议need+1GiB时填充任务；不为占满显存抢跑后续波次或绕过共享锁。CUDA/mem_get_info异常或CPU降级即停止新增并留证。
- [ ] **图与PPT**：复用八任务机制源数据，仅做RiNALMo式标注与视觉复核；新图必须经RID/result、协议/统计、图内数值/图注三轮对账。只改目标页，保留用户手调内容、微软雅黑与1.5倍行距，另存独立修订版。
- [ ] **归档与代码**：现行源包保存CSV/JSON、RID、协议、脚本、metadata、PNG/PDF和manifest；旧图/旧表/废弃文档核引用后归档，不删除隔离证据。每批确认代码在 `/home` 提交并推送GitHub，权威大文件同步 `/teams`。
- [ ] **最终验收**：完成PPT ZIP/XML、markitdown、fix/layout、嵌图哈希、字体行距、LibreOffice渲染和未修改页diff；所有未闭合矩阵继续标NA/范围，不以阶段版冒充最终科学结论。

## N14. 2026-10-30 续接执行与图源复现修复

- [x] **三套交接同步**：本地、`/home/cunyuliu/rna-ft-eval/docs` 与 `/teams/.../handoff` 的 spec/tasks/checklist/PPT交接/绘图索引已统一；同步前版本保存至 `/teams/.../backups/handoff_pre_goal_continue_20261030/`，五份文件三地SHA256一致。
- [x] **现行PPT独立复核**：29页MRL更新版的PPT/PDF SHA256与交接一致；29页PDF总览和分组图已检查，任务地图与8个机制页无需重做。layout Issues=0，171个非空段落全部为Microsoft YaHei与1.5倍行距。源包104个登记文件通过目录与tar两条独立哈希核验；AppleDouble和`__pycache__`仅作待清理元数据，不纳入科学源文件。
- [x] **复现问题定位**：直接运行v13包内绘图脚本可复现FileNotFoundError，根因是输入文件名仍固定在20261028/20261029；没有把“104个文件哈希正确”误当成“入口可复现”。
- [x] **绘图修复与验收**：`latest_work_input()`按日期选择当前输入并保留MRL日期标签；本地13/14共同PNG逐字节一致，唯一资源图差异由两条新增650M MRL frozen random解释，目标MRL图/CSV和等价线图/CSV一致。远端MRL数据、尺寸和视觉复核通过，全仓387 tests通过。`/home`提交=`49fe6e2`。
- [x] **GitHub与下一源包**：远端直连GitHub超时后改用本机API中转，`rnaft-expansion-20261027` 新提交为 `2e8b55c536af9330c089ce8b3c2f286287af68f3`；分支HEAD、单文件变更和三地源码SHA256均通过。下一源包revision纳入修复脚本并排除缓存/AppleDouble，v13历史包不覆盖。
- [x] **实时主矩阵增量proof**：互补220 complete+3 running+101 runnable，per-base 16 complete+254 runnable，MRL/modification 152 complete+28 runnable，均0 conflict。去重后8任务主矩阵714格为338 complete+3 ledger running+373 runnable；已导出338个唯一RID主矩阵CSV，best-val全台账另为443 accepted+4 rejected，两种计数不混用。
- [x] **RNA-Sc等价线注册**：固定30M full@3e-5 vs 650M LoRA@3e-4，8任务×双split×七档×3 seeds×2臂=672格。初次草稿的ncRNA runner被dense门禁拒绝，未训练；改用 `finetune_one` 后通过唯一性、LR、batch、dense和388 tests。正式表672 runnable、0 conflict，仍在P4后启动。`/home` commit=`df8c65b`，GitHub=`f3267222f2bad12e97f10b010dec0c4c8d5a0f1c`。
- [ ] **继续科学矩阵**：沿用N13实时proof和现有主矩阵队列，complete不重训、running不双开；只有主矩阵阶段门通过后才启动LR/PEFT-rank，不以绘图修复或注册表替代任何实验完成。

## N15. 2026-10-30 夜间八任务扩展与 30 页交付执行清单

> 用户当轮要求：①第 3 页后介绍 8 任务；②①a-4 任务扩展按 ①a 风格重绘（优先官方模型）；③机制 8 任务双 split 三状态（已完成，复核即可）；④②③④⑤⑤b⑤c⑤d 补齐 8 任务。本轮先冻结顺序再执行，禁止边跑边改协议。

- [x] **P0 调度扩容**：per-base 父队列 3→6 worker、complementary 4→6 worker（SIGTERM 旧父进程、子进程保留），新增 LR tuning 3 worker 独立队列；复核 10 个真实 CUDA 进程并行、util 94→99%、显存 15.3 GiB/32.7 GiB，无同 RID 双开。
- [x] **P0 图与页**：任务地图页改为「4 类 = 3+1+2+2」并说明不复制任务；①a-4 改为其余 5 任务 × 5 官方模型 × 六柱（标准 6 色、n<3 斜线、未闭合留白），与前 3 页合并覆盖 8 任务。
- [x] **⑤b 拆分**：⑤b-1 时间×性能 8 任务散点（random split、中位 wall）；⑤b-2 显存 5 模型×3 策略（Frozen<LoRA<Full，650M full 未跑）。旧「LoRA≈frozen/650M full 超 24GB」措辞按实测弃用。
- [x] **⑤d 换页**：审计表 → 148M/650M 覆盖热图（0=未闭合，不是 0 分），逐任务逐臂标已完成种子数。
- [x] **②③⑤ 文案**：② 写明 320 LR 格已启动、tuned 240 格在其后；③ 写明 rank8 六格 0.918/0.900 与 960 格注册表；⑤ 写明 MRL/m6A 5 模型六柱无崩溃带、C5c 2016 格已注册。
- [x] **验收**：30 页 ZIP CRC 正常；layout 越界 0；全部文本 run 为 Microsoft YaHei；非空段落 1.5 倍行距；独立 fontconfig 实际渲染中文正常；文本 diff 仅演示页 4/8/18/19/21/23/26 与新增 27、总结 29。
- [x] **源包与归档**：`figure_source_data_20261030_eight_task_v14/`（17 文件，manifest SHA256=`5c9ee9aa3da92360aa7996d357181e42f874087444050b3ab5fbc579d6938827`）；旧图/旧表/历史文档移入 `archive_20261030/`，不删隔离证据。
- [ ] **P0 剩余主矩阵**：per-base 251 格 + complementary 86 格（ncRNA/CRISPR/modification/MRL/SSP 缺口）；每闭合一批即重绘 ①a-4 与 ⑤d，禁止用 registry 大小冒充完成。
- [ ] **P1 MRL/modification 28 格**：补齐 650M full/family 等；n=2 仍斜线，不写三种子。
- [ ] **P2 LR 320 → tuned 240**：80 组 task×model×split 四档 proof 齐全后按 held-out best_val 选档（并列取较低 LR），再生成 tuned 正式格；test 指标不参与选档。
- [ ] **P3 PEFT/rank 960**：rank4/8/16 + DoRA × 8 任务 × 5 官方模型 × 双 split × 3 seeds；与主矩阵同 RID 不双开。
- [ ] **P4 C5c 2016**：8 任务 × micro/mega/giga × LoRA/full × 双 split × {10,100,1000,1500,2000,2500,3000} × 3 seeds；650M 仅在 28+1 GiB 窗口启动。
- [ ] **P5 RNA-Sc 等价线 672**：30M full@3e-5 vs 650M LoRA@3e-4，逐任务 84 格；只有两臂曲线均闭合才计算逐 seed 等价点。
- [ ] **P6 E6**：650M LoRA seeds17/29/43 三格；其余 27 格已 complete，不重训。
- [x] **重复启动处置**：重启父队列后 `RiNALMo-micro frozen s43 family` 与 `ERNIE-RNA frozen s29 family` 出现同 RID 双开；按 `/proc` 清单保留先启动 PID（3389298/3393786）、终止后启动 PID（3398319/3398327），复核无其他重复格。教训写入 spec §10.38-⑨：父进程重启前必须用 `/proc` 实际 runner 清单与 ledger 对齐，禁止立即重放注册表。
- [x] **artifact-root 回归修复**：重起队列时漏设 `RNAFT_ARTIFACT_ROOT`，导致新完成格写入 `/home/.../artifacts` 而注册表指向 `/teams/...`，proof 全部报 conflict。已按 spec §10.38-⑩ 终止错环境父/子进程并以 `env RNAFT_ARTIFACT_ROOT=/teams/...` 重起三个父队列；`/proc/<pid>/environ` 与 teams 新目录时间戳双重验证通过。错根期间的 9 格作废，不计数、不进均值。
- [x] **P3 前置小批（rank4/16）**：`rank_micro_r4r16_20261031.json` 固定 RiNALMo-micro × LoRA × rank{4,16} × 8 任务 × 双 split × 3 seeds = 96 格，RID 带 `_r4/_r16_bestval_v1` 与主矩阵 rank8 不重；2-worker 队列已起（state=`status/rank_micro_r4r16`，`RNAFT_ARTIFACT_ROOT` 指向 teams），首个格 `ft_rinalmomicro_noncodingrnafamily_lora_s17_random_r4_bestval_v1` 已建目录。该批只服务结论③的 rank 轴，不替代 P2 的 LR 选择门。
- [x] **20261031 台账刷新**：delta 导出 408+95=503 accepted（0 rejected）；夜间 v3 再 +277 = 800 accepted（2 rejected）；四图按新台账重绘；148M 六臂闭合任务 4→5（新增 SSP）；过滤口径写入两个构图脚本并做 smoke/diag/rank/seed101/C5c/错根六类排除；PPT/PDF 与源包 v15 已重出并复验。
- [x] **20261031 三条补测车道**：A 线 ncRNA 全参 8 格 LR 诊断（`stale_missing_artifacts` 复位后重跑，4 worker，`status/ncrna_lr_recover_20261031`）；B 线等价线 420 格 micro-full@1e-5 vs mega-LoRA@3e-4 × 7 任务 × 5 档 × 双 split × 3 seeds（4 worker，`status/equiv_tiers_20261031`，SSP n=2000 的 12 格按 complete 自动 skip）；C 线 SpliceAI family frozen 2 格 SIGTERM 重跑（2 worker，`status/repair_20261031`）。三线均独立 state-dir，不动 5 条主队列。
- [x] **650M 取舍定稿**：用户决定「不做 650M」——LoRA 峰值 17 GB、full 25 GB，单卡 32.7 GiB 在与主队列并行时无法开跑；⑤c-0/⑤d/⑤b-2 三页显式写「显存受限，本轮不测」，已有 650M 格保留为覆盖陈述，不补零、不写规模律。
- [ ] **A 线定稿**：8 格 LR 网格齐后写「同 split 仅改 LR」对照，判定 ncRNA 全参坍缩是 LR 过高（真坍缩）还是测评口径（伪坍缩）；当前 family@1e-5=0.8703、random@3e-4=0.0956 已回。
- [x] **B 线首图**：`build_equivalence_8task.py` 已产出 3/8 可判面板（ncRNA/modification/MRL），CRISPR 标「正例过少（0.59%，需 ≥6000 档）」，其余待分层；图暂存 fig_20261030，不进正文。
- [ ] **B 线补齐**：SpliceAI/SSP/降解/SSI 分层与 ncRNA family 档位落地后，≥6 面板再替换 ④ 页。
- [ ] **归档与同步**：本地/`/home` docs/`/teams` handoff 三地 SHA256 一致；新图源包与 PPT/PDF 同步 teams delivery；确认代码提交 `/home` 并推送 GitHub。
