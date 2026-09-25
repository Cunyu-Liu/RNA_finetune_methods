# 预印本 v0.7.2 送审速览（2026-09-25，HEAD 02ab55f）

## 一句话
在 RNA-LM 上受控对比三种微调策略（frozen+头 / LoRA r=8 / 全参），五个核心发现：
序列级任务的微调收益大半是家族级泄漏；最优策略是任务粒度的属性而非模型属性。

## 五大发现（abstract 顺序）
1. **微调有效但收益依赖任务粒度×切分**：随机切分 +0.04~+0.43，家族切分崩塌至 0.06-0.12 带
   （崩溃需要骨干更新——frozen/head-only 不崩）；
2. **泄漏敏感度 = 粒度 × 家族密度**：per-seq Δ+0.68~0.91 vs per-base Δ−0.007~−0.042；
3. **默认 LR 是不挑架构的陷阱**：3e-4 全参崩为 ln(C) 熵平原（三架构一致），tuned 全恢复；
4. **等价线双轨全谱（用户设计验证）**：官方 RiNALMo LoRA 处处胜 full（0.969>0.957）；
   受控系 full 5/5 全胜（0.896>0.855），30M full 0.862 ≈ 650M LoRA 0.855——
   两系方向在所有尺度上相反；单家族存在性反例，不作普适主张；
5. **m6A 六档全谱 + 粒度×策略镜像**：lora 1M-650M 全饱和（0.941-0.948）；
   同一受控 650M 上 m6A lora>full（+0.021）而 ncRNA full>lora（+0.040）。

## 关键产物（/mnt/cunyuliu/rna-ft-eval/status/）
- fig_c5b.png（双系 8 尺度等价线终版）· fig_c1/c4/e3/lr_grid
- c4_table / e2_table / e3_table / stats（12:14 全刷，含 650M 全数据）
- figs/equivalence_line.pptx（PPT 等价线页，pptx_lint PASS）

## 数据可信度锚点
- ledger ~1090 行（run 级，flock-safe，全 test 集口径）
- 三遍全稿对账：2.3 谱线 15/15 + 崩塌带 8/8 + abstract 3/3 零误差
- 工程陷阱 4 项全部规则化（MIG 索引/解包序/自抛 OOM/RID 大小写）

## 完整文档
- paper/preprint_draft.md（v0.7.2 全稿）
- paper/preprint_zh_summary.md（中文对照+电梯陈述+审稿防线自查）
- TRAINING_LOG.md（全程记录，30+ 节）
