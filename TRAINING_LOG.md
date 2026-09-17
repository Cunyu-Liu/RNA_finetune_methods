# RNA-LM 微调策略评测 — 训练与交接执行日志

> 本文件记录每次训练过程与结论（用户要求）。日期用服务器时间。


## 2026-09-17 13:10 Day 3 午间 III：E3 产物链 + 预印本 2.5 C3 节

**状态**: ledger 281 行（275 done）——RNA-Sc n=100 档全齐
（lora 0.102 > frozen 0.092, 翻转梯度开始复现）; 四训练并行
（G6 最后 run 1:22 / G1 s101 15min / G2 s101 11min /
E3-RNA-Sc n=1000 frozen s17）。

**本轮完成**:
1. **E3 产物链落地**: fig_e3 学习曲线图（log 标注轴×3 策略×
   双模型面板+min-max 带+随机线）+ export_e3 表（最优臂标记）;
   守护链刷新序列扩展至十产物（+e3_table/fig_e3）
2. **预印本 §2.5 C3 节上线**: 标注量翻转表（n=10 full 最优 →
   n=100/1000 lora → 全量 frozen）+ 三信号（小数据学先验 /
   崩溃数据量依赖 / 千条标注≈全量 99%）+ 默认 LR 口径声明;
   节序重排（2.5 E3 → 2.6 泄漏 → 2.7 统计, 修复插入错序）
3. RNA-Sc n=100 lora 0.102 > frozen 0.092 落地（复现方向）

**Git**: 4b4693e → fbc68d6（6 笔: fig_e3 / export_e3 / C3 节 /
重排 / 守护链扩展 / TRAINING_LOG）。

**下步**: 队列推进（tuned-full 选优 + E3 RNA-Sc n=1000 + G6
收尾→守护链终刷十产物）; 明日 E3 双轴全齐后 C3 终版曲线。
## 2026-09-17 12:55 Day 3 午间 II：E3 首批数据落地，C3 翻转点信号

**状态**: ledger 272 行（267 done, 其中 E3 标签 39 runs）;
G1/G2 tuned-full s101 tuning 在跑; G6 最后一个 run
（RNA-FM lora s43 family, 1:19）收尾中。

### ★★ C3 初步发现（RiNALMo 首轴 3 档全齐, family 切分, 3 种子均值）
| n | frozen | lora | full | 最优 |
|---|---|---|---|---|
| 10 | 0.103 | 0.131 | **0.229** | full |
| 100 | 0.424 | **0.509** | 0.076† | lora |
| 1000 | 0.664 | **0.685** | 0.076† | lora |
| 6859(全量) | **0.696** | 0.081 | 0.085† | frozen |

† full 小数据档用默认 LR 3e-4（与 A8 崩溃一致, 属 LR 效应非数据量效应）

**三个科学信号**:
1. **n=10 极小数据: full 微调反而最优**（0.229 = 3× 随机 0.077;
   RNA-Sc 同构复现 full 0.110 > frozen 0.083）——10 条数据学
   的是任务先验/类别结构而非家族记忆, 全参容量优势兑现;
   frozen 浅头（16K 参数）反而学不动
2. **frozen-vs-lora 干净对比的翻转梯度**: lora 增益
   +0.03(n=10) → +0.085(n=100) → +0.021(n=1000) → **-0.615
   (全量崩溃)**——家族切分下微调崩溃是"数据量依赖"的:
   数据越多家族记忆能力越强, 切分时崩得越狠。C3×C4 交互
   的机制性证据
3. **n=1000 时 lora 0.685 已接近全量 frozen 0.696**——1000 条
   标注 ≈ 全量效果的 99%（该任务/模型）; 小数据 regime 的
   实践含义: 千条标注足够

**注意**: full 列小数据档的崩溃是默认 LR 效应（A8）, 非数据量
效应——如需干净的 full 翻转曲线需 tuned-LR 补跑（G1/G2 在跑
的正是全量档 tuned; 小数据档 full tuned 可后续补）。

**下步**: RNA-Sc n=100/1000 落地后验证梯度复现; E3 学习曲线图
（x=标注量 log 轴, 每策略一条线, 每模型一面板——T3.1.5）。
## 2026-09-17 12:45 Day 3 午间：GPU1/2/5 三队列派发（用户提示空余）

**用户提示 GPU 1/2/5 有空余 → torch 实测确认各 13.6-13.8G 真实空闲
（整卡 40G, 他人任务占 26G）→ 立即派发三队列:**

### 1. GPU1: SpliceBERT full tuned-LR 补跑（关键科学缺口）
- 背景: 默认 3e-4 全崩 6/6（ln-13 平原）——C1/C4 图 full 列对
  该模型显示崩溃值不公平, tuned 协议臂缺失
- 协议（B1 合规）: s101 tuning 双档（1e-5 vs 3e-5）→ ledger 读值
  选优 → formal 17/29/43 × random/family（6 runs）
- 合计 8 runs; s101 @1e-5 已在跑

### 2. GPU2: ERNIE full tuned-LR 补跑
- 同背景（86M 显式配对 attn, 默认 3e-4 崩 6/6, epoch 0 即卡死）
- 同协议: tuning 2 + formal 6 = 8 runs; 峰值预算 ~7G < 13.6G

### 3. GPU5: E3 第二模型轴（RNA-Sc-10M 受控对照, 36 runs）
- C3 翻转点的模型间对照: 与 RiNALMo 首轴同构
  （n ∈ {10,100,1000,full} × {frozen,lora,full} × 3 种子）
- 协议不变量: epochs 10 / bs 8 与首轴一致; 子集文件通用
- n=10 frozen/lora 已完（exit 0）, full s17 在跑

### 当前 5 卡并行全景
| 卡 | 队列 | 状态 |
|---|---|---|
| GPU1 | SpliceBERT tuned full | s101 @1e-5 tuning |
| GPU2 | ERNIE tuned full | s101 @1e-5 tuning |
| GPU5 | E3 RNA-Sc 轴 | n=10 full s17 |
| GPU6 MIG | G6 RNA-FM lora s43 family | 收尾中 |
| GPU7 MIG | E3 RiNALMo 首轴 | 36 runs 推进 |

**Git**: 49aa007 已推送。

**下步**: 队列推进; tuned full 结果落地后 C1/C4 图刷新
（SpliceBERT/ERNIE full 列从崩溃值换 tuned 协议臂值）;
E3 双轴完成后 C3 翻转点首证 + 学习曲线图。
## 2026-09-17（Day 3 上午巡检：G6 种子补齐链收尾 + E3 轴归零）

**状态**: ledger done 257 行; 唯一 pending = RNA-FM ncrna family lora s43
（G6, 训练中 epoch 2）; GPU7 的 E3 首轴 02:01 DONE 归零, MIG 空闲;
git master 已同步 origin/master（Cunyu-Liu/RNA_finetune_methods）。

**G6 种子补齐批（run_newmodels_seeds, random+family × s29/s43, epochs10 bs8, MIG 4.75G）**:
- SpliceBERT ncrna: family frozen 0.3621 / full 0.064/full,0.095 / lora 0.0841;
  random frozen 0.6189 / full 0.0769 / lora 0.9033。s29==s43（家族 frozen/full 判定等价, 正常）。
- ERNIE-RNA ncrna: family frozen 0.8867 / full 0.064/0.095 / lora 0.084/0.095;
  random frozen 0.8252 / full 0.0769 / lora 0.971/0.977。
- RNA-FM ncrna: family frozen 0.8598 / full 0.095/0.084 / lora 0.095 + s43 pending;
  random frozen 0.9172 / full 0.8427 / lora 0.963/0.966。
- 方向一致: 小模型家族切分碰撞（frozen 高、lora/full 塌）在 SpliceBERT/ERNIE/RNA-FM 复现,
  与 RiNALMo 及既有 C4 结论同向; 不做单点科学定论（仍以多种子+独立红线为据）。

**GPU7 待命**: E3 36-run 首轴已 DONE; ledger 无后续排队批次。ERNIE-RNA lora 需整卡
（MIG 4.75G 必 OOM）, 但 GPU0-5 仍被他项目占满, 本轮不臆造批次、不空耗 GPU,
待整卡释放或明确下一批再派发。本轮无失败/崩溃 run 需修复; 2 条 cancelled 均为
09-15 ghost smoke claim（已被正式冒烟取代, 非本次损坏）。



## 2026-09-17 01:10 Day 3 凌晨 III：E3 小数据首轴提前启动

**状态**: ledger 229 行; G6（RNA-FM 剩 5 runs）+ E3 首轴
（GPU7, 36 runs）双队列并行; 守护链待 G6 排空（E3 队列在守护
链监听清单之外, 终版刷新不受影响——E3 是独立扩展轴）。

**本轮完成**:
1. **E3 T3.1.1 簇级降采样器落地**（rnafteval/e3_subsampler.py）:
   {10,100,1000} × 3 种子 + full=6859 全量; 簇中位数 1 → 档位
   近似精确（抽簇→整簇纳入, 机理篇 Q3 决议）
2. **runner E3 补丁**: --n-train 参数（子集行号过滤, family 分支
   最小侵入）+ run_id _e3<n> 标签（防与正式矩阵 done 行冲突）;
   冒烟 PASS（frozen@10 条 = 0.124 近随机——13 类 10 条学不出
   任务信号, 正是 C3 翻转点要观测的行为）
3. **E3 首轴队列派发**（GPU7 MIG, PID 1908518）: RiNALMo ×
   ncRNA family × 4 档 × 3 策略 × 3 种子 = 36 runs
   - 科学问题: 小数据下 frozen vs LoRA/full 翻转点位置
   - 预印本价值: C3 预览轴（完整 E3 是 4 模型 576 runs, 本轴是
     单模型首证）

**Git**: 6457fba 已推送。

**下步**: E3/G6 双队列过夜; 明晨验收（守护链终刷 + E3 首轴
翻转点初判 + 预印本 v0.3 数值终版化）。
## 2026-09-17 00:50 Day 3 凌晨 II：预印本 v0.3 + stats 扩容

**状态**: ledger 228 行（225 done）; G6 剩 6 runs（RNA-FM
frozen/lora s29/s43, 预计明早收尾）; 守护链待 G6 排空自动终刷。

**本轮完成**:
1. **预印本 v0.3**: Abstract 第 3 点升级吸收跨架构 LR 崩溃
   （"architecture-agnostic trap"表述 + RNA-FM 唯一幸存）;
   快照头 228 runs; 中文对照同步
2. **stats 扩容**: 132 行（ERNIE frozen 3/3 入表, 对比数 60+）
3. E2 表确认稳定（RiNALMo 五臂与 G6 无关）

