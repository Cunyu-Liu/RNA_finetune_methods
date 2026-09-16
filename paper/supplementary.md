# Supplementary Materials — 骨架与数据源映射

> 自动产物优先：本文件只做导航与说明，具体数值一律从 status/ 下
> 的自动导出文件引用，避免手工誊写引入不一致（对齐 R9 口径纪律）。
> 状态：v0.1（2026-09-16）；队列收尾后由 chain_final_refresh 自动
> 刷新的产物即"终版数据面"。


## S0 产物索引（自动导出链, 8 artifacts）

| 节 | 产物 | 生成器 |
|---|---|---|
| S1/S2 | status/stats.md | rnafteval.stats |
| S3 | status/e2_table.{md,csv} | rnafteval.export_e2 |
| S4 | status/lr_grid_table.{md,csv} + figs/fig_lr_grid | rnafteval.export_lr_grid + figures |
| S5 | status/splits_table.md | rnafteval.export_splits |
| S6 | status/leakage_table.md | rnafteval.export_leakage |
| S7 | status/resources.md | rnafteval.export_resources |
| C1/C4 主图 | status/figs/fig_c1_matrix + fig_c4_delta | rnafteval.figures |
| C4 表 | status/c4_table.{md,csv} | rnafteval.export_c4 |

守护链 scripts/chain_final_refresh.sh 在全部训练队列排空后
自动重刷以上八件（终版数据面）；每件均可独立重跑（ledger/
parquet 为唯一数据源，无手工誊写环节）。

## S1 格级均值 + 种子 bootstrap 95% CI
- 数据源：`status/stats.md` §格级均值（46+ 格，mean [CI] n）
- 用途：主文 C1/C4 数值的区间支撑；种子数 3 的 CI 反映训练随机性
  下界（正文 Limitations 说明功效墙）。

## S2 全部配对对比（58 对，BH FDR q=0.05）
- 数据源：`status/stats.md` §统计检验表
- 用途：R2 防线证据——每条对比配对化（同模型同任务同切分内），
  BH 校正列注明；n=3 符号检验功效墙（min p=0.25）正文已声明。

## S3 E2 PEFT 五臂横评全表
- 数据源：`status/e2_table.md` + `status/e2_table.csv`
  （`rnafteval/export_e2.py` 自动导出）
- 内容：逐种子数值 + 训练参数量（full 33.5M / DoRA 0.57M /
  LoRA 0.55M / IA3 0.012M / head-only 0 + 16K head）
- 用途：主文 §2.3 的 C5 参考性观察（预注册表述：位次为参考性
  观察，非类级结论——spec §3.5 第 6 条）。

## S4 LR 网格全谱（A8）
- 数据源：`status/figs/fig_lr_grid.{png,pdf}` + ledger
  `*_s101_*` 行（双模型 × 4 LR × 2 策略）
- 用途：A8 证据链——full 甜区随规模左移（10M:3e-5 → 33M:1e-5）；
  LoRA 双尺度均需 3e-4；LR 错配翻转策略排名的定量展示。

## S5 家族切分构建详情（B4/R5）
- 数据源：`status/splits_table.md`（rnafteval/export_splits.py
  自动导出：三任务 rows/seqs/簇数/切分尺寸 + 每次导出现场
  groupby 零重叠复算）+ data/family_splits/*.parquet
- 关键数字：ncRNA 7,731 簇 / SSP 12,825 簇 / m6A 241,984 簇
  （rows 309,460 > seqs 308,915 = 宿主代理设计：同转录本多窗口
  共享簇归属）
- 用途：R5 地基证据——per-base 任务的宿主代理映射规则
  （spec §3.4 表）双层验证（构建断言 + 导期复算）。

## S6 官方切分泄漏审计（B1）
- 数据源：status/leakage_table.md（rnafteval/export_leakage.py
  可复现自动导出：官方 train/test 对齐全量聚类 parquet；
  **326/1200 = 27.2% 宿主级簇重叠** + 31-mer 30.6% + exact
  2.2% 三口径对照；含与首记录的口径差注）
- 用途：主文 §2.5；"官方 random 臂本身受宿主级泄漏污染"的定量
  支撑（可复现，每次导出重算）。

## S7 资源实测（E5/B6）
- 数据源：status/resources.md（rnafteval/export_resources.py
  自动导出：按策略 wall 中位数/峰值显存中位数/检查点体积，
  formal 与 tuning 分池；覆盖 185/186）+ ledger.jsonl 逐 run
- 用途：策略成本侧写；Schmirler Fig.5 式协议（长度 1024，单卡
  实测）在正文 Methods 摘引。

## S8 数据与代码可得性
- 仓库：github.com/Cunyu-Liu/RNA_finetune_methods
- 复现链：ledger.jsonl（run 级）→ export_c4/export_e2/stats/
  figures（产物级）→ 本 Supp 引用
- 预注册文档：spec §3.5（统计计划）与 §7（决策树规则）冻结于
  实验启动前（2026-09-14/v1.2）。
