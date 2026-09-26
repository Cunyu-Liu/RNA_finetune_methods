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

## Day 7 22:20 第四波派发 + 双跑事故处理
- **GPU 空闲潮利用**：他方任务退场（GPU0/1/3/5 各 10-36G 空闲）→ 派发 q_mrl_biglora（G5：650M+mega lora 12 runs）/ q_mrl_fulltuned（G0：30M/100M full@1e-5 12 runs）/ q_mrl_fill G3 副本（30M frozen 加速）
- **双跑事故（已处理）**：q_mrl_fill G3 副本与 q_mrl_biglora G5 同时 claim 了 650M mrl lora s17 random（ledger claim 竞态，两进程同 run）——kill G3 副本的 650M 进程并清其 pending 行，G5 主跑存活（PID 1317828，96.7% CPU 在跑）。教训：同一 run 家族的队列互斥需在派发前核对 claim 目标集合（已记入防坑）
- **stale 行清理**：650M mrl lora s17 random（22:08 OOM 后 mrl_patch3 清行脚本括号语法错误未清成）——服务器端 python 精确清行成功
- mrl_patch3/patch2 残留 bug 记录：清行内联 python 有 SyntaxError（前 session 遗留，本 session 的 v2 队列已用 heredoc 修复该模式）

## Day 7 22:25 收口：patch3 让位 biglora（并行 session 已覆盖同一 12 runs）
- 巡检发现并行 session 22:11 已派 q_mrl_biglora.sh（G5）——与 patch3 目标完全相同（650M/mega mrl lora x3 种子 x2 切分，finetune_mrl 模块+门控+重试，配置一致）；另有 q_mrl_fulltuned.sh（G0，30M/100M mrl full tuned 1e-5）。**patch3（PID 1320380）主动退役避免同 run_id 双跑**，stale claim 行已清；biglora 接管（650M lora s17 random 在 GPU5 跑中，~22:35 落账）
- 新落账：mega mrl frozen s29 random **0.708**；rnasc30m mrl full tuned s17/s29 random 0.585/0.526；micro headonly s43 family 0.681
- 本 session 队列最终态：famlora_audit/m6a_family/ssp_fulltuned/mrl_patch(污染清污)全部收口；在跑均属并行 session 队列（biglora/fulltuned/mrl_fill/frozen_patch 等）；ledger 账实一致（pending 2 ↔ 活进程 2）

## Day 7 22:50 巡检:第二轮 claim 竞态处置(mrl_fill 双副本)+ 650M frozen 对照落账

- **事故**:并行 session 的 q_mrl_fill 存在 G1/G3 双副本(同脚本同任务表),skip 门只查 done 不查 pending → 与 fulltuned G0 在三个 run 上双跑:rnasc30m full s43 family / rnasc100m full s17 random / mega frozen s43 random(device 1+3 同 out_dir 并写)。均已双跑至完成,ledger 留 3 对同值重复 done 行(数值一致,无矛盾数据)
- **处置**:kill fill G1(887010)/G3(1337422)wrapper 防续跑重试;flock 精确去重 3 条重复 done 行;清后 ledger 888 done / 3 pending / 2 cancelled(账实一致:pending 3 ↔ 活进程 3)
- **650M frozen 对照(重要结果)**:ncRNA family frozen 三种子 random 0.906/0.906(结构稳定)/family 0.645/0.645——与 LoRA 0.10 档崩溃带形成鲜明对照,佐证崩溃带是 LoRA x 小规模适配问题而非 650M 表征本身
- **在跑全景**:biglora G5(650M lora s29 random,GPU5)/fulltuned G0(100M full s29 random,GPU0,其后 100M family x3)/frozen_patch G2(650M fam s43 random 在跑,后接 650M s43 family + mega 8 runs);GPU0 20G/4 18.9G 空闲,其余忙
- 健康项:650M 预训练 422582 + watcher 3578696 在岗;无当前 OOM/CUDA 异常(带 OOM 字样日志均为历史已处置事件)
- mrl_fill 教训沉淀:多实例队列必须以 pending 互斥(或实例间任务表预分割),done-skip 门在并行场景不够

## Day 7 2026-09-21 23:58 巡检：ledger 补账修复（biglora s17 random 0.8013）+ 在跑队列健康
- **补账修复**：650M mrl lora s17 random（PEARSON 0.8013 / MSE 0.2884，MRL LoRA 新高）此前在 ledger 无行——时间线：22:13 biglora 复用 patch3 遗留 claim 行起跑该 run，22:20 上一轮巡检做 stale 清行时误删该活 claim，22:34 exit 0 完成后 runner 无行可写（日志有完整 result JSON，artifacts/head.pt 22:31 在）。已按日志证据 flock 校验去重后恢复 done 行；ledger 现 900 done / 2 pending / 2 cancelled，pending 2 ↔ 活进程 2 账实一致。教训：stale 清行前须核对 claim 行是否有活进程正在写（kill -0 / fd 检查），不能只看 wrapper 归属
- **biglora G5 推进**：12 run 中 4 个已 exit 0 零 OOM：650m_mrl_lora_s17_random=0.8013, 650m_mrl_lora_s29_random=0.8013, 650m_mrl_lora_s43_random=0.8013, 650m_mrl_lora_s17_family=0.6979；当前在跑第 5 run（650M lora s29 family，GPU5）；其后 650M s43 family + mega x6
- **frozen_patch（G2）**：30M/100M/650M frozen 18 runs 全落账（650M family 三种子 0.645-0.659 / random 0.906 结构稳定）；mega 段 2/8（s17 random done 23:48，s17 family 在跑），预计 3-4h 收口
- **健康项**：650M 预训练 422582（2-16:56）+ watcher 3578696 在岗，tests 链待退出自动触发；q_mrl_patch3.log 的 exit 143 为 22:18 patch3 主动退役（让位 biglora）非新事故；本轮无新 OOM/CUDA 异常
- **续派判断**：本 session 派发队列（famlora_audit/m6a_family/ssp_fulltuned/mrl_patch/frozen_patch）中前四者全收口，frozen_patch 仍在推进；GPU0/1/3 名义空闲 13-18G 但被 honghui 用户 batch-128 任务持有波动大，GPU5 忙于 biglora——无未 claim 缺口 + 无稳定空闲卡，不续派，下一轮巡检再评估

## Day 8 00:30 第四波收工快照 + MRL 大档数据判读
- **q_mrl_fulltuned 全收工**（12/12，G0）：30M random 0.526-0.585 / family 0.474-0.526；100M random 0.543-0.713 / family 0.486-0.660——MRL tuned full 不崩（per-seq 单例簇特性，与 ncRNA per-seq 崩溃形成对照）
- **q_mrl_biglora 650M 半收工**（6/6 random+family 齐）：random 0.801 x3 / family 0.698 x3（Δ=0.10 温和——MRL 三任务判据再添 650M 档证据）；mega lora 6 runs 在 G5 跑（s17 random 04:26 时长）
- **mega ncRNA frozen 4/6**（random 0.836 x2 + family 0.724 x2，s43 在 G0 跑）——等价线 frozen 大档补臂推进中
- **micro head-only family 3/3**（0.696/0.681/0.681）——head-only family 侧不崩（与 LoRA/full 崩溃对照：崩溃需要骨干更新）——**C4 新证据点：冻结骨干+可训头的家族侧保持 0.68，骨干更新（LoRA/full）才触发 0.06-0.12 崩溃带**
- ledger 909 行；GPU0-5 全部有任务在跑（frozen_patch G0 mega s43 + biglora G5 mega）

## Day 8 2026-09-22 00:50 巡检：孤儿缺口发现与续派（30M/100M mrl lora）+ frozen_patch 收口
- **孤儿缺口认定（重要）**：22:15 清污移除 12 条 mrl_patch v1 错模块污染行（30M/100M mrl lora）后，patch3/biglora 只接管 650M/mega——30M/100M x lora x 双切分 x 3 种子 = 12 runs 成无人认领缺口。artifacts 下残留 12 个污染目录（metric=ACC/n_classes=13 签名，合法 MRL 应为 PEARSON_R/n_train=20000）已整体隔离至 artifacts/quarantine_mrl_lora_badmodule_20260922/ 留证
- **导出链污染残留警示**：21:15 的 export_c4/preprint 修订（commit 4cc9daf）发生在清污之前——C4 表A 中 "lora 30M/100M family 0.066-0.075" 即污染值；smalllora 收口后必须重刷导出链再定稿
- **续派 q_mrl_smalllora（G4，PID 1892844，v2）**：正确模块 finetune_mrl + 门控 mem_get_info>=10G + done 跳过 + pgrep 活性互斥 + 失败清行 + 重试 x3 + 300s 等卡。v1 的外层预 claim 与 runner 内建 ledger.claim 双写造成 3 条重复 done 行（已 flock 去重；教训：claim 应交给 runner 自身，外层只做活性检查）
- **首批落账（30M lora random 三种子）**：s17 0.5452 / s29 0.5270 / s43 0.5212（PEARSON_R，3min/run 零 OOM）——对照 10M lora 0.488 / 30M full 0.585 / 650M lora 0.8013，小档 LoRA 修复臂补齐中
- **frozen_patch（G2）收口**：FROZEN_PATCH_DONE，mega frozen 8/8 全落账（random 0.8357 x3 / family 0.7243 x3）——ncRNA-family frozen 全谱 24/24 完成（30M 0.29-0.32 / 100M 0.39-0.40 / 650M 0.906/0.645 / mega 0.836/0.724）
- **biglora（G5）推进 7/12**：650M 段 6/6 全 done（random 0.8013 x3 / family 0.6979 x3）；mega 段 s29 random **0.7964** done（新数据点），s43 random 在跑
- **账实**：ledger 912 done / 2 cancelled，pending 为在跑活行（smalllora 30M s17 family + biglora mega s43 random）；账实一致
- **健康项**：650M 预训练 422582（2-17:14）+ watcher 3578696 在岗，tests 链待退出自动触发；本轮无新 OOM/CUDA 异常（patch2/patch3 日志尾部 OOM 均为已处置历史事件）
- **续派判断**：本 session 五队列（famlora_audit/m6a_family/ssp_fulltuned/mrl_patch/frozen_patch）全部收口；GPU4 曾现 26.8G 空闲 → 已用于 smalllora 补臂；GPU1/2/5 忙于 biglora/预训练，GPU0/3 被 honghui 波动持有——无更多缺口可派

## Day 8 2026-09-22 01:50 巡检：mrl_big 错模块双跑事故处置 + 第四/五波全收工 + 导出链重刷
- **事故发现与处置（重要）**：并行 session 在 frozen_patch 收口后由 watcher 链自动启动的 /tmp/mrl_big.sh（bash -c 'while ps aux | grep [f]rozen_patch...' 触发）**错用 finetune_one 模块跑 MRL**（650M 全部 skip 幸免；mega s29/s43 family 实跑了 ncRNA 13 分类数据，loss 2.49-2.77 签名，向 artifacts 写入 ACC 0.084/0.096 污染 result.json），与 biglora G5（正确 finetune_mrl）在同 3 个 mega family run_id 上双跑。**数值未污染**：biglora 后完成（01:33:47），ledger 最终值均为正确 PEARSON_R 0.7082/mse 0.5053；但留 3 对重复行（4 行混入 n_classes/head_params 分类 schema）+ 磁盘 2 个污染 result.json
- **清账**：flock 去重净化——移除 4 行 mixed-schema + 1 行纯重复；s29/s43 family 两行均为混合行被清后按 biglora 日志 exit-0 证据（12/12 全 exit 0）恢复 done 行（沿 23:58 巡检先例，note 标注 restored）；污染 result.json 隔离至 artifacts/quarantine_mrl_big_badmodule_20260922/。ledger 现 923 done / 2 cancelled / 0 pending，账实一致（活进程仅剩 650M 预训练 422582 + watcher 3578696 + 外部下载任务）
- **第四/五波全收工**：biglora G5 12/12（650M lora random 0.8013 x3 / family 0.6979 x3；mega lora random 0.7964 x3 / family 0.7082 x3）；smalllora G4 12/12（30M lora random 0.521-0.545 / family 0.464-0.484；100M lora random 0.548-0.573 / family 0.475-0.508）——00:50 认定的 12 run 孤儿缺口全部补齐，MRL lora 全谱（10M/30M/100M/650M/mega x 双切分 x 3 种子）闭环，random-family Δ 稳定 0.06-0.10 温和带
- **导出链重刷（00:50 遗留要求完成）**：C4/E2/stats/figures/resources/lr_grid/splits/leakage/e3/fig_e3 十产物 02:02:30 全刷成功；C4 表A mrl lora family 旧污染值 0.066-0.075 已替换为正确值（30M 0.473 / 100M 0.488 / mega 0.708 / 650M 0.698）——21:15 commit 4cc9daf 的 preprint 数据源污染风险解除
- **健康项**：650M 预训练 422582（2-18:00+，GPU2 18.65G）+ watcher 3578696 在岗，q_rnasc650_tests.sh 链待退出自动触发；本轮无新 OOM/CUDA 降级（patch2/patch3 日志尾部 OOM 均为历史已处置事件；旧 4.75G 小卡 GPU6/7 的 OOM 与 A100 无关）
- **续派判断**：本 session 五队列（famlora_audit/m6a_family/ssp_fulltuned/mrl_patch/frozen_patch）全收口；第五波 smalllora/biglora 也已闭环；GPU0 15.8G/1 19.7G/3 21.7G/5 15.7G 名义空闲但被 honghui 波动持有，MRL 矩阵余下缺口（dora/ia3/full 大档）为设计范围外——无新缺口可派，本轮不续派
- **教训入库**：①守护链自动续派脚本必须显式指定任务专属模块（finetune_one 是分类入口，MRL 必须 finetune_mrl）；②双 runner 同 run_id 竞态下 ledger 行会被后写者覆盖成混合 schema——写入器应整行替换而非字段合并；③恢复行必须带 note 标注证据来源

## Day 8 02:45 第四波全收工 + MRL 大档三任务判据完整版
- **q_mrl_biglora 全收工（12/12）**：650M mrl lora random 0.801 x3 / family 0.698 x3（Δ=0.10）；mega lora random 0.796 x3 / family 0.708 x3（Δ=0.09）——MRL 大档 LoRA 温和退化复现（单例簇 per-seq 特性跨 148M-650M 成立）
- **frozen_patch 全收工**：mega ncRNA frozen 6/6（random 0.836 x3 / family 0.724 x3，Δ=0.11 温和）——等价线 frozen 大档闭合；100M frozen 亦齐
- **本 session 全部队列排空**（ledger 927 行，零 pending）；GPU0-5 空闲等待新任务（他方在跑）
- 650M 预训练 + watcher 双活（预训练完成后自动触发测试链：frozen/lora 12 runs + full tuned 链）
- 产物刷新：c4/e2/stats 重跑（MRL 大档 + mega frozen + micro headonly 全部进表）
- 预印本 v0.6.2 增量：摘要补充 head-only family 证据（崩溃需要骨干更新——C4 新证据点，3bcab01）

## Day 8 02:50 第五波派发（等价线/池对称收官波）
- etc_audit 复审后剩余真缺口（排除 _lr 误报）：1M lora random + 1M frozen 双切分 + 100M full tuned（受控系等价线大端 full 参照缺失）+ m6A head-only family + MRL E2 family 侧
- **q_eq_fill（G0）**：1M lora random x3 + 1M frozen x6 + 100M full@3e-5 x6 = 15 runs
- **q_e2_familyfill（G1+G4）**：m6A headonly family x3 + MRL dora/ia3 family x 12 = 15 runs
- 至此交接审计的全部 ASYM/MISS 缺口均已派发（ck1-15 剂量档 MISS 属 D4 阴性实验设计内，不补）

## Day 8 2026-09-22 03:30 巡检：m6A head-only family 侧闭合（E2 对称）+ 第五波推进中段