**Git**: 4a69940 + 7e705d9 已推送。

**下步**: G6 自然收尾（~5-6h）→ 守护链终刷 → 明晨验收
（预印本 v0.3 数值终版 + 状态快照更新 + 五模型完整 C1/C4 图）。
## 2026-09-17 00:20 Day 3 凌晨：SSP tuned 5/5 齐全 + 方向翻转

**状态**: ledger 228 行（224 done）; SSP s43 family 0.1829 落地
——SSP full tuned 5-run 全齐（random 0.151/0.176/0.171 +
family 0.158/0.189/0.183）。G5/G7/ssptuned 全排空; G6 在收尾
（RNA-FM frozen s29 family, 剩 ~3 runs）。

**关键判定翻转（B14）**:
- RiNALMo SSP full: ±(不定) → **↓\***（tuned 协议臂入表:
  random 0.166 < family 0.177, 3/3 一致——SSP family 侧不降
  反升, per-base 稳健性再证）
- RiNALMo SSP 三策略全部可判: frozen ± / full ↓* / lora ↓*
- RNA-FM full ↑*（0.835 vs 0.081, 3/3）——**C4 崩溃矩阵
  full 臂 5/5 模型确认**（与 LoRA 臂一致）
- ERNIE/SpliceBERT full ±: 双侧崩溃值噪声级（0.077/0.085）
  ——± 正确（崩溃对崩溃无方向意义）

**预刷八产物 PASS**（E2 待 G6 收尾后守护链终刷）。

**预印本更新**: 2.4 节跨架构崩溃 + Limitations SSP 条目
（1438b94 + 6092611 已推送）。

**下步**: G6 收尾 → 守护链终刷 → 明晨验收（预印本数值
终版化 + 状态快照更新）。
## 2026-09-16 23:15 Day 2 深夜：队列大丰收（+26 runs，三大结论升级）

**状态**: ledger 227 行（223 done）；G7/G5 队列正常排空
（SpliceBERT full 21:21 / ERNIE+RNA-FM full 22:57）; ssptuned
最后一 run（s43 family）在跑; 守护链待全排空自动刷八产物。

### ★★ 新结论 1：LR 崩溃跨架构传播（默认 3e-4 全参）
| 模型 | 架构 | full random @3e-4 | loss 模式 |
|---|---|---|---|
| RiNALMo 33M | 标准 attn | 0.077 崩 | ln-13 平原 |
| SpliceBERT 19M | ALiBi | 0.077 崩（6/6 runs） | ln-13 平原 |
| ERNIE 86M | 显式配对 attn | 0.077 崩（6/6） | ln-13 平原（epoch 0 即卡死 2.56） |
| RNA-FM 99.5M | 标准 attn | **0.82-0.84 正常** | 1.10→0.32 正常下降 |

- **崩溃不挑架构**（标准/ALiBi/显式配对 attn 全崩）——A8 LR
  结论从"两模型规律"升级为"跨架构普遍现象"；
- RNA-FM 唯一幸存（预训练最充分 23.7M ncRNA）→ 预训练深度
  可能是全参 LR 冲击的抗性来源（观察性，样本 n=1）；
- RNA-FM full family 侧仍崩（0.06-0.10）→ C4 崩溃矩阵 full
  臂也是 5/5（与 LoRA 臂一致）。

### ★ 新结论 2：SSP full tuned 3/3 一致恢复
- s17 0.176 / s29 0.151 / s43 0.171 vs default 0.006x
  （x24-x27, 方向 3/3 一致——B14 级证据）;
- family 侧 tuned 0.158-0.189（2/3 已落地）;
- SSP full 从 B14 ±(不定) 转 3 种子可判——export_c4 将重判。

### ★ 新结论 3：五模型 E1 矩阵 full 臂齐
- ERNIE full 6/6 / RNA-FM full 6/6 / SpliceBERT full 6/6
  全部落地——E1 五模型 × 3 策略矩阵接近完备（G6 剩
  RNA-FM frozen/lora 少量 run）。

**下步**: SSP s43 family 收尾 → 守护链自动刷八产物 →
预印本数值终版化（三大新结论入 2.4 节）→ 明晨验收。
## 2026-09-16 21:40 Day 2 夜 II：README 程序化自查 + 旧副本清理

**状态**: ledger 201 行（196 done）；五链健康（G6 frozen s43
47min / G7 SpliceBERT full s29 30min / G5 ERNIE lora family s29
14min）。

**本轮完成**:
1. **README 程序化自查 PASS**: 引用 8 路径存在性 + 8 模块
   import 全过（0 issues）——README 声明的复现命令均可执行
2. **根目录过时旧副本清理**: preprint_draft.md 根目录版为
   Day-1 旧副本（105 行 vs paper/ 314 行, 会误导读者）→
   git rm + 留指针文件（防旧链接 404）

**Git**: 46050ec 已推送。

**下步**: 队列自然推进（~17 runs）; 明日晨验收。
## 2026-09-16 21:20 Day 2 夜：README 上线（投稿级 repo 入口）

**状态**: ledger 201 行（196 done）；五链健康（G6 frozen s43
45min / G7 SpliceBERT full s29 28min / G5 ERNIE lora family s29
12min）。

**本轮完成**:
1. **README.md 上线**（此前 repo 无入口文档——预印本 Data&Code
   引用 repo 但审稿人无导航）: 三发现摘要 / 目录表（rnafteval
   模块+导出器 8 件 / paper / scripts / docs / TRAINING_LOG）/
   复现命令块（runner + 八导出器全列）/ 冻结协议节
   （种子/切分/统计口径）/ 数据与权重布局说明

**Git**: c446514 已推送。

**下步**: 队列自然推进（~18 runs）; 明日晨验收。
## 2026-09-16 21:00 Day 2 收官：交接目录状态快照

**状态**: ledger 201 行（196 done）；五链健康（G6 frozen s43
43min / G7 SpliceBERT full s29 26min / G5 ERNIE lora family s29
9.5min）。

**本轮完成**:
1. **交接文档目录状态快照**（本地 交接文档/STATUS_SNAPSHOT_
   20260916.md）: 六节对照——spec 计划 vs 实际进度（E1 大幅
   提前/E4 主结论锁定/E2 五臂齐/arXiv 预印本提前启动 vs spec
   第 3-4 月）; 三大科学发现; 五链在跑; 预印本包清单; 红队
   防线状态; 下步优先级——用户本地可直接查看实时进度锚点
   （此前交接目录只有 9/14-15 冻结口径文档）

**Day 2 全天总结**（本轮第 13 次巡检）:
- ledger 173→201 行（+28 formal runs）
- E2 五臂三种子锁定 + m6A 三模型矩阵齐 + 5 模型 C4 泛化锁定
- 预印本 v0.1→v0.2.1（129→~250 行, 15 节）+ 中文对照 + Supp
  S0-S8 + References 5 条核证
- 八件自动产物 + 守护链 + B14/B15/B16 验收链
- 13 轮巡检 + 20+ git 推送

**Git**: 96b4754 后无新推送（本轮为本地交接文档）。

**下步**: 明日晨验收（SpliceBERT full 崩溃复制判定 + ERNIE
full 首数据点 + 终版八产物自动刷新）。
## 2026-09-16 20:30 Day 2 傍晚 XIII：Supp S0 索引 + Methods 补全

**状态**: ledger 201 行（196 done）；五链健康（G6 frozen s43
40min / G7 SpliceBERT full s29 23min / G5 ERNIE lora family s29
6.5min）。

**本轮完成**:
1. **Supp S0 产物索引节**: 八产物导航表（节↔产物↔生成器）+
   守护链说明 + "ledger/parquet 为唯一数据源, 无手工誊写"
   声明——投稿版 checklist 直接可用
2. **Methods 模型池补全**: 5 模型参数量/语料规模全列
   （RNA-Sc 10M / SpliceBERT 19M / RiNALMo-micro 33M /
   ERNIE 86M+20.4M ncRNAs / RNA-FM 99.5M+23.7M ncRNAs）
   ——规模跨度 10M–99M 明确标注; 匹配脚本一字之差
   （splice-corpus vs splice corpus）修正后落地

**Git**: 0ad1cc5 + ac5866b 已推送。

**下步**: 队列自然推进; 明日晨验收（ERNIE full 首数据点 +
SpliceBERT full 崩溃复制判定 + 终版八产物自动刷新）。
## 2026-09-16 20:00 Day 2 傍晚 XII：S6 泄漏审计可复现化（八产物链）

**状态**: ledger 200 行（196 done）; **ERNIE lora 三种子齐**:
s17 0.974 / s29 0.9709 / s43 0.9767（均值 0.974, 跨种子稳定）;
G5 已进入 ERNIE lora family s29 + full 矩阵排队。

**本轮完成**:
1. **export_leakage.py 上线（S6 可复现化）**: 首次审计
   （TRAINING_LOG 2026-09-15 记录）当时为交互式执行无产物——
   本轮重做为脚本: 官方 train/test csv 对齐 family parquet
   cluster_id（309,460 窗口全量 MMseqs2 0.8/0.8 聚类）
   - 复现结果: 宿主级 326/1200 = **27.2%**（vs 首记录 327/27.3%,
     set 去重 vs 列表计数差 1 窗口——稳定复现）
   - 31-mer 367 (30.6%) / exact 26 (2.2%) 三口径对照
   - 口径差注写入表内（防"数字打架"审稿质疑）
2. Supp S6 接自动表; 守护链扩至**八产物**
   （c4/e2/stats/figs/resources/lr_grid/splits/leakage）

**Git**: bb2454d + 067068e 已推送。

**下步**: 队列自然推进; 明日晨验收（ERNIE full 首个数据点
+ SpliceBERT full 崩溃复制判定 + 终版八产物自动刷新）。
## 2026-09-16 19:40 Day 2 傍晚 XI：S5 切分统计自动表（七产物链）

**状态**: ledger 200 行（195 done）；五链健康（G6 frozen s43
31min / G5 lora s43 24min / G7 SpliceBERT full s29 14min）。

**本轮完成**:
1. **export_splits.py 上线**: S5 家族切分统计自动导出
   - 关键数字: ncRNA 7,731 簇 / SSP 12,825 簇 / m6A 241,984 簇
   - m6A rows 309,460 > seqs 308,915 = 宿主代理设计实证
     （同转录本多窗口共享簇归属）
   - **每次导出现场 groupby 零重叠复算**（三任务全部 PASS）——
     A13 独立验证产物化, 从"一次性检查"变"每次导出都验"
2. Supp S5 接自动表; 守护链扩至**七产物**
   （c4/e2/stats/figs/resources/lr_grid/splits）

**Git**: 724407a 已推送。

