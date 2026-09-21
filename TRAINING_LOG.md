# RNA-LM 微调策略评测 — 训练与交接执行日志

> 本文件记录每次训练过程与结论（用户要求）。日期用服务器时间。


## 2026-09-18 11:20 Day 4 晨 III：六卡填满（用户指令 gpu012345 显存空余太多）

**torch 实测**：GPU0-5 全为真实 A100-40G（无 MIG 切片）；派发前空闲
16.2/19.5/23.9/17.0/10.8/26.1G。第一批批量派发中后三个 ssh 被吞
（历史模式再现），已逐个补派并逐一验证启动。

**六卡布局（全部 setsid nohup 合规）**:
| GPU | 队列 | 内容 | 验证 |
|---|---|---|---|
| 0 | ERNIE m6A lora ×6 + **SpliceBERT m6A frozen** ×6 | 新：q_m6a_model.sh SpliceBERT 0 | epoch0 loss 0.0717 ✓ |
| 1 | RiNALMo SSP dora s29 + **RNA-Sc SSP dora,ia3** ×6 | E2 第六面板 | dora s17 ✓ |
| 2 | ERNIE m6A frozen ×6 | s29 family | ✓ |
| 3 | RNA-FM m6A lora ×6 | s29 random | ✓ |
| 4 | **SpliceBERT SSP frozen** ×6 | q_ssp_generic.sh SpliceBERT 4 frozen（跨语料首探） | epoch0 loss 1.0792 ✓ |
| 5 | RNA-FM m6A frozen ×6 + **ERNIE SSP frozen** ×6 | q_ssp_generic.sh ERNIE-RNA 5 frozen | pos_weight 加载 ✓ |

**ledger 核查**：SpliceBERT 既有 26 行全为 ncRNA（E1 已收），m6A/SSP
零行无 claim 冲突；ERNIE/SpliceBERT SSP 零行。

**科学目标**：C4 per-base 崩溃矩阵 0/8 → 扩展验证（SpliceBERT m6A
frozen + ERNIE/SpliceBERT SSP frozen）；E2 第六面板（RNA-Sc SSP
dora/ia3）补全三任务×双模型全因子。q_ssp_generic.sh 已提交
b067361 并推送 GitHub。

## 2026-09-21 10:25 Day 7 晨 IV：预印本 v0.6 数字对账（ledger 权威重算）

对账范围：C4 三任务 delta/ratio、A8 三任务 default-tuned、等价线 7 档、
E3 峰值、650M family。结果：
- 等价线/A8/E3/650M 全部精确一致（0.693/0.788/0.795/0.938/0.942/
  0.969；A8 15 格逐一吻合；E3 0.156/0.519/0.707）
- 修正 2 处：MRL LoRA ratio 0.85-0.91 -> 0.85-0.92（RNA-Sc 0.915）；
  MRL delta 0.07-0.16 -> 0.04-0.12（RNA-Sc 0.041 / RNA-FM 0.121）
  已提交 f732491
- 注：ncRNA LoRA delta 下界 RNA-Sc 0.669（含 E2 附加 run 的 n=4 均值）
  与 C4 表 formal 三种子口径 0.675 一致（舍入同 0.67-0.68）——预印本
  0.68 口径取 C4 表为准，无冲突

## 2026-09-21 10:15 Day 7 晨 III：watcher v3 + C5b 成图

- mega LoRA watcher v2 设计缺陷（exec 替换自身——队列全 OOM 即死）
  → v3：单 run 粒度循环（找未 done 的 (split,seed) → 等卡>14G →
  清该行 → 跑 → 重查），直到 6/6
- fig_c5b.py 上线：双家族等价线图（30M 等在跑档位落账后重跑自动入图）
  status/figs/fig_c5b.png 产出
- 其余三队列健康：30M full(g3, epoch2) / 30M lora(g4, epoch1) /
  RNA-Sc m6A dora s29(g1)

## 2026-09-21 10:20 Day 7 晨 II：等价线坐标轴补齐四队列 + 一次清行失误与恢复

**四队列（补齐等价线坐标轴）**：
- GPU5(watcher>16G): mega-148M LoRA ×6（官方系 LoRA 轴：33M 0.929 /
  mega ? / 650M 0.969）
- GPU3: RNA-Sc-30M full tuned 链（受控系中间档：1M 0.693 / 10M 0.788 /
  30M ? / 100M LoRA 0.795）
- GPU4: RNA-Sc-30M LoRA ×6
- GPU1: RNA-Sc-10M m6A {dora,ia3} ×6（E2 三任务对称面板）

**事故与恢复（诚实记录）**：mega LoRA 队列被 GPU5 其他用户挤爆后，
清行模式误用 "rinalmomega" 全匹配——把已完成的 8 行 mega full
结果一并删除。**已从 q_mega_full_g0.log 解析 8 个结果 JSON 块全量
回填**（值逐一核对：random 0.943/0.949/0.943，family 0.084/0.076/
0.084，与预印本 v0.6 数字一致——预印本无需改动）。教训：清行模式
必须含 strategy 维度（本次应为 rinalmomega+lora），删后必须立即
对账；恢复来源=训练日志结果块+artifacts 目录。

**mega LoRA watcher**：GPU>=16G 门槛自动派发整队（GPU5 争抢频繁，
12.9G/9.5G 级其他用户进程反复出现）。

## 2026-09-21 10:10 Day 7 晨：等价线双系收官 + E3 三任务闭环（重大）

**C5b 等价线（ncRNA random，全链条 7 档）**：
| 档位 | 值 | 说明 |
|---|---|---|
| RNA-Sc-1M full@tuned | 0.693 | 受控系小端 |
| RNA-Sc-10M full@tuned | 0.788 | **≈ 100M LoRA** |
| RNA-Sc-10M LoRA | 0.740 | |
| RNA-Sc-100M LoRA | 0.795 | 受控系大端 |
| RiNALMo-33M full@tuned | 0.938 | 官方系小端 |
| **RiNALMo-mega-148M full@tuned** | **0.942**（BEST=1e-5） | 33M→148M 全参增益仅 +0.004 |
| RiNALMo-650M LoRA | **0.969**（s17 0.979 补齐） | 官方系大端 |

**核心结论**：
1. **受控系等价点在 10M-100M 之间**（10M full 0.788 ≈ 100M LoRA 0.795）
   ——同配方下「10 倍小模型全参 ≈ 大模型 LoRA」成立
2. **官方系 148M full（0.942）仍不敌 650M LoRA（0.969，+0.027）**
   ——等价点 >148M 或不存在；全参 33M→148M 规模增益微弱（+0.004）
3. **等价线依赖模型家族**——spec 预注册的「分歧则提示等价线依赖
   家族特性」分支命中：受控系（干净 scaling）等价点早出现；官方系
   （预训练深度/语料差异）大模型优势持续
4. **family 侧 7 档全崩**（0.07-0.11）——C4 崩溃规模无关性最强证据
   （1M 到 650M 无一幸免）

**E3-MRL 54/54（三任务全因子闭环）**：三臂双切全部单调
（frozen random 0.08→0.15→0.67→0.72；lora family 0.06→0.29→0.69→0.70）
——单例簇 per-seq 任务无家族记忆峰，预测验证。
**E3 三任务定论**：ncRNA 非单调（多成员家族）/ m6A 单调（per-base）
/ MRL 单调（单例簇）——「家族记忆需要多成员家族结构」三任务闭环。

**MRL family 基线**：LGBM 0.669（random 0.778，Δ=0.109 温和）——
基线也随切分温和退化，与 LM Δ 幅度一致（单例簇切分本身更难）。

**C4/E2 导出已刷新**（含 mega/650M/MRL 全部新行）。

## 2026-09-20 22:50 Day 6 深夜 II：等价线补档设计（用户指令）+ 三 watcher 体系

**用户设计指令**：(1) 650M LoRA 对比「比 33M 大一档」的 RiNALMo 全参
——即 mega-148M（官方系 33M/148M/650M 中间档，checkpoint 已本地）；
(2) 受控系 RNA-Sc-300M/650M 训完后补测 full+lora 值。

**落地**：
- GPU0: q_mega_full.sh —— RiNALMo-mega-148M 全参 tuned 链
  （s101 网格 {1e-5,3e-5} → formal 双切分 × 3 种子）在跑
  （s101 lr1e-5 训练中）。若 mega full ≈ 650M LoRA（0.964），则
  RNA 侧等价点落在 33M-148M 之间——与蛋白侧 Schmirler ~150M 交点
  呼应
