# 8 任务选型最终确认稿 v2（数据实测后修订）

> 上稿基于文献推测；本轮已在新集群逐一实测 BEACON 备份数据（beacon_raw 13 任务目录全在）。关键实测发现：

## 数据实测（决定选型）

| BEACON 任务 | 数据状态 | 粒度 | 类型 |
|---|---|---|---|
| **degradation (OpenVaccine)** | ✅ train 2155 / val 245 / test 3634；`deg_Mg_pH10` 等 8 列逐碱基**连续数组**（每序列 68 浮点实测验证） | **per-base** | **回归** ← 就是您要的第 4 类 |
| **spliceai** | ✅ train 144,628 行；labels = 0/1/2 字符串（100nt 窗，稀疏正点 ~3%） | **per-base** | 3 分类 |
| **structural-score-imputation** | ✅ test 3095；`struct_true` = 每位一个 0-1 连续分（100 位，与序列等长）| **per-base** | **回归**（备选） |
| crispr-off-target | ✅ 但 label 是**连续 cleavage 分数**（非二分类），更适合回归 | per-seq | 回归 |
| secondary-structure (bpRNA) | ✅ 现役 runner 在用 | per-base | 标签二分类 |
| **rbp** | ❌ beacon_raw 无此目录（13 目录里没有） | — | — |

## 修订后的 8 任务（最终建议）

| # | 任务类 | 任务 A（现有） | 任务 B（新增） | 数据依据 |
|---|---|---|---|---|
| 1 | 序列级分类 | ncRNA 家族分类 | **crispr-off-target**（按连续分数离散化为三档：高/低/无切割——或直接当序列级回归用；实测 label 连续，两用法都可，倾向三档分类以填"分类"格） | BEACON 现成 280k 行 |
| 2 | 序列级回归 | MRL | **（若 1 用分类）MRL 已覆盖**；备选 crispr 连续分数做序列级回归 | 同上 |
| 3 | 碱基级分类 | m6A | **spliceai 3 分类** | 144k 行现成 |
| 4 | 碱基级回归（新类） | **degradation (deg_Mg_pH10)** | **structural-score-imputation**（第二碱基级回归，同格双数据集互证——正合 spec"每类 ≥2 数据集"纪律） | 两个都现成 |

**改动要点 vs 上稿**：
- 碱基级回归 = degradation + structural-score-imputation 双数据集（互证，比单 eCLIP 更稳且零下载）；
- RBP 撤回（数据不在备份）；
- crispr-off-target 实测是连续分数——建议做序列级回归第 2 任务（与 MRL 互证），序列级分类第 2 任务改用其三档离散版或接受"分类类 = ncRNA + m6A/spliceai 已 2 个"的解释。

## 待您确认（一句话即可）

- 碱基级回归双数据集（degradation + structural-score-imputation）是否同意？
- crispr-off-target 当"序列级回归第 2 任务"（连续分数）还是"分类第 2 任务"（离散三档）？

确认后我立即写 loader/runner（degradation 与 ssi 需新的 per-base MSE 头）→ smoke → 派 8 任务矩阵。

---

## 2026-10-24 执行口径冻结与科学完整性纠正

### 唯一任务/指标注册表

| 任务 | 粒度与类型 | 主指标 |
|---|---|---|
| noncoding-rna-family | per-seq 分类 | ACC |
| crispr-off-target | per-seq 二分类 | PR-AUC |
| mrl | per-seq 回归 | Pearson r |
| modification | per-base 分类 | AUC |
| spliceai | per-base 三分类 | macro-F1 |
| degradation | per-base 回归 | PCC（MCRMSE 辅助） |
| structural-score-imputation（运行名 `ssi`） | per-base 回归 | PCC（MCRMSE 辅助） |
| secondary-structure | per-base 分类 | F1 |

CRISPR 当前正式 runner 使用二分类 PR-AUC，不再保留“连续回归/三档分类”未定口径；后续若增加回归臂，必须独立注册、独立 RID，不能与现结果混用。

### B20 纠正门禁

2026-10-24 实测：HF RnaTokenizer 自动加入 `<cls>/<eos>`，NucleicBERT 加入 `[CLS]/[SEP]`；旧 spliceai/degradation/SSI runner 未排除这些位置，造成标签错位。上述模型旧结果不得进入图表或论文；RNA-Sc 无特殊 token，不受此实现错误影响。所有修正版必须：

1. 训练与评估共用 special-token/PAD 排除后的监督 mask；
2. 全长度 tokenizer 校验为单碱基映射，k-mer 直接报错；
3. 支持 degradation scored window 与确定性右截断；
4. 使用 `_b20fix` 新 RID，旧行和旧 artifacts 备份后隔离；
5.  ledger done + result.json + 真实 tokenizer smoke + CUDA smoke + validation 收敛证据齐全后才可标正式完成。

### E6 official 纠正门禁

旧 official 分支在未掩码输入上读取同位答案，存在标签泄漏，旧 official E6 数值冻结、不得引用。修正版为固定 15% masked-position MLM NLL：pre/post 使用同一 seed 201 掩码，pre_b 使用 seed 707 独立掩码，noise band 为独立掩码/顺序重评差异； corrected RID 使用 `_mlm15fix`。controlled causal NLL 与 NB hidden drift 分支分开审计，不与 official MLM 口径混写。