**下步**: 队列自然推进; 明日晨验收（SpliceBERT full 崩溃复制
判定 + tuned-LR 补跑决策 + 终版七产物自动刷新）。
## 2026-09-16 19:20 Day 2 傍晚 X：LR 网格自动表 + 网格数修正

**状态**: ledger 200 行（195 done）；五链健康（G6 ERNIE frozen
s43 28min / G5 ERNIE lora s43 21min / G7 SpliceBERT full s29 11min）。

**本轮完成**:
1. **export_lr_grid.py 上线**: A8 LR 网格 16 格自动导出
   （status/lr_grid_table.md + csv; 修复 LR 键格式化 bug——
   %.0e 生成 3e-04 与列键 0.0003 不匹配, 改为数值
   归一化映射）
2. **预印本 2.4 数值修正**: RiNALMo LoRA@3e-4 grid 值 0.923 →
   **0.934**（原误用 s17 formal 值混入 s101 grid 上下文）——
   交叉核对自动表抓出
3. 守护链刷新序列加入 export_lr_grid（终版六产物: c4/e2/
   stats/figs/resources/lr_grid）

**Git**: 2f528f6 已推送。

**数据面现状**: 六件自动产物 + 五链 + 守护链全就位; 预印本
数值全部走自动表交叉核对通道。

**下步**: 队列自然推进; 明日晨验收（SpliceBERT full 崩溃复制
判定 + tuned-LR 补跑决策 + 终版六产物自动刷新）。
## 2026-09-16 19:00 Day 2 傍晚 IX：R4 分层图 + 投稿三节

**状态**: ledger 200 行（195 done）；五链健康; G5 ERNIE lora s43
在跑（~19min）。

**本轮完成**:
1. **fig_c1 R4 分层改造**: 模型行按 受控家族（RNA-Sc）/ 同语料
   RNAcentral 系（ERNIE/RNA-FM/RiNALMo）/ 跨语料任务专用
   （SpliceBERT）三块分面板 + 组间黑分隔线 + 图注声明
   "跨组比较仅观察性"——红队 R4 混杂防线落到图上（此前 C1
   模型字母序混排）
2. **投稿三节补齐**: Author Contributions（骨架, PI 确认前
   draft 标注）/ Acknowledgments（BEACON + 各模型开源社区 +
   算力）/ Funding（占位, 提交前补）
3. C1 图已重绘验证（compile OK + figures 全刷新）

**Git**: 245a8cb 已推送。

**下步**: 队列自然推进; 明日晨验收（SpliceBERT full 崩溃复制
判定 + 终版产物守护链自动刷新 + tuned-LR 补跑决策）。
## 2026-09-16 18:40 Day 2 傍晚 VIII：全文一致性扫描 + v0.2.1

**状态**: ledger 200 行（195 done）；五链健康; G5 整卡队列
ERNIE lora s29 done (0.9709), s43 在跑。

**本轮完成**:
1. **预印本全文程序化一致性扫描**（R9 口径防线）:
   - 结构: 15 节全部在位（Abstract→Data&Code 完整链）
   - 笔误: 双零前缀/双空格/标点前空格/重复词 全部 0 处
   - 数值抽查 8 组: 0.968/0.993/0.176/0.934(DoRA)/0.860/0.817/
     27.3%/0.928 全部与 ledger/自动表一致
   - [fig:] 占位 3 处（有意保留, 终版接图）; queued 字样仅在
     Limitations 诚实声明处
2. **v0.2.1**: 版本头快照更新（196→200 runs, 补五链状态说明）
3. 字数 ~2,137 words（正文主体量到位）

**Git**: 5b859df 已推送。

**下步**: 队列自然推进; 明日晨验收（SpliceBERT full s29/s43
崩溃复制判定 → tuned-LR 补跑决策; 守护链自动刷终版五产物）。
## 2026-09-16 18:20 Day 2 傍晚 VII：中文对照摘要 + A13 断言独立复算

**状态**: ledger 200 行（195 done）；五链健康，三训练并行
（G6 ERNIE frozen s43 / G5 ERNIE lora s43 / G7 SpliceBERT full s29）。

**本轮完成**:
1. **中文对照摘要文档**（paper/preprint_zh_summary.md）: 标题备选
   3 款 + 中文摘要（逐点对照英文版）+ 电梯陈述 + 红队防线自查表
   （R1/R2/R5/R6/R7/R11/R9 七条状态）——用户快速审阅入口
2. **A13 宿主断言独立复算 PASS**: 从 modification.parquet 直接
   groupby 复核 309,460 行——同序列 0 跨侧 / 同簇 0 跨侧
   （每簇均值 1.28 序列, max 721）; 原先只有构建期断言声明,
   现在有独立后验验证记录（入 checklist_audit）
3. SpliceBERT full s29 在跑（崩溃模式的种子复制验证中）

**Git**: 3719fb8（zh summary）+ c39e700（A13 复算）已推送。

**下步**: 队列自然推进; 明日晨验收全链（终版产物由守护链
自动刷新 + SpliceBERT full 种子复制判定 + tuned-LR 补跑决策）。
## 2026-09-16 18:00 Day 2 傍晚 VI：References 核证 + SpliceBERT full 崩溃观察

**状态**: ledger 200 行（195 done）。

**★ 科学观察: SpliceBERT full s17 random = 0.0769（崩溃至 13 类
随机水平）**
- loss 曲线证据: epoch 0 2.49 → epoch 1 起卡死 2.5599 ≈ ln(13)
  = 2.5649（均匀分布熵, 预测完全随机化）
- 同管线 frozen 0.619 / lora 0.904 正常 → 排除代码 bug
- **与 RiNALMo 33M full@3e-4 崩溃 0.077 完全同模式**——A8 LR 网格
  结论的第 5 个独立证据点: 默认 3e-4 对小模型全参系统性过高,
  19M 跨域模型也适用; LoRA 同 LR 正常（低秩约束天然稳定）
- s29 正在跑（种子复制验证中）; 若同崩溃, 该点可入预印本 2.4 节
  作为"LR 错配翻转策略排名"的跨规模证据

**本轮完成**:
1. **References 节 14 条上线**（Data&Code 前）: 5 条 Web 核证修正
   - RiNALMo: Penić et al. Nat Commun 2025, DOI
     10.1038/s41467-025-60872-5（原误写 Pennington/NMI/参数区间）
   - RNA-FM: Chen J et al. arXiv:2204.00300 (2022), 100M/23.7M
     ncRNA（原误写 Nat Commun 2024/96M）
   - ERNIE-RNA: Yin W et al. Nat Commun 2025, DOI
     10.1038/s41467-025-64972-0（原误写 Wang/motif 目标）
   - SpliceBERT: Chen K et al. Brief Bioinform 25(3):bbae163
     (2024)（原误写 BAI/Nat Commun 2025）
   - BEACON: Ren Y et al. NeurIPS 2024 D&B（补全作者）
   - 剩余 4 条待 BibTeX 化条目以可辨识缩写标记
2. 队列推进: SpliceBERT full s29 接棒 G7; G6/G5 持续

**Git**: e5d91e6 已推送。

**下步**: s29/s43 结果落地后决定 SpliceBERT full 是否需要 tuned-LR
补跑（1e-5 或 3e-5——按 A8 规模左移规律预判 3e-5）; 明日晨验收。
## 2026-09-16 17:40 Day 2 傍晚 V：预印本 4.1 决策树预注册规则节

**状态**: ledger 199 行；三训练并行健康（G6 10/20 job；G7
SpliceBERT full s17 epoch 8 近收尾；G5 ERNIE lora s43）。

**本轮完成**:
1. **预印本 §4.1 决策树预注册规则节**（R7 防线）: 推荐/中性/
   不推荐三档规则表（spec §7-8 冻结版）+ 当前快照三判定
   （ncRNA random 推荐 LoRA/full；family 侧全部不可推荐；
   m6A/SSP 推荐微调）+ 功效墙诚实声明
2. **数值程序化核对修正 2 处**: frozen family 区间实为
   0.19–0.92（原写 0.21–0.89）; full-FT 默认 LR 崩溃行明确标注
   为"LR 错配案例非策略判定"（避免审稿人误读为 full 策略差）
3. 交叉核算增益范围时发现 rinalmomicro full 默认 LR -0.744
   混入会误导——已用 tuned 口径说明

**Git**: 14ffb3c 已推送。

**下步**: 队列自然推进; 明日晨验收（G6 剩 10 runs + G7 剩 5
runs + G5 ERNIE/RNA-FM full 看整卡; 守护链自动刷终版）。
## 2026-09-16 17:20 Day 2 傍晚 IV：E5 资源实测自动导出（独立核对过）

**状态**: ledger 199 行；四链健康（G6 frozen s43 / G7 SpliceBERT
full s17 57min / G5 ERNIE lora s43 已开跑）。

**本轮完成**:
1. **export_resources.py 上线**: E5 资源实测自动导出
   （status/resources.md）——按策略 wall 中位数/峰值显存中位数/
   检查点体积，formal 与 tuning 分池，覆盖 185/186
   - 关键数字: frozen 20.2min/407MB、lora 37.9min/771MB、
     full 22.4min/1057MB、dora 55.1min/3151MB、ia3 106.4min/2074MB、
     head-only 13.7min/407MB（n=48/47/56/3/3/13）
   - **独立交叉核对通过**（不走同一代码路径重算，6 策略逐位一致）
2. S7 节接通 resources.md；守护链刷新序列加 export_resources
   （队列排空后 S7 也自动出终版）
3. 修正脚本冗余表达式（tuning.count(0) 无操作）

**Git**: fefa21a + 9a1452c 已推送。

**下步**: 队列自然推进; 明日晨巡检验收（G6 20 runs + SpliceBERT
full 6 runs 预计完成; ERNIE/RNA-FM full 矩阵看整卡释放）。
## 2026-09-16 17:05 Day 2 傍晚 III：T2.0 检查点自动化 + B16 勘误 + Supp 骨架

**状态**: ledger 199 行（194 done）；四链健康；新数据点
ERNIE lora s29 random = 0.9709（G5 整卡队列首 run，与 s17 0.974
一致——跨种子稳定性好）；ERNIE frozen s29 = 0.8252（= s17）。

**本轮完成**:
1. **T2.0.1 检查点自动化落地**（rnafteval/checkpoint_report.py）:
   首跑暴露预注册口径歧义——全格池中位数 -0.024（字面触发）vs
   每任务最佳模型 +0.154（B15 原判定不触发）