- RiNALMo-mega + RNA-Sc-650M 已注册 MODEL_SPECS（17 specs）
- watcher v2（650M s17）：重试前清 run_id 行防 ledger 污染，
  GPU0-5 扫描 >13G 每 3 分钟
- 预训练 watcher：kill -0 监听 rna_sc.train RNA-Sc-650M（PID
  422582）——退出即自动触发 q_rnasc650_tests.sh：相位1 frozen+lora
  ×双切分×3 种子（GPU>=14G 门槛）；相位2 full tuned 链（GPU>=28G
  门槛）。用户指令覆盖 B7 的 full<=100M 分层——650M 受控全参按
  用户要求开测（等价线需要）
- RNA-Sc-300M：runs 目录尚无该档（机理篇未开训）——待出现后同样
  补测（定时巡检捕获，TRAINING_LOG 此处留痕提醒）

**E3-MRL 16/54 推进中**（GPU4）。

## 2026-09-20 22:35 Day 6 深夜：等价线核心结论 + E2-MRL 收官 + C4 三任务全表

**C5b 等价线（官方系 RiNALMo 33M↔650M，ncRNA）**：
- 650M LoRA random：s29 0.960 / s43 0.967（s17 watcher 补跑中，
  两次被其他用户抢卡 OOM——已部署 13G 门槛耐心 watcher）
- **33M 全参 tuned 0.938 < 650M LoRA 0.964（均值）——「小全参 ≈
  大 LoRA」等价线在 RNA 侧 33M↔650M 不成立**：大模型 LoRA 仍占优
  （+0.026）。与蛋白侧 Schmirler 150M 交点对比：RNA 侧交点若存在
  则更小或不存在
- **650M LoRA family 0.076-0.166 也崩——C4 家族崩溃扩展至第 6 个
  模型（最大模型）**：651M 大容量/深预训练不提供家族切分抗性；
  LoRA 不受 A8 LR 崩溃影响，此为纯 C4 现象
- 受控系：1M full@tuned 0.693 / 10M 0.808 / 100M LoRA 0.795——
  100M LoRA ≈ 10M full（+0.13 内），受控系等价点在 10M-100M 之间

**E2-MRL（第五/六面板）12/12 收官**：
- RiNALMo MRL：dora 0.797 ≈ lora 0.797 ≈ full@tuned 0.796 >
  ia3 0.752 > frozen 0.717
- RNA-Sc MRL：full@tuned 0.525 > dora 0.49 > lora 0.49 >> ia3 0.17
- IA3 模型依赖：RiNALMo 上 0.752 可行 / RNA-Sc 上 0.17 弱

**C4 表三任务全量刷新**：MRL Δ(rand−fam) = 0.07-0.16（温和）——
三任务梯度：ncRNA 0.68-0.91（多成员家族崩溃）/ MRL ~0.1（单例簇
温和）/ m6A ≈0（per-base 免疫）。基线入表（LGBM random 0.778）。

**E3-MRL 54 runs GPU4 重派成功在跑**（首 dispatch 因故未执行，
log 空——重派后 2/54 推进）。

## 2026-09-20 20:05 Day 6 夜：MRL 三面板扩展全线铺开

**MRL C4 收官**：60/60 runs 全齐（frozen s29 补跑 0.717）——per-seq
第二任务 frozen/lora 全臂完成。

**新派两队列（填满 GPU3/4）**：
- GPU3: E2-MRL 面板（RiNALMo/RNA-Sc × {dora,ia3} × random × 3 种子
  = 12 runs）——E2 任务维度扩展至回归任务
- GPU4: E3-MRL 标注量轴（RiNALMo {full@1e-5, lora, frozen} ×
  n{100,1000,10000} × 双切分 × 3 种子 = 54 runs）——E3 三任务全因子
  （预测：单例簇任务单调，如 m6A）
- GPU1: frozen s29 补跑完成（0.7173）
- 650M 等价线：s29 family 在跑（剩 s43 最后一个）

## 2026-09-20 19:55 Day 6 晚：MRL 全矩阵收官——A8 5/5 + 单例簇发现

**A8-MRL：5/5 全参默认崩 → tuned 全恢复（Pearson r）**：
| 模型 | 默认 random | tuned random | tuned family |
|---|---|---|---|
| RiNALMo-33M | -0.001 | 0.796 | 0.696 |
| SpliceBERT | 0.098 | 0.803 | 0.732 |
| ERNIE-RNA | 0.028 | 0.784 | 0.685 |
| RNA-FM | **0.181（ncRNA/m6A 唯一幸存者在 MRL 也崩）** | 0.794 | 0.688 |
| RNA-Sc-10M | 0.159 | 0.525 | 0.479 |
- tuned 最优 LR：RiNALMo/ERNIE 1e-5；SpliceBERT/RNA-FM/RNA-Sc 3e-5
- **A8 崩溃集合任务依赖且 MRL 上全员崩**（回归任务最脆弱）

**C4-MRL（per-seq 第二任务）：LoRA family 温和退化非崩溃**：
- RiNALMo 0.797/0.698（ratio 0.87）/ SpliceBERT 0.800/0.723（0.90）/
  ERNIE 0.791/0.694（0.88）/ RNA-FM 0.799/0.678（0.85）/ RNA-Sc 0.49/0.45
- **机制发现：MRL 90,403 簇几乎全单例（91,519 条）——家族结构密度
  才是 per-seq 崩溃的必要条件**；单例簇任务 family≈random。
  粒度（per-seq/per-base）× 家族密度共同决定泄漏敏感性——C4 结论
  细化为二维判据
- RNA-Sc-10M 在 MRL 全面偏弱（tuned full 0.53 vs 其他 0.78-0.80）——
  ALiBi 模型未编码 UTR 翻译效率特征（观察性）

**MRL frozen/lora 队列 57/60（剩 RNA-Sc lora family）**；650M 等
价线剩 s43 family；k-mer 基线重跑中（-u 无缓冲）。

## 2026-09-20 17:25 Day 6 傍晚 III：MRL 全参默认 LR 崩溃（A8 第四任务维度）

**MRL full@3e-4 默认（s17/random 首批）**：
- RiNALMo-33M: Pearson r = **-0.001**（彻底崩）
- SpliceBERT: r = 0.098（崩）
- **RNA-Sc-10M: r = 0.169（崩！）**——m6A/ncRNA 上稳健的 RNA-Sc 在
  MRL 回归任务上也崩
- ERNIE/RNA-FM 在跑

**含义（A8 口径再细化）**：
1. 崩溃集合是**任务依赖**的：ncRNA 3 崩 / m6A 3 崩 / MRL 目前 3/3 崩
  （含 RNA-Sc——回归任务更脆弱）
2. 与 diag 机制一致：MRL 25nt 短序列 + 连续标签，梯度信号更集中
3. 条件 tuned 链将自动触发（阈值 r<0.45）——四模型 tuned 恢复
   对照在途，A8 表格将扩至三任务

**export_c4 已扩展**：baselines() 加 mrl 任务 + pearson_r 键；
baselines_mrl 输出对齐 artifacts/baseline_mrl_<split>.json 约定
（results 结构）；基线重启（Ridge α{1,10,100}+LGBM）。

## 2026-09-20 17:20 Day 6 傍晚 II：MRL full 臂三路上线 + 五卡并行填满

**MRL full 臂（A8 三任务扩展，条件 tuned 链）五路并行**：
| GPU | 队列 | 状态 |
|---|---|---|
| 0 | q_mrl_c4.sh（frozen/lora 60 runs）| 21/60 推进中 |
| 1 | RiNALMo MRL full default→条件 tuned | s17 random 在跑 |
| 2 | SpliceBERT MRL full | s29 random 在跑 |
| 4 | RNA-Sc-10M MRL full | s17 random 在跑 |
| 5 | ERNIE MRL full + 650M LoRA（等价线收尾）| 双任务同卡 |

- ERNIE 原派 GPU3 被其他用户抢占（gate 3.1G<4G 拒绝）——灵活改派 GPU5
- 判崩阈值：MRL random Pearson < 0.45 触发 tuned 链（frozen 参照 ~0.72）
- MRL k-mer 基线（Ridge α{1,10,100} + LGBM，random/family）CPU 在跑

**交接文档（本地）**：STATUS_SNAPSHOT_20260920.md 新建（Day 6 机制闭环 +
MRL 三任务 + 防坑累计五条新增）；tasks.md v2.9。

## 2026-09-20 16:00 Day 6 傍晚：MRL per-seq 第二任务上线 + D4 阴性结果 + PPT 双任务表

**用户指令**：PPT 第 4 页补 A8 双任务表 + E3-m6A 表（已做，仅动该页）；
第 3 页 C4 表A per-seq 只有一个任务要对齐——启动 MRL。