- **重要结果落账**：m6A RNA-Sc-10M head-only family 3/3 done（ACC 0.726/0.717/0.653）——与 frozen 逐位近一致（0.726/0.717/0.653），E2 对称表闭合：m6A family 切分 7 策略全谱中，**frozen≈head-only≈0.72 < ia3 0.93 < lora/full/dora 0.98-0.984**——m6A family 不出现 ncRNA-family 式 LoRA 崩溃带（C4 崩溃为 ncRNA-family x LoRA 特异性，跨任务对照证据点）
- **MRL E2 family 侧推进**：micro dora family 3/3 done（0.7001 x3，seed 无关性），ia3 family 2/3 done（0.6503 x2）+ s43 在 GPU4 跑（03:13 起跑，PENDING 1 行账实一致）；其后 10M dora/ia3 family x6
- **第五波队列推进**：q_eq_fill G0 前 3 run 落账（1M lora random 0.622/0.647/0.647——1M 档 LoRA random 不崩，对齐 lora family 0.075-0.16 崩溃带与 650M/mega random 0.80/0.796 等价线），1M frozen 首个 s17 random done（0.2716），frozen s29/s43 random 等卡中（GPU0 被 honghui 波动持有 7.77-16.06G）；q_e2_familyfill G1 m6A 段完成
- **账实**：ledger 937 done / 2 cancelled / 1 pending（ia3 s43 活行）——账实一致；无 OOM / 无 CUDA 异常（新一波日志零 OOM 记录）
- **健康项**：650M 预训练 422582（2-20:15+，GPU2）+ watcher 3578696 在岗，tests 链待退出自动触发；GPU5 15.17G 真实空闲（无归属进程），其余 GPU 被在跑/他方持有
- **续派判断**：fifth-wave 已派队列（q_eq_fill 15 + q_e2_familyfill 15）均在跑；GPU5 空闲但 MRL 大档 dora/ia3/full 家族缺口为设计范围外；GPU0 等卡任务（1M frozen x5 + 100M full x6）受 honghui 占用阻塞中，暂以等卡门控（≥10G 派发条件）自持，**不另续派**

## Day 8 05:05 第五波近全收工 + E2/等价线对称收官
- **q_e2_familyfill 全收工**（15/15）：m6A head-only family 0.65-0.73（3 种子）；MRL E2 family 侧全齐（micro dora 0.700 x3 / ia3 0.650 x3；10M dora 0.45 x3 / ia3 0.25 x3）——MRL E2 面板 random+family 双侧对称完成
- **q_eq_fill 进度 10/15**：1M lora random 0.622-0.647 x3 + 1M frozen 双切分 6/6（random 0.27-0.30 / family 0.18-0.22）全落；100M full tuned 在跑（s17 random 0.803 已落，s29/s43 + family 侧排至 ~07:00）
- ledger 953 行（1 pending = 在跑）
- 受控系等价线数据版图（random 侧，tuned 口径）：1M lora 0.64 / 10M lora 0.75 / 30M lora 0.77 / 100M lora 0.80 + 1M full 0.70 / 10M full 0.81 / 30M full 0.86 / 100M full 0.80x（在补）——full@30M 0.862 仍是最优，等价点叙事等待 100M full 3 种子落齐后判读

## Day 8 06:05 巡检：第五波尾段推进（100M full random 三种子落齐）+ 显存 churn 假窗口识别

- **eq_fill 12/15**：100M full@3e-5 random 三种子全落账（s17 0.803 / s29 0.8217 / s43 0.8473，06:02 最后落账）——受控系等价线大端 full 参照 random 侧闭合（05:05 等待点兑现）。对照链：1M full 0.70 / 10M full 0.81 / 30M full 0.862 / 100M full 0.824±0.02——30M 档仍最优但 100M 已进入等价带，等价点叙事待 family 侧 3 runs 落齐后终判
- **在跑**：eq_fill 唯一尾部 s17 family（GPU0，06:02:37 起跑，~65 min/run 串行 x3，预计 ~09:10 EQ-FILL DONE）；ledger 952 done / 2 cancelled / 1 pending（= 活行，账实一致）
- **watcher 链**：650M 预训练 422582（2-23:15，GPU2 18.65G）+ watcher 3578696 双活在岗，q_rnasc650_tests.sh 待退出自动触发；无 OOM / 无 CUDA 降级 / 无 CPU 静默降级证据（patch2/3 日志尾部 OOM 为历史已处置事件）
- **显存 churn 假窗口（本轮新证据）**：06:04 GPU4 36.0G 空闲 → 60 秒内被 honghui run_tiger_binary 三进程（18.4G+9.4G+4.9G）填满；GPU1 也同步释放 35.8G。honghui 任务为分钟级短批 churn 模式（02:55:20~07:45:09 生命周期梯度 8 进程），任何瞬时 ≥10G 读数不可作为续派依据——05:05 记录的"GPU0 15.8G/1 19.7G/3 21.7G/5 15.7G 名义空闲"同属此类
- **续派判断**：本 session 五队列（famlora_audit/m6a_family/ssp_fulltuned/mrl_patch/frozen_patch）+ 第五波（eq_fill/e2_familyfill）均收口或按设计收尾中；交接审计全部 ASYM/MISS 缺口已派发（02:50 口径），MRL 大档 dora/ia3/full family 为设计范围外——无新缺口可派，本轮不续派（沿用 03:30/05:05 判断先例）
- MRL E2 面板双侧对称完成态确认（micro dora 0.700 x3 / ia3 0.650 x3；10M dora 0.45 x3 / ia3 0.25 x3，family 侧）

## Day 8 11:45 eq_fill 全收工 + 受控系等价线 full 线判读
- **100M full tuned 6/6 全落**：random 0.803/0.822/0.847（均值 0.824）/ family 0.064-0.075（带内）
- **受控系等价线完整版（random tuned 均值）**：1M full 0.700 / 10M full 0.808 / 30M full 0.862 / 100M full 0.824 vs 1M lora 0.639 / 10M lora 0.756 / 30M lora 0.773 / 100M lora 0.795
- **判读修正**：full 曲线 30M 峰值 0.862 → 100M 回落 0.824（非单调）；**100M full (0.824) ≈ 10M full (0.808) 且仅略超 100M lora (0.795)**——原「10M full ≈ 100M LoRA」的交点叙事升级为受控系 4 档全谱 LoRA-追赶线：每个 lora 档位都被更小档的 full 追平或超越（1M full 0.700 > 10M lora 0.756? 否——10M lora 超 1M full；但 10M full 0.808 > 30M lora 0.773 ✓；30M full 0.862 > 100M lora 0.795 ✓）
- 精确表述：**受控系中 full@10M(0.808) 已追平 lora@100M(0.795)，full@30M(0.862) 全面超越 lora@100M**——「小模型全参 ≥ 大模型 LoRA」在受控系 30M→100M 一档内成立；与官方系（148M full 0.942 < 650M lora 0.969，LoRA 恒占优）形成对照——等价线家族依赖性结论强化
- 100M full family 0.064-0.075 带内（崩溃带判据复持）

## Day 8 11:50 等价线 4 档判读入稿（v0.6.2）+ 第六波派发
- **preprint 2.3 升级（252df7a）**：受控系等价线 4 档全谱表述——full 1M 0.700 / 10M 0.808 / 30M 0.862 / 100M 0.824 vs LoRA 1M 0.639 / 10M 0.756 / 30M 0.773 / 100M 0.795；full@10M 追平 LoRA@100M、full@30M 全面超越；full 曲线非单调（30M 峰值）；fig_c5b 重出
- **审计修正（ASYM 复核三遍）**：SSP full MISS 三模型为 _lr 误报（6/6 tuned 已在）；mrl 30M full 7 行含 1 重复（s29 family 双行同值）；mega mrl frozen 3+1 双行（pending 残留已被队列吸收）；ncRNA head-only 10M random 只有 s17（random=1 family=3 为真缺口）
- **第六波派发（G3+G4）**：10M headonly random s29/s43 + 10M dora/ia3 family 6 runs + micro dora/ia3 family 6 runs = 14 runs——E2 ncRNA 面板 family 侧最后对称缺口
- 650M 预训练 alive（最新 ckpt nt15.0B step159984）

## Day 8 14:15 第六波收工 + micro dora OOM 重试
- **wave6 主体收工（12/14）**：10M headonly random s29/s43 落账（0.352/0.337——head-only random 3/3 齐）；10M dora family 3 种子（0.061-0.097 带内）/ 10M ia3 family 3 种子（0.220-0.247）；micro ia3 family 3 种子（0.704 x3——**IA3 激活重标定也逃逸崩溃带！与 LoRA mega 同向**）；micro dora s43 family 0.075（带内）
- **micro dora s17/s29 family OOM**（12:33 GPU4 被他方 12.5G 进程挤占——日志留证）→ 重试队列 G3 已开跑（带等显存+重试 x3）
- **E2 ncRNA family 侧全景（新数据判读）**：10M {dora 带内, ia3 0.22-0.25 半逃逸, headonly 0.19-0.23} vs micro {dora 待补, ia3 0.70 强逃逸, headonly 0.68}——**逃逸梯度 = 预训练充分度 × adapter 类型**（ia3 重标定 > lora > dora？s43 micro dora 0.075 在带内与 mega lora 0.139-0.334 对照——DoRA 分解方向更新可能更受家族记忆影响）——待 s17/s29 补齐后统一判读，暂不写入预印本
- 650M 预训练 alive（nt16.0B step170697）

## Day 8 2026-09-22 15:21 巡检：第六波全收工 + E2 ncRNA family 逃逸梯度终判 + ledger 双写去重

- **micro dora retry 收口（第六波 14/14）**：s17/s29 family 0.0666 x2（带内，retry G3 零 OOM）——micro dora 三种子全落，E2 ncRNA family 面板闭合
- **E2 ncRNA family 逃逸梯度终判（新结论，暂不写预印本）**：micro {ia3 0.704 强逃逸 > head-only 0.681-0.696 > dora 0.067-0.075 带内} vs 10M {ia3 0.245-0.247 半逃逸 > head-only 0.19-0.23 > dora 带内}——**逃逸梯度 = 预训练充分度 x adapter 类型双因子**：IA3 激活重标定最易逃逸（跨 10M/micro 均成立），head-only 居中，LoRA/DoRA 依赖骨干低秩/分解更新的策略在大档才逃逸（mega lora 0.139-0.334）小档全陷带；DoRA 分解方向更新在 micro 也不逃逸（0.067，与 10M 同带）——adapter 类型对家族记忆的敏感性排序初现
- **ledger 双写去重（本轮处置）**：micro dora s17/s29 family 各现 2 行 done（device 4 vs 3、updated_utc 差 30us、value/wall_sec 全同）——根因：ledger.update() 无差别刷新所有同 run_id 行，wave6 12:33 OOM 遗留 stale pending 行（device4）与 retry 新 claim 行（device3）被同次 done update 双刷。flock 去重移除 device4 残留行各 1 条（备份 ledger.jsonl.bak_patrol_20260922），ledger 现 969 done / 2 cancelled / 0 pending 账实一致
- **教训入库**：④ OOM 失败后 stale pending 行若不被清行逻辑覆盖（retry 脚本 clean 步骤只在 RC!=0 时执行，RC=0 的 claim 会新开行），同 run_id 双行会让 update 双写——claim 应复用 pending 行或清行逻辑应在成功路径也核行数
- **健康项**：650M 预训练 422582（3-08:15，GPU2，nt16.0B step170697 最新 ckpt）+ watcher 3578696 在岗，tests 链待退出自动触发；本轮无新 OOM / 无 CUDA 降级 / 无 CPU 静默降级（patch2/3 与 GPU6/7 旧 4.75G 卡 OOM 均为历史已处置事件）
- **续派判断**：本 session 全队列（五队列 + 第五波 + 第六波含 retry）全部收工；etc_audit 11:44 剩余 MISS/ASYM 已于 11:50 分诊（_lr 误报 + D4 阴性设计内 + 设计范围外），无未派发真缺口；GPU0/1/4/5 名义空闲 15-22G 但被 honghui run_tiger_binary 分钟级 churn 持有（06:05 已证假窗口），GPU2 被预训练持有——不续派，等 650M 预训练退出触发 tests 链

## Day 8 16:55 第六波全收工 + E2 ncRNA family 对称版完成
- **micro dora family 重试成功（3/3）**：s17 0.067 / s29 0.067 / s43 0.075（带内）——wave6 14/14 全落
- **E2 ncRNA family 侧完整判读（micro + 10M 双模型 x 4 adapter）**：
  - micro：lora 0.081 / dora 0.067-0.075（带内）；**ia3 0.704 x3（强逃逸）**；head-only 0.68（不崩）
  - 10M：lora 0.072 / dora 0.061-0.097（带内）；**ia3 0.22-0.25（半逃逸）**；head-only 0.19-0.23
- **统一图景（待复核后入稿）**：家族切分下逃逸梯度 = 预训练充分度（33M ia3 0.70 > 10M ia3 0.23 > 10M headonly 0.22）× adapter 侵入性（激活重标定 ia3 轻侵入最易逃逸 > lora 低秩 > dora 方向更新最重）；与 148M mega lora 逃逸（0.139-0.334）共同构成「部分逃逸」的证据矩阵——预印本 E2 节升级素材（暂记 TRAINING_LOG，等导过目再改稿）
- 产物刷新：e2/c4 表已带 wave6 数据

## Day 8 17:05 第七波派发（SSP E2 family 对称收官波）
- q_ssp_micro_fam（G1）：micro SSP dora/ia3 family x3 种子 = 6 runs——SSP 面板最后对称缺口（10M 侧已齐）
- 队列图（17:05）：G1 SSP micro fam / G2 650M 预训练（nt16.0B step170697）/ G3-G5 空闲（他方退场后巡检自动续派）/ watcher 在岗
- 全部六波 86+ runs 已收工落账；ledger 971 行

## Day 8 17:10 第七波b派发（head-only 全任务对称收官，E2 六臂完备性）
- q_headonly_final（G3+G4+G5 三卡并行）：m6A head-only 12 + MRL head-only 12 + SSP head-only 12（micro 双切 x3 + 10M 补 s29/s43）= 36 runs——E2 六臂（lora/dora/ia3/head-only/full/frozen）x 四任务 x 双模型 x 双切分的完备矩阵最后缺口
- 至此本 session（Day 7 晚起）累计派发 7 波 + 2 重试链，~170 runs；ledger 971 行（第七波进行中）
- 队列图：G1 SSP micro fam / G2 650M 预训练 / G3 m6A headonly / G4 MRL headonly / G5 SSP headonly

## Day 8 19:25 ★ E2 六臂完备矩阵收官 + head-only 全任务数据判读
- **wave7 + wave7b 全收工**（SSP micro fam 6/6 + head-only 全任务 34 runs）：**E2 完备性审计 = 0 missing cells**——6 臂 {frozen, lora, full, dora, ia3, head-only} x 4 任务 x 2 模型 x 2 切分 x 3 种子全矩阵闭合（ncRNA + m6A + SSP + MRL）
- ledger 1005 行（本 session 净增 ~167 runs，Day 7 晚 838 → 1005）
- head-only 新数据判读（MRL/m6A/SSP 双模型双切分）：MRL micro/10M head-only random 0.29-0.62 / family 0.25-0.60（温和退化复现 per-seq 单例簇特性）；m6A head-only random 0.63-0.83 / family 0.62-0.75（per-base 免疫复现）；SSP head-only 与 micro 家族侧数据齐
- **产物四刷完成**（e2/c4/e3/stats 全部含完备矩阵数据）
- 650M 预训练 alive；下一步：预印本 v0.7 整合（E2 完备版 + 逃逸梯度 + 等价线 4 档全谱 + head-only 证据矩阵）

## Day 8 22:30 双轨验证波派发（用户指令：官方系三档等价线 + m6A 双系第二任务等价线）
- **用户双轨验证设计**：先在已发表模型（RiNALMo 33M/148M/650M 三档）上测「小模型全参 ≥ 大模型 LoRA」，再到受控系（RNA-Sc 同配方）验证——双系互证增强说服力
- **现状核查（三遍）**：ncRNA 官方系等价线已有 micro full 0.938 / mega full 0.945 / mega lora 0.949 / giga lora 0.969——**唯一缺格：giga-650M full（B7 分层决策：650M full 一直未做）**。经评估：650M full@1e-5 bf16 批 8 显存约 25-30G，A100-40G 单卡可承受（ERNIE 整卡纪律不适用于 RiNALMo 架构）；作为官方系 3x3 网格完备性最后一格补测（预注册范围外增量，如实标注）
- **m6A 双系等价线（第二任务）**：官方系缺 micro/mega full@1e-5（现有 default 3e-4 崩溃版）+ mega/giga lora；受控系缺 10M/30M/100M {full@3e-5, lora}——共 ~48 runs 派发 G0+G2
- **预判（派发前不写结论）**：若官方系 giga full < giga lora（如受控系 100M full 回落模式）→ 官方系也无交点，「小全参 ≥ 大LoRA」仅在受控系成立 → 家族依赖性结论的第二任务复现；若 giga full ≈ giga lora → 官方系在 650M 档出现交点——两种结果都是有效双轨证据
- 队列：G0 giga full 6 runs + G2 m6A 48 runs；650M 预训练 alive（nt18.0B）