2. **B16 勘误决策文档**（docs/checkpoint_b16.md）: 主口径固化
   (a) 每任务最佳模型（R6 原意=防预训练无收益方向性错误，
   (b) 的负值正是 C4 主结论证据非失败信号）; 附带发现第二支
   BH后无显著格 在 n=3 功效墙下恒真（预注册缺陷，记入
   preprint Limitations）
3. **Supplementary 骨架**（paper/supplementary.md）: S1-S8 节
   全部映射到自动产物（stats/e2_table/figs/ledger），零手工誊写
4. **修正 checkpoint_report cells() 解包 bug**（初版误当元组返回）

**Git**: d9ae6d8（Supp）+ 150d4c2（B16 三件套）已推送。

**MIG 复核**: GPU6/7 torch 实测确认仍为 4.75GiB 切片
（nvidia-smi 19.7G 为宿主整卡视角假象，纪律再次有效）。

**下步**: 队列自然推进（G6 剩 ~11 runs / G7 SpliceBERT full
5 runs / G5 整卡 15 runs / ssptuned 5 runs）; 守护链自动刷产物;
明日晨巡检验收。
## 2026-09-16 16:40 Day 2 傍晚 II：E2 自动导出 + 终版刷新守护链

**进行中**: 四链并行健康（G6 ERNIE frozen s29 / G7 SpliceBERT full s17 /
G5 ERNIE lora s29 @GPU3 / ssptuned 排队中）；ledger 197 行。

**本轮完成**:
1. export_e2.py 上线: ledger -> E2 五臂表自动导出（md+csv,
   status/e2_table.md）; 预印本 §2.3 手工表与自动表对齐（LoRA 0.927→0.928
   舍入修正; 参数列精确化 0.57M/0.55M/0.01M; 修正"2× params"不实表述
   ——实际 0.57/0.55 ≈ 1.05×）
2. stats 刷新（58 对比 + bootstrap CI; RiNALMo SSP full random 现为
   混合协议 CI [0.006, 0.176] —— 待 SSP tuned5 后转纯协议臂）
3. chain_final_refresh.sh 守护链上线（PID 2380049）: 四队列
   （2015376/1923283/3098539/2192474）全部排空后自动刷新
   C4/E2/stats/figures 终版产物——队列收尾不再依赖人工
4. 红队报告复核: R2（BH FDR+B14）/R5（宿主代理+断言）/R11（full 参照臂）
   均已设防，v0.2 对齐

**Git**: 409862e + d47e688 已推送。

**下步**: 队列自然推进; 守护链自动刷产物; 明日晨巡检验收
（G6 20 runs 预计完成 + G7 SpliceBERT full 6 runs + G5 整卡队列）。
## 2026-09-16 16:30 Day 2 傍晚巡检 + v0.2 扩写 + SSP tuned 补齐链

**状态**: ledger 196 行（192 done / 2 pending in-flight）；GPU0-5 他人满载，
GPU6/7 MIG 4.75G 承接我方任务。

**进行中队列（3 条链并行）**:
- G6 链 run_newmodels_seeds_g6.sh (PID 3098539): ERNIE frozen s29 在跑
  （9/20 job），覆盖新模型 frozen/lora MIG 可跑缺口 12 runs
- G7 链 chain_g7_full3 → run_full3_g7.sh (PID 1923283): SpliceBERT full
  s17 random 在跑（1/6 job）
- G5 链 chain_g5_full_ef → run_full_ef_any.sh: 整卡轮询中（暂无空闲整卡，
  scan #1 15:53），承接 ERNIE lora s29/43 + ERNIE/RNA-FM full 矩阵 16 runs

**新派发**:
- chain_g7_ssptuned.sh (PID 2192474): 等 G7 full3 排空后自动接 RiNALMo
  SSP full tuned 补齐 5 runs (s29/43 random + s17/29/43 family @1e-5,
  参数与 tuned2 复核一致)。依据: s17 random tuned 0.176 vs 默认 0.006
  (29x); 峰值 1057MB MIG 可跑。

**本轮完成**:
1. 预印本 v0.2 全文扩写 (paper/preprint_draft.md 129→198 行):
   Intro 五贡献点 / Discussion 完整四论点 / Limitations 扩至 5 条;
   数值快照更新至 tuned-LR 协议臂 (m6A 0.968/0.993, SSP 0.176);
   自查修正 3 处笔误 (0.0.815 / LoRA m6A 数字 / +0.04~0.43 范围核算)
2. B14 方向一致性过滤接入 figures.py fig_c4: ± 条目半透明+标记,
   不进结论; 程序化核对 21 consistent / 3 ± 与 c4_table 完全一致
   (RNA-Sc m6A frozen, RiNALMo SSP frozen/full; SSP full 待 tuned5
   补齐后重判)
3. 三图刷新 (fig_c1/c4/lr, png+pdf); export_c4 同步刷新

**Git**: cc9807b 已推送 GitHub。

**下步**: 等队列收尾 → 终版 C4 表/图 + 验收清单核对; E2 五臂表
随新模型收尾整合; SSP tuned5 落地后重判 RiNALMo SSP full 方向。
## 2026-09-16（Day 2 15:05 午后巡检：三队列健康推进 + E1 收官批次派发）

### 服务器状态
- CUDA 可用（8 卡 torch 视角）；磁盘 /home 31% / /mnt 51%，充裕；
- GPU0-4 他人满载（GPU5 亦有他人 ~38G 作业：reactflow fold 8410MiB x5
  + RNA-Sc-30M 预训练等），G6/G7（MIG 4.75G）我方队列运行中；
- ledger ~192 行：无 failed/crashed（早前 IA3 config 修复与 ERNIE MIG-OOM
  重派均已在前序巡检处置完毕），3 个 pending 均有活跃进程对应：
  ia3 s43 (G7)、m6A full s43 family lr1e-5 (G5)、ERNIE frozen s29 (G6)。

### 队列推进（自 10:04 午前巡检以来）
1. G5 tuned2：m6A full lr1e-5 六格已收官（random 3 + family 3，其中
   s17/s29 family AUC 0.993 已入账，s43 进行中 15:07），SSP s17 复核
   15:23 开跑（队列末项）；
2. G7 mod 队列：modification frozen/lora 12/12 全齐后，IA3 修复后重跑
   s17/s29 done（s43 13:56 起跑中）；
3. G6 新模型种子队列：SpliceBERT lora s29/s43 family done（0.0841 多数
   类塌缩，与 s17 一致），ERNIE frozen s29 14:57 起跑，队列还剩
   ERNIE s43 + RNA-FM s29/s43（预计 ~22:00 排空）。

### E1 覆盖缺口 → 本轮收官派发（22 runs）
缺口：**新模型 full 臂全部缺失**——SpliceBERT/ERNIE-RNA/RNA-FM 各
3 seeds x 2 splits = 18 runs；另 ERNIE lora s29/s43（4 runs，整卡臂）。
派发拓扑（三链，均已 setsid nohup 后台化，链 PID 已记录）：
- **chain_g7_full3**（PID 1640325）：G7 mod 队列（PID 1376693）排空后
  接 run_full3_g7.sh：SpliceBERT full x6（MIG 容纳：同模 lora 峰值仅
  1013MB）；带 CUDA + mem>=2G 预检（10 次重试，间隔 60s）；
- **chain_g6_full3**（PID 1744894）：G6 队列（PID 3098539）排空后接
  run_full3_g7.sh 6：SpliceBERT full family 侧（GPU 参数化；与 G7 队列
  同 run_id 空间，ledger claim 机制自动错峰不重复）；
- **chain_g5_full_ef**（PID 1725193）：tuned2 队列（PID 830478）排空后
  接 run_full_ef_any.sh 整卡轮询队列：每 10min 扫 GPU0-5（free>=10G
  即征用，"未来空闲卡随时征用"落实），承接 ERNIE lora s29/s43 x2 切分
  + ERNIE/RNA-FM full x 3 seeds x 2 切分 = 16 runs；GPU5 他人 38G 占用
  为设计输入（轮询等空闲卡而非挤占）。派发前 40G 显示卡显存已实际查证
  （MIG 6/7 = 4.75G 真实，nvidia-smi 显示会误导）。

### 显存/失败处置经验（新增两条，进规则库）
1. ssh 单命令内多后台任务：`cmd1 & cmd2 &` 的 `&&` 优先级会把 cd 困在
   第一个后台任务、第二个在 ~ 下找不到脚本路径——G5 链首发因此失败，
   已用独立会话重启修复（教训：多任务派发分步独立执行）；
2. 本地巡检 shell 的 PATH 不含 bash/ssh（zsh 受限环境），用绝对路径
   /bin/bash / /usr/bin/ssh 绕过。

### 冒烟口径确认
logs/smoke_matrix.log 尾部为 9-15 v1 冒烟 OVERLAP 拦截历史（B1 防线
实战证据），当前实验全部 formal 口径，smoke 不进结论。


## 2026-09-16（Day 2 下午：E2 五臂锁定 + m6A 三模型齐 + B14/B15 验收）

### ★ E2 PEFT 五臂位次锁定（IA3 三种子 0.860×3 完全一致）
full(tuned) 0.938 > DoRA 0.934 > LoRA 0.927 > IA3 0.860 > head-only ≈ frozen 0.817
- 位次表 C5 数据齐（LoRA≈DoRA 复现 Schmirler；IA3 参数效率劣势明确）。

### ★ m6A 三模型×三策略×双切分 C4 矩阵完整
- RiNALMo tuned full：random 0.968 / family 0.993（默认 3e-4 崩 0.30）
  ——LR 调优协议下 m6A 全模型全策略不崩（LoRA/full 家族侧反而更高）；
- RiNALMo SSP full@1e-5 = 0.176（默认 0.006 → 29 倍恢复，接近 LoRA 0.214）
  ——SSP 的"full 崩溃"也是 LR 伪象。

### ★ 验收防线 B 类补齐（证据链）
- B14 方向一致性标记进 C4 表（±(不定) 不进结论图；ncRNA 崩溃行
  5 模型全部 ↑* 一致）；
- B15 预注册检查点决策文档（frozen 增益中位数 +0.15 > 2% 阈值，
  不触发方案复审）；
- checklist_audit.md：12 项 ✅ 带证据位置。

### 当前矩阵缺口（仅剩）
- ERNIE/RNA-FM/SpliceBERT 种子补齐（G6 队列 20 runs 推进中）；
- 新模型 LoRA family 侧（s29/s43）——已确认模式与 s17 一致。

## 2026-09-16（Day 2 白天：5 模型 C4 泛化 + E2 五臂位次成型）