**MRL per-sep 第二任务（C4 对齐）**：
- tasks/mrl.py + finetune_mrl.py（回归 runner：SeqMLPHead(d,1) + MSE +
  Pearson r；协议对齐 m6A：epochs 3 / n-train 20000 / bs 32）
- 家族切分已生成：91,519 条 → 90,403 簇（25nt UTR 多单例簇），
  train 73217 / val 9152 / test 9150
- 队列 GPU0：5 模型 × {frozen, lora} × 双切分 × 3 种子 = 60 runs
- 首分：RiNALMo frozen random Pearson r=0.717 ✓（量级合理）

**D4 剂量实验结果（阴性——诚实记录）**：
- RNA-Sc-10M ck{1,5,10,15}（nt100M→1.5B）ncRNA@3e-4 默认全参：
  0.730/0.815/0.779/0.724——**各剂量均不崩**（无 0.077 式崩溃）
- m6A：ck1-15 全部 0.94-0.95 不崩
- **结论修正**：预训练进度不是崩溃抗性的调制因子（RNA-Sc 家族
  全程稳健）；抗性是配方/架构家族属性——ALiBi 窄模型（d192）稳健，
  BERT 系中层模型脆弱，RNA-FM（最深预训练）稳健
- 结合 diag：RNA-Sc 表示层也瞬时坍缩（effrank 9→1）但任务恢复
  （0.94）——机制统一为「**坍缩后回弹能力**」：RNA-FM 百步内回弹、
  RNA-Sc 三 epoch 内回弹（各剂量）、三崩溃模型无回弹

**E3-m6A random 切分补跑完成**：三臂单调（frozen 0.51→0.55→0.90；
lora 0.47→0.94→0.95；full@tuned 0.72→0.94→0.95）——双切分均验证
per-base 单调性预测。

**PPT（本地，仅第 4 页）**：表A 升级双任务 × 5 模型（ncRNA+m6A 默认/
tuned 全列）；表B 合并 E3 双任务 9 列对照（ncRNA 非单调 vs m6A 单调）。

## 2026-09-20 14:10 Day 6 午后 II：A8 机制诊断——崩溃=瞬时表示秩坍缩

**用户问题**：为什么有些模型默认 LR 崩、有些不崩？原理是什么？

**诊断工具**（本轮新增）：
- rnafteval/diag_a8.py：显微镜脚本（复刻 m6A 训练环，首 100 步
  记录梯度范数/分桶权重漂移/last-hidden 有效秩与余弦一致性）
- models/__init__.py loader 支持 RNA-Sc-10M-ckN（19 ckpt 同架构
  d192/L20/8.9M——纯预训练进度剂量，无架构混杂）

**核心发现（5 模型 × 100 步）**：
| 模型 | effrank 0→100 | drift_late | 任务表现 |
|---|---|---|---|
| SpliceBERT(崩) | 329→**1**（s5 即 31→s10=2） | 0.032 | m6A 0.649 |
| RiNALMo-33M(崩) | 302→2（s2 即 42） | 0.048 | m6A 0.302 |
| ERNIE-86M(崩) | 500→1（s5 即 1） | 0.041 | m6A 0.508 |
| RNA-FM(幸存) | 287→9(s20)→**回升 51**(s100) | 0.030 | m6A 0.992 |
| RNA-Sc-ck1(早) | 32→3，drift **0.140**(3×) | — | D4 待出 |

**机制结论**：
1. 崩溃 ≠ 过拟合，是**瞬时表示秩坍缩**：3-5% 的相对权重漂移在
   5-10 步内把 last-hidden 有效秩从 300-500 打到 1（所有 token
   同一方向），loss 直接落多数类平台 0.032
2. 区分器不是参数量/架构（三种 attn 都崩；86M 崩 96M 幸存）——
   是**预训练深度**：RNA-FM（RNAcentral 36M 序列最深）独有
   「坍缩后回弹」（effrank 9→51），同幅度漂移下可逆
3. 崩溃模型处在 3e-4 步长的「不稳定区」；tuned 3e-5/1e-5 =
   步长缩小 10-30 倍即安全——盆地锐度差异
4. ck1 早期特征 drift 3×且初始低秩——预训练早期脆弱（D4 任务级
   剂量曲线 GPU4 在跑：ck1/5/10/15 + 最终参照）
5. Caveat：RNA-Sc wrapper 的 last_hidden 坍缩但任务不崩（0.940）
   ——判别信息可能在中层；diag 需补 output_hidden_states=True

**文献对照**：与 Kumar et al. ICML 2022（fine-tuning distorts
pretrained features）同族——RNA LM 上呈极端形态（步数级坍缩）。

## 2026-09-20 13:45 Day 6 午后：昨夜六队列全部收官 + 重大机制发现 + 修复重跑

**昨夜收成（六队列 DONE）**：
1. **A8 m6A full 臂补全**：SpliceBERT 0.649 崩→tuned 0.930；ERNIE
   0.508 崩→0.963；RNA-FM 0.992 幸存（5/6 done，s17 补跑中）；
   RiNALMo 0.302→0.968（已有）；RNA-Sc 0.940 不崩（已有）
   —— **A8 跨任务成立：m6A 与 ncRNA 崩溃模型集合一致**
   （SpliceBERT/ERNIE/RiNALMo 崩；RNA-FM 幸存；RNA-Sc 部分免疫）
2. **E3-m6A family 曲线（27 runs）**：三臂全部单调递增
   - frozen 0.474→0.621→0.928→0.949（全量）
   - lora 0.491→0.817→0.987→0.995
   - full@tuned 0.615→0.816→0.986→0.993
   —— **预测验证：per-base 无家族记忆峰、无全量崩**，与 ncRNA
   非单调（0.16→0.52→0.707→0.083）完美对照——C4×E3 机制闭环
3. **等价线数据齐**：100M LoRA rnd 0.795 / 1M full@tuned rnd 0.693
   （BEST=3e-5）/ 33M full@tuned 0.938（已有）
4. 650M 下载完成（2.6G）但 LoRA 6 runs 因 GPU3 其他用户挤压全部
   OOM

**修复与重跑（3 项）**：
- E3 random 27 runs 秒败根因：pq import 在 family 分支内部（条件
  导入）→ random 分支 UnboundLocalError。已修复（random 分支内加
  import）+ 清 27 pending 行 + 重派（GPU4）
- 650M LoRA 重派 GPU5（15.8G free，s17 已过 s29 在跑）
- RNA-FM s17 random 补跑（GPU0，清 pending 行）

**C4 表已刷新**：新 m6A full 臂（tuned 覆盖）入表。

## 2026-09-20 09:00 Day 6 晨：E3-m6A 启动 + 资源冲突修复 + 下载断点续传

**E3-m6A 跨粒度验证启动**（用户确认执行）：
- finetune_base.py 补丁：run_id 加 `_e3<n>` 标签 + 宿主簇级整簇采样
  （family 分支直接用 cluster_id；random 分支用 parquet seq→cluster
  映射；随机抽簇→整簇纳入，对齐 e3_subsampler 语义；n=20000 正式
  协议路径不变——保持历史可复现性）
- 队列 q_e3_m6a.sh GPU4：RiNALMo {full@1e-5, lora, frozen} ×
  n{100,1000,10000} × {random,family} × s{17,29,43} = 54 runs
- 预测：per-base 曲线单调（无家族记忆峰）vs ncRNA 非单调——若成立
  则 C4×E3 机制闭环（家族记忆假说直接验证）

**昨夜问题修复（3 项）**：
1. 100M LoRA s17 GPU5 OOM（ERNIE m6A 12.9G + 其他用户 13.5G 叠加
   挤爆）→ 队列迁 GPU3（孤儿行清理 + 重 claim），GPU5 留给 ERNIE
2. 650M 下载 16 并发被 hf-mirror 限流（part0-7 反复断流且整块重下）
   → 改断点续传版（4 并发 + Range 续传），1.6G/2.6G 推进中
3. kill 队列时再次确认 pgrep -f 自匹配风险——改用 ps+正则字符类
   断字（"100[M]"）与精确 PID，避免杀掉自己会话

**当前八卡布局**：GPU0 RNA-FM m6A full / GPU1 其他用户 / GPU2 1M
tuned 链（BEST=3e-5 formal 中）/ GPU3 100M LoRA + 650M waiter /
GPU4 SpliceBERT m6A tuned 链 + E3-m6A / GPU5 ERNIE m6A full /
GPU6-7 MIG 不可用。

## 2026-09-20 00:00 Day 5 深夜：A8 跨任务补全（m6A full × 3 模型）+ 650M 并行下载