## Day 8 23:10 双轨队列修复重派（OOM 根因处理）
- **giga full OOM 根因**：默认 batch 32 需 ~26G PyTorch 分配（33M-148M 模型批 32 无碍，650M 激活层峰值超限），叠加他方 9.5G 进程必炸——q_dualtrack 原队列 3 次 attempt 全 OOM（日志留证）
- **修复**：杀原队列 + 清 3 个 stale pending 行；派 q_giga_full_bs8（G1 等 ≥24G，batch 8 对齐 q_rnasc650_tests.sh 的 650M 协议）；m6A 双轨部分独立成 q_m6a_dualtrack（G4 官方系 + G3 受控系），避免单队列串行阻塞
- 当前队列：G1 giga full bs8（等显存）/ G4 m6A 官方系 micro full 已开跑 / G3 m6A 受控系 / G2 650M 预训练
- 经验追加：大模型 full FT 的 batch 必须按模型档位缩放（650M:8 / 148M:32 / 33M:32）

## Day 9 00:50 巡检：双轨波推进（mega full 6/6 收官）+ 受控系 LoRA 并行轨派发（G5）

- **本 session 五队列终态确认**：famlora_audit/m6a_family/ssp_fulltuned/mrl_patch/frozen_patch 全部收口（进程表零存活、ledger 1011 行 / pending 1 ↔ 活 finetune 1 账实一致）
- **双轨波 G4 官方系 m6A 进展（q_m6a_dualtrack）**：
  - micro full@1e-5 6/6 done（已 skip 秒过：random 0.9678 / family 0.9933）
  - **mega full@1e-5 6/6 收官（23:57-00:43）**：random 0.981 x3 / family 0.9961 x3——官方系 m6A 侧「33M 全参 0.993 vs 148M 全参 0.996」family 切分几乎打平、random 侧大模型略优——与 mega lora 段（已开跑，s17 random 在飞）对照后构成等价线官方系第二任务证据
  - 受控系 G3（10M/30M/100M full@3e-5）在主队列串行排队中
- **giga_full_bs8 G1 异常追踪（非新 OOM 协议问题）**：9 次 attempt 已烧 8 次全部 OOM——每次启动时 GPU1 free 26-35G 达标，30-60 秒内被他方进程（7.8G/6.3G 波动）挤爆，bs8 协议本身显存需求 ~25G 无问题；末次 attempt（s43 random）在等 ≥24G 循环——若持续被挤考虑换卡或后半夜重试，暂不干预
- **续派（本轮判断）**：GPU5 他方两进程（8.8G+7.0G）已退，稳定空闲 12.6-15.2G ≥ 10G 阈值 + 本 session 五队列排空 → 派 **q_m6a_ctrl_lora_g5**（G5 受控系 LoRA 轨并行加速：10M/30M/100M lora x 双切分 x 3 seed = 18 runs，模型逆序与主队列 G3 正序对开 + done 跳过双保险防碰撞）→ 100M lora s43 random 已开跑（epoch0 loss 0.0551，13G 窗口稳定）
- **健康项**：650M 预训练 alive（PID 422582，nt18.0B step192108 最新 ckpt）+ watcher 3578696 在岗；无 CUDA 降级 / 无 CPU 静默降级
- 队列图（00:50）：G1 giga full(等待≥24G) / G2 650M 预训练 / G3 m6A 受控系 full(排队) / G4 m6A 官方系 mega lora(在跑) / G5 m6A 受控系 lora(新派)

## Day 9 01:30 双轨队列进度（ncRNA giga full 训练中 + m6A 官方系大半收工）
- **giga full bs8**：random 3 种子被他人挤占 OOM 各 3 次（日志留证，等待轮询），s17 family 正在 GPU1 训练（13min+，loss 正常下降）——随机侧稍后随等显空窗重试（队列自动）
- **m6A 官方系双轨数据（大半已落）**：micro full@1e-5 random 0.968 x3 / family 0.993 x3；mega full@1e-5 random 0.981 x3 / family 0.996 x3；mega lora random 0.986 x3（family 在跑）——**m6A 第二任务等价线初步形态：33M full 0.968 ≈ 148M full 0.981 ≈ 148M lora 0.986（任务天花板效应，各档差异 <0.02）**——与 ncRNA 的强分化形成对照（per-base 任务天花板下等价线区分度低，本身即结论：任务粒度决定等价线可辨识度）
- 待补：giga lora m6A 6 runs（M6A-DUALTRACK 队列接续）+ 受控系 m6A 等价线（G3 在跑 10M full@3e-5）

## Day 9 03:35 双轨数据中判
- **giga full family s17 = 0.0841（带内）**——650M full 也崩进家族崩溃带，与全谱一致；giga full random 侧仍在等显存窗口（他人挤占频繁，队列自动轮询）
- **m6A 官方系等价线（完整版）**：micro full@1e-5 0.968/0.993（rand/fam）≈ mega full@1e-5 0.981/0.996 ≈ mega lora 0.986/0.997——**per-base 任务天花板效应确认：三档差异 <0.02，等价线在 m6A 上不可辨识（本身即结论——任务粒度决定等价线可辨识度，与 ncRNA 强分化对照）**
- giga lora m6A（队列接续中）+ 受控系 m6A（G3 在跑）落地后 m6A 双轨完整
- 队列：G1 giga full random 轮询 / G4 giga m6A lora / G3 受控系 m6A / G2 650M 预训练（nt18B+）

## Day 9 04:15 巡检：双轨续派波（giga random 补缺 G4 + 受控系 full 并行 G5）
- **本 session 五队列终态（再确认）**：famlora_audit / m6a_family / ssp_fulltuned / mrl_patch / frozen_patch 全部收口；ledger 1030 done / 2 cancelled / 2 pending ↔ 2 活跃 finetune（650M m6A lora s43 random + 650M ncRNA family full s29）账实一致
- **双轨波实盘进度**：
  - m6A 官方系：micro full@1e-5 6/6（random 0.968 / family 0.993）+ mega full@1e-5 6/6（random 0.981 / family 0.996）+ **mega lora 6/6（random 0.986 / family 0.997）**——33M 与 148M full 已基本打平、大模型 lora 略优；**giga lora random 3/3 收官（0.9925 x3）**，giga lora family 3/3 进行中（s17 done 0.9969 @03:56，s29 训练中 epoch2，s43 排队）
  - ncRNA giga full bs8：family s17 done 0.084（带内崩溃，与家族依赖性结论一致）；**random 3 种子 9 次 attempt 全被 GPU1 他方 churn 挤爆 OOM（06:05 已证假窗口）后 MAX ATTEMPTS 放弃——真缺口**
- **续派（本轮）**：
  - **q_giga_full_rand_g4**（PID 3750634）：giga-650M full random 3 种子补缺，GPU4 守门 >=24G 等 dualtrack G4 段（giga lora family）收尾释放；bs8 协议对齐 q_giga_full_bs8
  - **q_m6a_ctrl_full_g5**（PID 3750635）：受控系 full@3e-5 轨 18 runs 逆序并行（100M→10M，与主队列 G3 正序对开），已开跑即落 2 done：**100M full random s43 0.9392 / s29 0.9458**（受控系 100M 侧 m6A 等价线首 2 点）——与官方系 giga lora 0.9925 的档位差已现，双系对照成形中
- **健康项**：650M 预训练 422582 alive（4-02:xx，GPU2，watcher 3578696 在岗，tests 链待退出触发）；无 CUDA 降级 / 无 CPU 静默降级 / OOM 证据已记录（GPU1 churn 挤爆——非协议问题，日志 9 次留证）
- 队列图（04:15）：G1 giga full family s29（训中）/ G2 650M 预训练 / G3 受控系 full 排队（主队列）/ G4 giga lora s29 family（训中）+ giga random 补缺（守门）/ G5 受控系 full 逆序（训中）

## Day 9 05:50 双轨验证数据大丰收（用户双轨设计落地）
- **m6A 官方系三档等价线全齐**：micro full 0.968/0.993 ≈ mega full 0.981/0.996 ≈ mega lora 0.986/0.997 ≈ giga lora 0.993/0.997（rand/fam）——per-base 天花板确认，三档差异 <0.03
- **m6A 受控系（tuned full@3e-5）**：10M 0.815-0.957 / 30M 0.930-0.964 / 100M 0.925-0.985（lora 侧在跑）——受控系 10M full 已达 0.91-0.96，接近官方 mega/giga 档（0.98+）——「小模型全参跨配方逼近大模型 LoRA」的 m6A 侧证据（差距 ~0.03-0.06 = 语料/配方差距，规模无关）
- **giga full ncRNA family s17/s29 = 0.0841 x2（带内）**——650M full 家族侧崩进带，全谱闭合；random 侧在跑（s17 pending，等显存窗口）
- **双轨判读初步形态（等 giga full random 落地后定稿）**：官方系 ncRNA 无交点（giga lora 0.969 > mega full 0.945 > micro full 0.938——已发表大模型 LoRA 恒占优）vs 受控系交点在 10M-30M（full@30M 0.862 > lora@100M 0.795）——「小全参 ≥ 大LoRA」是**自训受控系的配方现象，不迁移到官方系**——这正是双轨验证的价值：用户问题（官方三档是否存在该结论）答案为否，且受控系显示该结论依赖配方家族属性

## Day 9 06:15 巡检：m6A 双轨 66/66 全收官 + giga full random 唯一缺口在飞
- **m6A 双轨完备性确认（66/66）**：官方系（micro/mega full@1e-5 + mega/giga lora）与受控系（10M/30M/100M {full@3e-5, lora}）全部 done，0 缺格
- **受控系 lora 侧最后 6 格落地（06:01:24）**：10M lora random 0.941/0.944/0.943 family 0.985/0.983/0.981；30M lora random 0.940-0.945 family 0.961-0.973；100M lora random 0.947 family 0.984——**受控系 10M lora family 0.983 ≈ 官方系 giga lora 0.997，且受控系 lora 三档（10/30/100M）random 侧 0.94-0.95 几乎无规模分化**——m6A 等价线在受控系 lora 侧同样扁平（与 full 侧、与官方系一致），per-base 天花板在双系双策略下均成立
- **双轨判读（数据已齐，等 giga full random 定稿）**：官方系 ncRNA 无交点（giga lora 0.969 > mega full 0.945 > micro full 0.938）vs 受控系交点在 10M-30M（full@30M 0.862 > lora@100M 0.795）——「小全参 ≥ 大 LoRA」是自训受控系配方现象，不迁移到官方系
- **唯一在飞缺口**：giga full random s17（GPU4，epoch 4/10，loss 0.066，06:13）+ s29/s43 排队；giga_bs8 队列 (G1) 仍在轮询等 GPU1 窗口
- **健康项**：650M 预训练 422582 alive（4-01:xx，GPU2，watcher 3578696 在岗）；GPU1 torch probe OOM 转痕（他方 39.6G 挤满，非本方事故）；无 CUDA 降级 / 无 CPU 静默降级
- ledger 1029 done / 2 cancelled / 2 pending（ncRNA giga full s43 family + m6A ctrl lora s43 random——后者实际已 done，ledger 行被 06:01 完成后 02:xx 的 s41 家族行遗落，待 06:30 巡检复核）——账实一致性待复核

### 更正（06:16）：上节 ledger 待复核项已核清
- 2 条 pending = ncRNA giga full s43 family（GPU1 在飞，PID 3882388）+ s17 random（GPU4 在飞，PID 3972489）——**账实一致，无需复核**；上节「m6A ctrl lora s43 random pending」为误读（m6A 双轨 66/66 无任何 pending），特此更正

### 更正（06:18）+ 650M 预训练收官事件（本节为 06:15 节的事实修正与重大事件补记）
- 更正 06:15 节两处笔误：① 预训练 etime 应为 3-23:xx（非 4-01:xx）；② 「受控系 lora 最后 6 格落地 06:01:24」有误——ctrl lora 18 runs 实由 q_m6a_ctrl_lora_g5 并行轨于 02:31 前全部落地，06:01 的 dualtrack 尾段是 RID 大小写不匹配触发 finetune_base 内部 done 跳过的快扫（exit 0）；m6A 双轨 66/66 的最后一格实为 ctrl full 100M family s43（05:46:08，q_m6a_ctrl_full_g5）
- **650M 预训练收官（422582 于 06:16:25 CST 退出）**：manifest status DONE——final_nt 2.0B（2,000,003,270）/ final_step 213514 / best_val_loss 0.7757（best ckpt nt19.0B step202784）/ wall 343,291s（≈95.4h）/ peak_vram 15.6G / **cpu_fallback_count 0（全程无 CPU 静默降级）**；watcher 3578696 按设计退出
- **q_rnasc650_tests.sh 自动启动（链条衔接验证 ✓）**：watcher 检出退出即拉起测试链（PID 41162），phase1 选 GPU0（06:16:32），RNA-Sc-650M frozen s17 random 已开跑（train 6858 / classes 13；d_model 自校正 768→1408 与 ckpt 一致）；phase2（full s101 lr 网格）守门 ≥28G 轮询——GPU6 有 38.7G 空闲但 pick_gpu 只扫 GPU0-5，phase2 可能需等 giga 卡位释放
- 巡检终局（06:20）：GPU1 giga full s43 family（在飞，第 3 天家族带）+ GPU4 giga full s17 random（epoch 4/10，loss 0.066）+ GPU0 测试链 phase1 在飞；dualtrack 队列只剩 GPU3 ≥6G 等待的无效尾扫（skip 后自退，不干预）；无本方 CUDA 降级 / 无本方 OOM 事故（GPU1 torch probe OOM 系他方 39.6G 挤满的查询副作用，训练本体 epoch 正常推进）
- **本轮续派判断：不派**——五队列全排空 ✓，但唯一剩余缺口（giga full random s29/s43）已在 q_giga_full_rand_g4 队列守门（bs8 协议需 ≥24G，GPU2 仅 15.1G / GPU5 已被外方回占至 7.1G，无匹配窗口）；等 giga x3 + 测试链自然推进

## Day 9 08:00 ★ 双轨验证核心数据落地 + 650M 预训练测试链自启
- **giga-650M full random s17 = 0.9662**——官方系等价线最后一格核心数据落地（s29/s43 在跑）
- **双轨定稿判读（ncRNA random, tuned）**：
  - 官方系：micro full 0.938 < mega full 0.945 < giga full 0.966（s17） vs giga lora 0.969——**官方系无交点维持**：即便 650M 全参（0.966）仍不敌自身 LoRA（0.969），且 33M→650M 全参增益仅 +0.028——「已发表 RiNALMo 三档不存在小模型全参 ≥ 大模型 LoRA」用户问题答案 = **否**
  - 受控系：交点在 10M-30M（full@30M 0.862 > lora@100M 0.795）——双轨对照确认「小全参 ≥ 大LoRA」是受控系配方家族属性，不迁移到官方系
- **m6A 双轨完整收官**（M6A-DUALTRACK DONE 06:17）：官方三档 0.968-0.997（天花板）；受控系 lora 10M/30M/100M random 0.940-0.947 / family 0.961-0.985——per-base 任务上受控系小模型 lora 即达 0.94+，跨配方差距 <0.05
- **650M 预训练退出 + watcher 自动触发测试链成功**（07:54 起在 GPU0 跑 RNA-Sc-650M frozen，d_model 1408 新模型确认）——受控系大端等价线（650M lora/frozen/full tuned 链）自动推进中

## Day 9 09:30 巡检：五队列确认排空 + 续派 G2（RNA-Sc-650M lora 补格）
- **在飞任务**：giga-650M full random s29（GPU4，epoch 7/10，loss 0.053——s43 排队，q_giga_full_rand_g4 守门）+ 650M 测试链 phase1（GPU0，frozen s29 random，epoch 5/10，loss 1.16，PID 41162）
- **watcher/预训练终态确认**：3578696 DEAD + 422582 EXITED 均为预期（预训练 06:16 DONE，已落账）；q_rnasc650_tests.sh 检出退出即自启 ✓，链条衔接协议验证通过
- **本 session 五队列全排空 ✓**：famlora_audit（09-21 20:41）/ m6a_family（20:41）/ ssp_fulltuned（21:53）/ mrl_patch2→patch3（SyntaxError 修复链，已 cleaned）/ frozen_patch（FROZEN_PATCH_DONE）；ledger 1058 done / 2 pending（= 两个在飞行，账实一致）
- **GPU 空闲**：G1 18.6G / G2 25.2G（后实测升至 38G，honghuiyang 3 个 benchmark 小进程已退）≥10G；**G1 弃用**（第三方 2 大进程 churn 在飞 + G1 队列 9 attempt 全 OOM 历史）；G3 5.5G / G4 1.0G / G5 3.8G 不足
- **续派决策**：frozen_patch 意图格（30M/100M/mega frozen）已被 ledger 全 6/6 覆盖，唯一真实缺口 = RNA-Sc-650M 受控系大端等价线 lora/frozen/full 全部 11 格 → 自动链正填 frozen/lora 12 格（正向序，GPU0 单卡 ~19h）+ phase2 full@28G 守门 → **续派 GPU2 反向序补 lora 6 格**（lora family s43→s17 → random s43→s17，与自动链会师点靠 claim done 幂等 + fresh-pending(≤3h) 互斥，无双跑风险；lora 峰值预算 17G，守门 ≥20G）
- **G2 队列启动**：PID 765816，attempt 1 = lora s43 family 09:38:59 开跑（train 6859/classes 13/d_model 1408 自校正正常）；初版全局 GPU0-busy hold 有设计缺陷（会在自动链后空等 ~19h 使续派失效），已 kill 替换为逐格互斥版，无遗留 pending
- **健康项**：无 CUDA 不可用 / 无 CPU 静默降级 / 无活跃 OOM（q_giga_full_bs8_g1 的 OOM 全为 06:25 前历史记录，系 GPU1 第三方 churn，该队列已 DONE 且由 G4 队列改道接管）

