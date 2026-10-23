
## 2026-10-13 晚（1016：is_done 双格式根治 + 队列解锁 + 配额事故处置）

### 1. 第四层假完成变体根治（is_done 双格式）
- **根因**：MRL/modification runner 的 e3 run_id 为 `_e3<n>_lr<lr>`（e3 在前），q_fill.is_done 只匹配 `_lr<lr>_e3<n>` → 1011 六 worker 在 9 个已完成格上 claim-blocked 死循环数小时（无 GPU 浪费但阻塞队列推进）；q_plan_need 同缺陷导致台账 missing 误报（1010 报 5 实为 68）
- **修复**：is_done 双格式匹配（lr_e3 + e3_lr 两种顺序都认）+ 新增 audit_1016.py 权威审计器（含 rank/n_train/lr 精确匹配）

### 2. 调度解锁 + 陈旧卡锁清理
- 1010 四 worker 全卡 33-34G 大格（need 过标定：650M frozen 34G → 实测峰值 5031MB）→ 拆分 1016 双 plan：mega_e3 27 格（小格 need 重标定 4/36/40G）+ bigtail 41 格（650M frozen need 34→8G）
- **kill -9 留下 10 个陈旧卡锁**（SIGKILL 不执行 finally rmdir；5 个是 Oct 6 的周旧锁）→ 清锁后 6 训练立即启动；教训：kill worker 前先让其自然退出，或杀后手动清锁
- keepalive_1016.sh + cron */10 装岗（worker 死亡 10 分钟内自动重拉）

### 3. 磁盘配额事故（tar_stage 111G → /mnt 归位，经用户确认）
- home 配额 100% 满导致写入 0 字节失败（keepalive 首次创建被截断）；tar_stage 230 个 tar 分片（111G，hf_models/codonflow 等多课题备份，22:38 后无活跃写入进程）→ **用户确认后** mv 至 /mnt/cunyuliu/tar_stage_1013；写测试通过
- 教训：见 tar_progress.log 有 [19:00]/[22:11]/[22:37] 三次 quota exceeded 记录——此前已多次失败

### 4. 队列真态（23:02）
- 1016 mega_e3：27 格中 frozen 首批已落地（e310 全落 + e31000/e33000 在跑）；bigtail 41 格（NB mrl 1 在跑 + AIDO×3 + 650M 36）
- AIDO 3e-05×3（1007 遗留）：s17 首跑 OOM（共享卡挤压）后自动重试中
- 1011 尾格：7 格（m6A E3×3 + SSP rank×4）由 keepalive_e3rank + 1016 体系接管

## 2026-10-14 凌晨（1016c：TOCTOU 双抢 OOM 竞态根治）

- **现象**：AIDO 3e-05 s17 与 mega full s29 同时在 GPU0 开训 → AIDO OOM 死亡（36.62MiB free 时仍试图分配）
- **根因**：grab() 检查 free 与训练进程实际分配显存之间存在数分钟 ramp 窗口——AIDO 抢 slot_1（margin 48G 判定通过后开始 ramp），mega s29 在 ramp 完成前看到 free≥40G 也抢 slot_0 → 双双开训 → 后者 OOM。经典 TOCTOU
- **修复**：need≥30G 的格要求**独占整卡**（双 slot 全空 + 1.15× margin）+ finally 释放兄弟 slot——同卡大格竞态结构性消除
- 伴随治理：孤儿锁二次清理（kill -9 遗留）；bigtail plan need 升序重排（1c77713）后 650M frozen 批量落地恢复吞吐
- NB mrl default-LR 三种子 -0.0016 落地（A8 默认崩溃第 2 架构确认）；audit_1016 56→44

## 2026-10-14 关机前最后收口（1016e：mega/650M 大模型 E3 图 + PPT s11）

- mega E3 终态：frozen 12/12（全档常值 0.72 家族切分）+ lora 9/12（e310/1000/5000 三档 3 种子全）+ full 5/12（e310 3 种子 + e31000/5000 各 1 种子被关机截断）
- 650M E3 终态：frozen 12/12 全齐（0.65 常值）+ lora 3/12（e310 落地 0.16）
- 新图 fig_ppt_e3_bigmodels.png（双面板大模型车道）+ PPT 新增 s11（16 页）；三遍验证（值 vs ledger tol 0.012 过 / CRC PASS / 嵌入 MD5 过 / lint PASS）
- 科学判读：大模型家族切分下 frozen 常值远高于 micro（0.72/0.65 vs 0.68 但起点更稳）、微调臂温和——容量对崩溃带有缓冲效应（full@5000=0.70 vs micro 0.068）