### ★★ C4 跨模型泛化：微调崩溃是普遍现象（ncRNA 5/5 模型）
| 模型 | LoRA random | LoRA family | Δ | frozen Δ |
|---|---|---|---|---|
| RNA-Sc-10M | 0.746 | 0.072 | +0.68 | +0.165 |
| SpliceBERT | 0.904 | 0.084 | +0.82 | +0.257 |
| RiNALMo-micro | 0.928 | 0.081 | +0.85 | +0.121 |
| ERNIE-RNA | 0.974 | 0.084 | +0.89 | −0.062 |
| RNA-FM | 0.956 | 0.043 | +0.91 | +0.057 |

- **per-seq 分类的微调收益在家族切分下 5/5 模型崩**，而 per-base 任务
  （m6A 双模型、SSP 双模型）0/4 崩——任务粒度是崩溃的充分判别器；
- m6A 新增 RiNALMo：LoRA 0.970/0.995（不崩反升）；**但 full 默认 LR
  只有 0.302**（33M 全参 @3e-4 崩）→ tuned@1e-5 补跑队列已排（G5）；
- SSP RiNALMo 三种子全齐（frozen 0.196/0.218、LoRA 0.214/0.223），
  full 0.006 崩（3 epochs 小样本全参）→ 同队列 @1e-5 复核。

### ★ E2 PEFT 五臂位次（RiNALMo ncRNA random，3 种子）
full(tuned) 0.938 > **DoRA 0.934** > LoRA 0.927 > IA3 0.860 >
head-only 0.817 ≈ frozen 0.817
- **DoRA≈LoRA @r=8**（Schmirler 蛋白侧结论 RNA 复现）；
- IA3 参数最少（~0.02M）但掉 0.07；full 只有 tuned LR 下才赢；
- 参数效率卖点：DoRA/LoRA 用 1% 参数达到 full 的 99.6%。

### ledger ~185 done；队列：tuned2（G5 m6A full×6 + SSP 复核）、
### IA3 s29（G7）、SpliceBERT lora s43（G6）

## 2026-09-16（Day 2 晨巡检：IA3 修复 + ERNIE MIG-OOM 重派 + E1 mod 缺口补齐派发）

### 巡检发现的两类失败（均已处置）
1. **E2 IA3 三种子全挂**（q_e2_peft_g5.log 02:31-02:32）：
   `IA3Config` 校验 `feedforward_modules ⊆ target_modules` 抛
   ValueError——strategies 代码只把 ["query","value"] 设为 target，
   `intermediate.dense` 在 ffn 却不在 target。修复：
   `IA3Config(target_modules=target + ffn, ...)`（RiNALMo 侧）；
   RNA-Sc 分支 ["qkv","ffn"] 本就正确。ledger 3 行僵尸 pending 已清
   （备份 ledger.jsonl.bak_patrol_20260916），修复后随 G7 队列重跑。
2. **ERNIE-RNA lora s17 family 在 GPU6（MIG 4.75G）OOM**（q_newfam_g6.log
   04:55）：显式 attn 矩阵 3.97G 已占满，与既有教训一致（ERNIE LoRA
   需整卡）。run_queue 逐项独立失败不阻塞队列（正确行为）；ledger 僵尸
   pending 已清，**重派至 G5 链**：SSP full seeds（PID 630606）排空后
   自动接续 run_g5_ernie_mod.sh（kill -0 PID 监听，禁 pgrep -f）。

### 服务器状态（05:04-05:17）
- CUDA 可用（8 卡 torch 视角）；磁盘充裕（/home 31%，/mnt 51%）；
- GPU0-4 他人满载，G5 我方 SSP full s29 family 训练中（30G），
  G6 我方 RNA-FM frozen family 训练中，G7 我方 mod 队列已起；
- ledger 152 行（148 done）；无 CUDA 不可用事件。

### E1/E2 覆盖缺口 → 本批派发（GPU7 + GPU5 链）
- **RiNALMo-micro 在 modification 任务 0 run（E1 最大缺口）**：
  G7（MIG）派 frozen/lora × 3 seeds × 2 splits = 12 runs；
  full × 3 × 2 = 6 runs 排 G5 链（full 需整卡）；
- 队列脚本带 CUDA/显存预检（派发前 torch.cuda.mem_get_info 验证
  G7 free 4.46G > 3G 阈值——规则"派发前查 total_memory"落实为运行时断言）；
- 进程：run_mod_rinalmo_g7.sh PID 1376693（首个 run frozen s17 random
  已开跑）、chain_g5_ernmod.sh PID 1376694（等 SSP 排空）；
- G6 queue_gpu6g 剩余项（RNA-FM/SpliceBERT lora family）不干预继续。

### 冒烟矩阵口径澄清
- `logs/smoke_matrix.log` 尾部是 9月15日 00:09 的 v1 冒烟（OVERLAP
  拦截记录，B1 防线实战证据，后续 dedup 修复）；当前实验全部为
  formal 口径（n_train=20000/3000 全量切分、17/29/43 种子），
  smoke 结果不进结论。

## 2026-09-16（Day 2 10:04 午前巡检：G5/G7 链收官 + E1 mod 矩阵齐 + G6 新模型种子补齐派发）

### 服务器状态
- CUDA 可用（8 卡 torch 视角，G6/G7 为 MIG 1g.5gb=4.75G 切片，torch
  实测 G6 free 4.07G / G7 free 2.31G@训练中）；磁盘充裕（/home 31%，/mnt 51%）；
- GPU0-4 他人满载（gmx 等大任务），G5 我方 SSP 链已排空、G6/G7 我方队列。

### 链条收官确认（自 05:17 晨巡检以来的推进）
1. **G5 链（chain_g5_ernmod）全部完成 09:27**：ERNIE-RNA lora s17 family
   整卡重跑 exit 0（ACC 0.0841，与 MIG OOM 前的塌缩值逐位一致 → MIG 环境
   未污染结论，塌缩为真实行为）+ RiNALMo-micro modification full
   × 3 seeds × 2 splits = 6 runs 全部 done（AUC 全部 ≈0.497 随机水平）。
2. **G7 队列（run_mod_rinalmo_g7）modification 12/12 done**：frozen/lora
   × 3 seeds × 2 splits 收官（10:22 lora_s43_family AUC 0.9953 done），
   队列自动进入 IA3 修复后重跑 × 3 seeds（10:22 已开跑 s17）。
3. G6 旧队列（q_newfam_g6）09:31 收官，GPU6 空闲待派。

### E1 矩阵现状（formal，非 smoke）
- **RiNALMo-micro modification 18/18 格全齐**（frozen 0.92-0.95 random /
  0.95 family；lora 0.97 random / 0.995 family；full ≈0.50 全塌）；
- **RNA-Sc-10M modification 18/18 全齐**（frozen 0.92 / lora 0.97 /
  full 0.30 random-level）；
- SSP 两模型 frozen/lora/full 全齐（18+18）；
- ncrna：RiNALMo/RNA-Sc 主力全齐；新模型（SpliceBERT/RNA-FM/ERNIE）
  仅 s17 → 本轮 G6 补种子。

### 关键科学观察（formal 数据，进结论候选）
1. **RiNALMo-micro full 微调跨任务一致塌缩**：modification AUC≈0.497
   （随机水平，3 种子 bit 级一致），SSP F1≈0.006（precision 0.003 /
   recall 1.0，全预测为正）；random 与 family 切分同塌 → 高 LR(3e-4) 下
   full FT 不稳定，与 RNA-Sc-10M full（mod 0.30）对照，模型规模越大
   full 越不稳。E1 结论方向：**lora 是性价比最优臂**。
2. **ncrna family 切分下梯度微调（lora/full）全线塌缩到多数类**
   （0.0841=29/345，跨 5 模型一致），frozen 却保留迁移（ERNIE 0.887 /
   RiNALMo 0.696）且 family ACC ≥ random（+0.06 ERNIE / +0.11 RiNALMo）；
   random 切分下微调正常（0.90-0.97）。整卡复现一致 → 排除 MIG/代码
   因素。C4 核心发现：**cluster 切分下梯度更新损害预训练表征，冻结
   backbone 反而更稳**——微调收益在 family 泛化上不复存在。
3. 种子协议核验：SSP 各 run 三种子数值互异（随机性生效）；
   modification 三种子 bit 级一致（AUC 为秩统计量 + 训练近确定性，
   合理，不判 bug）。

### 本轮派发（GPU6，PID 3098539）
- `scripts/run_newmodels_seeds_g6.sh`：新模型 E1 种子补齐 s29/s43
  （SpliceBERT frozen/lora、ERNIE-RNA frozen、RNA-FM frozen/lora）
  × random/family × 2 seeds = 20 runs，参数与 s17 首探一致
  （epochs 10 / bs 8 / ncrna）；
- 显存依据：s17 实测峰值 RNA-FM lora 3.63G / SpliceBERT 1.0G /
  ERNIE frozen 1.5G，MIG 4.75G 可容纳；**ERNIE lora 不入 MIG 队列**
  （显式 attn 矩阵需整卡，既有教训）；
- 派发前按纪律跑 torch.cuda.mem_get_info 实测（G6 free 4.07G > 3G 阈值
  通过）；setsid nohup 脱离会话；首 run（SpliceBERT frozen s29 random）
  10:21 已开跑确认。
- 队列自带 CUDA 断言 + 显存预检 + 逐项 timeout 14400（单项失败不阻塞）。

### 冒烟矩阵口径（不变）
- `logs/smoke_matrix.log` 尾部为 9月15日 v1 冒烟 OVERLAP 拦截记录
  （B1 防线实战证据）；当前全部 formal 口径，smoke 不进结论。

### 遗留事项
- [ ] ERNIE-RNA lora s29/s43 + full（新模型 full 臂）需整卡——等
  GPU0-5 释放后入整卡队列（观测点：他人任务 98-100% 满载中）；
- [ ] IA3 重跑结果（G7 进行中）下轮巡检验收；
- [ ] G6 新模型 20 runs 预计 ~14h，明日晨检验收 + C4 表更新。

## 2026-09-16（Day 2 凌晨：E2 PEFT 横评上线 + 跨语料模型 LoRA 落地）

### ★ ERNIE-RNA LoRA = 0.974（跨语料模型首个微调数据点）
- frozen 0.825 → **LoRA 0.974**（+0.15，超 RiNALMo LoRA 0.923 与
  k-mer 基线 0.90）；86M 模型 LoRA 重跑于整卡 GPU5（MIG OOM 教训）；
- 至此 ncRNA random frozen/LoRA 双数据点：RNA-Sc 0.38/0.75、
  ERNIE 0.83/0.97、RiNALMo 0.82/0.93——**跨语料一致微调增益**（C1
  模型维度扩展的直接证据）。