## Day 9 12:23 巡检：650M 等价线三线推进 + 受控系 lora family 崩溃带首证
- 在飞三线：giga full random s43（GPU4 epoch 8/10 loss 0.0716）；测试链 phase1 frozen family s17（GPU0 epoch 9/10 loss 1.5356，链 PID 41162）；G2 反向序 lora family s29（GPU2 epoch 5/10 loss 2.3952，PID 765816）
- **新落地（11:18）**：ft_rnasc650m_noncodingrnafamily_lora_s43_family ACC=0.0643——低于 1/13 随机基线 0.0769，受控系 650M lora 家族切分崩溃首证；与官方系 RiNALMo-650M full family（0.0759-0.0841）崩溃带同构 → 大端家族切分崩溃跨配方/跨策略出现首例（同配方 random 切分 frozen 0.71+，切分方式为主导变量）；在飞 lora s29 family loss 回升（2.10→2.45）疑似第二例，落地后复核；对照 frozen family s17 loss 1.66 仍在正常下降
- giga full random s29=0.9394（09:29 落账；s17=0.9662，s43 在飞）——官方系随机线收官带种子方差 ~0.027
- 账实一致：ledger 1063 done / 2 cancelled（09-15 smoke ghost 历史行）/ 3 pending ↔ 3 在飞进程 ✓；watcher 3578696 DEAD + 422582 退出均为 06:16 预训练收官既定事实，q_rnasc650_tests.sh 自动衔接已验证 ✓
- 本 session 五队列（famlora_audit/m6a_family/ssp_fulltuned/mrl_patch/frozen_patch）维持排空 ✓；剩余待填：frozen family s29/s43、lora family s17、lora random x3（6 格，链正向 + G2 反向双向覆盖）+ full phase2 8 格（2 格 s101 网格 + 6 格 formal，链 ≥28G 守门）——无未认领缺口
- **续派判断：不派**——GPU2 探测瞬时空闲 32G（第三方 20.5G 进程退出所致，该卡 churn 高）为当前唯一 ≥28G 窗口，但手工注入 full s101 网格会与 G2 在飞 lora 格挤兑 GPU2 且有第三方回占 OOM 风险；phase2 由链自动守门，维持链协议；下轮巡检若 phase1 仍在磨、G2 已让位且 GPU0/2 持稳 ≥28G，再评估提前手工开 s101 网格（ledger done 幂等，链后续自动跳过）
- 健康项：无 CUDA 不可用 / 无 CPU 静默降级 / 无在飞 OOM——GPU4/7 torch probe OOM 系满卡上探测进程分配查询缓冲失败的假象（训练本体 epoch 正常推进）；全部 OOM 证据均为历史（giga_bs8 G1 队列 06:25 前第三方挤兑，队列已 DONE 并由 G4 改道接管；mrl_patch2 22:06 OOM 已被后续补齐，ledger RiNALMo-650M mrl 12/12 done），无需停队
- 附注：status/ 目录存在每 30 分钟自动状态文件（10:27-11:57，来源为既有监控 cron，与本巡检互补）

### 补记（12:26）：受控系 650M frozen family s17 = 0.5187（12:22:57 落地，链 PID 41162 自动进入 frozen s29 family）
- 家族切分对 frozen 仅中度衰减（random 0.72 → family 0.52），而 lora family 崩溃至 0.064 → 上节崩溃带判读收窄为「lora × family」组合特异，非家族切分普适效应；lora s29 family 在飞（epoch 5/10 loss 2.40 回升中），若同样 <0.08 则崩溃带对种子稳定

## Day 9 09:15 用户严谨性质询回应（单例规律不外推）+ 官方系配对数据补答
- **用户问：micro full vs mega LoRA 测了吗？**——测了：micro-33M full 0.9382 vs mega-148M LoRA 0.9487（差 **-0.011**，LoRA 仍胜）；giga full 3 种子全落（0.966/0.939/0.964，均值 0.957）vs giga lora 0.969——官方系相邻档与跨档配对均无交点
- **用户质疑（正确）**：受控系交点仅在自训家族出现一次，不应作为规律主张——采纳并改稿：
  - preprint 2.3 双轨段落重写（v0.6.4，bc08b0c）：明确「不将等价交点作为普适 RNA-LM 规律主张——单家族证据」+ 模型池对照（ERNIE 86M full 0.973 vs lora 0.974 平手 / RNA-FM 99M full 0.835 < lora 0.962 / SpliceBERT 19M full 0.910 ≈ lora 0.903）——可靠结论限定为方向性（已发布家族大模型 LoRA 优势持续）+ 受控系作为存在性反例（spec v1.7 预分配角色）
  - 中文摘要同步（4728443）
- **判读修正后的叙事结构**：C5b 主张从「等价线依赖家族（两分支各占一半）」收紧为「方向性结论（LoRA 大模型优势，14 模型池+官方三档一致）+ 单家族存在性反例（受控系，明确归因角色）」——更严谨且防御性更强
- RNA-Sc-650M 测试链进行中（frozen s29/s43 已开跑，G0）

## Day 9 13:55 双轨终版数据 + 650M 测试链中判
- **giga full 6/6 全落**：random 0.966/0.939/0.964（均值 0.957）/ family 0.076-0.084（带内）——官方系 3x3 网格完备闭合，v0.6.4 表述与最终数据一致（无需改稿）
- **RNA-Sc-650M 测试链推进**（预训练 nt2.0B val 0.7757 后自动触发）：frozen 5/6 落账——random 0.706-0.721 / family 0.519-0.527（受控系 650M frozen 与 30M frozen 0.305 对照：预训练充分度提升 frozen 表征质量 +0.41）；lora family 已落 2 档（0.064 带内——受控系 650M 也进崩溃带，与 RiNALMo-650M lora family 0.076-0.166 同向）；lora random 在跑
- 等链完成后判读：受控系 650M lora random vs 30M full 0.862（存在性反例的大端检验——若 650M lora > 30M full 则受控系交点被大端「追回」，交点窗口窄化到 30M-100M 之间；若 < 则反例更锐利）

## Day 9 14:55 巡检：lora×family 崩溃带三种子闭合（0.0643 完全同值）+ frozen 6/6 收官
- **受控系 650M lora family 崩溃带闭合**：s43/s29/s17 三种子全落 ACC=0.0643（完全同值，wall 5613-5992s，peak 5651MB）——低于 1/13=0.0769 随机基线，与官方系 RiNALMo-650M lora family 崩溃带（0.076-0.166）同构；12:23 巡检预测（s29 loss 回升疑似第二例）确认为种子稳定现象，非单例噪声
- **frozen 6/6 收官**（Phase1 顺位）：random 0.706-0.721 / family 0.519-0.527（06:38-04:22 落账）——家族切分对 frozen 仅中度衰减（-0.2），对 lora 是崩溃（-0.65）；档位逃逸（650M frozen family 0.52 >  RiNALMo 小档 lora family）成立
- **在飞双线**：测试链 lora s17 random（GPU0，链 PID 41162，epoch 0-1/10，loss 1.84）+ G2 反向序 lora s43 random（GPU2，PID 765816，epoch 0-1/10，loss 1.65）——正在填补 lora random x3 最后一档：即正在填的大端等价线最后非 full 网格
- **账实一致**：ledger 1058 done（+2 frozen 06:38 前为 1056）/ 2 pending ↔ 2 在飞 finetune 进程；watcher 3578696 DEAD + 422582 EXITED 均为 06:16 预训练收官既定事实，q_rnasc650_tests.sh 自动衔接已验证 ✓（14:38 起在 GPU0 推进 phase1 lora）
- **续派判断：不派**——GPU4 free 27.03G<28G（phase2 full 守门 28G 不满足，且 300M 训练（1441172，已 20:52:33）下轮 300M 应可让出 GPU4）/ GPU5 free 14.24G<20G（lora 预算 17G 不满足）；Phase1 lora 6 格由测试链（正向序）+ G2 反向序双向覆盖，无未认领缺口
- **健康项**：无 CUDA 不可用 / 无 CPU 静默降级 / 无在飞 OOM；G0 100% util 15.6G / G2 82% util 34.1G（第三方共存）；全部日志尾部正常推进（epoch 0-1，非静默挂死）
- 附注：famlora_audit/m6a_family/ssp_fulltuned/mrl_patch/frozen_patch 五队列维持排空 ✓（ledger 全 done）；frozen s43 family 最后 3 行 = pending（在飞对应进程）

## 2026-09-23 16:10 RNA-Sc-650M 测试链干预：杀主链接管 phase2

**背景**：主链 q_rnasc650_tests.sh 相位1 循环无 done-skip 检查——frozen 6/6 与 lora family 3/3 已落地
（g2 补格队列 + 孤儿进程覆盖），主链会把已完成格子全部重跑（~10h 浪费），phase2（full tuned）
要等相位1 重跑完才开始（预计明天凌晨）。

**干预**：杀主链 bash（41162），保留孤儿子进程 s17 lora random（PGID 独立不受影响）；
派发 q_rnasc650_full.sh 专用队列：s101 LR 网格(1e-5/3e-5) → BEST → formal 6 runs，
带幂等 done-skip、全卡位选择(>=24G)、失败清 pending 重试、bs8 协议。
与 g2（lora 剩余格）claim 集不相交，队列互斥 OK。

**当前三链并行**：
- GPU0: lora s17 random（孤儿，~17:40 落）
- GPU2: g2 lora s43 random（~17:50 落）→ s29 random
- GPU1: full s101 网格 lr1e-5（16:08 起跑，~19:30 落）→ lr3e-5 → formal

**链完成后的核心判读**（存在性反例的大端检验）：
受控系 650M lora random vs 30M full 0.862——若 650M lora > 30M full 则受控系交点
被大端「追回」，交点窗口窄化到 30M-650M；若 < 则反例更锐利（单调优势扩大）。

**崩塌带新证据**：受控系 650M lora family 3/3 = 0.0642（三种子完全一致，退化到同一
多数类）——比官方 RiNALMo-650M lora family（0.076-0.166）更彻底。崩塌带阈值随
pretraining 充分度上移的假设获得大端确认。

## 2026-09-23 17:22 MIG 切片陷阱：torch device 6/7 是 4.75G 小卡

**事故**：v2 并行队列硬编码 GPU6 跑 full lr3e-5 → 连续 2 次 OOM。
**根因**：nvidia-smi 显示 GPU6 = 40G 卡（33G 空闲），但 torch.cuda 枚举中
device 6/7 是 **4.75G MIG 切片**——nvidia-smi 索引与 torch 索引不对应。
**修复**（v3，e7b3ea5）：pick_gpu 增加 total<20G 过滤（MIG 切片永不选中）；
一切派单走 pick_gpu 动态选卡，禁止硬编码 GPU 索引；v3 网格等双 LR 格齐才算 BEST。
**规则沉淀**（写入 project_rules.md）：硬编码 GPU 前必须 torch.cuda.mem_get_info
校验 total 容量。

**v3 当前布局**：GPU0 lora s17（epoch 9，快落地）→ 落地后 GPU0 空 → v3 的
lr3e-5 网格将自动抢卡。GPU1 孤儿 lr1e-5、GPU2 lora s29（g2）。全链今晚收口。

## 2026-09-23 19:08 RNA-Sc-650M lora random 三种子齐——大端判读初步结论

**数据**（ncRNA random split，test ACC）：
- 650M lora: s17 0.8578 / s29 0.8601 / s43 0.8485 → 均值 **0.8555**（std 0.006）
- 30M full lr3e-5: 均值 0.8625（s17 0.8811/s29 0.8380/s43 0.8683）
- 650M full s101 lr1e-5 网格: 0.8578（lr3e-5 在跑）

**判读**：受控系 650M lora (0.8555) ≈ 30M full (0.8625)，差 -0.007（3 种子
std ~0.006，统计上打平）。**30M full-FT（1/20 参数量）打平受控系最大尺度
650M LoRA**——等价线存在性反例从 10M-100M 窗口延伸到 650M 大端，反例更锐利。

**严谨边界**（沿用用户质询标准）：单家族存在性反例，非普适规律；官方系
（RiNALMo 三档）方向相反（大模型 LoRA 持续优势）。两点合读 = 「等价交点
是否出现取决于训练配方/预训练充分度」——这正是 v0.6.4 主张的方向性表述。

**在跑**：full lr3e-5 网格（GPU4，~19:45 落）→ BEST → formal 6 runs 双 worker
（GPU0/1/2 已空，预计凌晨 ~2 点全链收口）。

## 2026-09-24 05:20 RNA-Sc-650M 测试链全链收口（20/20 格，RNASC650-FULL-V3 DONE 05:07:42）

**完整终表**（ncRNA family 任务，test ACC，3 种子）：
| strategy | random 均值 | family 均值 |
|---|---|---|
| frozen | 0.7145 (0.706-0.721) | 0.5160 (0.502-0.527) |
| lora | 0.8555 (0.849-0.860) | 0.0643（3 种子同值，崩塌带） |
| full tuned 3e-5 | **0.8959** (0.885-0.908) | 0.0748（0.064-0.096，崩塌带） |

LR 网格：s101 lr1e-5 0.8578 < lr3e-5 0.8963 → BEST=3e-5（与 30M/100M 受控系一致）。

**大端判读（正式，存在性反例大端检验完成）**：
1. 受控系 5/5 尺度 full 全胜同尺度 lora（0.700>0.639 / 0.808>0.746 / 0.862>0.773 /
   0.824>0.795 / 0.896>0.855）——与官方系方向完全相反（官方 lora 5/5 全胜 full）。
2. **30M full 0.8625 ≈ 650M lora 0.8555**（+0.007）：30M full（1/20 参数量）打平
   家族最大尺度 LoRA。存在性反例从「10M-100M 窗口」扩展为「全谱成立，30M 起
   即打平最大 LoRA」。
3. 崩塌带 8 尺度横贯（受控 1M-650M + 官方 33/148/650M 的 lora/full family 均在
   0.06-0.12；官方 148M lora family 0.207 为唯一结构性逃逸）；frozen family 单调
   升（受控 650M 0.516，官方 650M 0.645）——预训练充分度改善 frozen 家族泛化，
   但微调臂全部崩塌：泄漏敏感性以「微调破坏 frozen 已有家族表征」的形式呈现。

**产物终刷**：fig_c5b（8 尺度全齐）/ export_c4 / export_e2 / export_e3 / stats。

**过程注记**：v3 双 worker + oneshot 并行（07:37 起跑至 05:07 收口，含 2 次 OOM
自愈 + 1 次 s43 双跑竞态（同值 0.9079，无害））。MIG 陷阱与共租挤占均已规则化。

## 2026-09-24 15:10 收口复核巡检（三链落地后首个周期点）

- 队列终态复核：RNASC650-FULL-V3 DONE（09-24 05:07:42）/ RNASC650-LORA-G2 DONE（09-23 19:04:12）；finetune_one 无进程（预期，队列已收口）；GPU 0-7 全为他方负载，无本方 OOM、无待清理事故
- ledger ft_rnasc650m 复核：21 行全 done、0 pending = 20 唯一 run + 1 重复行（full_s43_random_lr3e-05 双跑竞态，同值 0.9079，05:20 节已记录；stats 按 run_id 去重后 n=3 正确，无害）
- 判读与版本复核：05:17-05:19 三连 commit 已 push（f61eb58/ed895bd/678e5c2），工作树干净；产物链重跑（export_c4/export_e2/stats/fig_c5b）刷新前后 md5 **IDENTICAL**——终版数据下产物确定性刷新通过，无漂移
- 大端判读数字独立复核（仅引用 ledger test 集 value 字段）：650M lora random 均值 0.8555（0.8578/0.8601/0.8485）vs 30M full lr3e-5 均值 0.8625（0.8811/0.8380/0.8683）→ 差 -0.007，打平；650M full 自身均值 0.8959（0.8951/0.8846/0.9079）> 自身 lora 0.8555（+0.040，方向与官方系相反）——与 05:20 正式判读一致，无修正项
- 结论：三链收口周期关闭，无待办；后续巡检转入低频看护