## 2026-10-14 晚（集群恢复：cron 重装 + 12 worker 重启 + rank m6A 补格新派 + GitHub 推送）

- **恢复验证**：ledger 2236 行 md5 1ce3d75c（与关机备份一致）；git HEAD 906dbce（与备份盘一致）；artifacts 2173 目录；audit_1016 = 34 格（与关机清单一致，无静默丢失）
- **GPU 拓扑变化**：6/7 号卡从 MIG 1g.5gb（4.75G 视图）变为整卡 40G——q_fill 的 total<20G 过滤现已放行 6/7 号卡，可用卡从 6 张升 8 张
- **cron 重装**：9 条全部恢复（status/monitor/refresh/stale_reset/close_monitor ×2/keepalive ×2）
- **worker 重启**：1016 双 plan ×4 shard + AIDO 3e-05 ×3 = 11 个；3 分钟内 650M lora e31000/e33000（关机中断格）重新开跑、ERNIE rank ×2 开跑——GPU2/3/4 100% 满载
- **新派 p2_rank_m6a_1014_plan（18 runs，commit 203e08a 已推 GitHub）**：ERNIE/RNA-FM/SpliceBERT × modification × lora × r{4,16} × 3 种子 @random——关机期间备份审计发现的结论③ m6A 面板缺口（ncRNA/SSP 面板此前已齐）
- 期间判读：UNEXPECTED 头权重提示 = lora 加载预期现象（非错误）；epoch 0 loss 0.028 正常

## 2026-10-15 凌晨（1014b 收口：rank m6A 补格 18/18 全落地 + rank 图 v8 + PPT s7 更新）

- **p2_rank_m6a_1014_plan 18/18 全落地**（~1.5h，2×2+2 补启分片；教训：启动 4-shard plan 必须把分片号全列——只起 s0/s1 会让 s2/s3 的格静默饿死）
- **终值（m6A lora random，3 种子均值）**：ERNIE r4 0.9892 / r16 0.9904；RNA-FM r4 0.9746 / r16 0.9870；SpliceBERT r4 0.9556 / r16 0.9554；micro（旧有）r4 0.979 / r8 0.970 / r16 0.974
- **判读**：架构差 0.955-0.990 主导，rank 差 ≤0.02（m6A 面板与 ncRNA/SSP 完全一致）——「rank 二阶旋钮」结论跨三任务闭合
- **rank 图 v8**（status/figs/fig_ppt_ranksweep.png）：三面板全 4 模型；MRL 面板维持 r8 口径（r4/r16 不在 E2 spec——E2 只扫 ncRNA+DMS 2 任务，SSP/m6A 已是扩展）
- **PPT s7 换图 + banner 更新**：嵌入 MD5 验证通过、lint PASS、orico 同步（md5 双端一致 894e0580）
- 期间 1016 尾格推进：650M lora e31000 ×3 重跑中 + AIDO 3e-05 ×2 在飞（等大卡窗口）

## 2026-10-15 深夜（1015b/c：AIDO 3e-05 OOM 三轮复盘 + bs1 整卡协议重派）

- bs32 → bs16 → bs1 失败链：bs16 峰值仍 30.5-31.5G（1.6B 常驻基底 ~20G 不随 bs 缩）+ 共享卡 4-8G 负载 → 39.5G 卡放不下；508 次重试后 GAVEUP×5 轮
- 终版协议 p2_aido_3e5_bs1_1015_plan（3187fc0）：bs=1 + need 34G 整卡独占 + timeout 16h = fullbig 1e-05 成功同款；stale running 行 ×2 清理 + 孤儿锁 gpu_0/gpu_4 清理（kill 遗留，ps 双证无占用后 rmdir）
- 预印本 v1.0：§2.5 cross-arch rank 段 + 头部增量注记（84fd070/d147993）
- 当前 8 卡满载（外部 7 进程 + codonflow×2 + AIDO mrl s29 dev2 训练中）——34G 整卡窗口由 keepalive 自动轮询抢占

## 2026-10-15 凌晨（1015d：650M full e3 need 重标定——第五层饿死形态根治）