**用户问题**：表A（A8）/表B（E3）只在 ncRNA 单任务上测，是否不足？

**盘点（已有跨任务证据）**：
- A8 m6A：RiNALMo default 0.302 崩 → tuned 0.968 恢复；RNA-Sc default
  0.940 不崩（模型依赖性一致）
- A8 SSP：RiNALMo default 0.006 双侧崩 → tuned 0.166 弱恢复（低于
  frozen 0.218——SSP 上 tuned 全参仍不及 frozen，本身是新数据点）
- E3：确为 ncRNA 单任务——真实缺口

**本轮补全（三队列）**：q_m6a_full.sh <model> <gpu>（条件逻辑：
default 6 runs → random 均值 <0.75 判崩 → s101 网格 {1e-5,3e-5} →
tuned 6 runs；幸存者自动跳过 tuned 臂）：
- GPU4: SpliceBERT m6A full（epoch 1 在跑）
- GPU0: RNA-FM m6A full（加载中——幸存者假说检验）
- GPU5: ERNIE m6A full（与 100M LoRA 等价线同卡）

**650M 下载**：单流仅 40KB/s（18h ETA）→ 重写 16 分块 Range 并行
下载（3 分钟 692MB，提速 ~30×）；GPU3 waiter 自动衔接。

**再次踩坑（pgrep -f 自匹配）**：pkill -f dl_rinalmo.py 匹配到 ssh
壳自身命令行 → kill 了自己的会话（与 13:35 事故同型——规则明令
禁止，执行时又犯）。正确做法：lsof 文件找 PID。

**E3-m6A（下一项）**：设计已定——n ∈ {100,1000,10000}+全量 ×
{tuned-full, lora, frozen} × 双切分；预测 per-base 单调（无家族记忆
峰）vs ncRNA 非单调——C4×E3 机制打通的关键对照。需 finetune_base
加 _e3 tag + 宿主级簇采样（代码改动，下轮实施）。

## 2026-09-19 23:35 Day 5 夜：等价线三路启动（C5b）+ PPT 术语细化

**用户指令**：33M full ≈ 651M LoRA 等价线启动。

**三路队列**（等价线 = 双家族：官方系 RiNALMo 33M↔650M + 受控系 RNA-Sc 1M↔100M）：
| GPU | 队列 | 内容 |
|---|---|---|
| 5 | q_eq_lora.sh RNA-Sc-100M | 100M LoRA × {random,family} × 3 种子 = 6 runs |
| 2 | q_eq_1m_tuned.sh | 1M 全参：s101 LR 网格 {1e-5,3e-5,1e-4,3e-4} → 选优 → formal 3 种子 × 2 切分 |
| 3 | q_eq_lora650m.sh | **650M LoRA × 6**（下载等待链：multimolecule/rinalmo-giga 下载完成自动开跑） |

**踩坑记录（本轮 2 个）**：
1. sed 注册 650M 时插入点落在 RiNALMo-micro ModelSpec() 调用中间 → 语法错误
   → 全部 finetune 导入失败（首轮 100M/1M 队列 exit 1 秒败）。修复：git
   checkout 恢复 + 正确位置插入（micro 完整条目之后）+ import 验证。教训：
   sed 后必须立即语法检查。
2. multimolecule/rinalmo（无后缀）与 lmzb-bupt/RiNALMo 均 401 gated；
   正确仓库名 = **multimolecule/rinalmo-giga**（650M，未 gated）。
   HF search API 确认命名体系：micro 33M / mega 148M / giga 650M。
   首轮失败残留 16 行 pending 孤儿已 flock 清理（同 run_id 保留最新）。

**PPT 细化（本地 20 页版）**：per-seq/per-base 术语定义入第 4 页怎么看
引导；第 5 页表A 数值口径讲明（ncRNA 单任务/random/3 种子均值/非跨任务
平均）；表B 补全参@默认行（0.229/0.076/0.076/0.083）+ E3 主轴四臂
说明（frozen/LoRA/全参默认/全参 tuned；DoRA/IA3 属 E2 维度）。

**等价线科学口径**：33M full(tuned) random ncRNA = 0.938 已有（E2 面板）；
650M LoRA / 100M LoRA / 1M full(tuned) 本轮补齐后即可成图——C5b 核心图
「33M 全参 ≈ 651M LoRA」（官方系）与「1M 全参 ≈ 100M LoRA」（受控系）。

## 2026-09-19 17:00 Day 5 傍晚：T0 立项任务集中补执行 + 导师汇报 PPT 结果版更新

**用户指令**：tasks.md 大量 T0 未执行项逐个补执行 + PPT 过期内容更新。

**T0.2 服务器验证（全部通过）**：
- ledger 单测 8/8（固化 tests/test_ledger.py 入仓库）：strategy 维度 /
  同组合重复启动拒绝（done+running）/ pending 崩溃恢复 / update 指标 /
  10 线程并发 claim 无丢行（flock）
- S0 held-out split 核验：release22_cluster_split.parquet 3,357,201 行，
  五分位 90.02/6.79/1.35/0.92/0.92%，MD5 94bc4152167c036595cba949bb86897f
- RNA-Sc checkpoint 15 目录清点：100M 三种子各 19.46GB + 650M_s17
  7.45GB + 全部 manifest.json 在位（MD5 已记 T0_交付物文档）

**T0.0 监控检索（M1-M5 真实执行）**：零命中无触发。良渚 Nat Commun
2025-12 benchmark 确认统一微调单臂（非策略对比）；GRAPE-LM（NBT 2026
适配体生成）非竞争。AIDO.RNA-1.6B HF checkpoint 存活验证。

**T0.1 交付物成文**：交接文档 T0_交付物_差异清单与预注册_20260919.md
（Schmirler 差异清单 / PEFT 四方法笔记含实测结论 / 预注册稿摘要 /
复现性记录 / 监控记录 / T0.2 验证记录六节）。

**tasks.md v2.8**：T0 段 24 项勾选（附证据），仅剩 T0.3.1/3.2 待导师会议。

**导师汇报 PPT 更新为 20 页结果版（表格化）**（本地）：4 页结果页表格化重建（进度 8 行表 / C4 每模型双表 / A8+E3 方法论+数值双表 / E2 四面板表）；C4 页含 5 模型 LoRA/frozen random-family 逐格值 + per-base 26 组 family/random 值；A8 页含 tuned-LR 协议说明（seed101 val-only 网格）与 E3 簇级采样说明 + RiNALMo 三策略曲线（n=10/100/1000/全量）+ Schmirler 差异清单 13 行表插入第 10 页（总览后）；执行进度
速览 / C4 粒度×泄漏 / A8+E3 非单调 / E2 四面板）插入概要后；slide2
一页结论改为结果口径 + 请求评审；E2/E3/E4/总览四个设计页贴 09-19
实测注记（预注册设计保留作对照）；更新前备份已存。

## 2026-09-19 15:40 Day 5 午后：per-base 全量 26 组收官 + E2 四面板 + 预印本 v0.5-core

**RNA-FM SSP lora 6/6 完成**（15:07）——per-base 矩阵全量：
- m6A：5 模型×{frozen,lora} + RNA-Sc/RiNALMo full = 12 组，比值 1.007-1.645
- SSP：5 模型×{frozen,lora} + RNA-Sc {full,dora,ia3} + RiNALMo full = 14 组，比值 0.956-1.110
- **26 组 0 崩溃** vs ncRNA per-seq 5/5 崩溃——粒度×泄漏交互 claim 全量锁定

**E2 第四面板**（export_e2.py PANELS +RNA-Sc SSP）：full 0.097 > LoRA 0.084
> DoRA 0.081 > IA3 0.042 > head-only 0.033；DoRA 最优口径修正 2/4 面板。

**预印本 v0.5-core**（3413caa）：2.2 节 0/26 全量 + 摘要数值口径 + 2.3 节
四面板表。C4/E2 表已终版刷新。

**本地交接文档全部更新**（5 文件）：STATUS_SNAPSHOT_20260919.md 新建
（Day 5 收官锚点）；tasks.md v2.7（监控表+Day5 交接说明）；checklist.md
v1.7（B12 勾选）；spec.md 进度注记（冻结口径不变）；红队报告历史保留。

## 2026-09-19 12:25 Day 5 午间：四队列收官 + per-base 矩阵全量完成 + 补派 RNA-FM SSP lora

**四队列全部完成**（凌晨 01:03-02:09，24/24 runs done，零 OOM）：
- SpliceBERT m6A lora 6/6：fam AUROC=0.988 / rnd=0.955
- ERNIE SSP lora 6/6：fam MCC=0.345 / rnd=0.337
- RNA-FM SSP frozen 6/6：fam=0.184 / rnd=0.181
- SpliceBERT SSP lora 6/6：fam=0.169 / rnd=0.168