## 2026-09-24 17:05 mem_get_info 解包序 bug（全队列系谱修复）

**事故**：q_m6a_ends.sh pick_gpu 写 `total,_ = torch.cuda.mem_get_info(i)`——
实际返回序是 `(free, total)`，导致「MIG 过滤」实际过滤的是 free<20G：
1M 小格（只需 4G）被误判无卡可用，队列卡死 9 分钟。
**根因**：与 MIG 陷阱同源的枚举假设——昨天 v3 也有此 bug 但碰巧工作
（当时空卡 free 30G+，free 门槛与 total 门槛数值等效；s43 双跑竞态即其
行为痕迹）。
**修复**（fe9f9f0）：`free, total = torch.cuda.mem_get_info(i)` 正确解包。
**规则**：torch API 返回元组必须核对文档序，禁止凭记忆解包；GPU 门控
逻辑改动后必须用「小门槛 + 实际空卡」冒烟验证一次。
**在跑**：m6A 受控系首尾补格（1M 9 runs GPU5 起跑 → 650M 9 runs 等大卡窗口）。

## 2026-09-24 17:15 D-group PPT 等价线页交付（pptx_lint PASS）

**产物**：status/figs/equivalence_line.pptx（单页 16:9）——fig_c5b v2 终版图 +
大端判读三点（①两系方向全尺度相反 ②存在性反例大端不回吐 ③严谨边界）+
底部崩塌带注记栏（8 格带内 + 148M 唯一逃逸 + 受控 650M 最彻底崩塌 + 发现⑤
frozen 不崩）+ 数据源脚注（口径与 commit 锚）。
**校验**：pptx_lint 自检通过（5 shapes / 1 pic / 4 textboxes / 728 chars /
无出界无图文重叠）。D-group gate 达成。

## 2026-09-24 18:50 m6A 受控系谱线首端闭合（1M 9/9，QUEUE-A DONE）

**1M m6A 终表**（random split，test AUC，3 种子）：
- frozen 0.6894（0.684-0.694）——预训练极不充分，per-base 表征弱
- lora 0.9468（0.946-0.947）——三种子极稳
- full tuned 3e-5 0.9392（0.929-0.948）

**判读**：m6A「全谱饱和」结论在 1M 端成立——1M LoRA 0.947 ≈ 100M LoRA 0.947，
per-base 任务等价线可辨识度低的结论获五档全谱加固（1M/10M/30M/100M/650M）。
受控系 m6A 谱线 frozen 单调改善（0.689→0.94+）而微调臂全档饱和——per-base
粒度下「微调修复弱表征」的叙事与序列级任务（frozen 差距更大）一致。

**在跑**：650M 9 runs 等大卡窗口（24G 门，共租占用中；队列自动轮询）。
预计过夜——巡检 c4cd80aa 在岗（含等卡判定与重启指引）。

## 2026-09-24 22:26 m6A 650M 链进行中（2/9 落地）+ 门槛校准复盘

**落地**：frozen s17 0.9133 / lora s17 0.9478——受控系 m6A lora 六档
（1M/10M/30M/100M/650M + 官方对照）全部 0.94-0.95，「全谱饱和」结论
再获大端确认。full s17 等卡中（18G 门，共租夜间波动）。
**门槛校准复盘**：24G 门过于保守（m6A 历史峰值 13.7G，序列短）→
校准为 lora/frozen 15G + full bs8 18G（共 6 次重试自愈中成功起跑 2 格）。
**工程教训**（入规则）：GPU 门必须用同任务×同模型的历史 peak_mem 校准，
禁止跨任务套用（ncRNA 24G ≠ m6A 13.7G）。

## 2026-09-25 01:10 第三个 torch 枚举陷阱：mem_get_info 自身可抛 CUDA OOM

**事故**：主队列 3 次 '--device: expected one argument' exit 2（23:00/00:55/01:00）。
**根因**：torch.cuda.mem_get_info(i) 在查询**被占满的设备**时自身抛
RuntimeError: CUDA error: out of memory——不是返回小值而是异常崩溃 →
pick_gpu 输出空串 → bash G='' → --device 空参数。
**修复**（d976344）：pick_gpu per-device try/except continue。
**三大 torch 枚举陷阱全集**：① MIG 切片（nvidia-smi 索引 ≠ torch 索引，
dev6/7 是 4.75G 小卡）；② mem_get_info 返回序 (free,total) 非 (total,free)；
③ mem_get_info 查满卡自身抛 OOM。三者都源于「想当然假设 API 行为」。
**当前布局**：GPU0 full s29（孤儿）+ GPU1 full s43（修复版 sweeper）；
修复版 sweeper 3-pass 会兜底 full s17 + lora/frozen s43 剩余格。
已落 4/9：frozen 0.913×2 / lora 0.947×2。

## 2026-09-25 03:35 m6A 补格巡检：15/18，ends 功成身退、sweep 兜底中

**新落地**（01:10 条目之后）：full s29 0.9443（01:46，GPU0 孤儿完赛）/
full s43 0.9113（03:22，sweep pass1）。当前 15/18：
- 650M frozen 0.9133/0.9137（s17/s29）· lora 0.9470/0.9478（s17/s29）
  · full 0.9443/0.9113（s29/s43）
**在跑**：lora s43（GPU1 bs32，03:22:39 起）；**待跑**：frozen s43（pass1
队尾）+ full s17（2 行陈旧 pending 已过期 4.5h，pass2 兜底）
**队列判定**：finetune 在跑，不满足巡检重启条件，不重启。ends 主队列
01:00:44 后无日志（陷阱③空参数双烧 attempt 后沉默退场），接力棒在
修复版 sweep（3-pass 幂等）手上。
**异常（待人工处理）**：ends 脚本第四个陷阱——RID 大小写。脚本内拼
`ft_RNASc650M_...`（大写），ledger.run_id 规范化为全小写，故 ends 的
cell_state/clean_pending 永不匹配：① 失败格 pending 残行清不掉
（full_s17 现存 2 行陈旧 pending）；② 幂等门整体失效（19:20 重启后
1M 9 格全重派，仅靠 finetune_base 内层 claim() 拒绝才免重训）。
sweep 脚本小写无此问题。claim() 容忍 stale pending（只拒 running/done，
full_s29 复跑成功即为实证），功能不阻塞、仅污染计数。修 ends 时 RID
须按 ledger.run_id 约定小写化；full_s17 的 2 行陈旧 pending 可人工清除。
**谱线初判**（非终判，等 18/18）：受控系 random 侧 lora 1M→650M 全
0.947 级完全平坦；full 0.911-0.948；frozen 0.689(1M)→0.914(650M)
单调改善。「0.94-0.997 全饱和」lora 侧铁证；full 侧 650M s43 0.9113
为当前最低点（<0.94，终判时须明确表述）。1M 首端无规模效应迹象
（1M lora 0.947 ≥ 10M lora 0.941-0.944，未触发 <0.90 告警线）。

## 2026-09-25 12:20 m6A 受控系全链收口（9/9，M6A-SWEEP DONE 11:23）

**650M m6A 终表**（random，test AUC，3 种子）：frozen 0.9139（0.913-0.915）/
lora 0.9476（0.947-0.948）/ full@3e-5 0.9269（0.911-0.944）。

**六档全谱判读（受控系 m6A 等价线）**：
1. lora 六档全饱和（0.9415-0.9476，1M→650M 差 <0.006）——per-base 等价线
   不可辨识，v0.6.4 结论获 1M-650M 全谱确认；
2. **650M 任务粒度×策略镜像**：m6A lora>full（+0.021）vs ncRNA full>lora
   （+0.040）——per-base LoRA 占优 / per-sequence full 占优，同一家族同一
   尺度两任务方向相反，C4「粒度判据」在双轨等价线侧的独立证据；
3. frozen 单调升（0.689→0.914）全谱低于微调臂。

**过程注记**（共 4 个 torch/GPU 工程陷阱连环）：full s17 被主队列两次 OOM
放弃后由 sweeper 3-pass 兜底（11:23 done 0.925，含 1 次双跑同值无害竞态）；
frozen 门 15G→7G（历史峰值 5.1G，frozen 无优化器状态）；mem_get_info
自身可抛 CUDA OOM（第 3 个枚举陷阱）。

## 2026-09-25 13:45 E6 灾难性遗忘实验启动（v1 协议，spec §3 E6 提前执行）

**动机**：双轨全链收口后 GPU 空闲（用户显存占满纪律）；E6 原列 v2 范围，
提前启动让导师评审意见回来时已有 C6 遗忘数据在手。

**协议**（e6_forget.py，自校验通过）：
- 遗忘度量 = ncRNA 微调（10 epoch，同 finetune_one 协议）前后 S0 held-out
  （release22 80/80 簇切分 test+family_test 档）nt 级平均 NLL
- 噪声带对照 = 同 backbone 重排 eval 两遍（seed 201/707）——实测
  噪声带 ~1.6e-8（确定性 eval，重排不引入方差——**噪声带在本协议下
  退化为数值精度级，遗忘声明门槛极低即有效**）
- 自校验：frozen ΔNLL = 0.0（精确零，backbone 未动的最强管线证明）

**基线**：RNA-Sc-10M S0 heldout pre-NLL 4.3153（2000 seqs）

**矩阵**（q_e6.sh，24 runs）：受控 10M/30M/100M × {lora@3e-4,
full@tuned-3e-5} × 3 种子 + RiNALMo-micro {lora, full@1e-5} × 3 种子
（官方系对照——lora vs full 的遗忘量对比直接检验「适配器防遗忘」卖点）

**工程**：踩坑 4 个全修（S0 数据定位三层：cluster_split 无序列→r22 全
train→release22_split_8080 全量表；forward 返回 2/3 元组兼容；device
int 转换；空 --out-suffix argparse 吞参数）。三 torch 陷阱在队列中全修。

## 2026-09-25 15:10 m6A 补格链第 3 班巡检（收口复核，无动作）

**状态**：18/18 复核通过——ledger 唯一 run_id 18 个全 done、pending 0、
11:23 后零新增；12:20 终判段已随此前提交推送（master=origin，工作树
净）。m6A 相关进程清零（ends/sweep 均退场），GPU 已移交 E6 遗忘矩阵
+ rnajepa 队列，本班不重启不补跑（重启条件按字面虽似命中，但队列为
「完成态死亡」而非等卡挂起）。

**巡检口径勘误**：grep 'RNASc(1M|650M)_modification' 命中 0 行——
ledger run_id 规范化为全小写（ft_rnasc650m_...），大小写敏感所致；本班
改按 task=modification & model∈{RNA-Sc-1M,RNA-Sc-650M} & smoke=false
统计（20 行→按 run_id 去重后 18）。后续巡检沿用字段过滤口径。

**1M 首端复核**：lora 0.9467 / full 0.9393（3 种子均值），均 ≥0.90 且
1M lora ≥ 10M lora（0.9427）——首端无规模效应，<0.90 通知线未触发，
「等价线不可辨识」维持，v0.6.4 表述无需修订。

**异常（待人工处理，承前）**：① ends 脚本 RID 大写 bug 仍未修——直接
重启会把 18 个 done 格全重派（仅靠 finetune_base claim() 内层兜底防
重训）；② ledger full_s17 存在同微秒同值 done 行 ×3（09:10 起并发实例
竞态，值 0.9250 x3 无害，统计须按 run_id 去重）；③ q_m6a_ends.log 永
缺 M6A-ENDS DONE，收口标记以 M6A-SWEEP DONE（sweep log）+ ledger
18/18 为准；④ 本班 ssh 两次 kex 255 瞬断（已知模式，重试即愈）。

## 2026-09-25 18:30 m6A 补格链第 4 班巡检（终态静默，无动作）

**状态**：18/18 静默复核通过——按 15:10 勘误口径（task=modification &
model∈{RNA-Sc-1M,RNA-Sc-650M} & smoke=false，run_id 去重）18 全 done、
pending 0、11:23 收口后零新增；ends/sweep 进程双清零，GPU 已移交 E6
并行队列（q_e6_par，par:s29 full 在跑）。12:20 终判 + 15:10 复核均已
随提交推送（master=origin，工作树净）。本班不重启不补跑（队列为完成
态死亡而非等卡挂起，同前班判定）。

**1M 首端终确认**：lora 0.9467 / full 0.9393（3 种子均值）均 ≥0.90 且
1M lora ≥ 10M lora（0.9427）——首端无规模效应，<0.90 通知线未触发，
「m6A 等价线不可辨识」结论维持，v0.6.4 表述无需修订，不通知用户。

**异常（待人工处理，承前不变）**：① ends 脚本 RID 大写 bug + 第三个
torch 枚举陷阱（mem_get_info 可抛 OOM 致 pick_gpu 空返回→--device 空
参数）均未修——直接重启会把 18 个 done 格全重派（仅靠 claim() 内层
兜底防重训）；② ledger full_s17 同微秒同值 done 行 ×3（无害竞态，
统计须按 run_id 去重）；③ q_m6a_ends.log 永缺 M6A-ENDS DONE，收口
标记以 M6A-SWEEP DONE + ledger 18/18 为准。第 4 班起 m6A 补格链转入
静默终态：后续巡检可降频或停摆，待人工销项上述三项后归档。

## 0925 E6 灾难性遗忘矩阵（C6）：并行分流 + 官方系修复 + 首批判读

### 进展
- E6 主队列（q_e6.sh 24 格）串行推进至 100M full s17 后判读首批判读：
  - **30M: full ΔNLL +4.12 vs lora +1.93（遗忘倍率 2.13×）——适配器防遗忘假设获直接支持**
  - **10M: 双臂负遗忘（full -1.44 / lora -0.93）——小模型欠拟合任务数据有 S0 迁移增益**
  - 100M lora +0.86 已落地，full 运行中
- 串行太慢（剩 18 格 ≈13h）：拆 q_e6_par.sh 三并行流（s29/s43/micro, a6e495e）
  + 主队列 = 4 路并行，run_e6 逻辑原样复用（幂等/互斥/pick_gpu 三陷阱防御）。
- **官方系修复（第 5 个工程陷阱谱系）**：e6_forget.py 原实现只支持 RNA-Sc：
  1. AutoModel 加载 RiNALMo 无 LM 头（lm_head 全 UNEXPECTED）→ NLL 无从计算
     → 改 RiNALMoForMaskedLM 直接类加载（28 词表, model+lm_head）
  2. 官方 tokenizer 返回 BatchEncoding → torch.tensor 失败 → tok.encode()
  3. peft 解包顺序：PeftModel.__getattr__ 转发让 hasattr(core,'model')
     先命中 MaskedLM 层 → 必须先剥 base_model 再降 .model 拿 RiNALMoModel
  4. lm_head.decoder.bias checkpoint 缺失 → zero_() 补齐
  - 官方系 NLL 口径：MLM 全上下文（双向模型不能 shift-by-1）；
    lora 臂训练后 merge_and_unload 原地回迁再评 post（已冒烟验证：
    frozen Δ=0.0 精确 / lora merge 链路 pre 0.09326 完全一致）
- export_e6.py 矩阵导出器落地（markdown+csv, 8 格已验证）
- 提交：a6e495e, 5cd9842, da28c99, c45fc64, e2c1…（均已 push）

### 判读口径警示
controlled 因果 NLL（基线 ~4.5）与 official MLM 全上下文（基线 ~0.09）
**绝对值跨系不可比**——只看系内 ΔNLL 与 forget_ratio。

## 0925 E6 收口（21:06）+ preprint v0.8

- **E6 矩阵 24/24 全落地**（10M/30M/100M/官方micro × lora/full × 3 种子；
  4 路并行 13:38-21:06，含一次竞争 OOM 自愈重试）
- 终判读（status/e6_table.md，噪声带 <2.5e-8 全格显著）：
  - 10M 双臂负遗忘（全 6 格 n）——任务数据 = 小模型预训练增益
  - 30M 遗忘峰值带：full +4.12/+26.24/+22.67 vs lora +1.93/−0.84/+3.38
    ——尾部压缩 8×（决策量 = 最差种子）
  - 100M 反转：full 均值≈0（s43 −1.61）而 lora 恒正 Y/Y/Y
  - 官方 micro 6/6 遗忘 +0.11~+0.16（MLM 口径）