- **发现**：bigtail 剩余 650M full e3 格 need=33G（1016 前的过标定存量），但 ledger 实测峰值仅 24.7G（e310 格）——21G 空闲窗口反复出现却全被 33G 门槛挡住（wait/no-card 循环数小时）
- **修复**：p2_650m_full_e3_recal_1015_plan（899e8dc）——9 格重派 need=26G；启动 3 分钟内 e33000 s17/e31000 s29 双双开跑（GPU2/4），验证标定正确
- **B24 纪律再证**：need 标定必须同 bs 语境引用 ledger peak_mem_mb（650M full bs32 peak 25014MB → e3 子集同 bs 峰值 24679.9MB 一致）
- 650M full e31000 s43 / e33000 s29 / e35000 ×3 继续在飞；mega lora e33000 三格等 36G 窗口；AIDO 3e-05 bs1 等 34G 整卡

## 2026-10-15 清晨（1015d 修正：recal 撤回——26G 门与双 slot 叠加致自撞 OOM）

- **复盘**：1015d 的 need=26G 重标定是错误判断——e310 峰值 24.7G 是空卡口径；真实运行中 backward+碎片峰值 ~34G（OOM 堆栈实证）。26G 门通过后训练启动再 OOM；且 slots=2 允许两个 26G 任务叠同卡（26+26>39.5）加剧
- **原 33G 整卡协议才是对的**（bigtail plan 原值）——已 kill recal worker、清理其制造的 pending 行；ledger 完整性核验 2256 行（2 个 done 行完好，无污染）
- **教训（B24 升级第二版）**：need 标定不能只看 ledger peak_mem_mb 的单值——空卡峰值 ≠ 共享卡峰值（碎片 + ramp）；判据应为「ledger peak × 1.3 或整卡独占」二选一，中间地带最危险
- 650M full e3 剩余 7 格由 bigtail 原协议（33G 整卡）继续排队；AIDO 3e-05 bs1 / mega lora 同等大卡窗口

## 2026-10-15 上午（1015f：650M full 三天 GAVEUP 真根因——bs 协议错配）

- **真根因确证**：q_full_big.sh 的 spec_bs() 对 RiNALMo-650M 给 **bs=8**（全部既有 650M full 正式行 = bs8、peak 25014MB）；而 1016 bigtail plan 对 650M full 传 bs=None → finetune_one 默认 bs32 → 峰值 35-37G → 整卡也 OOM。此前三天（10-13 起）650M full/lora 大量 GAVEUP 的元凶即此 bs 错配（lora 行同查：q_e6_official4 里 650M full bs=4——官方系 650M full 行都是小 bs）
- **修复**：p2_650m_full_e3_bs8_1015_plan（59e6ae3）——9 格 bs=8/need 26G；s17/e35000 首格 GPU2 开跑（batch-size 8 实证）、s29/e31000 GPU0 并行
- **纠错链记录（防再错）**：1015d 误判「need 过标定」→ 撤回；1015e need 34→30（AIDO）；1015f 找到真根因 bs——三次尝试全部留痕，最终以成功先例的 spec_bs 为准（B24 纪律的完整版：**need 与 bs 必须同时从成功先例抄**）

## 2026-10-15 下午（1015g：cron 路径 bug 修复——/mnt 无 scripts，重装 crontab 后 8 小时静默失效）

- **发现**：恢复时重装的 crontab 沿用恢复指南的 /mnt/cunyuliu/rna-ft-eval/scripts/ 路径——该路径无任何脚本（脚本在 /home）；cron 每次触发静默失败 → keepalive/stale_reset/close_monitor 全部停摆 8 小时（期间 bigtail 四 shard 全 GAVEUP/DONE、AIDO bs1 worker 静默死亡无人重拉）
- **修复**：crontab 全量 sed /mnt→/home 路径；14:00 keepalive 首次正常触发（重拉 bigtail×3）——日志恢复滚动
- **处置**：手动重启 AIDO bs1 s0/s2 + 650M bs8 网格；清冗余历史 plan worker（1010/1007/bs16/e3rank——只 skip 不干活但占 CUDA context）；killed 后孤儿锁已核（现存 6 锁全部对应活跃训练 dev0/2/3/5，mtime 新鲜）
- **当前 7 训练并行**：AIDO 3e-05 s17（dev5！bs1 整卡抢到了）+ Sc-300M e3 ×3 + 650M lora s29/s43（dev2）+ mega lora s17（dev4）——GPU 0/3/4 100% 满载
- **教训（入 checklist B25 候选）**：重装 crontab 后必须「等一个触发周期 + 查日志 mtime」验证真实生效，不能只看 crontab -l