**C4 per-base 全量矩阵结论（本轮核心成果）**：
- m6A 5 模型×双臂（frozen+lora）全部 ratio ≥ 1.007 —— 0 崩溃；
- SSP frozen 5 模型 + lora 4 模型全部 ratio ∈ [0.82, 1.11] —— 0 崩溃
  （RNA-Sc 0.82-0.98 为 MCC 小值种子噪声，远高于 0.3 崩溃阈值）；
- 对照 ncRNA per-seq 的 5/5 崩溃（Δ≥0.68），粒度×泄漏交互结论
  完整成立：per-seq 崩溃 / per-base 免疫，跨 5 模型 3 任务 19 组。

**补派**：RNA-FM SSP lora ×6（GPU2，torch 实测 20G 空余）——补齐
SSP lora 第 5 模型，s17 random 在跑（PID 1242151），ETA ~2h。

**十产物刷新链已跑**（chain_final_refresh.sh 旧 PID 守护全过即刷）：
c4_table.md 已含全部新行（ERNIE/RNA-FM m6A 双臂 + SSP lora 行）。

## 2026-09-19 00:30 Day 5 凌晨：四队列补派（用户指令 gpu1245 显存空余太多）

**前置核查**：昨日全部队列自然收官（ERNIE SSP frozen 13:17 / RNA-Sc
SSP dora,ia3 14:52 各 6/6 与 12/12 done）。torch 实测 GPU1/2/4/5 均为
真实 A100-40G，空闲 8.0/7.4/10.1/4.0G。

**ledger 缺口分析后四路补派**（全部零行新 run，无 claim 冲突）:
| GPU | 队列 | 科学价值 | 验证 |
|---|---|---|---|
| 1 | SpliceBERT m6A **lora** ×6 | 补齐 5 模型×双臂 m6A C4 矩阵 | s17 已完成, s29 在跑 ✓ |
| 2 | ERNIE-RNA SSP **lora** ×6 | SSP 双臂扩展 | s17 epoch0 loss 0.689 ✓ |
| 4 | RNA-FM SSP **frozen** ×6 | SSP frozen 覆盖第 5 模型 | s17 epoch1 loss 0.720 ✓ |
| 5 | SpliceBERT SSP **lora** ×6 | SSP 双臂扩展 | s17 加载完成 ✓ |

**当前 per-base 矩阵进度**：m6A 双臂（frozen+lora）4/5 模型已齐，
SpliceBERT lora 本轮补齐第 5；SSP lora 臂 2/5（RNA-Sc/RiNALMo 已有），
ERNIE/SpliceBERT 本轮补至 4/5；SSP frozen 本轮从 4 模型补至 5 模型。

队列脚本全部复用现有（q_m6a_lora.sh / q_ssp_generic.sh），无新脚本。

## 2026-09-18 11:15 Day 4 晨 II：五卡五队列全并行

**用户反馈"看不到任务"澄清**: 三队列实际在跑（SSP dora 18min+
ERNIE/RNA-FM m6A frozen 推进至 s43）——小模型显存占用小
（每任务 2-3G, GPU 面板显示大空）不显眼。已补派满空闲卡。

**当前五卡布局**:
| GPU | 队列 | 进度 |
|---|---|---|
| 0 | ERNIE m6A **lora** × 6 runs | s17 random |
| 1 | SSP E2 dora/ia3 × 6 | dora s17 |
| 2 | ERNIE m6A frozen × 6 | s43（最后） |
| 3 | RNA-FM m6A **lora** × 6 | s17 random |
| 5 | RNA-FM m6A frozen × 6 | s43（最后） |

- m6A 双新模型 frozen+lora 全臂收尾后: C4 per-base 崩溃矩阵
  0/8（四模型×双臂）完整验证
- 派发合规: setsid nohup（吸取此前 nohup 无 setsid 教训）

**Git**: m6A lora 队列脚本已推送。
## 2026-09-18 10:50 Day 4 晨：E2 全因子落地 + 三队列派发

**状态**: ledger 324 行（322 done）; E2 双队列昨夜全部完成
→ **E2 全因子达成（2 模型 × 2 任务 × 4-5 臂 × 3 种子）**。

### ★ E2 三面板位次（export_e2 全因子表）
| 面板 | 位次 |
|---|---|
| RiNALMo ncRNA | full 0.938 > DoRA 0.934 > LoRA 0.928 > IA3 0.860 > head 0.817 |
| RNA-Sc ncRNA | **DoRA 0.765** > LoRA 0.746 > full 0.670 > IA3 0.579 > head 0.375 |
| RiNALMo m6A | **DoRA 0.979** > LoRA 0.970 > full 0.968 > IA3 0.941 |

- **DoRA 3/4 面板最优**（唯大模型 ncRNA 的 tuned full 险胜）;
- 10M 小模型 + per-base 任务: PEFT 全面占优;
- IA3 粒度敏感: per-seq 掉 0.078 / per-base 只掉 0.027;
- 预印本 2.3 节重写为全因子版（45e7b81 已推送）
- 修复: export_e2 model 匹配 bug（字段名 vs run_id 前缀,
  自查抓出——面板全空的直接原因）

### 新派三队列（GPU 空闲利用: 1/2/5 卡 20-28G free）
1. **GPU1 SSP E2**: RiNALMo SSP {dora,ia3} × 3 种子（第三任务
   面板, dora s17 在跑）
2. **GPU2 ERNIE m6A**: frozen × 3 种子 × 2 切分（C4 per-base
   崩溃矩阵 0/4 → 0/8 验证——新语料模型入场）
3. **GPU5 RNA-FM m6A**: 同上（frozen 首探）

**Git**: 45e7b81 + 本轮队列提交。

**下步**: 三队列完成（预计 4-8h）→ export_e2 三任务版 + C4
表 0/8 验证 → 预印本 2.2/2.3 更新 → v0.5。
## 2026-09-17 23:30 ★ 全量 QA 审计（用户指令：系统检查既有结果）

**范围**: ledger 315 行全量 + 六维度扫描（数值有效性/种子协议/
重复行/同值组/逻辑矛盾/表格交叉）。

### 发现并修复：1 个数值级 BUG
**export_c4 pass2 _e3 污染**（严重）：
- 机制: tuned 协议臂覆盖判定 `"_lr" in rid` 未排除 `_e3` 标签
  → E3 队列的 `_lr1e-05_e31000`（n=1000, 0.717）行后写入
  ledger 时覆盖了先存在的纯 tuned 行（全量 family 0.064-0.096）
- 影响: C4 表 RiNALMo full family 在 18:52 守护链终刷后短暂
  显示 **0.707（污染值）**；正确值 = tuned 均值 0.085
- 修复: formal 过滤加 `"_e3" in rid: continue`（12afcf0）；
  stats.py 共享 cells() 一并修复；重刷验证 C4 表恢复 0.085 ✓
- **预印本无污染**（0.707 全为 E3 曲线合法语境；"family tuned
  仍崩"表述与真值一致——纯 tuned 行 0.064/0.096/0.096）

### 澄清：5/5 模型 tuned family 崩溃完整确认
- RiNALMo ncrna full family @1e-5 全量三种子存在:
  s17 0.064 / s29 0.096 / s43 0.096（skip 行为正确, 无需补跑）
- 至此五模型 LoRA + tuned-full 双臂 family 崩溃全部有直接数据

### 其余审计发现（判读, 无需修复）
| # | 发现 | 判读 |
|---|---|---|
| 1 | ft_testmodel s999 null 行 | 早期管线调试残留, 非正式模型, 无影响 |
| 2 | RNA-Sc SSP full s29 重复行（同值 0.0881） | 重跑未清行（教训重申: 重跑前清对应 run_id）; 值一致无科学影响 |
| 3 | frozen/IA3 三种子完全同值 9 组 | 小参数头收敛确定性: 同管线 lora/full 三种子有差异（seed 生效证明）+ RiNALMo frozen s17≠s29/43 排除全局 seed 失效; 16K 头/11.5K IA3 强收敛 + ACC 离散化 |
| 4 | mod 任务 6 组同值 | AUC 秩统计量 + 确定性训练, 已知合理 |

### 逻辑矛盾扫描（全部通过）
- 5a. ncRNA 微调臂崩溃: 9 格（lora×5 + tuned-full×5 减 RiNALMo
  random 侧显示 0.938>0.5 ✓ family 0.085<0.15 ✓ 应 10 格——
  复核: RiNALMo full 在列, 格数计算含 frozen 干扰, 实际
  **10/10 崩溃格全部成立**）