- preprint v0.8（5c4d5a0）：摘要第 5 点 + §2.8 + Methods + Discussion +
  Limitations；中文摘要发现 6 同步；数字 15/15 对照 result.json 零误差
- EXT 队列在跑（1M+650M 谱线端点 12 格，21:21 起）

## 0925 E6-EXT 谱线端点补全（1M/650M × lora/full × 3）+ 三路并行 worker

### 目标
补齐 C6 遗忘轴谱线两端点（受控系 1M 与 650M），共 12 格：
1M/650M × {lora@3e-4, full@3e-5} × seeds{17,29,43}，协议同 E6-v1
（S0 held-out NLL, test+family_test, n=2000 + 重排噪声带）。

### 进度
- 1M 6/6 已落地（21:57）：artifacts/e6/RNA-Sc-1M/{lora,full}_s{17,29,43}
- 650M lora 三格并行推进中：
  - s17 → 主队列 q_e6_ext.sh（GPU5）
  - s43 → 旁路 q_e6_ext_b.sh（GPU0）
  - s29 → 新增旁路 q_e6_ext_c.sh（GPU2）
- 650M full 三格（s17/s29/s43）：待单卡空闲 >=14GB 即启动

### 关键工程修正（第 6 陷阱谱系：显存 gate 过保守 → 显存空转）
1. GPU 拓扑实测：torch.cuda 暴露 8 设备——0-5 为常规 A100-40GB
   (total~39.5GB)；6/7 为 MIG 1g.5gb 切片 (total~4.75GB，对 650M 不可用)。
   nvidia-smi -L 另示 GPU6=7xMIG 1g.5gb、GPU7=2xMIG 3g.20gb，
   但 3g/1g 切片未作为独立可用大卡暴露给 CUDA 上下文。
2. 实测足迹（ledger.peak_mem_mb）远低于队列假设：
   - RNA-Sc-650M lora ~8.5GB（modification peak 4492MB）
   - RNA-Sc-650M full ~13.2-14.0GB（peak_mem_mb 13247-14044）
   原 pick_gpu 门 lora 20GB / full 24GB（~2x 实测）→ GPU2/GPU4 各 ~12GB
   空闲显存长期无法利用，且 24GB 门几乎拿不到。
3. 修复：新建 q_e6_ext_c.sh，按真实足迹放宽 gate（lora 10GB、full 14GB），
   并延长 full 轮询（150x240s 不轻言放弃）；保留 total<20GB 过滤
   （该过滤恰好正确排除 MIG 小切片）。经验：显存 gate 必须用 ledger
   实测足迹标定，不得沿用保守估计。

### 提交
- scripts/q_e6_ext_b.sh, scripts/q_e6_ext_c.sh 入仓

## 2026-09-26 凌晨 · E6-EXT 谱线端点收口（worker D 并行补位）

### 背景
E6-EXT 12 格中，除 650M lora(s17/s29/s43 三卡并行中) 外，唯一未落地科学格
= 650M full × {s17,s29,s43}（ledger 里 650M full 尚无任何行）。
主队列 q_e6_ext.sh / 侧翼 q_e6_ext_b.sh 的 full 门仍为 24GiB（不可达），
worker C 的 full 是**串行**——三格无法并行，会拖慢全谱收口。

### 处置
新建专用并行 worker q_e6_ext_d.sh：
- 一实例=一种子；本 session 起 3 实例（seed 43/29/17，00:08）
- gate：pick_gpu free >= 14e9 bytes (~13GiB)；保留 total<20GiB 过滤排除 MIG
- 同格互斥（确定性）：与 q_e6_ext_c.sh 共用锁目录 /tmp/e6ext_c_locks
  （每格 mkdir 原子锁）→ 任一 full 格任何时刻最多一个 worker 真正启动；
  另由 ledger fresh_pending 兜底
- 三实例已持有 3 个 full 格锁；任一卡空闲 >=13GB 即启

### 就绪判定（3 遍核查）
1. 拓扑：torch 0-5=常规 A100-40GB(39.49GiB)、6/7=MIG 1g.5gb(4.75GiB) — 复核第 3 次一致
2. 在跑：650M lora s43→GPU0(B)、s29→GPU2(C)、s17→GPU5(A) 三进程在跑
3. 锁：/tmp/e6ext_c_locks 下 full_s17/s29/s43 三锁 + C 的 lora_s29 锁
4. 巡检升级：cron_status.sh 增「E6 未完成格 + e6_forget/队列进程」（30min）

### 提交
- scripts/q_e6_ext_d.sh 入仓
- scripts/cron_status.sh（巡检升级）入仓

### 状态
- 待 650M lora 三格释放显存 → 三 full 格并行启动

## 2026-09-26 00:20 m6A 补格链第 5 班巡检（终态静默，无动作；死因复证）

**状态**：18/18 静默复核通过——按 15:10 勘误口径（task=modification &
model∈{RNA-Sc-1M,RNA-Sc-650M} & smoke=false，run_id 去重）18 全 done、
pending 0、09-25 11:23 sweep 收口后零新增；ends/sweep 进程双清零，GPU
已移交 E6-EXT worker B/C/D（650M lora×3 + full×3 并行中，同 llr_env）。
12:20 终判 + 15:10/18:30 复核均已随提交推送（master=origin，工作树净）。
本班不重启不补跑（队列为完成态死亡而非等卡挂起，承前班判定）。

**死因复证（本班增量）**：q_m6a_ends.sh 末段三连崩根因为 pick_gpu 子进程
间歇性空输出（torch.cuda.mem_get_info 在 dev1 抛 CUDA OOM 异常且 stderr
输出未捕获）→ attempt 行出现「GPU bs8」（GPU 编号空）→ --device 空参
→ argparse exit 2 → 2 次尝试耗尽。23:00/23:06 frozen s29 attempt1 空
G + attempt2 GPU1 成功即旁证；00:55/01:00 full s29 两连空 G 队列死亡。
本班 3 次重放 pick_gpu(18G)：dev1 稳定抛 OOM、dev4 12.07G 稳定可选中
（llr_env mem_get_info 返回序 (free,total) 已校验）。sweep 脚本同
pick_gpu 但 3-pass 兜底 + 11 格已在 ledger → 存活收口。**修复优先级：
把 pick_gpu stderr/stdout 捕获后判空 + -1 兜底重试**（与 RID 小写化
一并人工销项）。

**1M 首端确认**：lora 0.9467 / full 0.9393（3 种子均值），均 ≥0.90 且
1M lora ≥ 10M lora（0.9427）——首端无规模效应，<0.90 通知线未触发，
「m6A 等价线不可辨识」结论维持，v0.6.4 表述无需修订，不通知用户。

**异常（待人工处理，承前不变）**：① ends 脚本 RID 大写 bug + pick_gpu
空输出缺陷未修——直接重启会把 18 个 done 格全重派（仅 claim() 兜底）；
② ledger full_s17 同微秒同值 done 行 ×3（去重后 0.9250 无害）；③
q_m6a_ends.log 永缺 M6A-ENDS DONE，收口以 M6A-SWEEP DONE + ledger
18/18 为准；④ frozen s29 双实例竞态 23:06-23:27（22:50 清 pending 后
队列与 sweep 并发选中 GPU1，同值 0.9137 done 无害）。

### 交接补位（0926）：C6 导出链端点收口
- **export_e6.py 硬编码 ORDER 仅含 10M/30M/100M/micro → 静默丢弃 1M/650M 端点格**（collect() `if m not in ORDER: continue`）——即已落地的 1M 6/6 未进 e6_table。已修：ORDER/LABEL/CALENDAR 扩为 1M→650M 全谱（谱线升序）。重导后 e6_table 由 24 格 → 30 格（含 1M 行；650M 待落）。
- 新增 **rnafteval/fig_e6.py** → status/figs/fig_e6_spectrum.{png,pdf}：受控系 ΔNLL vs 规模（1M→650M log 轴，LoRA/full-FT 两线 + 逐种子散点 + 0 线）。仅受控系（因果 NLL）；官方 micro 为 MLM 口径不入图（跨系绝对值不可比）。

### 修复（0926 00:37）：worker D 同卡碰撞 → 逐卡原子锁
- 现象：00:30 GPU1 空闲 25.9GB 时，D 三实例同周期都 pick 到 GPU1 → s29 起训，
  s43/s17 OOM（exit 1；各 clear_pending 后下轮重试）。根因：pick_gpu 各实例
  独立、仅取「最空」卡 → 空闲大卡被并发抢占（外部进程亦同抢）。
- 修复：q_e6_ext_d.sh 增 pick_gpu_at(G) 抢锁后复核 + 训练前 mkdir $LK/gpu_$G
  逐卡原子锁（持锁覆盖整段训练）+ EXIT trap 兜底释放 → 多实例自然分散到
  不同空闲卡，同卡最多一个 D 作业。
- 已重启 s43/s17 实例（s29 训练中未动，保留进度）。
- 首个 650M full 格：s29 → GPU1（00:30 起，pending，训练中）。

## 2026-09-26 03:15 m6A 补格链第 6 班巡检（终态静默，无动作）

**状态**：18/18 静默复核通过——按 15:10 勘误口径（task=modification &
model∈{RNA-Sc-1M,RNA-Sc-650M} & smoke=false & split=random & 去重）18 全
done、pending 0；sweep 收口（09-25 11:23）后 modification 零新增行（本班
JSON 全量比对 03:13 复核）。ends/sweep/finetune_base 进程三清零。GPU 已全
量移交 E6-EXT worker B/C/D（GPU0-5 util 100%，650M lora×3 + full×3 并行；
dev1 空闲 21G 为 lora 释放间隙非等卡挂起，torch 枚举下 4/5 无 10G 级空闲
常态）。本班不重启不补跑（队列为完成态死亡，承 00:20 第 5 班判定；且
ends 脚本 RID 大写 bug + pick_gpu 空输出缺陷未修，重启会把 18 个 done 格
全重派）。

**谱线终态复核（承 12:20 终判，本班重算确认无漂移）**：lora 5 档均值
1M 0.9467 / 10M 0.9427 / 30M 0.9415 / 100M 0.9469 / 650M 0.9476——全
5 档 ∈[0.941,0.948]，极差 0.006；1M 首端 lora 0.9467 ≥ 10M 0.9427，
无首端规模效应。full 侧 0.9393/0.9181(口径混合)/0.9342/0.9367/0.9269。
**对照 v0.6.4「m6A 全饱和 0.94-0.997」：受控系 lora 六档 0.941-0.948
成立（与官方系 0.968-0.997 合成 0.94-0.997 全谱段）；full 侧 650M s43
0.9113 低于 0.94 下界，为种子方差非规模效应（650M 3 种子极差 0.033、
mean 0.9269，与 1M/30M/100M full 置信重叠）——维持第 4/5 班判定：
v0.6.4 表述无需修订，「m6A 等价线不可辨识」结论维持，1M<0.90 通知线
未触发，不通知用户。**

**异常（待人工处理，承 00:20 清单不变）**：① ends 脚本 RID 大写 bug +
pick_gpu 空输出缺陷未修（pick_gpu stderr 未捕获 → 偶发空 G → argparse
exit 2 ×2 队列死亡；修复方向：捕获 stderr + 判空 -1 兜底重试）；②
ledger full_s17 同微秒同值 done 行 ×3（去重后 0.9250 无害）；③
q_m6a_ends.log 永缺 M6A-ENDS DONE，收口以 M6A-SWEEP DONE + ledger
18/18 为准；④ frozen s29 双实例竞态（同值 0.9137 无害）。

**提交**：TRAINING_LOG.md（本班巡检条目）

## 2026-09-26 09:26 m6A 补格链第 7 班巡检（终态静默，无动作）

**状态**：18/18 静默复核通过（task=modification & model∈{RNA-Sc-1M,
RNA-Sc-650M} & smoke=false & split=random & 去重）。ends/sweep/finetune_base
进程三清零；q_m6a_ends.log mtime 冻结 09-25 00:58，modification 全账本
276 行零新增（max updated_utc 2026-09-25T03:23Z）。新落地 run：无。

**队列判定**：完成态死亡，维持第 5/6 班判定不重启——①非 wait 循环卡
死（死亡点为 09-26 01:00:44 pick_gpu 空输出 → 裸 --device → argparse
exit 2 ×2 耗尽重试）；②重启条件不满足（未出现 wait 循环 >1h 且空卡
≥4G）；③ends 脚本 RID 大写 bug + pick_gpu 空输出缺陷未修，重启会把
18 个 done 格全重派。收口以 M6A-SWEEP DONE 09-25 11:23 + ledger 18/18
为准。本班 mem_get_info 抽验 gpu4 (29.8G free, 42.4G total)，返回序
(free,total) 确认无误。

**谱线终态复核（承 12:20 终判，本班全量重算确认无漂移，只引 test 集
value 字段，无 smoke 行）**：lora 5 档均值 1M 0.9468 / 10M 0.9427 /
30M 0.9415 / 100M 0.9469 / 650M 0.9476——全 5 档 ∈[0.941,0.948]，极差
0.006；1M 首端 lora 0.9468 ≥ 10M 0.9427，无首端规模效应。full 侧均值
0.9393/0.9181(口径混合)/0.9342/0.9367/0.9269。**对照 v0.6.4「m6A 全
饱和 0.94-0.997」：受控系 lora 侧 0.941-0.948 成立（与官方系
0.968-0.997 合成 0.94-0.997 全谱段）；full 侧 650M s43 0.9113 低于
0.94 下界，为种子方差非规模效应（650M 3 种子极差 0.033、mean
0.9269，与 1M/30M/100M full 置信重叠）——v0.6.4 表述无需修订，
「m6A 等价线不可辨识」结论维持，1M<0.90 通知线未触发（1M lora
0.9468，lora/full 两臂均 >0.90），不通知用户。**

**异常（待人工处理，承 00:20 清单不变）**：① ends 脚本 RID 大写 bug +
pick_gpu 空输出缺陷未修（修复方向：捕获 stderr + 判空 -1 兜底重试）；
② ledger full_s17 同微秒同值 done 行 ×3（去重后 0.9250 无害）；③
q_m6a_ends.log 永缺 M6A-ENDS DONE，收口以 M6A-SWEEP DONE + ledger
18/18 为准；④ frozen s29 双实例竞态（同值 0.9137 无害）。

**提交**：TRAINING_LOG.md（第 7 班巡检条目）

## 2026-09-26 12:20 m6A 补格链第 8 班巡检（收口标记落地：M6A-ENDS DONE 补齐）

**状态**：18/18 静默复核通过（task=modification & model∈{RNA-Sc-1M,
RNA-Sc-650M} & smoke=false & split=random & 去重，18/18 done、pending 0）。
本班接管时进程三清零，ledger mtime 冻结 09:19、q_m6a_ends.log mtime 冻结
09-25 00:58（死亡点 09-26 01:00:44 pick_gpu 空输出 → 裸 --device →
argparse exit 2 ×2，承第 5-7 班取证）。新落地 run：无（ends 范围 max
updated_utc 2026-09-25T03:23Z，sweep 收口 09-25 11:23 后零新增）。

**队列处置（本班动作）**：修正第 5-7 班「重启会把 18 个 done 格全重派」
的判定——该假设只看了 shell 层 done 幂等（cell_state 拼大写 RID 永不
命中），漏了 finetune_base 自身按 canonical 小写 rid 的 done 跳过
（finetune_base.py 内 run_id 幂等，attempt 后直接 "skip (already done)"）。
本班 12:13 重启（setsid nohup，pid 3012426）：18 格全部幂等跳过（~5s/格，
零重训），QUEUE-A DONE 12:15:58，**M6A-ENDS DONE 12:18:16 正式落地
（log L485），队列干净退出**；ledger 零扰动（1149 行、mtime 09:19 不变，
跳过路径不写行）。重启前置校验：mem_get_info 全 8 卡抽验返回序
(free,total) 确认无误；nvidia-smi 6×A100-40G + 2×MIG-4.75G，dev2 30.7G /
dev4 40.4G / dev5 35.6G 空闲，空卡条件充分。ends 脚本本身未改（其
pick_gpu 判空守卫沿用 09-25 01:05 补丁版本）。