## 1016（10-15 晚）僵尸 worker 无限复活确诊 + 紧急备份（用户指示中断）
- **确诊**：q_p1_monitor.sh AUTO-REFILL glob `p2_*.json` 无限复活 3 个判死计划（1010/1007/bs16）——25 个 q_fill worker × 8 卡 × 418MiB CUDA context ≈ 每卡 10.4G 被铺满 → AIDO bs1 need30 永远 wait(no card)；ledger 3 行 running 为假心跳
- **手术方案（未执行，四步）**：见 Mac 交接文档/巡检日志.md 第二十七轮 §2（mv 判死 plan → dead_plans/ + pkill q_fill + 重启正式 worker + 验证 418MiB 数）；B26 纪律候选 = AUTO-REFILL 白名单制
- 中断快照：ledger 2293/2289 done；AIDO 3e-05 ×3 + 650M full e3 尾 1 + mega lora ×3 未收口；PPT 17 页终版不受影响
- 本轮动作：全部最新结果 rsync → orico 04 盘（ledger 2293 / artifacts / status / code / paper / logs）

## 2026-10-18 晚 · 新集群（RTX 5090）恢复 + q5090 队列首批数据

- 环境：torch 2.11.0+cu128（Blackwell sm_120）；单格复算基准 micro frozen s17 random ACC 0.7366（老集群 0.739，跨硬件复现 ✅）
- q5090 队列（audit 22 缺格）首批落地（ledger 原始行）：
  - mega full@1e-05 family e31000：s17 0.8107 / s29 0.8084（健康，与 e31000 档位预期一致）
  - **mega full@1e-05 family e33000：s17 0.0759 / s29 0.6121 / s43 0.0643 —— 崩溃带命中（2/3 落 0.06-0.08 带）**
  - 判读：与 1013 过渡带叙事一致——家族记忆崩溃临界点 3000-5000 在 mega full 上同样成立（e31000→e33000 从 0.81 崩到 0.06-0.61，种子方向不稳定=临界区特征）。lora e33000 历史 0.807/0.821 健康（LoRA 免疫证据 +1）
  - 1 个 RC=1（mega lora s43 e33000，缺 accelerate 包）已装包并排 retry daemon
- E6 官方 18 格：ledger 已注册 pending，等 S0 文件（release22_split_8080.parquet，用户从 orico 补传）；monitor_loop 哨兵自动启动
- 备注：监控 monitor_loop 15min 在岗；q5090 22 格预计 1-2 天跑完

### 1018 晚 二批数据判读（650M lora e3 车道）

- 650M lora family e31000 三种子完全相同值 0.09579439 —— 独立排查（3 遍核对）：
  - e3_subsets 三种子文件 md5 互不相同（数据侧无雷同）；值 = family test 多数类频率（856 行 top-class 0.0958 精确一致）→ 三种子全部坍缩到恒预测多数类的同一退化解
  - 判读：650M LoRA 在 1000 条家族切分下坍缩到 majority-class（与崩溃带叙事一致）；种子间数值相同是坍缩到常数预测的自然结果，非数据泄漏（已验证数据/种子独立）
  - 对照：650M lora e33000 s17 = 0.0759（带内）；历史全量 family lora 0.076-0.084 一致；random 切分 0.94+ 不受影响

## 2026-10-23（1023：新任接手巡检 + 47 行假 running 清理 + q_master 协议修正 + monitor v2 + frozen 车道）