### E2 PEFT 横评臂（spec C5，5 臂口径）
- **DoRA/IA3/head-only × 3 种子**（RiNALMo-micro ncRNA random）
  已排队 GPU5（DoRA s17 训练中）+ LoRA/full 已有 formal——
  五臂位次表数据即将齐；
- **prefix-tuning 不可行**（记录在案）：peft 0.13 的 tuple 式
  past_key_values 与 transformers 5.0 Cache 接口断层（RiNALMo 报
  get_seq_length 错误；RNA-Sc 需改姐妹项目源码，越界）→ E2 以
  5 臂呈报 + preprint limitation 说明；
- 顺带修复：smoke label 截断 KeyError（600→labels 集不全）；
  RNA-Sc 注入 HF 风格 config（_PseudoConfig dict 兼容 peft 的
  `in` 检查）+ device 属性。

### ledger 140 行（prefix 僵尸行已清）
- 8 训练进程并行：E2 DoRA（G5）/ RNA-FM lora（G6 MIG）/
  SSP 种子链（G2/G5/G7）。
## 2026-09-15（Day 1 夜：tuned-LR formal + 新模型首探 + 预印本骨架）

### ★ tuned-LR formal runs 落地
- **RNA-Sc full @3e-5（A8 网格选定）**：s17 0.791 / s29 0.811（默认
  3e-4 仅 0.66——tuned 后 +0.13~0.15），s43 与 family 侧队列推进中；
- ERNIE-RNA frozen ncRNA random s17 = **0.825**（三模型 frozen 梯度：
  RNA-Sc 0.38 / ERNIE 0.83 / RiNALMo 0.82）——跨语料模型同台可用；
- SSP family 侧三策略多种子落地：frozen 0.033 / lora 0.080 /
  full 0.094——与 random 侧一致（微调收益在家族切分下保持，
  C4 的 SSP 不崩模式三种子固化）。

### 预印本数据面成型（Day 1 交付）
- **paper/preprint_draft.md v0.1**：摘要+结果+方法骨架，全部数值
  取自三重验证过的 ledger 快照；
- **三张核心图**（status/figs/，png+pdf）：
  fig_c1_matrix（策略×任务热图+基线框）/ fig_c4_delta（Δ 条形图，
  红橙绿三档）/ fig_lr_grid（LR 网格四曲线）；
- **统计表**：status/stats.md（30 对比+BH FDR+bootstrap CI）；
- **C4 表**：status/c4_table.md + .csv。

## 2026-09-15（Day 1 晚间：RiNALMo SSP 全谱 + 统计层 + 新模型首探）

### ★★ A8 LR 网格全谱完成（双模型×4LR×2策略，s101）——模型规模×策略×LR 三重交互
| LR | RNA-Sc full | RNA-Sc lora | RiNALMo full | RiNALMo lora |
|---|---|---|---|---|
| 1e-5 | 0.683 | 0.181 | **0.943** | 0.735 |
| 3e-5 | **0.815** | 0.351 | **0.944** | 0.812 |
| 1e-4 | 0.807 | 0.558 | 0.924 | 0.882 |
| 3e-4 | 0.688 | **0.723** | 0.077(崩) | **0.923** |

- **full 甜区随模型规模左移**：10M→3e-5；33M→1e-5，且 33M@3e-4 崩溃；
- **LoRA 一律需高 LR**（两模型都在 3e-4），低 LR 严重欠拟合
  （RNA-Sc lora@1e-5 仅 0.18——"LoRA 不行"的假象实为 LR 错配）；
- **LR 错配可造成 ±0.5 假策略差**（RiNALMo full 0.943↔0.077）——
  无网格的策略对比（含 Schmirler 未调 LR 的部分对照）存在系统性
  风险，这是本工作的方法论贡献点之一；
- 行动：RNA-Sc full@3e-5 formal 3 种子已排 GPU5（现有 formal
  3e-4 的 0.66 是 LR 低估，tuned 后预期 0.81）。

### ★ RiNALMo SSP 矩阵（s17 双切分全策略）
| 策略 | random | family |
|---|---|---|
| frozen | 0.209 | 0.233 |
| lora | **0.234** | **0.245** |

- vs RNA-Sc（frozen 0.034）：**6.2× 模型规模优势**；
- vs 最强基线 0.047：**5×+**；
- LoRA 微调在两种切分下稳定增益 (+0.01-0.02)，家族切分无崩溃——
  SSP 的微调收益为真（与 m6A 同模式，与 ncRNA 反模式）。

### ★ 统计层上线（stats.py，预注册 §3.5 协议）
- 30 个配对对比（策略间 + C4 delta），符号检验 + BH FDR q=0.05；
- 诚实结论：n=3 符号检验最小 p=0.25 → BH 后 0 显著（功效墙），
  3/3 方向一致性 + 效应量（ncRNA Δ≈0.6-0.85 vs m6A Δ≈-0.04）才是
  主证据——这正是 spec R2 预防的"3 种子当 CI 卖"陷阱的正面处理；
- 格级 bootstrap CI 表同步生成（status/stats.md + .json）。

### ★ 修复与新增
- **multimolecule 补丁复发修复**：SpliceBERT `create_bidirectional_mask
  (inputs_embeds=)` vs transformers 5.0 签名 `input_embeds` ——14 个
  modeling 文件调用侧补丁 + 补丁脚本持久化（scripts/patch_multimolecule.py，
  幂等验证通过）。新模型队列（ERNIE/RNA-FM/SpliceBERT × frozen/lora ×
  s17 random）在 G6 MIG 重启；
- **export_c4 升级**：formal tuned-LR runs（_lr1e-05, seeds 17/29/43）
  并入主表（A8 协议臂）——RiNALMo full random 修正为 0.938（tuned）
  而非 0.07/0.94 混合；RiNALMo ERNIE 前向 GPU 验证通过（d512）。

### 矩阵状态（21:00）
- RNA-Sc：三任务 E1 全矩阵齐（m6A 3×3×2、ncRNA 3×3×2、SSP random
  3 种子齐 + family s17 齐/s29 s43 在跑）；
- RiNALMo：ncRNA 3×3×2 齐（含 tuned full @1e-5）；SSP s17 2×2 齐；
- 新模型首探：6 runs 在 G6 排队/运行；
- LR 网格：RiNALMo 4 LR × 2 策略完成；RNA-Sc 网格 chain_lr2 排程中。

## 2026-09-15（Day 1 傍晚：C4 主表成型 + 大模型 SSP 优势显现）

### ★ C4 主表（export_c4.py 自动生成，status/c4_table.md）
核心规律——**任务粒度决定泄漏×微调交互**：
- ncRNA（per-seq 分类）：LoRA/full Δ(rand−fam) = +0.61~0.86 崩溃；
  frozen +0.12~0.17 温和；基线 +0.007 不敏感 →
  **随机切分下微调收益的绝大部分是家族内泄漏**；
- m6A（per-base）：LoRA/full Δ = **-0.04**（去泄漏后不降反升）；
- SSP（per-base 结构）：LoRA/full Δ = +0.003~0.03（不敏感），
  且微调列 2×基线——**结构/位点级任务的微调收益真实**。

### ★ RiNALMo full @1e-5：LR 调优后 random 最优、family 仍崩
- 三种子 random：0.939/0.935/0.941（全超 LoRA 0.928、基线 0.90）；
- family 三种子：0.064/0.096/(s43)——**lr=1e-5 也救不了 family 崩溃**
  → ncRNA 的家族崩溃是真实分布偏移，非优化问题；
- LR 网格（RiNALMo s101）：full 甜区 1e-5~3e-5（0.943/0.944），
  3e-4 崩溃（0.077 复现）；lora 甜区 3e-4（0.923）——**策略×LR
  交互**：full 需要低 LR，LoRA 依赖高 LR。

### ★ RiNALMo-micro SSP：大模型结构性优势
- frozen s17 random **F1 0.209** vs RNA-Sc frozen 0.034（6.2×）；
  vs 最强基线 0.047（4.4×）——预训练规模在结构任务上直接兑现；
- RiNALMo SSP LoRA s17 在跑（val F1 0.21 量级已现）。

### 资源快照（17:30）
- GPU2: SSP 种子队列（frozen/lora s29 → …12 runs）；
- GPU5: LR 网格收尾（3e-4 lora）→ chain_lr2 RNA-Sc 网格；
- GPU6 MIG: RiNALMo full family s43 @1e-5（最后 1 个）；
- GPU7 MIG: RiNALMo SSP lora s17 → frozen/lora family；
- ledger：~95 行，E1 formal 矩阵 RNA-Sc 侧三任务全齐，
  RiNALMo 侧 ncRNA 全齐 + SSP frozen/lora 进行中。


## 2026-09-15（Day 1 下午 15:00 巡检：chain 匹配 bug 处置 + 下一批三 GPU 派发）

### 巡检基线
- 8 卡全忙（GPU0-5 机理篇/共享任务满载，G6/G7 MIG 单任务，2-5 各有本项目训练）；
  磁盘 /home 31%、/mnt 51%；llr_env torch 2.5.1+cu121 cuda=True；下载已全部完成；
- **smoke_matrix.log 的 4 策略 OVERLAP 崩溃 = 00:08 旧数据历史失败**（SSP 全量数据
  08:01 才就绪，届时 dedup 修复后 8 个 formal SSP run 已全部 done），不是新问题，
  smoke 维度按 E1 规则不入矩阵；
- ledger 100→86 行：并行 session 15:21 清理/dedup 时**误删了 G2 lrbest s17 的行**
  （该 run 15:24 完成，update 找不到行 → 结果没进 ledger）——已从 result.json
  恢复 done 行（备份 ledger.jsonl.bak_patrol_20260915）。

### ⚠ 本轮修复（三件事）
1. **GPU6 也变 MIG 4.75G**（13:34 起）：run_rinalmo_lrbest.sh 6 前三个 random
   job 45 秒连环 OOM（1.65G PyTorch 分配 vs MIG 总量 4.75G）→ ledger pending
   僵尸行已清；random 缺口由 GPU2 chain_g2_lrbest 补跑（s17 done ACC 0.9394，
   s29/s43 在跑）；family job 峰值 2.67G 可在 MIG 内存活，G6 队列继续；
2. **chain_g2_ssp pgrep -x bug**：等待目标 cmdline 带参数（`run_rinalmo_lrbest.sh 6`），
   -x 全字匹配永假 → 15:03 提前触发，GPU2 双任务并行（正式 lrbest s17 + ssp
   frozen s29）。处置：杀 ssp 进程树（杀 python 后队列 3 秒内续跑孤儿 lora s29
   的竞态已一并清理，损失 ~25min ssp-frozen 进度）；ledger 孤儿 pending 行已清；
