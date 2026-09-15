# RNA-LM 微调策略评测 — 训练与交接执行日志

> 本文件记录每次训练过程与结论（用户要求）。日期用服务器时间。

## 2026-09-15（Day 1 上午 08:25 巡检：SSP 波次重启 + 冒烟矩阵旧故障结案）

### 巡检结论（全绿，无重大资源异常）
- 8×A100-40G：GPU0-5 被他人占满（各 31-39GB / util 100%），GPU6/7 空闲（~5G/3.7G）；磁盘 /home 30%、/mnt 51% 充足；
- ledger 40 行：done 35 / pending 7（ncRNA 矩阵 3 种子基本齐、modification LoRA+full 3 种子齐）；
- **冒烟矩阵 00:09 OVERLAP 崩溃结案**：复现验证（载入当前数据+代码跑零重叠断言）随机臂/家族臂均通过
  ——系 dedup 修复（f27b5fe）之前的旧故障，冒烟矩阵随后已重跑成功（smoke 行 done）；
- 环境段误报修复：status_check.sh [2] 由不存在的 envs/rnaft 改为 llr_env+pypath：
  torch 2.5.1+cu121 / transformers 5.0.0 / peft 0.13.2 / cuda True。

### 异常与处置
1. **SSP 两 run 静默死亡**（lora_s17_random 跑到 epoch 2 中断、frozen_s17_family epoch 0 前中断；
   无 traceback、非 CUDA OOM、进程消失）→ 判定 SIGHUP（未挂 nohup）→
   wave2 以 nohup+setsid+timeout 14400 重启（GPU6: frozen/headonly s17 family；GPU7: lora/full s17 random）；
2. **⚠ SSP F1=0.0 重大异常**：frozen/headonly s17 random 正式完成（wall 1733s）但
   precision/recall/F1 全 0；kmer LGBM 基线 F1 也仅 0.043（random）/0.0（family）→
   判定 SSP 评测口径或配对解码存在系统性 bug，**SSP 全部结果（含已完成 run）暂不可作为科学结论**，
   待并行会话 smoke 复现修复后重测；
3. modification 补跑队列（GPU2）正常：full 17/29/43 完成 AUC .939/.942/.939，
   frozen/head-only 29/43 排队中；
4. 并行会话清理了 ledger 中 secondarystructure 行并重派部分 run——两会话经 ledger
   claim 互斥，无双重运行。

### 进行中（08:25 派发）
- GPU6 wave2: SSP frozen s17 family → head-only s17 family；
- GPU7 wave2: SSP lora s17 random → full s17 random；
- GPU7 旧队列: RiNALMo frozen s43 random（07:32 起）；GPU6 旧队列: ncrna headonly s29/s43
  family + RiNALMo full s17 family；GPU2: modification 补跑。

### modification m6A（random，正式）三种子小结
LoRA .941/.944/.943、full .939/.942/.939、frozen .645（s17）、head-only 排队 ——
LoRA≈full≫frozen 方向 3 种子成立（frozen/headonly 补齐后入正式表）。


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
