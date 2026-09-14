"""Schmirler 协议 → RNA 适配差异清单 (T0.1.3)

来源：Schmirler, Heinzinger & Rost, Nat Commun 15:7407 (2024) 精读笔记 + spec v1.2。
用途：交接执行人必读；写作期对照。

| # | Schmirler 蛋白侧做法 | 本课题 RNA 适配 | 理由 |
|---|---|---|---|
| 1 | 8 pLM (ESM2 三档/ProtT5/Ankh/…) | 14 正式模型分 Tier-A 8 + Tier-B 6；混杂分层三面板 | RNA 模型语料/架构混杂更重（红队 R4） |
| 2 | 8 任务（二/三级结构、功能、深度突变等） | 10 任务，结论承载类（结构/功能）每类 ≥2 数据集 | 单数据集不做类结论（红队 R1） |
| 3 | frozen vs full FT 两臂 + PEFT 横评（LoRA/DoRA/IA3/Prefix） | 同构：frozen+头 / LoRA / head-only / full + E2 横评 | 机理篇 Q8 裁剪 LoRA → 本篇独占 |
| 4 | 浅头 = 单隐层 MLP（隐宽 32） | 完全对齐（隐宽 32） | 直接可比 |
| 5 | per-residue 任务 token 级头 | per-base 头同构；per-seq 用注意力池化/CLS | TokBench mean-pool 教训（禁 mean-pool） |
| 6 | LoRA rank 默认、目标模块 | rank=8, alpha=4(=rank/2), q/k/v/o | 对齐 BEACON 协议口径 |
| 7 | Ankh 混合精度/full FT 不稳定 → 剔除并声明 | 651M/1.6B 不做 full FT，limitation 明写 | 同款分层处理 |
| 8 | 615 预测器 ≈ 8×8×(2 臂)×部分 | Tier-A 8×10×3×2×3 种子 + Tier-B 观察层 | 预算重算（红队 R3） |
| 9 | 无家族级切分轴 | 双切分（随机/家族）+ §3.4 切分单元表 | RNA 家族级分布偏移是核心卖点（C4） |
| 10 | 无多重比较校正 | BH FDR q=0.05 + 方向一致性门槛 + 预注册 | 红队 R2/R7 |
| 11 | GPU 时/显存实测（Fig.5） | E5 同款三项记录（wall-clock/峰值显存/ckpt 体积） | 直接对齐 |
| 12 | 配方决策树收尾 | 同款 + 预注册阈值（>2% 且 BH 显著=推荐） | 红队 R7 |

核心不可搬项：蛋白侧"Slope 模型排名不可靠"叙事（RNA 侧由机理篇承载）；
蛋白侧大语料假设（RNA 标注小 1-2 个量级 → C3 小数据轴是主战场）。