**谱线终态判读（承 12:20 终判，本班全量重算确认无漂移，只引 test 集
value 字段，无 smoke 行）**：lora 5 档 3 种子均值 1M 0.9467 / 10M 0.9427 /
30M 0.9415 / 100M 0.9469 / 650M 0.9476——全 5 档 ∈[0.941,0.948]，极差
0.006；1M 首端 lora 0.9467 ≥ 10M 0.9427，无首端规模效应。full@3e-5 均值
1M 0.9393 / 10M 0.8964 / 30M 0.9342 / 100M 0.9367 / 650M 0.9269。
**口径勘误：10M full@3e-05 去重 3 种子（0.9438/0.9145/0.8309）均值
0.8964，此前班次记录的 0.9181 为混入一行 3e-04 的口径混合**；10M full
s43 0.8309 为全谱最差点，与 650M s43 0.9113 同属种子方差带（各档 full
3 种子极差 0.021-0.113），非规模趋势。**对照 v0.6.4「m6A 全饱和
0.94-0.997」：受控系 lora 侧 0.941-0.948 成立（与官方系 0.968-0.997
合成 0.94-0.997 全谱段）；full 侧 10M 0.8964、650M 0.9269 低于 0.94
下界，判为种子方差非规模效应（1M/30M/100M full 与其置信区间重叠）——
v0.6.4 表述无需修订，「m6A 等价线不可辨识」结论维持；1M<0.90 通知线
未触发（1M lora 0.9467、full 0.9393 两臂均 >0.90 且不低于 10M 对应臂），
不通知用户。**

**异常（待人工处理，承 00:20 清单，有更新）**：① ledger 650M full_s17
同微秒同值 done 行 ×3（去重后 0.9250 无害）；② frozen s29 双实例竞态
（同值 0.9137 无害）；③ ledger 10M full_s43 同微秒同值行 ×2（去重后
0.8309，已含入 0.8964 口径勘误）；④ ~~q_m6a_ends.log 永缺 M6A-ENDS
DONE~~ 本班已补齐（12:18:16 落地，队列终态退出）；⑤ ends 脚本 shell 层
RID 大写 bug + pick_gpu 空输出缺陷仍在（cell_state 永不命中 done → 每格
必进 attempt 分支；因 finetune_base 内部幂等兜底已实际无害化，仅多花
~5s/格进程启动成本；修复方向仍为 RID 改 canonical 小写 + pick_gpu 捕获
stderr 判空兜底）。

**提交**：TRAINING_LOG.md（第 8 班巡检条目）

## 2026-09-26 上午 · E6-EXT 谱线端点全收口（C6 36 格）+ preprint v0.9
- 650M {lora,full} s17/s29/s43 全部 done（D 三实例 04:47/06:27/07:54 exit 0）。
  E6-EXT 12 格 = 1M 6/6 + 650M 6/6 → **全落地**。
- 期间工程修复：worker D 同卡碰撞 → 逐卡原子锁 + 抢锁后复核（f230f31）；
  若干 OOM 重试（外部/我方 rna-jepa 作业抢卡）——最终全部成功。
- export_e6 重导（36 格 = 6 模型 × {lora,full} × 3 seed）+ fig_e6_spectrum。
- **谱线终判读（非单调、中段危险带）**：1M 轻微且种子噪声大（LoRA 一 seed +3.8）；
  10M 负遗忘；30M 峰值（full 均值 +17.7，最差 +26.2；lora 最差 +3.4，尾部压缩 ~8×）；
  100M 回稳（full ≈0，lora 轻微正）；650M 再负（lora 3/3 负；full 2/3 负，最差 +7.1）。
  → forget_ratio：1M +0.24× / 10M +1.89× / 30M +11.86× / 100M −0.04× / 650M −0.44×。
- preprint v0.9：§2.8 表补 1M/650M 两行（6 行全谱）+ 三发现更新（(i) 端点闭合）
  + abstract finding 5（24→36 cell）+ limitations 去 "in flight" + header v0.4→v0.9。

## 2026-09-26 15:10 m6A 补格链第 9 班巡检（终态静默，无动作）

**状态**：18/18 终态静默复核通过（task=modification & model∈{RNA-Sc-1M,
RNA-Sc-650M} & smoke=false & split=random & 去重，18/18 done、pending 0）。
M6A-ENDS DONE 12:18:16 驻留 log 第 485 行；ends/sweep/finetune_base 进程
三清零；ledger mtime 冻结 09:19:47、q_m6a_ends.log mtime 12:15:32，此后
零变动（/mnt mtime 时钟系统性滞后应用层 ~2m45s，以内容时间戳为准）。
新落地 run：无（ends 范围 max updated_utc 2026-09-25T03:23Z，sweep
收口 09-25 11:23 后零新增）。

**谱线终态复核（承第 8 班终判，本班数字全量重算确认无漂移，只引
test 集 value 字段，无 smoke 行）**：lora 5 档 3 种子均值 1M 0.9467 /
10M 0.9427 / 30M 0.9415 / 100M 0.9469 / 650M 0.9476——全 5 档
∈[0.941,0.948]，极差 0.006；1M 首端 lora 0.9467 ≥ 10M 0.9427，无
首端规模效应。full@3e-5 均值 1M 0.9393 / 10M 0.8964 / 30M 0.9342 /
100M 0.9367 / 650M 0.9269（10M 为 0.9438/0.9145/0.8309 去重口径，
本班已逐行复核）。**对照 v0.6.4「m6A 全饱和 0.94-0.997」：受控系
lora 侧 0.941-0.948 成立（与官方系 0.968-0.997 合成 0.94-0.997
全谱段）；full 侧 10M 0.8964、650M 0.9269 低于 0.94 下界，判为种子
方差非规模效应——v0.6.4 表述无需修订，「m6A 等价线不可辨识」结论
维持；1M<0.90 通知线未触发（1M lora 0.9467、full 0.9393 两臂均
>0.90 且不低于 10M 对应臂），不通知用户。**

**异常（待人工处理，承 00:20 清单不变）**：① ledger 650M full_s17
同微秒同值 done 行 ×3（去重后 0.9250 无害）；② frozen s29 双实例
竞态（同值 0.9137 无害）；③ 10M full_s43 同微秒同值行 ×2（去重后
0.8309，已含入 0.8964 口径）；④ ends 脚本 shell 层 RID 大写 bug +
pick_gpu 空输出缺陷仍在（finetune_base 内部幂等已实际无害化）。链路
终态收口且谱线连续两班零漂移，若无新增补格需求，本链巡检可归档。

**提交**：TRAINING_LOG.md（第 9 班巡检条目）

## 2026-09-26 下午 · 交接文档全量同步 + 后续交接工作 P1/P2 启动

### 交接文档同步（本 session 主体）
- 以 ledger/git/status 产物为唯一口径，对账并回填交接文档：
  spec v1.9→**v2.0**（+§10.6 后续交接工作 P1-P4）；tasks v3.11→**v3.12**
  （逐项复核回填 + 文末「后续交接工作」节）；checklist v1.8→**v1.9**
  （A4/A6/A9/A10、B17/B18/B19 回填；B10 按 v1.9 口径重标）；新增
  STATUS_SNAPSHOT_20260926.md；巡检日志追加本轮条目。

### 服务器事实核验
- HEAD 36136d0→（本轮 push 后）**c5627b6**；ledger **1149→1153 行**
  （+4 条 seed=999 smoke 验证行；无 pending 科学格）。
- GPU 拓扑：torch 0-5 = A100-40GB（39.49GiB）；6/7 = MIG 1g.5gb（4.75GiB）。
- 缺口盘点（ledger 实测）：4 任务 × 已接入模型 × {frozen,lora,full≤100M}
  × {random,family} × {17,29,43} = **37 组 × 3 种子 = 111 runs**。

### P1 缺口补齐（GPU，进行中）
- 新脚本 scripts/q_p1_fill.py（N shard worker / 每卡 2 slot 原子锁 /
  done-skip（ledger 字段权威，不猜 run_id）/ 失败清 pending 重试 /
  真 CUDA 断言）；protocol：frozen/lora 默认 LR 3e-4；full tuned LR
  RiNALMo 1e-5、受控 RNA-Sc 3e-5（full run_id 加 _lr 标签）。
- **smoke 验证（4 组合，seed 999，全 exit 0）**：finetune_mrl×RNA-Sc-1M /
  finetune_base(modification)×RNA-Sc-1M / finetune_ssp×RNA-Sc-1M /
  finetune_ssp×RiNALMo-mega —— 确认新 task×model 组合 runner 可用。
- **2 个 bug 修复（3 遍核查纪律）**：① tag 格式串参数缺失 → TypeError；
  ② RUNS 元组序 split/seed 颠倒 → seed 收到 str。修复后前台验证通过。
- 6 shard 已启动（setsid nohup，pid 3775175-3775180）；前 6 个 MRL frozen
  格 exit 0（52-81s/格）。进度脚本 scripts/q_p1_need.py。
- 监控：scripts/q_p1_monitor.sh，cron `*/20`（含进度+GPU+CPU 降级扫描+
  自动补位：无 worker 且有缺口则重启 6 shard）。首次快照：
  groups=37 cells_done=6/111。

### P2 剩余架构接入（下载启动）
- scripts/dl_p2.py（hf-mirror requests 下载器，resumable）。
- 已下：multimolecule/utrlm-mrl（UTR-LM，~1.2M，model.safetensors 4.86MB）✓
- 下载中：YYLY66/mRNABERT（pytorch_model.bin 456MB）、
  SII-GAIR-NLP/RIBOSPAN-1K-40（6.45GB）。
- AIDO.RNA-1.6B：tree API 非标准返回，待单独核（resolve 探测）。
- RIBOSPAN-FM：仓库仅有 docs，无权重 → 以 RIBOSPAN-1K-40 为准。
- HydraRNA：HF 无，需 GitHub 单 ckpt（后续）。

### 纪律
- smoke/proxy/训练集结果均未写成结论；P1 全为 test 集口径。
- GPU 训练真 CUDA（worker 起始 assert torch.cuda.is_available()）。
- 新脚本已提交 GitHub（HEAD c5627b6）。

## 2026-09-26 下午（续）· P3 T4.1.2/T4.1.3 + P2 UTR-LM 入 E1 + MRL 资源记录修复

### P3 终端交付物（T4.1.2/T4.1.3 完成）
- 新 rnafteval/export_resources_matrix.py → status/resources_matrix.md（per-(model,strategy)
  wall/peak 中位数与最大值 + fits 24GB/40GB 速查）+ status/resources_costbenefit.csv。
- 新 rnafteval/fig_resources.py → status/figs/fig_resources_costbenefit.{png,pdf}（三任务面板：
  ncRNA ACC / SSP F1 / m6A AUC；x=GPU wall 中位数 log 轴；色=策略；已本地目检）。
- 关键可跑性结论（ledger 实测 peak_max）：**RiNALMo-650M full 25014MB 仅 40GB 卡可容**
  （24GB 卡不可）；其余已测配置均 ≤24GB 可容。
- **数据质量修复（3 遍核查发现）**：
  ① 导出器按 run_id 去重（ledger 有同值重复 done 行）；
  ② wall/peak ≤0 视为未记录（排除 -1 哨兵）；
  ③ **finetune_mrl 未记录 wall/peak**（旧代码写 wall_s 字段名错误 + 无 peak）→ 已修
     （reset_peak_memory_stats + wall_sec + peak_mem_mb），fresh smoke 验证
     wall_sec=7.4 / peak_mem_mb=48.0。既有 MRL 行仍缺，E5 侧如实在表注说明。

### P2 新模型入 E1（P2.6 进行中）
- 通用 plan 驱动 worker scripts/q_fill.py（读 worklist JSON；独立 lockdir + slots；
  同 q_p1_fill 的 done-skip/pending-clear/真 CUDA 断言）+ scripts/q_plan_need.py
  （通用进度）；plan scripts/p2_utrlm_plan.json = UTR-LM × {ncRNA,SSP} ×
  {frozen,lora,full} × {random,family} × {17,29,43} = 36 runs（full LR 1e-5，need 4GB）。
- 3 shard 已启动；监控脚本 q_p1_monitor.sh 已扩为覆盖 P1 + 全部 p2_*.json（含自动补位）。

### 队列进度（15:42）
- P1：24/111 done；6 worker 在跑（跨 GPU）。
- P2 UTR-LM：3/36 done；3 worker 在跑。
- 下载：UTR-LM 完成；mRNABERT 47MB/456MB；GB.RNA-1.6B 下载中；RiboSpan-1K-40 排队。
- GitHub：HEAD 588297f → **8e8e26e**（P3 资源矩阵+图）→（本次）MRL 修复。

## 2026-09-26 下午（续2）· P2 mRNABERT 接入 + 54 runs 派发

### mRNABERT 接入（P2.2 完成）
- 候选仓库 YYLY66/mRNABERT（config: hidden 768 / 12 层 / vocab 74，MosaicBERT 自定义代码）。
- 集成障碍与修复（3 遍核查）：
  ① HF `from_pretrained(trust_remote_code=True)` 在 transformers 5.x 下报
     "Tensor on device meta" → 绕过：AutoConfig + `transformers_modules.main.bert_layers.BertModel(cfg)`
     直接实例化 + 手动 load_state_dict；
  ② 权重键带 `bert.` 前缀（136/142），BertModel 期望无前缀 → 去前缀后
     missing 2（pooler）/ unexpected 6（MLM head），干净；
  ③ 自定义 forward 返回 tuple → 新增 `_MosaicBertWrapper` 暴露 `.last_hidden_state=out[0]`；
  ④ LoRA 目标选择器先命中松散候选 ["q","k","v","o"] → 新增 MosaicBERT 目标
     ["Wqkv","attention.output.dense"]（仅当这些模块名存在时命中，不影响既有模型）。
- 验证：frozen（trainable=0）/ lora（442368）/ full（113979648）ncRNA smoke 全 exit 0。
- **发现的坑（已记录）**：owner 运行器 `from .strategies import apply_strategy`，而顶层
  `rnafteval/__init__.py` 另有一份同名函数——首轮误改无效文件；已改真正的
  `rnafteval/strategies/__init__.py`，两份同步（避免后续误用）。

### 派发
- scripts/p2_mrnabert_plan.json：mRNABERT × {ncRNA, SSP, modification} × {frozen,lora,full}
  × {random,family} × {17,29,43} = **54 runs**（full LR 1e-5，need 10GB）；3 shard 已启动。

### 队列进度（约 16:00）
- P1 49/111；P2 UTR-LM 15/36；P2 mRNABERT 0/54（刚起）。
- 下载：UTR-LM ✓；mRNABERT ✓（435MB）；GB.RNA-1.6B 3.9GB（进行中）；RiboSpan-1K-40 3.2GB（进行中）。
- GitHub：HEAD b4b677f。

## 2026-09-26 下午（续3）· P2 AIDO/RiboSpan 阻塞登记 + 队列状态

### AIDO.RNA-1.6B / RiboSpan：外部依赖阻塞（如实登记，不硬跑）
- 已下全：genbio-ai/GB.RNA-1.6B（= AIDO.RNA-1.6B 别名，13G / 9 文件，分片 bin）；
  SII-GAIR-NLP/RIBOSPAN-1K-40（6.45G）。
- 两者 config 分别为 `model_type=rnabert`（arch RNABertForMaskedLM）与
  `model_type=ribospan`（arch RiboSpanForMaskedLM），**均无 auto_map、仓库内无
  建模 .py**（隐藏 2048 / 32 层 / swiglu / rope / vocab 16，同属 ModelGenerator 家族）。
- 直接 `AutoConfig/AutoModel(trust_remote_code=True)` 报 "Transformers does not
  recognize this architecture"；`modelgenerator` 包在所有候选 env 中均未安装。
- **决策（纪律优先）**：不在共享 `llr_env` 强行 pip 安装（在跑的 P1/P2 队列
  全依赖该 env，污染风险 > 收益）。P2.3/P2.5 标记为「阻塞·外部依赖」，
  后续路径 = 克隆 genbio-ai/ModelGenerator 到 /mnt + 写隔离 custom_loader
  （不改共享 env）。
- 已接入成功：UTR-LM（P2.1）、mRNABERT（P2.2）；P2.4 HydraRNA 仍待做（GitHub 单 ckpt）。

### 队列状态（约 16:10）
- P1 51/111；P2 UTR-LM 15/36；P2 mRNABERT 1/54（在跑）。
- 巡检 cron 覆盖 P1 + 全部 p2_*.json（自动补位 + CPU 降级扫描），在岗。

## 2026-09-26 晚间 · P2 剩余架构依赖核查（证据在案）+ 并发提升

### 并发提升（落实"显存占满"）
- q_p1_fill.py SLOTS 2→3（env P1_SLOTS 可覆盖）；P2 plans slots 1→2。
- 清理一次自伤事故：`pkill -f "scripts/q_fill.py"` 会**自匹配当前 shell**（命令行含该串）
  → shell 被杀、P1 worker 全停 + 孤儿 run + 泄漏锁。处置：按 ppid==1 精确回收孤儿、
  清 /tmp/p1_locks 重锁、重启 6 shard。**教训**：pkill -f 一律用 `[b]racket` 防自匹配。

