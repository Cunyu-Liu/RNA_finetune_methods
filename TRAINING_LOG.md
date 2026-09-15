# RNA-LM 微调策略评测 — 训练与交接执行日志

> 本文件记录每次训练过程与结论（用户要求）。日期用服务器时间。

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