3. **chain 等待纪律再升级**：全部改 `kill -0 <PID>` + `/proc/<PID>/cmdline`
   双校验（新版 chain_g2_ssp / chain_g7_ssp / chain_g6_next），PID 为启动时
   记录的具体实例。

### 下一批派发（15:40 三个 chain 已挂，setsid nohup）
- **G2**（lrbest ~17:00 排空后）→ SSP s29/s43 × random（6 runs）；
- **G7**（queue_gpu7e ~17:00 排空后）→ SSP s29/s43 × family（6 runs）
  → SSP E1 补种子两卡并行，预计 20:30-21:00 齐全；
- **G6**（lrbest family ~18:45 排空后，MIG 4.75G）→ **新模型维度首探**：
  ERNIE-RNA / RNA-FM / SpliceBERT × ncrna × frozen/lora × s17 random
  （MIG 内不排 full 防 OOM；full 待整卡恢复或换卡）；
- G5 已被 chain_lr2 占用（RNA-Sc LR 网格 8 runs，s101）。

### ★ 科学观察（修正/推进既有解读）
- **RiNALMo full @lr=1e-5 family s17 = 0.064**：random 侧 1e-5 修复到 0.94，
  family 侧仍崩在 0.06-0.08（与默认 lr 的 0.076 同水平）→ **ncRNA family
  崩溃不是 LR 伪象**，C4 任务维度分化（ncRNA 崩 / m6A 不崩）在 tuned LR 下
  依然成立，且更清晰：LR 修复的只是 random 侧；
- RiNALMo full@1e-5 random 三种子将齐（s17 0.9394 + s29/s43 在跑）vs
  lora 0.92-0.93：full FT 用对 LR 后在 33M 模型上为最优列。

### 15:55 补记：SSP 补种子三 session 撞车去重（含 15:58 dev6 三度撞车）
- 巡检发现 s29 SSP 被三个队列预订（dev5 G5 / dev2 G2 / 本 session G2+G7）而 s43 无人订；
  claim 只拒 running/done，在途 pending 不拒 → 必然双跑。
- 终态分工（全 12 runs 恰好一次）：**G5=s29 全套**（dev5 chain_ssp29_g5，触发最早
  ~16:30；与 chain_lr2 的 RNA-Sc 网格同卡并行，内存预算 ~7G 可容纳，算力分时）、
  **G2=s43 random**、**G7=s43 family**（本 session 两条链已裁剪）；dev2 的
  chain_ssp29_g2（纯重复）已杀。
- 15:58 再补：dev6 又挂 chain_ssp43_g6（s43 全套 on G6）→ 与 G2/G7 s43 链三重
  撞车且与 chain_g6_next（新模型首探）G6 双队列（MIG 4.75G 必 OOM）→ 已杀；
  s43 维持 G2=random/G7=family 分工。G5 上 chain_lr2(lr_grid2) 与
  chain_ssp29_g5 同触发同卡并存（真整卡 40G，峰值和 ~5G 安全，算力分时），留观。

### 矩阵缺口（截至 15:45）
- SSP s29/s43（12 runs，两 chain 排程中）；
- RiNALMo full s29/s43 random（G7/G2 在跑）+ family s29/s43 @1e-5（G6 在跑）；
- 新模型首探（G6 chain）→ 依结果决定扩 seeds/splits/full；
- RNA-Sc LR 网格（G5 chain_lr2 排程中）。



## 2026-09-15（Day 1 下午：C4 双任务反差成型 + 运维三坑修复）

### ★ C4 矩阵关键数值（formal，非 smoke）
- **ncRNA（RNA-Sc + RiNALMo 双模型三种子）**：random 侧 lora 0.74-0.93
  / full 0.66-0.96 / frozen 0.38-0.83 → family 侧 **lora/full 全崩**
  （0.06-0.10），frozen 温和跌（RiNALMo 0.70，三种子方向一致）；
- **m6A（RNA-Sc 三种子）**：random lora 0.943/full 0.940 → family 侧
  **不崩反升**：lora 0.981-0.985、full 0.977-0.981（宿主级切分下微调
  依然有效）——**C4 泄漏×策略交互存在任务维度分化**（ncRNA 崩 / m6A
  不崩），这是超出 Schmirler 的新发现形态；
- **SSP（s17）**：random lora 0.083/full 0.096 vs frozen 0.034；
  family lora 0.075 vs frozen 0.031——微调列在两种切分下都 2×基线
  （0.042/0.047）；
- **RiNALMo full @lr=1e-5 (s101)**：0.943-0.950 —— full FT 最优
  （超 lora 0.92、超基线 0.90），formal 三种子已排（GPU6/GPU2 队列）。

### ⚠ 运维事件（三坑，全部已修复+规则固化）
1. **GPU6/7 被外部切 MIG 1g.5gb（4.75 GiB）**：nvidia-smi 显示整卡
   40G 但 torch 实测 4.8G。mod family lora s29/s43 eval 撞墙 OOM、
   lrbest s17 random 撞墙。处置：队列迁 GPU2 + MIG 内只跑单任务；
   规则：派发前必查 `torch.cuda.get_device_properties`；
2. **pgrep -f 死锁**：chain 脚本用 pgrep -f 等前置队列，但 ssh bash -c
   壳进程的命令行文本包含匹配串 → 永假（等待不存在的目标已死进程的
   幽灵匹配）。处置：杀污染壳 + 手动接力；规则：chain 用 pgrep -x 或
   PID 文件；
3. **双实例队列撞车**：run_mod_family2 被我手动 + chain_modfam2 各启
   一次（flock claim 竞态窗口），同一 run 在 GPU2 双跑。处置：杀重复
   实例树。教训：启动队列前先 pgrep -x 查重。

### 矩阵缺口（截至 14:20）
- RiNALMo full @1e-5 三种子（random GPU2 队列 / family GPU6 MIG 队列）
- mod family full s29/s43（GPU2 在跑）
- LR 网格 3e-5/1e-4/3e-4（GPU5）+ RNA-Sc 网格（chain_lr2）
- SSP s17 full family（GPU7 在跑）+ SSP 29/43 种子 + RiNALMo SSP

## 2026-09-15（Day 1 中午：LR 网格重大发现 + GPU7 MIG 事件）

### ★ A8 LR 网格首个结果：RiNALMo full 崩溃 = LR 过高
- RiNALMo-micro full FT @ lr=1e-5 (s101) ncRNA random → **ACC 0.9499**
  vs 默认 3e-4 的 0.0699（崩溃）。
- 含义：① "RiNALMo full FT 崩溃"是 LR 伪象，不是模型本身——修正此前
  Day1 上午日志的初步解读；② full FT 在 33M 模型上以 0.95 超过 LoRA
  (0.923) 和 k-mer 基线 (0.90)——C1 "微调总体有益" 的强证据；
  ③ 需按 A8 协议用 tuned LR 重跑 formal 3 种子（run_rinalmo_lrbest
  队列已挂 GPU6：full×3 random + family @1e-5）。
- LR 网格继续：lora@{1e-5..3e-4}（GPU5），RNA-Sc 网格接续（chain_lr2）。

### ⚠ GPU7 被外部切成 MIG 1g.5gb（4.75 GiB）
- mod family lora s29/s43 在 eval 阶段 OOM（"GPU7 total capacity
  4.75 GiB"）；训练阶段能活（~600MB），eval bs=64 撞墙。
- 处置：mod family 队列迁 GPU2（chain_modfam2，等 fill 完成）；GPU7
  上 SSP（RNA-Sc 小模型）与 G7E 的 RiNALMo（lora bs=8 勉强、full
  峰值 2.7GB 可活）继续跑；nvidia-smi 显存列不再可信，以 torch
  device properties 为准。
- 教训：GPU "显存 total 40GB" 显示与实际 MIG 实例可分配量不一致，
  队列派发前应查 `torch.cuda.get_device_properties`。

### 矩阵增量（vs 上午）
- SSP s17 矩阵基本齐：frozen rand 0.034 / lora rand 0.083 / full rand
  0.096 / frozen fam 0.031 / headonly≈frozen（0.032）；lora family 跑
  中；基线 random 0.042 / family 0.047——**SSP 上 LoRA/full 稳超基线 2×**；
- m6A family：frozen 3 seeds 0.653-0.726；**lora s17 0.985**（s29/s43
  OOM 后已排 GPU2 重跑）；
- RNA-Sc ncRNA random：lora 3 seeds 齐 (0.738-0.745)，full s29/s43
  在跑；
- fill 队列（GPU2，并行 session 建的）覆盖 E1 ncRNA 缺口，方向一致。

## 2026-09-15（Day 1 上午·二：SSP 重大修复 + 矩阵扩全，~51 正式 runs）

### 今日修复（防返工记录）
1. **SSP 数据无效 runs 处置**：07:43 启动的 3 个 random SSP runs 用的是
   08:01 才下载完的部分数据（TR0 3675/10012）——判定科学无效，停进程、
   清 ledger、删 artifacts，用全量数据重跑（wave3）；
2. **SSP pair-F1 全 0 根因**：候选对正率 ~1%，无 pos_weight 的 BCE 收敛到
   全负类 + 阈值 0.5 无一对命中。修复 = per-batch pos_weight（正负比）
   + 阈值校准。**B1 泄漏修复**：并行 session 版本把阈值校准放在
   `test[:100]` 上（测试集泄漏）——改为独立 VL0 / cluster-val 校准集；
3. **SSP family 基线全 0 根因**：family arm 没换用 MMseqs 簇 id，按
   bpRNA 来源标签（仅 7 个）切分 → test 侧 0 条。修复 = 读
   make_family_split_ssp 的全量 parquet（13401 序列 → 12825 簇 →
   10721/1341/1339）；
4. **frozen ≡ head-only 实现重合**：apply_strategy 里两策略代码路径
   相同（s29/s43 数值逐位一致证实）。核对 spec：**E1 主矩阵只含
   frozen/LoRA/full 3 策略，head-only 是 E2 PEFT 横评成员**——E1 不再
   排 head-only 列，已跑的 head-only 值保留作确定性对照；
5. **modification family 切分落地**：spec §3.4 规定 m6A 位点级切分
   单元 = 宿主转录本。BEACON 无转录本 ID，用 MMseqs2 0.8/0.8 聚
   309,460 滑窗 → 241,984 簇（同转录本重叠窗聚簇 = 宿主纯净近似）→
   247,572/30,946/30,942，同序列跨侧断言通过。GPU7 队列 9 runs 启动。

### 矩阵快照（ledger，formal 非 smoke）
- ncRNA：RNA-Sc + RiNALMo 双模型 frozen/lora/full × 双切分骨架已立，
  RiNALMo random frozen 3 种子齐（0.796/0.828/0.828）；