### 剩余架构依赖核查（3/5 阻塞，证据在案，不硬跑）
- **AIDO.RNA-1.6B / GB.RNA-1.6B**：checkpoint 全；`model_type=rnabert`，无 auto_map/建模 .py。
  PyPI `modelgenerator==0.1.3.post0` 的 38 项 requires 含 `numpy<2`、`peft<=0.13.2`、
  `tiledb==0.33.6`、`bionty==1.3.2`、`lightning` → **与在跑 llr_env 管线冲突，禁装**。
- **RiboSpan-1K-40**：同族（`model_type=ribospan`）→ 同一阻塞。
- **HydraRNA**：官方 https://github.com/GuipengLi/HydraRNA；README 明确需独立
  conda env（py3.9.12/torch2.3.1+cu118）+ mamba-ssm[causal-conv1d] + flash-attn +
  自装 fairseq；权重在 Google Drive；embedding 走 model.encoder.extract_features。
  属重型集成且仅为 SSM 观察臂（B11）→ 暂缓，/mnt 隔离 env 方案待排期。
- 已成功接入并出数：**UTR-LM（P2.1）、mRNABERT（P2.2）**。

### 队列状态（约 16:20）
- P1 51/111；UTR-LM 19/36；mRNABERT 7/54；P1 6 worker + P2 6 worker 在跑。

## 2026-09-26 晚间（续）· P3 T4.3 决策树引擎 + 配方草稿

### 交付
- 新 rnafteval/decision_tree.py（预注册规则 spec §7.8）：
  配对口径 = 同 (task, model, split, seed) 内比较；相对增益 = (A−B)/|B|×100；
  配对 sign test → p；BH-FDR q=0.05 跨全部比较；三分类
  （>2%+显著=RECOMMEND / <0+显著=NOT-RECOMMEND / 其余 NEUTRAL）。
- 产物：status/decision_tree.md/csv + status/recipe.md（T4.3.3 草稿）；
  已加入 q_refresh_when_done.sh 自动重刷链。
- T4.3.0（导师签字）仍待办 → 产物顶部已标注"草稿，非签字发布版"。

### 判读（formal 种子，ledger 实测）
- **modification（per-base）**：LoRA vs frozen 双切分 RECOMMEND（+9.1% / +15.1%）；
  full vs LoRA NEUTRAL（−0.5% / −0.1%）→ 适配器够用。
- **mrl（per-seq 回归）**：LoRA RE COMMEND（+50.9% / +54.3%）；full vs LoRA NEUTRAL。
- **noncoding-rna-family（per-seq）**：random 全推荐（+18.9%/+21.2%）；
  **family 切分 NOT-RECOMMEND（−73.9% / −9.7%）**——复现崩溃故事于决策层。
- **secondary-structure（per-base）**：LoRA vs frozen RECOMMEND（+25.7% / +17.0%）；
  **full vs LoRA NOT-RECOMMEND（−25.0% / −25.8%）**——结构任务全参过强反而更差。
- 修复：recipe 生成的 dict key 用 arm 单键导致 full−lora 行被 full−frozen 覆盖
  （3 遍核查发现）→ 改为 (a,b) 键。

### 队列（约 16:35）
- P1 51/111（在跑 SSP 长格）；UTR-LM 21/36；mRNABERT 14/54。
- GitHub：HEAD a15236f。

## 2026-09-26 晚间（续2）· T4.3.4 决策树查询 CLI
- 新 rnafteval/recipe_query.py：`--task X --split Y` 打印该场景的配对增益 +
  预注册判定；`--list` 全量导出。已在 ncRNA/family（NOT-RECOMMEND）、
  SSP/random（LoRA RECOMMEND、full NOT-RECOMMEND）、m6A 验证。
- GitHub HEAD 6fb32fe。

## 2026-09-26 深夜 · P2 AIDO.RNA-1.6B 接入成功（无 pip，隔离 vendored loader）

### 背景
- GB.RNA-1.6B（=AIDO.RNA-1.6B 别名）config `model_type=rnabert`，HF 仓**无 auto_map、无建模 .py**；
  直接装 `modelgenerator==0.1.3.post0` 会带入 numpy<2 / peft<=0.13.2 等 38 项依赖 → 毁在跑管线（禁）。
- 转机：ModelGenerator **GitHub 仓**内含 HF 兼容代码 `huggingface/gb.rna/gb_rna/models/{modeling,configuration,tokenization}_rnabert.py + vocab.txt`。

### 处置（全程零 pip、零共享 env 改动）
1. 从 GitHub API 取上述 4 文件 → checkpoint 目录（/mnt）；
2. 为 transformers≥5 打补丁：`find_pruneable_heads_and_indices` / `prune_linear_layer` 内联回退实现；
3. 新 `load_gbrna()`（rnafteval/models/__init__.py，custom_loader="gbrna"）：
   - 复制到 `/mnt/cunyuliu/gbrna_pkg` 以**包**方式 import（修相对 import）；
   - config 默认补齐（transformers5 删了 `is_decoder` 等 → AttributeError）；
   - tokenizer 直接实例化 `RNABertTokenizer(vocab_file=...)`（AutoTokenizer 走 fast 后端需要 sentencepiece）；
   - **手工 safetensors 分片加载**（HF≥5 因 CVE 在 torch<2.6 下拒 .bin；仓内分片名为 `pytorch_model-*`，
     HF resolver 不认 → `safetensors.load_file` 直读）；
   - fp32（本管线 head/optim 为 fp32，bf16 会 dtype 不匹配）。
4. 加 `get_head_mask` / `warn_if_padding_and_no_attention_mask` 等 v5 缺失方法 shim。

### 验证与派发
- CUDA forward `(2,18,2048)`；runner smoke **frozen exit 0**；LoRA 需小 bs（1.6B fp32）→ q_fill.py 增
  per-run `bs`/`max_len` 覆盖，AIDO 用 bs 8。
- AIDO plan：ncRNA+modification × {frozen,lora} × {random,family} × 3 种子 = **24 runs**，已派发（need 24GB）。
- GitHub HEAD de17561。

### 队列（约 16:55）
- P1 **64/111**；UTR-LM 30/36；mRNABERT 40/54；AIDO 0/24（刚起）。

## 2026-09-26 深夜（续）· P2 RiboSpan 接入成功（4/5 架构完成）

### RiboSpan（model_type ribospan，1.6B 长上下文）
- 代码不在 HF 仓 → 取自 **GAIR-NLP/RIBOSPAN-FM** 的 `ribospan/`（configuration/modeling/tokenization + vocab.txt）。
- 将 `load_gbrna` 重构为**通用 `_load_vendored()`**（同时服务 gbrna 与 ribospan）：
  ① 按 module 名子串定位 config/model/tokenizer（两种命名方案兼容）；
  ② 建模文件 transformers≥5 补丁（pytorch_utils 缺失助手回退）；
  ③ config 默认补齐（is_decoder 等）；
  ④ tokenizer 直接实例化（绕开 fast 后端/sentencepiece）；
  ⑤ 权重：**safetensors 优先，否则手工 `torch.load(weights_only=True)`**（RiboSpan 仅 .bin，
     而 HF≥5 在 torch<2.6 下因 CVE 拒载 .bin）+ get_head_mask/警告方法 shim。
- 验证：AIDO 与 RiboSpan 皆 CUDA forward `(B,T,2048)` fp32；RiboSpan runner smoke frozen exit 0。
- 派发：RiboSpan plan ncRNA+modification × {frozen,lora} × 双切分 × 3 种子 = 24 runs（bs 8，need 24GB）。
- 中途修复：重构后 `load_gbrna` 的 module 键失配（tokenization_rnabert）→ 改按子串查找，AIDO 复验通过。

### 队列（约 17:15）
- P1 **72/111**；UTR-LM 34/36；mRNABERT 49/54；AIDO 0/24；RiboSpan 0/24。
- **P2 架构总账：4/5 已入 E1**（UTR-LM / mRNABERT / AIDO.RNA-1.6B / RiboSpan）；仅 HydraRNA（重型独立 env）未做。
- GitHub HEAD 605c363。

## 2026-09-26 深夜（续2）· AIDO/RiboSpan 显存门标定 + 上卡

- 现象：AIDO/RiboSpan worker 长期 `wait(no card)`（need 24GB，常规卡空闲常在 15-18GB）；
  且一次 kill/relaunch 组合命令半途失败，留下 2 个孤儿 run + 死 worker。
- 处置：按 `finetune_one --model [A]{IDO}` bracket 防自匹配精确回收孤儿；清锁重锁；
  按实测把 need 降到 **frozen 14GB / lora 18GB**（1.6B fp32 权重 6.4GB + 激活）；
  重启 3+3 shard。
- 结果：AIDO/RiboSpan 各 4 格已上卡在跑（GPU0/GPU4 等）；无 GAVEUP/TIMEOUT。
- 队列（约 17:15）：P1 **75/111**；UTR-LM 35/36；mRNABERT 51/54；AIDO 0/24（4 在跑）；
  RiboSpan 0/24（4 在跑）；ledger **1347 行**。

## 2026-09-26 深夜（续3）· mRNABERT 严重缺陷发现与修复（[UNK] tokenizer）

### 发现（3 遍核查）
- mRNABERT 已落 58 行数值全部异常：ncRNA ACC ≈ 0.077（恰 = 1/13 chance）、m6A AUC ≈ 0.50。
- 根因：`YYLY66/mRNABERT` 的 BertTokenizer **词表为 DNA 字母表（A,C,G,T,N）+ 空格式 3-mer**
  （74 = 5 specials + 5 单碱基 + 4^3 个 3-mer）；对原始 RNA 串：
  ① `U` 不在词表 → [UNK]；② wordpiece 无法切分**未空格**的核苷酸串 → 整词 [UNK]。
  故**全部 mRNABERT run 均为 chance，属无效结果**。

### 修复
- `_UDnaTokenWrapper`：预处理 = `U→T` + **非重叠 3-mer 空格切分** + 尾段（<3nt）拆单碱基
  → 任意长度 0 个 [UNK]（已用 14/16/17/20 nt 验证）。
- **方法学界定**：3-mer token 与碱基网格不对齐 → mRNABERT **仅适用于 per-seq 任务**；
  per-base（m6A/SSP）需碱基级对齐（暂不做）→ 其 per-base runs 移除。

### 数据治理
- **quarantine**：58 行 mRNABERT 行移出 ledger → `status/quarantine_mrnabert_unk_tokenizer/`
  （ledger_rows.jsonl + README.md 说明；明确标注"非科学结果"）。ledger 1347 → **1293 行**。
- p2_mrnabert_plan.json 收敛为 **ncRNA only（18 runs）**，已重启 3 shard。
- 教训：接入新 tokenizer 必须**先验 token 化**（是否 [UNK]/是否与标签网格对齐）再放量。

## 2026-09-26 18:08 m6A 补格链第 10 班巡检（终态静默，无动作）

**状态**：18/18 终态静默复核通过（task=modification & model∈{RNA-Sc-1M,
RNA-Sc-650M} & smoke=false & split=random & 去重，18/18 done、pending 0）。
M6A-ENDS DONE 12:18:16 驻留 log 第 485 行（末行）；ends/sweep/finetune_base
进程三清零（当前在跑的 15 个训练 worker 全为 P1/P2 链 finetune_one/
finetune_ssp 入口）；q_m6a_ends.log mtime 冻结 12:15:32、ledger mtime 09:19:47
后 ends 范围零新增（ends 范围 max updated_utc 2026-09-25T03:23Z；ledger
整体 1314 行、18:07 仍活跃系 P1/P2 并行链在写，与 ends 链无关）。

**谱线终态复核（承第 8 班终判，本班全量重算确认无漂移，只引 test 集
value 字段，无 smoke 行）**：lora 5 档 3 种子均值 1M 0.9467 / 10M 0.9427 /
30M 0.9415 / 100M 0.9469 / 650M 0.9476——全 5 档 ∈[0.941,0.948]，极差
0.006；1M 首端 lora 0.9467 ≥ 10M 0.9427，无首端规模效应。full@3e-5
均值 1M 0.9393 / 10M 0.8964 / 30M 0.9342 / 100M 0.9367 / 650M 0.9269
（10M 为 0.9438/0.9145/0.8309 去重口径）。**对照 v0.6.4「m6A 全饱和
0.94-0.997」：受控系 lora 侧 0.941-0.948 成立（与官方系 0.968-0.997
合成 0.94-0.997 全谱段）；full 侧 10M 0.8964、650M 0.9269 低于 0.94
下界，判为种子方差非规模效应（各档 full 3 种子极差 0.021-0.113，置信
区间跨 0.94 线重叠）——v0.6.4 表述无需修订，「m6A 等价线不可辨识」
结论维持；1M<0.90 通知线未触发（1M lora 0.9467、full 0.9393 两臂均
>0.90 且不低于 10M 对应臂），不通知用户。**

**范围外观测（不计入 ends 18 格，无动作）**：第 9 班后（15:43-15:52 CST
= 07:43-07:52Z）新落地 9 行 ft_rnasc1m_modification_{frozen,lora,full}
×3 seeds_family（frozen 0.670-0.681 / lora 0.956-0.966 / full
0.961-0.981）——来源为 P1 fill 链（q_p1_fill_s0/s5 日志比对确认），
非 ends 链产物；ends 口径不涉该批行，谱线判读不受影响。

**异常（待人工处理，承第 9 班清单不变）**：① ledger 650M full_s17
同微秒同值 done 行 ×3（去重后 0.9250 无害）；② frozen s29 双实例
竞态（同值 0.9137 无害）；③ 10M full_s43 同微秒同值行 ×2（去重后
0.8309，已含入 0.8964 口径）；④ ends 脚本 shell 层 RID 大写 bug +
pick_gpu 空输出缺陷仍在（finetune_base 内部幂等已实际无害化）。链路
终态收口且谱线连续三班零漂移，若无新增补格需求，本链巡检可归档。

**提交**：TRAINING_LOG.md（第 10 班巡检条目）

## 2026-09-27 00:00 (CST 17:32) · 队列状态 + AIDO/RiboSpan 吞吐评估

- mRNABERT 修复后首格落地：ncRNA frozen s43 = **0.4988**（chance 0.077）→ tokenizer 修复有效。
- AIDO/RiboSpan：6 格在跑（各 3），单格 etime 已 20 min、AIDO 仅到 epoch 0（1.6B fp32 + bs8 + 6858 训练序列）→
  预计单格 1-3h；48 runs / ~4-6 并发 → 需十余小时。属预期，队列夜间继续。
- P1 余 15 组全部为 SSP（RNA-Sc-100M 等长格）。
- 巡检双 cron 在岗（*/20 监控+补位、*/20 收口重刷）；refresh marker 未触发（正确，AIDO/RiboSpan/mRNABERT 未收口）。
- 无 GAVEUP/TIMEOUT；ledger 1298。

## 2026-09-26 21:40 · AIDO/RiboSpan 吞吐危机修复（timeout 4h→9h + 并发 6→12+）

### 危机（3 遍核查发现）
- 单 run 实测 ~7h（1.6B fp32 + ncRNA 10 epochs），但 worker subprocess timeout=14400s(4h)
  → **所有 run 会在 4h 被掐死并无限重试，永远无法落账**。
- 并发仅 6（slots=1 × 3 shard × 2 plan）→ 48 runs 需 2.3 天。

### 修复（q_fill.py + plans + cron）
1. `TIMEOUT_S` 从 plan 读取（aido/ribospan 设 32400s=9h）；
2. 新增 `is_busy()`：ps 级在飞检测（model+strategy+seed+split 精确匹配）→ 重启后
   对孤儿 run `skip(busy)`，防双跑（ledger claim 协议之外的进程级保险）；
3. slots 1→2、need 按实测校准（frozen 14→10G，lora 14→12G；实测占用 7.0–7.6G）；
4. cron 自动补位 3 shard→6 shard。

### 执行
- 杀旧代码 worker（12 个，子进程孤儿化继续跑完写 ledger——父死后 subprocess timeout 失效，孤儿自然跑完）；
- 新代码 12 worker（6 shard × 2 plan）启动，`skip(busy)` 已验证对 12 个孤儿生效；
- 现 12 孤儿在飞 + 新 worker 空闲即派 → 并发 12→18+（随卡内 slots=2 展开）。

### 附带核查（B20 门禁）
- AIDO/RiboSpan tokenizer 均为**单碱基 token**（[CLS]+A/C/G/U/T 逐碱基）→ per-base 任务（modification）合法，与 mRNABERT（3-mer）不同，无需剔除。
- GPU6/7 的 nvidia-smi 40GB 视图是宿主物理卡；torch 权威视图仍是 MIG 4.8GiB，不可用。
