# 预印本 v0.9 送审速览（2026-09-26，HEAD 1dc1751）

## 一句话
在 RNA-LM 上受控对比三种微调策略（frozen+头 / LoRA r=8 / 全参），六个核心发现：
序列级任务的微调收益大半是家族级泄漏；最优策略是任务粒度的属性而非模型属性；
灾难性遗忘真实存在、尺度非单调（中段危险带），适配器压缩遗忘尾部。

## 六大发现（abstract 顺序）
1. **微调有效但收益依赖任务粒度×切分**：随机切分 +0.04~+0.43，家族切分崩塌至 0.06-0.12 带
   （崩溃需要骨干更新——frozen/head-only 不崩）。
2. **泄漏敏感度 = 粒度 × 家族密度**：per-seq Δ+0.68~0.91 vs per-base Δ−0.007~−0.042。
3. **默认 LR 是不挑架构的陷阱**：3e-4 全参崩为 ln(C) 熵平原（三架构一致），tuned 全恢复。
4. **等价线双轨全谱（用户设计验证）**：官方 RiNALMo LoRA 处处胜 full（0.969>0.957）；
   受控系 full 5/5 全胜（0.896>0.855），30M full 0.862 ≈ 650M LoRA 0.855——两系方向在所有
   尺度相反；单家族存在性反例，不作普适主张。
5. **m6A 六档全谱 + 粒度×策略镜像**：lora 1M-650M 全饱和（0.941-0.948）；同一受控 650M
   上 m6A lora>full（+0.021）而 ncRNA full>lora（+0.040）。
6. **C6 灾难性遗忘全谱（36 格，1M→650M 新收口）**：非单调、中段危险带——30M 峰值
   （full 均值 +17.7、最差 +26.2；LoRA 最差 +3.4，~8× 尾部压缩）；1M 轻微、10M 负、
   100M 回稳、650M 再负（LoRA 3/3 负）；官方 33M 6/6 微忘自身分布。

## 关键产物（/mnt/cunyuliu/rna-ft-eval/status/）
- fig_e6_spectrum.{png,pdf}（C6 受控系 ΔNLL vs 规模谱线，新增）
- fig_c5b.png（双系 8 尺度等价线终版）· fig_c1/c4/e3/lr_grid
- e6_table.md/csv（36 格）· c4_table / e2_table / e3_table / stats
- figs/equivalence_line.pptx（PPT 等价线页，pptx_lint PASS）

## 数据可信度锚点
- ledger 1146 行（1137 done；run 级，flock-safe，全 test 集口径）
- C6 导出链修复：export_e6 原硬编码 ORDER 丢弃 1M/650M 端点格 → 已扩 1M→650M 全谱
- 工程陷阱族谱：MIG 索引 / 解包序 / 自抛 OOM / RID 大小写 / 显存 gate 过保守 / 同卡碰撞（逐卡锁）

## 完整文档
- paper/preprint_draft.md（v0.9 全稿）
- paper/preprint_zh_summary.md（中文对照+电梯陈述+审稿防线自查）
- TRAINING_LOG.md（全程记录，30+ 节）