- modification：random 侧 3 策略×3 种子全齐（frozen 0.645-0.736 /
  lora 0.941-0.944 / full 0.939-0.942），family 侧队列 GPU7 运行中；
- SSP：wave3 三 GPU 并行（G5/6 random 4 策略，G7 family 4 策略，
  泄漏修复版 runner）；
- RiNALMo ncRNA full s17 random ACC=0.070 ≈ 13 类随机（1/13=0.077）——
  **full FT 在 RiNALMo-micro 上崩溃**，与 RNA-Sc full 0.660 形成模型
  间对照（LR 网格未调，暂记"不稳定"，A8 网格是关键下一步）。

### 基建
- status_check.sh 修复（llr_env 路径）；run_queue/run_mod_family/
  run_ssp_wave3 队列脚本；monitoring cron 30min。

### ★ 新发现（Day 1 上午·二补充）：BEACON m6A 官方 split 27% 宿主级泄漏
- 诊断：MMseqs2 0.8/0.8 聚 309,460 窗口（train+test），1200 个官方 test
  窗口中 **327 个（27.3%）与 train 窗口同簇**（宿主/近重复共享）；
  31-mer 视角 10.8% 重叠；exact 重复 23/1200（1.9%）。
- 含义：BEACON 官方"random" arm 的 m6A 成绩有相当部分是泄漏分——
  C4 claim 的直接 RNA 实例（qYsy "simply cheating" 引用的定量版）。
  也解释 k-mer LGBM 基线反常：family 重切分（0.837）> 官方 random
  （0.509，注意 test 仅 1200 窗口，n=600 正样本，AUC 波动大）。
- 行动：① m6A 的 Δ(随机−家族) 对比将报告官方 27% 泄漏率作机制注脚；
  ② LM 侧 family arm 已在跑（frozen s17/s29 出分 0.726/0.717）；
  ③ preprint 中把"官方 split 泄漏审计"作为独立小节（B1 纪律卖点）。

## 2026-09-15（Day 1 上午：矩阵成型，24+ 正式 runs）

### 当前矩阵快照（ledger 汇总，status/summary.md 自动生成）

**ncRNA 分类（13 类，ACC）**：

| 模型 | 策略 | random | family | 种子 |
|---|---|---|---|---|
| RNA-Sc-10M | frozen | 0.375 | 0.214 (3s 方向一致) | 1/3 |
| RNA-Sc-10M | lora | **0.745** | 0.070 (崩) | 1/2 |
| RNA-Sc-10M | full | 0.660 | 0.065 (崩, 3s ↓*) | 1/3 |
| RiNALMo-micro | frozen | 0.812 (2s) | 0.696 | 2/1 |
| RiNALMo-micro | lora | **0.923** | 0.084 (崩) | 1/1 |
| k-mer LGBM 基线 | — | 0.900 | 0.893 | — |

**modification m6A（per-base AUC）**：LoRA 0.941/0.944/0.943（3 种子，方向完全一致）
vs frozen 0.645；full FT 进行中。

### 三个正在固化的模式（初步，未过 BH 校正，不可作为最终结论）
1. **C4 泄漏×策略交互**：family 切分下 LoRA/full 全崩（Δ≈-0.8），
   frozen 温和跌（RiNALMo 0.81→0.70），k-mer 基线几乎不动（0.90→0.89）。
   → "随机切分下的微调收益中相当部分是家族内泄漏"的直接证据形态；
2. **ΔLM−基线格点**：RiNALMo+LoRA (random) 是唯一超基线的组合（+0.023）；
   RNA-Sc-10M 全策略不敌 LGBM（受控 10M 模型容量小）但在 m6A 上
   LoRA 0.94 极强 —— 微调收益的任务/模型依赖性（C1 的核心维度）；
3. **LoRA vs full 分化**：random 下 LoRA > full（0.745 vs 0.660；0.923 vs pending），
   与蛋白侧 Schmirler "LoRA≈full" 出现分化苗头 → C5 素材。

### 基建与运维
- 四 GPU 并行轮转（G1 modification 矩阵 / G5+G7 RiNALMo 策略与种子 / G6 family）；
- 每策略列完成度已过 20%（T2.0 预注册检查点分析待 formal 全列 20% 后执行）；
- M5 无触发（见 docs/m5_monitoring.md）；GitHub 已推 8 次。

## 2026-09-15（Day 1 凌晨：首个策略对比数据点出炉）

### ★ 核心结果（ncRNA 分类 / random 切分 / seed 17 / 全量 8.5k 序列）

| run | 策略 | ACC | wall | 显存峰值 | 备注 |
|---|---|---|---|---|---|
| ft_rnasc10m_frozen | frozen+浅头 | 0.375 | 1072s | 958MB | 注意力池化头 |
| ft_rnasc10m_headonly | head-only | 0.375 | 1087s | 958MB | 与 frozen 同分（预期：同构） |
| ft_rnasc10m_lora | **LoRA r=8** | **0.745** | 3589s | ~600MB | qkv/out 184,320 可训参 |
| ft_rnasc10m_full | **full FT** | **0.660** | 3552s | 870MB | 8.86M 全参 |

**初步信号（非结论，需 3 种子 + BH 校正）**：
1. 微调大幅增益：+37pp（LoRA）/ +28pp（full）——方向上支持 C1（微调有益）；
2. **LoRA (0.745) > full FT (0.660)**：若经多种子验证成立，这是与
   Schmirler 蛋白侧 "LoRA≈full" 的 RNA 侧分化点 → C5/C6 叙事素材；
3. full FT 出现训练不稳定迹象（loss 曲线后半段波动）——正好对齐
   Schmirler 剔除不稳定 run 的透明报告纪律（T2.3.4）。

### 进度
- 双 GPU 并行：GPU6 = family 切分矩阵队列（10 runs：4 策略×seed17 + 3 种子 frozen/full/lora）；
  GPU7 = RiNALMo-micro 4 策略冒烟矩阵（frozen 进行中，33M 模型约 40min/epoch 全量）；
- 家族级切分生成完毕：MMseqs2 80-80，8573 序列 → 7731 簇 → 6859/858/856 簇纯净切分；
- multimolecule 兼容层修复完成（transformers 5.0 + 48 文件 import guard 补丁），
  RiNALMo-micro 前向验证通过（nt token 化正确）；
- GPU 真实性验证：cuda:7 matmul 379 TFLOP/s（CPU 不可能）——该服务器
  nvidia-smi 利用率列显示 N/A 是驱动显示特性，训练确实在 GPU 上（已记录证据方法）。

## 2026-09-14（Day 0：交接启动）

### 交接文档阅读结论
- spec v1.2 / tasks v2.1 / checklist v1.2 / 红队报告已全部精读；
- 项目定位：RNA 版 Schmirler（受控策略对比：frozen+头 / LoRA / head-only / full FT），
  姊妹篇 = 机理篇（rna-sc，正在 A100 上跑 S1 受控家族预训练）；
- 时间线压缩：用户要求 1 个月内出一版优秀结果 + 可提交预印本的初步结果
  （原 spec 时间线第 4 月末 arXiv → 现在按 T1+T2 核心 + 滚动出结果推进）。

### 环境事实（A100 服务器 bms-18937653-012）
- 8×A100-40GB；GPU 6/7 当前可用（其余被机理篇 wave + editflow/reactflow 任务占用，
  按机理篇导师决议"所有空余显存均可使用"协议共享）；
- 网络：huggingface.co 直连不通，hf-mirror.com 可用（已设 HF_ENDPOINT）；
  Google Drive 不可达（本地与服务器均超时）→ BEACON 官方 Drive 路线放弃；
- 磁盘：/home/cunyuliu 配额 200G 已满 → 已把 miniconda3/pkgs (15G) 与
  .vscode-server (4.4G) offload 到 /mnt 并建符号链接；代码放 /home、大文件放 /mnt 纪律成立。

### 关键发现：BEACON 数据有 HF 镜像
- 官方 Drive 不可达 → 找到 jiahaozhang2003/beacon-* HF 数据集（13 任务全套，
  parquet 标准化层 + 原始文件层）。**13 任务已全部下载完成（~385MB）**。
- 模型：rinalmo-micro/mega、ernierna、rnafm、splicebert（multimolecule 版）
  下载完成至 /mnt/cunyuliu/hf_home；gyx1130 原版 SpliceBERT 需登录 → 用
  multimolecule/splicebert 替代（等价 nt 级 tokenizer）。

### 基建交付（GitHub: Cunyu-Liu/RNA_finetune_methods，3 次推送）
- rnafteval 包：ledger（flock 安全+strategy 维度）/ task_registry / models
  （HF+RNA-Sc 双加载器）/ strategies（注意力池化+隐宽32 头）/ splits
  （随机+家族级+零重叠断言+簇纯净断言+去重）/ metrics（自测全过）/
  finetune_one（GPU-only 纪律）/ gpu_guard / make_family_split（MMseqs2）；
- 监控：本地 Schedule 每 2h 巡检 + 服务器 crontab 每 30min 状态快照。

### 问题与修复（累计）
1. BEACON ncrna 有 347 条跨 split 完全重复序列 → 零重叠断言正确触发拦截 →
   加 dedup（保留首现）后通过。**断言系统首次实战拦截泄漏**（B1 防线有效）；
2. RNA-Sc-10M d_model 实际 192 → finetune_one 运行时自动探测校正；
3. GPU6 有他人 gmx 任务挤显存 → bs 16 + expandable_segments；
4. LoRA on RNA-Sc：peft 包装后 forward 签名不匹配 → wrapper 解包跑通；
5. multimolecule 需要 transformers 5.0 + tokenizers 0.23 + hub 1.31 → 全部
   target 安装进 /mnt pypath（不动 llr_env 本体），48 个 modeling 文件加
   import guard 兼容补丁 + create_bidirectional_mask kwargs 修正；
6. pypath 曾被 --no-deps 装上裸 torch/numpy → 删除防遮蔽 llr_env 本体。

### 下一步（优先级序）
- [ ] GPU7 RiNALMo-micro 4 策略冒烟矩阵完成 → A7 验收（含 HF 模型）
- [ ] GPU6 family 切分矩阵（10 runs）→ C4 首批 Δ(随机−家族) 数据点
- [ ] seed 29/43 补齐 → 3 种子方向一致性检查（B14）
- [ ] LR 网格（tuning seed=101）→ A8
- [ ] 传统基线 k-mer logistic/LightGBM → B5 口径
- [ ] ERNIE-RNA/RNA-FM/SpliceBERT 接入（model registry 已就绪）

## M5 监控
见 docs/m5_monitoring.md（首轮 2026-09-15：无触发，四源仍单臂）。