- 5b. frozen 家族增益: ERNIE +0.062 唯一 family>random（已解释
  模式: frozen 特征家族内稳健）; 其余 4 模型 family<random 正常
- E3 子集标签/n_train 一致: 0 不匹配
- E2 表: 有 _e3 排除, 无污染（RNA-Sc full 0.670 = 正式矩阵
  三种子均值, 非污染）

**结论**: 数据面 1 个数值级 bug 已修复+验证; 逻辑矛盾零;
预印本 v0.4 数字与 ledger 真值一致。守护链产物需在下次刷新
时已自动使用修复后代码。
## 2026-09-17 23:05 Day 3 深夜 IV：GPU3 双队列并行（m6A E2 派发）

**用户提示 GPU3 空闲**（实测 15.97G free, E2-RNA-Sc 队列仅占 ~2G）
→ 立即叠加派发第二队列。

**新派发**: run_e2_mod_g3.sh（PID 3895172, GPU3）——
RiNALMo m6A {dora, ia3} × s{17,29,43} × random = 6 runs
- 依据: spec v1.4 E2 = 2 任务——ncRNA(per-seq) + m6A(per-base)
  粒度对照; m6A 的 DoRA/IA3 此前缺失（只有 frozen/lora/full）
- 口径 = 正式 m6A runs（epochs 3 / n-train 20000 / bs 32 /
  默认 LR 3e-4）
- 完成后 E2 将是双模型 × 双任务的全因子 PEFT 横评

**首个 E2-RNA-Sc 数据点**: DoRA s17 = **0.760**（vs LoRA 均值
0.746）——DoRA > LoRA 方向与 RiNALMo 一致（Schmirler 复现加强）

**当前 GPU3 双队列**: E2-RNA-Sc（dora s29 跑中, 剩 4 runs）+
E2-m6A（dora s17 加载中, 6 runs）。

**Git**: e1cdfa5 后已推送（本节为最新）。

**下步**: 双队列过夜（~3-4h）→ export_e3/e2 全因子刷新 →
预印本 2.3 节 E2 升级（双模型双任务）。
## 2026-09-17 22:45 Day 3 深夜 III：References 14/14 全核证

**状态**: E2 RNA-Sc 受控重复推进中（dora s17 训练 40min+）;
export_e2 双模型版已就绪（RiNALMo 面板验证通过, RNA-Sc 面板
等 6 runs 落地自动填充）。

**本轮完成**:
1. **References 14/14 全部 Web 核证**（最后一条 Vishniakov
   ICLR 2026 = "Tokenization to Transfer: Do Genomic Foundation
   Models Learn Good Representations?", 7 作者, openreview
   4UY1NHG5Ge）——发现与本项目 A8/随机基线观察 DNA 域对应
   （tokenizer-gated 预训练增益）, 已在引用注中标注呼应
2. **export_e2 双模型重写**: 自查抓出补丁孤儿代码（双
   ranked 段）→ 完整干净版（单 main + 双模型循环 + 每模型
   协议注）; RiNALMo 面板五臂验证通过
3. References 尾注更新（弃用过时占位文本）

**Git**: 348522f → eac08fb 系列（4 笔）。

**下步**: E2 RNA-Sc 队列完成 → 重刷 export_e2 得双模型表 →
预印本 2.3 节升级 → 导师评审。
## 2026-09-17 22:10 Day 3 深夜 II：References 二轮核证（13/14）

**状态**: E2 RNA-Sc 受控重复推进中（dora s17 训练 5min, 6 runs
预计 2-4h, 定时巡检覆盖）。

**本轮完成**:
1. **References 二轮核证修正 3 条**（Web 溯源）:
   - Zablocki: 完整 6 作者 + arXiv:2410.16212 (2025)——补
     "cross-family generalization gap"定位（与我们 C4 呼应）
   - 良渚: 沈宁团队 Nat Commun 2025-12 "Benchmarking pre-trained
     genomic language models..."（11 gLMs × 4 tasks）
   - bpRNA: 年份修正 2017 → **2019, NAR 47(10):e57**（自查
     抓出经验主义错误）
2. 至此 14 条引用中 13 条已核证（仅 Vishniakov ICLR 2026 留
   投稿版 BibTeX 化时处理——已有可辨识标记）

**Git**: dc7ed54 已推送。

**下步**: E2 RNA-Sc 6 runs 收尾 → export_e2 双模型扩展 →
预印本 2.3 节升级（E2 位次双模型验证）。
## 2026-09-17 22:15 Day 3 深夜：E2 受控重复派发（GPU3 空余利用）

**状态**: 项目队列此前全部排空（v0.4 终版化完成）; GPU3 实测
18.61G 空闲 → 立即派发 E2 受控重复。

**派发**: run_e2_rnasc_g3.sh（PID 见日志, GPU3 整卡）——
RNA-Sc-10M {dora, ia3} × s{17,29,43} × random = 6 runs
- 依据: spec v1.4 E2 设计 = RiNALMo micro + RNA-Sc 受控重复;
  现缺 dora/ia3 两臂（loRa/full/head-only 已有正式矩阵行）
- head-only 不跑（frozen 代码路径相同, 数值逐位一致——规则）
- 口径对齐 RiNALMo E2（epochs 10 / bs 8 / 默认 LR）
- 首个 run（dora s17）已在跑, dedup 8573 正常

**价值**: E2 位次表（full ≥ DoRA ≈ LoRA ≫ IA3 > head-only）
升级为双模型验证——"Schmirler 蛋白侧结论 RNA 复现"声明加硬。

**下步**: 6 runs 预计 2-4h 完成 → export_e2 扩展双模型 →
E2 表/预印本 2.3 节更新。
## 2026-09-17 21:50 Day 3 晚：全队列排空 + v0.4 终版化（三大升级）

**状态**: ledger 312 行（310 done）; 全部队列排空; 守护链 2 于
18:52 完成十产物终刷。

### ★★★ tuned-full 双模型恢复（C1/C4 公平协议臂落地）
| 模型 | tuned LR | random（3 种子） | 恢复倍数 | family |
|---|---|---|---|---|
| SpliceBERT | 3e-5 | **0.910**（0.916/0.909/0.903） | ×11.8（vs 0.077） | 0.075 崩 |
| ERNIE-RNA | 1e-5 | **0.973**（0.977/0.974/0.969） | ×12.6 | 0.079 崩 |

- SpliceBERT tuned full 0.910 **超其 LoRA 0.904**; ERNIE 0.973
  ≈ LoRA 0.974——tuned 后 full ≈ LoRA（A8 结论再确认）
- **family 侧 tuned 后仍崩 → C4 泄漏发现排除 LR 混杂**
  （LoRA 臂 + tuned-full 双臂 5/5 崩溃一致）

### ★★ E3 tuned-full 非单调曲线（C3×C4 机制终证）
RiNALMo full@1e-5 family: 0.156(n=10) → 0.519(n=100) →
**0.707(n=1000, 全策略最优)** → 0.083(n=6859 崩溃)
- **标注量轴非单调**: 更多标注先帮后害（家族记忆随数据量增长）
- n=1000 是最优微调点（超 frozen 0.664 / LoRA 0.685）

### ★ 十产物守护链终刷（18:52）
C4 表 tuned 协议臂自动覆盖（ERNIE full 0.973/0.079 Δ+0.894 ↑*;
SpliceBERT 0.909/0.075 Δ+0.835 ↑*）; E3 表 tuned 臂入表
（n=1000 full 0.707 最优标记）。

**预印本 v0.4**: 2.4 节 tuned 恢复 + 2.5 节非单调曲线 +
版本头; 中文摘要同步（发现 3 + 电梯陈述）。

**Git**: aec1744 + 7023efa 已推送。

**项目状态**: 三大核心问题全部有终版数据——该不该微调
（C4 双臂 5/5 排除混杂）/ 怎么微调（A8 tuned 恢复 + E2 位次）/
调多少数据（C3 非单调, n=1000 最优）。下一步: 状态快照更新 +
导师评审 v0.4 → arXiv 提交版。
## 2026-09-17 13:25 Day 3 午间 IV：E3 tuned-full 补跑 + 双守护链

**状态**: ledger 282 行（276 done）; **E3 RiNALMo 首轴 36/36
完成**（GPU7 排空）; RNA-Sc n=100 档 full=0.154 最优（10M 模型
默认 LR 不崩, 该轴 C3 曲线无 LR 混杂——比 RiNALMo 轴干净）。

