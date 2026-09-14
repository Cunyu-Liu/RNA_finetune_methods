# RNA-LM 微调策略评测 — 训练与交接执行日志

> 本文件记录每次训练过程与结论（用户要求）。日期用服务器时间。

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

### 基建交付（已 GitHub 首推：Cunyu-Liu/RNA_finetune_methods master 812ae76）
- rnafteval 包：ledger（flock 安全+strategy 维度）/ task_registry / models
  （HF+RNA-Sc 双加载器）/ strategies（注意力池化+隐宽32 头）/ splits
  （随机+家族级+零重叠断言+簇纯净断言+去重）/ metrics（自测全过）/
  finetune_one（GPU-only 纪律）/ gpu_guard（CPU 静默降级检测）；
- 监控：本地 Schedule 每 2h 巡检 + 服务器 crontab 每 30min 状态快照。

### 训练记录

| run | 状态 | 结果 | 备注 |
|---|---|---|---|
| ft_rnasc10m_ncrna_frozen_s17_random_smoke | done | ACC 0.783 | 600 样本 smoke，GPU 全流程首通（22s/3ep，721MB） |
| ft_rnasc10m_ncrna_frozen_s17_random | done | **ACC 0.375** | 全量 13 类（chance 0.077），6858 train，1072s，958MB —— 首个正式 run |
| ft_rnasc10m_ncrna_lora_s17_random_smoke | done | 跑通 | LoRA 184,320 可训参数（qkv/out 目标模块适配 RNA-Sc） |
| ft_rnasc10m_ncrna_full_s17_random_smoke | done | 跑通 | full 8.86M 全参 |

### 问题与修复（当天）
1. BEACON ncrna 有 347 条跨 split 完全重复序列 → 零重叠断言正确触发拦截 →
   加 dedup（保留首现）后通过。**断言系统首次实战拦截泄漏**（B1 防线有效）；
2. RNA-Sc-10M d_model 实际 192（6 层 × d=192？ckpt cfg 是 d=192 而非 specs 里的
   512）→ finetune_one 运行时自动探测校正 h_dim；
3. GPU6 有他人 gmx 分子动力学任务挤显存 → bs 降到 16 + expandable_segments；
   同时 GPU6 整卡利用率 N/A（gmx 挂在 MIG/不同容器视图），实际可用约 34GB；
4. LoRA on RNA-Sc：peft 包装后 forward 签名不匹配 → wrapper 解包
   peft.base_model.model 再调 encoder 原生签名，跑通；
5. RNA-Sc backbone FLOPs 薄（自训 10M 小模型）→ frozen 每 epoch ~107s（bs16），
   后续大模型（RiNALMo 33M+）预计更慢，需要 embedding 抽取共享优化（T2.1.1 计划）。

### 下一步（v5 矩阵收尾后）
- head-only 全量跑完 → 用修复版代码重跑 lora/full 全量（v5 里旧代码会崩）；
- RiNALMo-micro 接入 smoke（HF 路径）→ 4 策略 × 2 模型冒烟矩阵闭环 = A7 验收；
- LR 网格预实验（tuning seed=101）→ A8；
- 传统基线（k-mer logistic/LightGBM）在 ncrna 上出分 → B5 口径对齐。

## M5 监控
见 docs/m5_monitoring.md（首轮 2026-09-15：无触发，四源仍单臂）。
