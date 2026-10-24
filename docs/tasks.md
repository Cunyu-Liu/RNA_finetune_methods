# RNA-LM 微调策略评测：任务分解（TASKS）

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

- [~] official canonical 30 格 `_mlm15fix` 重跑中，首批 micro 3 格已过双证；旧 mega LoRA@1e-5 变体若保留另带独立标签。
- [~] E6-v2 official micro m6A-start 6 格已追加隔离并以 `_taskm6a_s0_mlm15fix` 重跑；累计隔离 300 行、251 个旧 result 文件。
- [ ] 修正版 official ΔNLL 逐行对账前，冻结旧 official 5–9×等表述；controlled/NB 结果分协议呈现。
- [ ] AIDO MRL s43 使用 `finetune_mrl` + 3 epochs + bs1 + 12h 的唯一 owner；q5090 错 runner 已修，audit_1016 必须回源核验而非只看状态。

## E. 监控、收敛与交付

- [~] monitor v2.2 已部署并核验单实例、锁释放、白名单和 GPU 低显存告警；后续持续按完成证据移出白名单，旧计划 glob 复活已禁用。
- [ ] 建立 validation-loss 平台审计；未达 `min_delta + patience` 的格不得标 final，续训以 `valplateau_v1` 独立记录，不与 fixed-epoch 静默混合。
- [ ] corrected 结果达到 B23 + 收敛门禁后，重刷导出表/图，进行至少三轮 ledger 原始行对账，再更新 preprint 与结果版 PPT。
- [ ] 每个修复/实验批次完成后提交并经 Mac bundle 通道推 GitHub；大型备份与 manifest 留 `/teams/HoulabData_1788502323/liucunyu/rna-ft-eval/`。
- [ ] 最终复核 spec/tasks/checklist、训练日志、PPT 与论文中的任务数、指标、有效格数和协议标签一致；T0.3.1 三签及 C/D 门禁不得因工程进度自行勾销。