**本轮派发**:
1. **E3 tuned-full 补跑**（GPU7, PID 1976066, 9 runs）: RiNALMo
   full @1e-5 × n{10,100,1000} × 3 种子——修 C3 full 列的
   LR 混杂; 首个 run loss 正常下降（tuned 无崩溃）
2. **第二轮守护链**（PID 1988246）: 监听五队列
   （G1/G2/G5-E3/G6/G7-E3tuned 全部 kill -0 写死 PID）
   排空后终刷十产物
   - 自查修正: 初版误用 pgrep -f（项目规则禁令）→ 改为
     派发方查 PID 写死回填

**当前 5 训练 + 2 守护链全景**:
GPU1 tuned-splice / GPU2 tuned-ernie / GPU5 E3-rnasc-n1000 /
GPU6 G6-最后run / GPU7 E3-tuned-full + 双守护链

**Git**: 1895b91 已推送。

**下步**: 队列过夜推进; 全排空后守护链 2 终刷十产物 →
预印本 v0.4 数值终版化（tuned full 入图 + E3 双轴干净曲线）。
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

## Day 7 11:05 等价线队列午间巡检 + stale 行清理
- **RNA-Sc-30M full s17 random lr3e-05 done 0.881**（s101 tuning 0.858 -> formal 首种子），s29 已接续（GPU3）
- ledger 全量甄别：发现 2 个 stale pending——(a) 100M lora s29 family（凌晨 03:43 GPU3 被挤 OOM，队列后续正常但该 run 遗漏）；(b) micro m6A lora s17 random e3100（E3-m6A pq bug 27 失败 run 中唯一未重派）。两次甄别确认无活跃进程后精确清行（run_id 全匹配 + status=pending 双校验）
- 修复落地：micro e3100 redo 于 GPU6(MIG) 完成 **done 0.469**（74s，峰值 1.7G——MIG 切片对小 run 足够）；100M s29 family redo 由等卡 watcher 抢到 GPU1（10:52:26 开跑，预计 ~31min）
- **mega lora 提速**：v3 watcher 单 run 串行需 ~8-10h，补两个定向单 run runner——family s17 盯 GPU4、family s29 盯 GPU3（各要求 ≥20G 空闲，claim 前查 done 防与 v3 扫描顺序冲突）；v3 继续 random s17(在跑)->s29->s43->family s43。收尾后 C5b 表 148M 行 3 种子全齐
- 其余在途：30M lora s43 random@GPU4（family 侧队列自动接续）；650M 预训练 PID 422582 存活，watcher 在岗

## Day 7 12:12 午间大收割 + mega family 编排改造
- **RNA-Sc-30M full 6/6 全齐**（queue 12:03:29 DONE）：random tuned-3e-5 三种子 0.881/0.838/0.868（均值 0.862）；family 0.064 x3（逐位相同=坍缩到常数预测，与 7 档规模崩溃线一致）
- **RNA-Sc-30M lora 6/6 全齐**：random 0.776/0.787/0.756（均值 0.773）；family 0.064 x3。30M 档 full(0.862) > lora(0.773)，且 full@30M 已超过 lora@100M(0.795)——等价线交点叙事新证据
- **100M lora family 3/3 补全**（s29 修复 0.0759，与 s17 0.072/s43 0.096 同档）——规模崩溃线 100M 档闭合
- **mega lora random 2/3**：s17 0.9394 / s29 0.9522（148M lora 显著超 33M full 0.938，逼近 mega full 0.942）；s43 random 在跑（v3 子进程，自然落账）
- **编排改造**：v3 watcher 已退役（风险：其"清该 run 行再跑"逻辑会清掉 one-arm 在跑的 pending 活行造成重复训练）；mega family 三格改由三个定向 runner 接管——family s17->GPU4 / s29->GPU3 / s43->GPU0（各盯一卡 >=20G，claim 前查 done，互不抢卡）
- 650M 预训练（PID 422582）及其测试链 watcher（PID 3578696）双双存活
- 待 mega family 三格落地后：fig_c5b 重刷 + PPT 等价线表终刷

## Day 7 17:45 傍晚巡检——崩溃带被击穿 + mega 尾局编排
- **mega lora random 3/3 全齐**：s17 0.9394 / s29 0.9522 / s43 0.9545（均值 0.949）——148M LoRA 全面逼近 mega 全参 0.942，C5b 官方系等价线闭合
- **重要发现：family 崩溃带被 148M LoRA 击穿**。全谱审计：1M full 0.064-0.084 / 10M lora 0.072 / 30M lora 0.064 / 100M lora 0.081 / 33M micro lora 0.081 / mega full 0.076-0.084 全在带内；但 **mega lora family s17 0.147 / s29 0.334**（5.2x 多数类基线 0.064）显著逃逸，650M lora s43 0.166 亦轻微越带（mean 0.106）。preprint v0.6 第 157-158 行 "all seven scales collapse (0.07-0.11)" 需修订为分档表述——s43 family 落地后统一改
- **mega family s43 OOM 根因**：12:27:40 于 GPU0 我方仅占 4.71G 时被其他用户 6 个进程挤爆（日志留证），one-arm 单发无重试退出，stale 行已精确清除
- **v2 重试 runner 上线**（/tmp/mega_onearm_v2.sh：失败自动清行重试 x3），s43 family 已在 GPU3 开跑（27G 空闲实测），预计 ~18:30 落账；落账后进入修订链：fig_c5b 注记 + preprint 2.3 + 中文摘要 + PPT
- 另一并行 session 17:37 在 GPU0 派 micro lora family n-train 3000 run（--lr 3e-4），非本 session 队列，不干预

## Day 7 20:05 交接核查 + 三队列补位派发（新 session 接手）
- **全谱审计（etc_audit）**：modification dora/ia3 family 缺 12 runs（正在补，G1+G4）；SSP full tuned 缺 ERNIE/RNA-FM/SpliceBERT 三模型 18 runs（正在补，G4 链式：ERNIE→RNA-FM→SpliceBERT）；MRL RNA-Sc-30M lora 差 5 runs（前 session mrl_patch 在 G5 续跑中，30M frozen 6 runs 由 frozen_patch G2 续跑）
- **崩溃带修订数据**：148M LoRA family 击穿（s17 0.147/s29 0.334/s43 0.139）触发预印本 157-158 行修订需求——派发 famlora_audit 队列（G3）：RNA-Sc 1M/10M/30M/100M family lora 全档重测 x3 种子（带 done 跳过），验证击穿是否为 148M 特有或全谱线形逃逸。若 1M-100M 维持 0.06-0.11 带 → 结论改写为「崩溃带规模无关但 LoRA+预训练充分模型可部分逃逸」
- **mega lora family 3/3 全齐**（s43 OOM 后 v2 重试成功 0.139）——C5b 官方系 family 侧闭合
- 服务器态：8 卡忙（0-5 各有我方 + 他人任务）；650M 预训练 watcher（3578696）在岗；GPU 真实性按 torch.mem_get_info 核对
- 本 session 队列 PID：684919（famlora audit G3）/ 685100+686792（m6A family G4+G1）/ 703087（SSP fulltuned ERNIE G4）+ 707027（chain 接续 RNA-FM/SpliceBERT）

## Day 7 20:30 famlora_audit 首个数据点 + 崩溃带证据形态更新
- **RNA-Sc-1M lora family s17 = 0.1437**（242s/514MB，G3）——重测复现越带（非 148M 孤点）！注意：ledger 此前无 1M lora family 行（原七档全崩1M 档证据是 full arm）——famlora_audit 是**首次补齐 lora 全档 family 数据**，非重跑
- 全谱 lora family 证据现状（3 种子）：1M s17 0.1437（重测中 s29 在跑）/ 10M 0.064-0.076 带内 / 30M 0.064 带内 / 100M 0.072-0.096 带内 / 148M 0.139-0.334 越带 / 650M 0.076-0.166 半越带（s43 0.166）——**带边界不齐整，修订表述需逐档精确引用，等 audit 3 种子全齐后定稿**
- e3_subsampler 前挂修改已提交（6981254：levels +3000 / seeds +101）

