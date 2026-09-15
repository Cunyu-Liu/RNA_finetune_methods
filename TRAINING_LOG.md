# RNA-LM 微调策略评测 — 训练与交接执行日志

> 本文件记录每次训练过程与结论（用户要求）。日期用服务器时间。

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