- 接手核验：ledger 2619→2633 行（done 2552→2578，+24 during session）；GPU 12.5G/32G 99% util；5 车道在飞（splmore/splfull2/splfull3/crisprfam/degrfull/nblane）
- **修复①：ledger 47 行假 running 残留**（容器无 cron，reset_stale_cron 从未被调用）——一次性清理（AIDO ncRNA 3 行 10-16 旧心跳 + spliceai 车道 OOM 残留等）；此后并入 monitor_loop v2 每 15min 执行
- **修复②：q_master Phase3 AIDO mrl s43 协议漂移**——旧脚本 epochs 10 + timeout 4h（成功先例 s17/s29 = epochs 3, wall ~7050-7250s）→ 改 epochs 3 + CELLTM 43200（12h）；q_master 重启带修复版
- **修复③：GPU 占满纪律**——新增 q_splfrozen 车道（micro/ERNIE × spliceai × frozen × 双切分 × 3 种子 = 12 格，frozen 便宜快速）；首 6 格 RC=0 已落
- **monitor_loop v2 装岗**：v1 仅快照+q5090 重拉；v2 新增 stale-running 清理 / 7 车道 worker 死亡自动 respawn / GPU<20G 且无训练时告警 / q_master 守护
- 备份：ledger + status + logs → /teams/HoulabData_1788502323/liucunyu/rna-ft-eval/（用户铁律：大文件去 teams）
- 代码：de541d3（集群）+ feb7cb0（GitHub，经 Mac bundle 中转——集群无 GitHub 凭据，Mac 有 SSH key；后续推送走此通道）
- 1016 尾格：audit=1（AIDO mrl full s43 random，q_master Phase3 等 drain 窗口）
- E6 官方 15 格（ERNIE/RNAFM × lora/full × 3 种子）：q_master Phase1 等 drain——注意其 bs32 在 32G 卡与车道并行会 OOM（10-19 三轮实测），届时按 B24 纪律降 bs 重派
- 新科学信号（本轮落地判读）：spliceai ERNIE lora s17 random 0.575 / RNAFM full 0.542 / Sc-300M full 0.463 vs micro lora 0.608——碱基级 3 分类上官方系 lora 稳定；frozen 0.35-0.39（ERNIE）与 micro frozen 0.39-0.44 同档

## 2026-10-23 晚（1023b 续：占满三车道 + 双开竞态处置 + RNA-FM frozen 首格落地）

- **GPU 占满铁律执行**：q_spl650（650M lora×6格）/ q_splmega2（mega lora×6格）/ q_splnbfroz（RNAFM+NB frozen×12格）三车道启动——GPU 12.4G→31.6G/32G 99% util（16 进程）
- **发现并处置双开竞态（B24 新变体）**：monitor v2 的 RESPAWN 逻辑与仍存活的旧 lane worker 产生双实例（q_splmega2 ×2 / q_splnbfroz ×2）→ 同一 run 双进程抢 ledger 行（650M s29 与 mega s29 各出现两份训练进程）→ kill -9 冗余实例（2763348/2840345/2814947 一侧）；残余影响：rnafm frozen s29 被双开 OOM 后 stale-reset 归 pending，由 v2 respawn 的实例重新认领
- **教训（B27 候选）**：monitor respawn 前必须先检测「该 lane 的 bash 进程是否已有存活实例」——grep .sh 匹配了两个不同路径形态（绝对路径 vs 相对路径 cwd 形态），导致误判死亡 + 双开。已用 kill 清单处置；monitor 判活改用 pgrep -f 全匹配
- RNA-FM spliceai frozen：s17 0.3791 / s43 0.3681（3 种子齐 2，s29 重跑中）——与 ERNIE frozen 0.35-0.40 同档
- RC=124 ×3（650M/mega lora s17 4h timeout 到点）——大模型 spliceai 144628 训练集 bs16 单 epoch ~2h+，6 epochs 超出 4h timeout 协议；**车道自动继续 s29（runner claim 幂等），s17 需后续补**（epochs 6 不变、timeout 提升至 8h 或减 n_train）
- 真态：ledger 2639 行 done 2582；GPU 26.6G 99%；monitor v2 + q_master + 9 lane bash 在岗

## 2026-10-23 晚二（1023c：monitor v2.1 双开竞态根治 + s17 timeout 格重派）

- **monitor v2.1 装岗（B27 纪律落地）**：判活从 ps aux | grep（路径形态匹配漏洞）改为 **pgrep -f 全匹配** + 每 lane spawn 锁（mkdir 原子 + 5min 自动释放）——双开竞态根治；装岗后各车道单实例验证通过（q_spl650/splmega2/splnbfroz/spl_s17_retry 全部 =1）
- **spliceai s17 timeout 格重派**：q_spl_s17_retry（mega/650M lora s17 random+family 4 格，10h 预算——RC=124 的 4h 预算修正：144628 × bs16 × 6ep ≈ 8-12h）
- GPU：26.6G→30.6G/32G 100%（14 训练进程）
- 真态：ledger 2641/2582；mega lora s29 ep2 / 650M lora s29 ep1 心跳正常；RNA-FM frozen s43 0.3681 落地（MICRO_F1 0.9997 揭示 macro-F1 主口径下正类稀疏的严格性）