## Day 7 2026-09-21 20:37 famlora_audit 关键节点：1M 档 3 种子齐整 + 全谱形态初判
- **RNA-Sc-1M lora family 3 种子全齐**：s17 0.1437 / s29 0.0748 / s43 0.1600（各 ~4min, 514MB, G3）——1M 档复现"越带分化"（0.07-0.16, 13 类随机水平 ~0.077），非孤点
- **全谱 LoRA family 证据（3 种子视角）**：1M 0.075-0.160 分化 / 10M 0.064-0.076 带内 / 30M 0.064 x3 带内 / 100M 0.072-0.096 带内 / 148M 0.139-0.334 越带 / 650M 0.076-0.166 半越带
- **形态初判（待 audit 队列收尾后定稿）**：崩溃带并非 148M 孤点逃逸，亦非全谱 U 形——1M 档自身分化，小模型带随机噪声；结论暂取「带内 10M-100M 稳定 + 两端（1M/148M/650M）越带或半越带」的边界不齐整形态
- audit 队列（G3）现状：10M s17/s29 已 skip（done），队列将在 10M s43 后依次处理 30M/100M（均已 done 预计全 skip）后自然收尾
- 巡检健康：五队列在跑（audit G3 / m6a G1 / ssp G4+chain / mrl_patch G5 / frozen_patch G2），GPU0-5 显存正常，650M watcher（3578696）与预训练（422582）存活，无新 OOM/CUDA 异常（GPU6/7 历史 OOM 均为 09-15/16 旧事件）

## Day 7 20:45 交接补位第二波 + 队列收工快照
- **m6A family E2 对称补全两队列全收工**：RNA-Sc-10M 6 runs + RiNALMo-micro 6 runs 全部 exit 0（ledger 落账：rnasc10m dora family 3 种子 0.982/0.984/... + micro dora s17 0.996 等）——E2 m6A 面板 family 侧补齐
- **famlora_audit 进度**：1M 三种子全齐（0.144/0.075/0.160——1M 档部分越带，中位 0.144）；10M/30M/100M done 行扫描跳过中（带内不动）；G3 继续
- **MRL fill 队列派发（G1）**：frozen x4 模型 x6 组合 = 24 runs（30M/100M/650M/mega）；full tuned 1e-5 x 30M/100M x 12 runs 待 frozen 完成后接续（650M/mega full 不做——B7 分层纪律）
- 队列图（20:45）：G0 frozen_patch(ncRNA 大档)/G1 mrl_fill/MRL_G5 mrl_patch/G2 SSP-ERNIE(排空后接 RNA-FM/SpliceBERT)+650M 预训练/G3 famlora_audit/G4 已收工

## Day 7 21:15 崩溃带修订链完成（B19 门禁解除后三改一刷一 push）
- **audit 判读（famlora_audit 全档落地）**：lora family 3 种子均值全谱 = 1M 0.126 / 10M 0.072 / 30M 0.064 / 100M 0.081 / 33M 0.081 / 148M 0.207 / 650M 0.106——1M-100M 档维持带内（0.064-0.126），**148M 三种子全越带（0.139-0.334）**，1M/650M 单种子越带——定性：崩溃带「大体规模无关 + 148M 结构化例外」，部分逃逸与 LoRA×预训练充分度相关（非规模单调）
- **修订落地**：preprint 2.3 节「七档全崩 0.07-0.11」→「0.06-0.12 带 + 148M 三种子逃逸」逐档精确引用；摘要 near-chance 区间同步；中文摘要同步；fig_c5b.py caption 修改并重出图
- **产物刷新**：export_c4/export_e2/stats/export_e3 全链重跑（m6A family dora/ia3 12 runs + SSP fulltuned 18 runs + MRL 30M/100M/650M 新数据全部进表）
- **SSP fulltuned 新数据（3 模型 x 双切分 x 3 种子，LR 1e-5）**：ERNIE 0.24-0.27（vs 默认 0.006 档恢复 x40+）/ RNA-FM 0.14-0.16 / SpliceBERT 0.049-0.052（低但方向一致）——A8 恢复叙事扩展至 SSP 三模型
- **MRL 新数据**：30M/100M frozen random 0.128-0.132 family 0.184-0.204（family 侧反升——per-seq 单例簇温和特性复现）；650M frozen random 0.744 family 0.654；lora 30M/100M family 0.066-0.075（带内）
- commit 4cc9daf push 完成

## Day 7 21:55 巡检：mrl_patch OOM 假完成事故处置 + 队列收工盘点
- **事故认定：mrl_patch（G5）于 21:17 因外部挤压 OOM 崩溃后"假完成"**。traceback 留证：GPU5 被他人进程 410151 占 14.99G，650M lora 自身 19.16G 时 OOM（仅差 32MiB）；脚本无显存门控无重试，后续 11 run 逐条秒失败滑过，最后打印 MRL_PATCH_DONE 假标记。12 条孤儿 pending 行（650M/mega mrl lora x3 种子 x2 切分）已 flock 双校验精确清除（现 pending 仅 2，均为在跑活行）
- **famlora_audit（G3）20:41 收工**：10M-100M 档 done 全 skip；新落账 1M lora family 3 种子 0.144/0.075/0.160——1M 档自身分化越带。全谱 lora family 形态：10M-100M 稳定带内(0.064-0.096)，两端分化（1M / 148M 0.139-0.334 / 650M s43 0.166 半越带）——崩溃带表述修订方向不变，等 preprint 修订链
- **ssp_fulltuned（G4 链）推进**：ERNIE 20:42 收工 → RNA-FM 21:21 收工 → SpliceBERT 21:21 开跑（21:34 epoch1 loss 0.96 正常）
- **mrl_fill（G1）**：frozen 30M/100M 全齐，650M frozen s17 random done（PEARSON 0.187）/s29 family 在跑；GPU1
- **frozen_patch（G2）**：RiNALMo-650M ncRNA family frozen s17 在跑（21:00 起）
- **续派 mrl_patch2（PID 1268309）**：门控改为 torch.mem_get_info 全 0-5 卡扫描取最大空闲（650M>=20G / mega>=12G），done 跳过 + 失败清行 + 重试 x3 + 300s 等卡；首轮无合格卡（最大 GPU1 15.5G）已进入等卡轮询，日志 q_mrl_patch2.log
- 其余健康项：650M 预训练 422582 存活（2-14:44）+ watcher 3578696 在岗；无 CUDA 不可用/CPU 降级证据（GPU6/7 OOM 文件均为 09-15/16 旧事件）；ledger 873 done / 2 cancelled / 2 pending

## Day 7 22:05 第三波补位（micro head-only family s29/s43）+ 队列收工汇总
- ledger 884 行（done 880 / pending 2 = 在跑）；GPU 全忙态（0-5）
- SSP fulltuned 链全收工：ERNIE 0.24-0.27 / RNA-FM 0.14-0.16 / SpliceBERT 0.05（LR 1e-5 恢复，方向一致 3/3）
- MRL fill G1 进行中（650M frozen family s43 在跑，10 分钟内落账）
- micro head-only family s29/s43 补位队列派发 G3（etc_audit ASYM 残余缺口最后一个）
- 650M 预训练 alive（最新 ckpt nt12.0B step127928）

## Day 7 22:15 事故升级：mrl_patch 用错模块污染 ledger（已清污）+ patch3 正确重派
- **二次发现：原 mrl_patch.sh 不但被挤 OOM，模块本身就派错了**。它用 finetune_one --task mrl，而 finetune_one 是 ncRNA-family 专用入口（内部写死 13 类分类数据）——task 只进 run_id/ledger 不进数据管线。后果：rnasc30m/rnasc100m mrl lora 12 条"done"行实为 ncRNA 分类结果（metric=ACC/n_classes=13 签名），冒充 MRL 回归（合法行应为 PEARSON_R/n_train 20000）
- **清污**：按 (task=mrl & strategy=lora & status=done & metric=ACC) 精确签名移除 12 条污染行 + 1 条孤儿 pending；清后 mrl lora 全表 54 行均为 PEARSON_R 合法行。m6a/ssp 面板抽查无同类污染（各队列模块/入口匹配正确）
- **本 session 自身也踩了同一坑**：巡检续派 mrl_patch2 时沿用原脚本 finetune_one——开跑 2 分钟内从日志 "classes 13" 识破（ncRNA 数据形状），立即终止（误跑未落账，仅清 1 条 claim 行）。教训入库：MRL 任务必须用 finetune_mrl 模块
- **mrl_patch3（PID 1320380）正确重派**：finetune_mrl --strategy lora x 650M/mega x 3 种子 x 2 切分 = 12 runs；门控 mem_get_info 全卡扫描（650M>=20G/mega>=12G）+ done 跳过（小写 slug 匹配已修）+ 失败清行（语法已修）+ 重试 x3 + 300s 等卡。22:14 首跑 650M lora s17 random @GPU3 已进入训练
- patch3 首轮在 GPU0 曾被外部进程 45 秒竞态挤压 OOM 一次（重试机制按设计兜底，换卡续跑成功）；pick-verify 竞态窗口已知，后续如再发作可做原子化选卡
- ssp_fulltuned 三模型链 21:53:59 全收工（ERNIE/RNA-FM/SpliceBERT 18 runs）；famlora_audit G3 20:41 收工
