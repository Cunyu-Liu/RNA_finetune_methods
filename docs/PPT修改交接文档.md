# PPT 修改交接文档（给接手人）

> 更新：2026-10-07 深夜 · 作者：TRAE agent（刘存宇课题）
> 用途：别人接手继续改 PPT 时的一切必读信息——文件、结构、数据口径、工具链、红线

---

## 1. 文件清单（ppt/ 目录）

| 文件 | 状态 | 用途 |
|---|---|---|
| **RNA_LM微调策略评测-结果版.pptx** | ✅ 主交付（11 页，简洁结果版） | 用户已确认为「结果展示」版——后续修改在此文件上进行 |
| RNA_LM微调策略评测-凌乱全面版.pptx | 归档（19 页，过程详解版） | 含 E1-E6 每个实验的「为什么做/怎么做/预期/实测」详解页——需要过程细节时从这里捞内容 |
| work/before_update_1007e.pptx | 备份 | 09-27 旧数据版（内容更新前） |
| work/before_fix_1007.pptx | 备份 | 数字修正前 |
| 旧/*.pptx | 历史备份（6 份） | 09-15 ~ 09-27 各阶段 |
| fig_ppt_*.png / fig_*.png / family_tsne_*.png | 图源（8 张） | 已嵌入 PPT 的图；如需替换/重生成见 §4 |

**~$ 开头文件是 PowerPoint 打开时的锁文件，忽略即可。**

---

## 2. 结果版 11 页结构（逐页说明）

| 页 | 标题 | 版式 | 数据源 |
|---|---|---|---|
| 1 | 封面（冻结/LoRA/全参三选一） | 原封面未动 | — |
| 2 | 执行进度速览 | 8×3 表格 | 服务器 status 表 + ledger 计数 |
| 3 | 结论① 泄漏幻觉：16 架构家族切分崩溃 | 全幅图 fig_ppt_16arch | c4_table.csv 权威值 |
| 4 | 机制可视化：坍缩的是分类头不是表征 | tsne 2×2 图 | t-SNE 旧图（09-21 生成） |
| 5 | 结论② 机制：默认 LR 是全参陷阱 | 全幅图 fig_ppt_a8_simple | ledger 3e-4 vs tuned 对比 |
| 6 | 结论③ 路线：PEFT + rank 扫描 | 全幅图 fig_ppt_ranksweep | ledger rank 48 格 |
| 7 | 课题定位：RNA 侧首个受控策略对比 | 6×5 对比表 | 领域调研（M5 监控两轮无重叠） |
| 8 | 结论④ 等价线：配方依赖 | 全幅图 fig_c5b | 服务器 status/figs |
| 9 | 结论⑤ 标注预算：小数据全参最优 | 全幅图 fig_e3_curves | e3_table.md 权威口径 |
| 10 | 结论⑥ 遗忘 30M 危险带 | 全幅图 fig_e6_spectrum | e6_table（87 格） |
| 11 | 总结：实践者三选一答案 | 三卡片 + 页脚证据规模 | 全部结论汇总 |

**每页版式**（s3-s10 统一）：26pt 深蓝标题 → 15pt 红色结论副题（一句话主结论）→ 图（4.9in 高带）→ 12.5pt 数据 banner（页底单行关键数字）。

---

## 3. 数据口径（改数字前必读——防手抄错误）

**唯一权威数据源 = 服务器 ledger**（`A100:/mnt/cunyuliu/rna-ft-eval/ledger.jsonl`，1916 行 done）。
导出表在 `A100:/mnt/cunyuliu/rna-ft-eval/status/`（c4_table.csv / e2_table.md / e6_table.md / e3_table.md 等，均自动导出）。

**PPT 中数字与导出表已逐格核对 3 遍**（程序化，tol 0.012），关键口径：

1. **崩溃带口径**：16 个含骨干更新臂的架构（HydraRNA 是 frozen-only 不计数）；3 个部分逃逸——UTR-LM full 0.15 / RiNALMo-mega LoRA 0.21 / RNA-FM tuned-full 0.53
2. **RiNALMo 家族数字用 grid-best 口径**：33M full **0.944**（3e-05）/ 148M full 0.945 / 650M full 0.956 / LoRA 0.928/0.949/0.969——不是旧的 1e-05 单点值 0.938
3. **E3 权威口径**（tuned backfill 后）：n=10/100/1000 full 全线最优 0.156/0.519/0.698；全量 6859 崩溃 0.083——旧表 0.229 已作废
4. **E6 矩阵 87 格**（51 ncRNA-起 + 18 m6A-起 + 18 保持度）：30M full 最差 +26.2 vs LoRA +3.4；官方谱 18/18 正遗忘（full 0.157→0.125、LoRA 0.118→0.026 随规模衰减）；1M 例外 LoRA 种子 +3.76 > full +2.5
5. **NB（NucleicBERT）全臂 3/3 种子**（1007 补齐）：ncRNA frozen 0.838 / lora 0.940 / full(tuned) 0.882；m6A lora 0.992
6. **在途数据**：AIDO full@3e-05 formal 3 种子补跑（worker 等卡轮转 + aido_close_monitor cron 自动收口）——落地后 1.6B 结论可从「tuning-seed 对比」升级为 3-seed

**红线**：任何数字写入 PPT 前必须先对 ledger 原始行或 status 导出表（纪律第四条）；导出表冲突 = 停用并回 ledger 裁决。

---

## 4. 工具链（改完必跑）

### 4.1 程序化数据表（生成期望值）
```bash
python3 code/tools/update_ppt.py --csv-dir <status csv 目录> --out <输出前缀>
# 从服务器拉最新表：scp A100:/mnt/cunyuliu/rna-ft-eval/status/c4_table.csv <本地目录>
```

### 4.2 表格逐格核对（PPT vs 期望值）
用 python-pptx 读 PPT 表格单元格，与 §4.1 产出的 json 逐格比对（历史脚本见交接文档巡检日志 1007 第 2/3 轮段落；tol 0.012 数值 / 0.006 E2）。

### 4.3 lint（结构完整性）
```bash
python3 code/tools/pptx_lint.py ppt/RNA_LM微调策略评测-结果版.pptx
# PASS 才可交付
```

### 4.4 格式六项检查（边界/重叠/字体/行距/字号/数据）
python-pptx 全页扫描脚本（同巡检日志内嵌代码）。**字体必须 Microsoft YaHei；正文 1.5 倍行距；表格 1.15**。

### 4.5 重生成图（数据变更时）
图脚本在服务器 `/tmp/fig_simple2.py`（16arch/A8）与 `/tmp/fig_ppt2.py`（rank/E6 官方谱）——数据变了从 ledger/c4_table 重渲染后替换。**注意 16arch 图必须从 c4_table.csv 直读**（曾因 ledger 过滤 bug 画成全零假图——见 §6 教训）。

---

## 5. 用户格式要求（改版时保持）

- 字体：微软雅黑（含表格——历史上有 217 个单元格 run 级字体缺失，已补齐，改动时留意 cell.text 赋值会重置字体）
- 行距：正文 1.5 倍；表格 1.15
- 字号：标题 26pt / 结论副题 15pt / banner 12.5pt / 表格 10-12.5pt
- 版式：一页一结论一图；无图文重叠；无越界
- **用户已手工调整过的样式不要再动**（卡片底色、封面、进度表框架等）
- 已确认方向：**简洁的结果展示，图表文并茂**——不要过程叙述、不要长段分析

---

## 6. 历史踩坑（改 PPT 前必读）

1. **zip 手术风险**：直接重写 pptx 的 zip（去重/删 part）曾产生 CRC 损坏 → PowerPoint 显示旧页数假象。**删页/清孤儿 part 一律用 python-pptx 正规 API，改完立即 `testzip()` + 重开验证页数**
2. **cell.text 赋值会重置字体**——每次改表格后必须重设 run.font.name
3. **手抄数字两次出错**（0927 mRNABERT 0.072→0.086、1007 grid-best 0.938→0.944）——数字一律程序化核对
4. **图数据源**：fig_ppt_16arch 曾因 ledger 过滤 bug 全零——生成图后必须打印数值断言
5. **等比缩放溢出**：add_picture 按宽度等比会超高——必须同时约束 max_w/max_h

---

## 7. 常用命令速查

```bash
# 查页数/结构
python3 -c "from pptx import Presentation; p=Presentation('ppt/RNA_LM微调策略评测-结果版.pptx'); print(len(p.slides))"

# CRC 完整性
python3 -c "import zipfile; print(zipfile.ZipFile('文件.pptx').testzip())"

# 服务器数据同步
ssh A100 'cat /mnt/cunyuliu/rna-ft-eval/status/c4_table.md'
scp A100:/mnt/cunyuliu/rna-ft-eval/status/figs/fig_c5b.png ppt/
```

**服务器**：`ssh A100`（~/.ssh/config 已配）；项目 `A100:/home/cunyuliu/rna-ft-eval`（代码）/ `A100:/mnt/cunyuliu/rna-ft-eval`（数据+ledger+图表）。

---

## 8. 接手人待办（若用户提新需求）

- [ ] AIDO 3e-05 formal 3 种子落地后（aido_close_monitor 自动收口）→ 更新 s5/s8 的 1.6B 数字为 3-seed 口径
- [ ] 预印本 v1.0（服务器 paper/preprint_v1.0.md）若后续修改 → 数字同步 PPT
- [ ] 用户偏好「结果展示」——新增内容优先图表化，每页一个结论

---

## 9. 1008 修订记录（七项问题处置）

- **13 页结构**（11+2）：s5=04b E4 泄漏交互新页、s11=09b E5 资源实测新页；其余沿用 11 页版式
- **换图 5 张**：fig_ppt_16arch（v2 四柱含 frozen）/ fig_ppt_a8_3task（三任务七模型）/ fig_ppt_ranksweep（v2 三面板）/ fig_ppt_c5b_v2（横轴数字+1.6B）/ fig_ppt_e3_curves（v2 含 3000 点）
- **新图 2 张**：fig_ppt_e4_delta / fig_ppt_e5_resources
- 图生成脚本（服务器 /tmp）：fig_1008c.py（16arch/a8/rank/c5b）+ fig_1008b.py（E3/等价线）+ fig_1008d.py（E4/E5）——数据全部直读 ledger
- 备份 ppt/work/before_fix_1008.pptx
- **坑**：图脚本 rid 过滤 `_ri` 子串会误杀 rinalmo/ribospan 前缀（产生全零图）；`_e310` 子串匹配误吃 `_e3100`——tag 匹配必须 `_` 分段
- 待办：E3 5000 档 + 300M 18 格落地后重刷 fig_ppt_e3_curves / fig_ppt_c5b_v2 并换图（数字同步改 banner）

## 10. 1009 二轮修订记录

- **14 页结构**（13+1）：新增 s11=09c 等价线探索页（fig_ppt_e3_equiv 交叉图）
- **换图 6 张**：fig_ppt_a8_3task（v3 数值+倍数）/ fig_ppt_ranksweep（v3 SSP+在飞标注）/ fig_ppt_why_opposite（两系归因）/ fig_ppt_e3_3tasks（三任务并排）/ fig_ppt_e5_resources（v3 重画）/ fig_ppt_e6_spectrum（v3 重画）
- **图生成脚本**（服务器 /tmp）：fig_1009.py（A8/rank/E5/E6）+ fig_1009b.py（why_opposite/E3 三任务/等价线）
- **用户批注已处置**：s5「没看懂」/ s9「不要加 aido」（why_opposite 改 RiNALMo 官方系）/ s12「太丑」（E5 重画）——批注框已删
- 备份 ppt/work/before_fix_1009.pptx
- 待办：78 runs（异架构 rank + MRL/m6A E3 + 30M/300M E3）落地后刷图

---

## 11. 1014 关机后修订记录（用户第 5 轮问题 + 等价线拆页 + 备份核验）

> 本轮在集群关机、仅备份盘（orico）可用的条件下完成。数据源 = orico 备份 ledger（2236 行，md5 与服务器一致）——纪律第四条（数字写入前过 ledger 原始行）全程执行。

### 11.1 用户 6 项问题处置总账

| # | 用户问题 | 处置 |
|---|---|---|
| 1 | s4「崩溃的是新家族分类头」结论怎么得出的，图上看不出来 | **证据链核验**：fam_umap_en.json（备份在案）——sil family 0.045→0.460 / random 0.121→0.527 数值无误。原表述是 0916 的推断（sil↑ + 新家族 ACC↓ 联合推出），但**图本身只显示聚类，不显示分类头**。已改写副题+banner 为显式证据链表述：「表征未坍缩（sil↑）+ 新家族 ACC 崩（0.06-0.10）⇒ 崩溃在决策边界」，读法写明「左=pre 右=post、上=random 下=family」 |
| 2 | 结论③图 Rank4/Rank16 是否还没跑完 | **ledger 审计**：ncRNA/SSP 面板 4 官方模型 r4/r16 全齐（24/24）；**m6A 面板 ERNIE/RNA-FM/SpliceBERT 的 r4/r16 从未入队**（只有 micro 有 6 行）——图无缺口是因 m6A 面板只画了 micro。补测方案见 §11.3-A |
| 3 | 结论⑤C 等价线图太丑 + 下方大片空白，拆成两张 | **已拆**：s12=⑤c-1 高预算档（fig_ppt_e3_equiv_high.png，ncRNA/MRL/m6A 三对）、新 s13=⑤c-2 低预算档（fig_ppt_e3_equiv_low.png，MRL+Sc-10M 两对）；数据直读备份 ledger 重画，值域独立、端点外置、胜负标注；嵌入 MD5 双验证通过 |
| 4 | 结论⑤B/⑥ 要不要补其他官方模型 | **评估结论：值得补但属 v2**——E5 资源页已覆盖 21 模型无需补；E6 遗忘轴目前仅 RiNALMo 三档 + 受控系（预注册口径），补 ERNIE/RNA-FM/NB 官方臂 = 54 runs ≈ 25-40 GPU 时，可把「LoRA 遗忘 < full」从 8 模型升到 11 模型。补测方案见 §11.3-B（用户说现在没时间，留给后人） |
| 5 | 备份数据能否支持结论复现 | **核验通过**（详 §11.2）：ledger/artifacts/status/代码/图全在；缺口 = 权重不在备份盘（HF 可重下 10 个 + RNA-Sc 7 ckpt 需老集群/机理篇 + HydraRNA 需作者）——数据表、统计、全部图表可复现，重跑训练需先恢复权重（恢复指南 §三） |
| 6 | 每页文字图片互相匹配检查 | **全 17 页逐页对账**，修正 4 处真实错误：s3 副题崩溃带范围 0.06–0.21 → 0.06–0.13 + 3 部分逃逸（0.15/0.21/0.53，v1.0 口径）；s7 banner SSP 架构差 0.17-0.24 → 0.17-0.35（ERNIE 0.33-0.35 漏写）；s11 banner「mega frozen 常值 0.72 / 650M frozen 0.65」误用全量档值 → 改 e3 车道真值 0.74→0.80 / 0.83-0.85；s15 页脚 1916→2232 runs + 在飞补测口径刷新。布局零越界零重叠、全 YaHei、lint PASS |

### 11.2 备份复现能力核验（orico 盘实测）

| 结论 | 所需数据 | 备份状态 |
|---|---|---|
| ①16 架构崩溃带 | c4_table.csv + ledger | ✅ 可复现（图表脚本在 code_git/rnafteval/figures.py 等） |
| ②LR 陷阱（A8） | ledger lr 网格行 + lr_grid_table | ✅ 可复现 |
| ③PEFT+rank | ledger r4/r8/r16 行 | ✅ 可复现（m6A 异架构 r4/r16 需补跑，见 11.3-A） |
| ④等价线双系 | c4_table + e3 行 + b59 行 | ✅ 可复现（新拆两图脚本：ppt/work/fix_1014/fig_equiv_split.py） |
| ⑤标注预算/过渡带 | ledger e3 全行 | ✅ 可复现（mega full e31000/5000 仅 1 种子、650M lora e31000 3 格 pending 关机中断——恢复后可补齐） |
| ⑤b 资源 | resources_costbenefit.csv | ✅ 可复现（21 模型全在） |
| ⑥遗忘 87 格 | e6_table + e6_official_table | ✅ 可复现 |
| 机制 t-SNE | fam_umap_en.json + png | ✅ 可复现（坐标+sil 全在） |
| 重跑训练本身 | 模型权重 | ⚠️ 部分可复现：HF 10 模型可镜像重下；RNA-Sc 7 ckpt（14G）在老集群 /mnt/cunyuliu/rna-sc（关机，恢复指南 §3c）；HydraRNA 需向作者索取；NB 在 Zenodo |

### 11.3 后续补测方案（用户指示「现在没时间，后续让别人补」）

**A. rank sweep m6A 面板补格（结论③完整性）**
- 缺口：ERNIE-RNA / RNA-FM / SpliceBERT × modification × lora × r{4,16} × 3 种子 = 18 runs（ncRNA/SSP 面板已齐）
- 队列模板：q_fill.py + p2_plan（照抄 1009 异构 rank 计划格式，只换 task=modification）
- 预算：≤6 GPU 时（m6A lora 单 run ~10min）
- 落地后：fig_ppt_ranksweep 的 m6A 面板从 micro 单模型升 4 模型；banner「m6A 0.90-0.99」复核

**B. E6 官方模型遗忘臂扩展（结论⑥普适性）——推荐**
- 现状：E6 仅 RiNALMo 三档（预注册范围）；受控系 6 档
- 补法：ERNIE-RNA(86M) / RNA-FM(96M) / NucleicBERT(404M) × {lora@3e-4, full@grid-best} × ncRNA 起点微调 × 3 种子 = 18 runs + S0 前后评（e6_forget.py 现成）
- 预算：~25-40 GPU 时（参照 micro full 2591s / lora 2040s 中位）
- 价值：LoRA 遗忘优势从「RiNALMo 家族 + 受控系」升到跨架构 4 官方家族——审稿人最可能问的「是否 RiNALMo 特有」直接封死
- 口径注意：属 v2 扩展（spec §10.3 之外），PPT banner 需如实标「v2 扩展臂」；NB full 用 tuned 1e-05（默认 LR 崩溃格不得入图——spec §10.7-⑪ 纪律）
- 图更新：fig_ppt_e6_official_v2 增行；PPT s14 换图 + banner 去「其他官方模型属 v2 未预注册」句

**C. 1016 尾格 34（已登记恢复指南，此处不重复）**

### 11.4 本轮工程记录

- 拆页方法：python-pptx 深拷贝 s12 全部 shape 到新 slide + `_sldIdLst.insert(12)` 控位——新页继承原版式（26pt 标题/15pt 副题/12.5pt banner），无需重排版
- 新图脚本：`ppt/work/fix_1014/fig_equiv_split.py`（数据断言防全零假图；中文字体 PingFang HK/Arial Unicode MS——Mac 本地渲染注意字体回退）
- 备份：work/before_fix_1014b.pptx（修改前 16 页版，CRC OK）
- 终态：**17 页**（16→17：⑤c 拆两页）；lint PASS；CRC PASS；两新图嵌入 MD5 验证通过
- 批注处置留痕：s3「迁移和微调都做了？」→ 是（图含 frozen+微调四柱），处置 = 删批注（图已自答）；s13/s14「要不要补其他模型」→ 评估入 §11.3，处置 = 删批注

## 12. 2026-10-26 导师讨论版续接

1. 当前主文件为 20 页，但第 7 页只展示 SpliceAI、degradation、SSI 三个新增任务；不得称“8 任务实验已补齐”。最新 spec §10.15 / tasks v3.28 为唯一新补测计划。
2. 8 任务以 spec §10.16 的官方语义为准：ncRNA/CRISPR/modification 为序列级分类，MRL 为序列级回归，SpliceAI/SSP 为碱基级分类，degradation/SSI 为碱基级回归。旧稿的 m6A per-base 与 CRISPR 连续值口径均不沿用。
3. 本轮先在原第 3 页后插入任务地图；结论①a 后放任务扩展图。其他页不重建，保留手调框架。批注框执行后移除，说明文字需区分已验证结果、间接证据和待复核假设。
4. 新补测以真实 held-out validation 为准；过拟合分支使用 `_bestval_v1`，保存并恢复最佳 checkpoint，result/plateau/ledger/runtime 必须一致。342 格只覆盖 SpliceAI/degradation/SSI，不是全 8 任务完成证明。
5. 旧 PPT 的图 4 等价线有跨家族/跨任务混用风险，图 8 机制标题把 t-SNE+ACC 的间接推断写成已直接定位。刷新前必须回到真实 ledger/result 和协议标签，不沿用 PPT 内数字作为数据源。
6. t-SNE 参考 RiNALMo 论文 Fig.2：使用分类 token/CLS 表征、真实家族标签着色和独立测试集合；本课题另保留预测头前 embedding，并补 pre/Post-LoRA/Post-full 对照。不能把 t-SNE 距离直接解释为机制因果。
7. 新增图统一四柱语义：浅蓝 frozen-random、灰蓝 frozen-family、浅橙微调-random、深橙微调-family；每任务单列主指标，避免 ACC/AUC/PCC/F1 混为“分数”。
8. 阶段交付优先输出独立修订版，不覆盖原始文件。每次保存后做 XML/zip、markitdown、layout、LibreOffice 渲染和嵌图校验；最终原数据、图脚本、协议清单与 PPT 同源交付。

### 12.1 本轮阶段交付（2026-10-26）

- 修订版 PPT 共 21 页：原第 3 页后新增“8 任务地图”，结论①a 后保留三任务阶段性扩展页。MRL/m6A 改为与结论①一致的四柱图；结论④改为 RNA-Sc/RiNALMo 同源规模分面，区分参数量与数据量。
- 机制页改为相关性证据和待检验假设，未把 t-SNE+ACC 直接写成分类头因果结论；资源、C5 和总结页统一为条件化推荐。旧批注和重复旧文字层已移除，原始 PPT 未覆盖。
- `validate_layout.py` 全 21 页 Issues=0；`pptx_lint.py` PASS；zip CRC 正常；新图嵌入 MD5 一致；LibreOffice 在独立 CJK fontconfig 下实际渲染中文正常。全 PPT XML 字体为 Microsoft YaHei，正文行距 1.5。
- 同源/四柱图数据见 `绘图数据索引_20261026.md`。三任务扩展原始表仍待远程回源，未将图片识别数字作为原始实验数据。
- 8 任务完整补测、三策略 t-SNE、33M rank8 复核、MRL/m6A 扩模型、同源 n↔m 等价线、C5b/C5c/C5d 补齐仍未完成；待远程恢复后按 tasks v3.28 执行，不以本次 PPT 修订替代实验完成。

### 12.2 rank8 与 MRL 正式结果更新（2026-10-27）

- RiNALMo-micro rank8 已完成 random/family × 3 seeds 六格三层验收：random ACC=0.918026±0.009421，family ACC=0.900312±0.005268。旧低值未复现，但差异原因仍需与旧 checkpoint/数据协议对照，不归因于 33M 本身。
- MRL micro LoRA/full × 双 split × 3 seeds 共 12 格通过三层验收：LoRA random 0.803926、family 0.711024；full random 0.799254、family 0.702377。仅限 micro，不提前推广为跨模型“MRL 不坍缩”。
- 结论③页已换为 `rank_review.png`：新增 ncRNA rank8 best-val 面板，SSP/MRL legacy rank 扫描按精确 RID 回源 108 条、36 组完整三种子；m6A 旧 per-base 数值不再显示，改为隔离占位。新旧协议没有混均值。
- 整份 markitdown diff 仅结论③页变化；该页 `validate_layout.py` Issues=0、PPTX CRC 正常、LibreOffice 实际渲染无溢出/乱码。其他用户手调页面未改。
- 原图与旧媒体已归档到 `ppt_work/replaced_media/`，新图、源 CSV/JSON、生成脚本与 PPT 均已保留。完整 8 任务、机制 post 和 C2–C5 仍未收口，当前文件是导师讨论版而非最终科学终版。

### 12.3 random 三状态机制图更新（2026-10-27）

- ncRNA random 的 pre / Post-LoRA / Post-full 已在同一 757 条 test 上完成联合 CLS t-SNE；高维 silhouette 依次为 0.026 / 0.239 / 0.608。该结果仅说明表示聚类增强，不等于跨家族泛化提升，也不直接证明分类头因果。
- 演示顺序第 9 页已替换为 `mechanism_ncrna_random_cls.png`，图注注明联合投影、perplexity=30、random_state=17、每状态 n=757；head.pool 图和逐点坐标保留为补充证据。family 与其余 7 任务仍在补测，不在本页提前写成完成。
- 第三轮视觉检查修正了图片框宽高比，按原图 4227×1384 等比例嵌入，并修正“三点按”为“三面板”。最终 `validate_layout.py --slides 9` Issues=0、ZIP CRC 正常、21 页 LibreOffice 实际渲染无溢出或乱码。
- 全稿 markitdown diff 仅第 9 页变化；包级 CRC 仅 `slide8.xml`、对应 rels 和替换媒体变化，其他页面未改。上一版保存为 `ppt_work/deck_before_mechanism.pptx`，旧图仍在 `ppt_work/replaced_media/`。该阶段 PPT SHA256=`774706ba483def3d2165d074fba518ce9d66f9bbd0659380f80511207b8bbb65`。

### 12.4 ncRNA 双 split 三状态机制页（2026-10-27）

- family 三状态已在同一 856 条 test 上完成，pre/LoRA/full 的 manifest hash 一致、cluster 三方隔离，post 均恢复 best-val 且 checkpoint proof=ok。CLS 高维 silhouette 为 0.023/0.242/0.589；与 random 的 0.026/0.239/0.608 并列展示，仍只作描述性诊断。
- 第 9 页升级为 `mechanism_ncrna_split_compare.png`：上排 random（757/state），下排 family（856/state）。每个 split 内对三状态联合拟合，两个 split 独立投影，不共享或混写坐标；其余 7 任务仍明确标为待补。
- 图由 `figure_source_data/build_mechanism_compare.py` 从两组逐点坐标 CSV 生成，PNG/PDF、源坐标和 `mechanism_ncrna_split_compare_metadata.json` 均保留。图片按 4189×1642 原比例嵌入。
- 最终 `validate_layout.py --slides 9` Issues=0、21 页渲染与 ZIP CRC 正常；markitdown 和包级 diff 仍仅第 9 页及其 rels/媒体变化。random-only 上一版保存为 `ppt_work/deck_before_splitcompare.pptx`。最终 PPT SHA256=`9755240876a6e50e01d30e5a8b3bdd945e00a378e9c7adb5c28d32768cd82a6b`。
- PPT、双 split 图、逐点坐标、绘图脚本和交接文档已备份到 `/teams/HoulabData_1788502323/liucunyu/rna-ft-eval/delivery/20261027/`；原始包另存 `backups/rnaft_delivery_20261027.tar.gz`，包 SHA256=`9b92b2b1224140b53b88a94119a9629dafd135889a75c0ba976698295dac30c4`，远程 PPT 哈希与本地一致。

### 12.5 MRL 双 split 机制页（2026-10-27）

- MRL random/family 各 seed17 三状态复用 micro best-val checkpoint，完整 test 分别为 7600/9150 条。LoRA/full 的 full-test Pearson r：random=0.803231225/0.801666645，family=0.720264749/0.694011763，均与源 result 对账通过；不重训源模型。
- 在 ncRNA 机制页后插入 MRL 机制页，演示顺序第 10 页，全稿 22 页。图为 `mechanism_mrl_split_compare.png`，每状态 1024 条，按 sequence hash 在预测前固定抽样；颜色为连续 true MRL，post 标注 full-test r，pre 不展示随机参考头性能，不计算分类 silhouette。
- `add_slide.py` 生成 slide22 后插入原 slide8 之后。新增页阶段的包级 diff 仅 `[Content_Types].xml`、presentation/rels 和新增 slide22/rels/MRL 媒体；后续仅将 ncRNA 页“其余 7 任务”同步为“其余 6 任务”。`validate_layout.py --slides 9,10,11` Issues=0、ZIP CRC 和 22 页实际渲染通过。
- 第一次渲染发现右上角 MRL 标签换行，已加宽标签框并保持右边界不变，再次渲染通过。最终 PPT SHA256=`b323a453961f140fc1d7c818e33654389942bf02f126eb8d743a9f4290a66705`。
- MRL 双 split 图、单 split CLS/head 图、逐点坐标、metadata、修复 manifest 和交接文档继续备份到 `/teams/HoulabData_1788502323/liucunyu/rna-ft-eval/delivery/20261027/`。其余 6 个任务的机制诊断仍未完成，不把本页写成 8 任务完成。

### 12.6 modification/m6A 双 split 机制页（2026-10-27）

- modification random/family 各 seed17 三状态复用 micro best-val checkpoint，完整 test 为 1200/30904 条。random LoRA/full m6A AUC=0.985530435/0.972017391，family=0.942003028/0.938341444，均与源 result 对账通过。
- 在 MRL 页后插入 m6A 机制页，演示顺序第 11 页，全稿 23 页。每状态 1024 条，m6A 阳性 random=45、family=202；图只展示索引 7 的标签视图，不把 12 个独立标签改成 softmax 单分类，也不计算分类 silhouette。
- 新增 slide23、对应 rels 和 modification 媒体；ncRNA 页仅将剩余任务数从 6 改为 5，其他 slide XML 未改。`validate_layout.py --slides 9,10,11,12` Issues=0、ZIP CRC 和 23 页实际渲染通过。最终 PPT SHA256=`07bb559d1b75c1c88b25328a5f7867275f8113d580e028c569b455a2b28983dd`。
- 原始 12 维 labels/logits/probabilities、valid mask、source-compatible mean AUC、valid-only mean AUC、source run_id、逐点坐标和 metadata 均保留。其余 5 个任务的机制诊断继续执行，不把本页写成全任务或其他模型“免疫”的证据。

### 12.7 CRISPR 双 split 机制页（2026-10-27）

- CRISPR random/family 各 seed17 三状态复用 micro best-val checkpoint，完整 test 为 3586/1933 条。random LoRA/full PR-AUC=0.653180944/0.057878348，family=0.598625327/0.112742613，均与源 result 对账通过；full 低值保留，不归因于测评失败。
- 在 m6A 页后插入 CRISPR 机制页，演示顺序第 12 页，全稿 24 页。每状态 1024 条，正例 27/11；正例富集只用于显示，PR-AUC/ROC-AUC 只使用完整 test，不展示 sampled 患病率或 sampled PR-AUC。
- 新增 slide24、对应 rels 和 CRISPR 媒体；ncRNA 页仅将剩余任务数从 5 改为 4。首次布局校验发现 CRISPR 标签约超宽 2pt，已加宽至 1.25 英寸并保持右边界不变。最终 `validate_layout.py --slides 9,10,11,12,13` Issues=0、ZIP CRC 和 24 页实际渲染通过。
- family 仅标为 pair-sequence cluster split，不宣称 guide-disjoint；t-SNE 不作因果证明。最终 PPT SHA256=`61adb426dd6957c1f7aa97cdaedcee2e7e6c5a3134fea2394859f73a82462e77`。其余 4 个任务的机制诊断继续执行。

### 12.8 SSP 双 split 机制页（2026-10-27）

- SSP random/family 各 seed17 三状态复用 complete best-val checkpoint。random 完整 reconstructed test 为 400 条序列、3,127,446 个 pair，LoRA/full pair-F1=0.1872/0.1605；family 为 2,966,351 个 pair，LoRA/full=0.1834/0.2122。precision/recall、validation threshold 和 val_f1 均与源 result 对账通过。
- 在 CRISPR 页后插入 SSP 机制页，演示顺序第 13 页，全稿 25 页。每状态 1,024 个 pair，unpaired/paired 各 512，均衡只用于显示；图使用真实 PairHead 输入，不用 CLS，不展示 sampled F1 或分类 silhouette。页面文案仅限定 seed17：random 上 LoRA 略高，family 上 full 更高，不写成普遍规律。
- 双 split 图为 `mechanism_ssp_split_compare.png`，由 `figure_source_data/build_mechanism_ssp_compare.py` 从 random/family 逐 pair CSV 生成。坐标、metadata、三状态 diagnostic、test manifest 和 aligned NPZ 均保留。新增 slide25、rId31、对应 rels 和 SSP 媒体；原 24 个 slide XML 与 rels 经去空白 XML canonicalization 复核均语义一致，未覆盖用户手调内容。
- 首次结构检查发现页面追加位置错误，已调整为 CRISPR 后第 13 页；首次渲染发现当前环境 CJK 字体映射缺字，改用工作区独立 fontconfig 后通过。最终 ZIP CRC、25 页 PDF、关键中文文本、1.5 倍行距和 Microsoft YaHei 检查通过，图片与页脚间隔 133,405 EMU。SSP 初版 PPT SHA256=`71d86a267c29cdc1345cc3e4286be037c4aaae4df1283748b309f5b2a2e70c25`。PPT、PDF、双 split 图、metadata、生成脚本和交接文档已备份至 `/teams/HoulabData_1788502323/liucunyu/rna-ft-eval/delivery/20261027/`，远端 PPT 哈希一致。其余 3 个任务的机制诊断继续执行。
- 后续仅同步 ncRNA 机制页的剩余任务数：副标题和页脚均由“其余 4 任务”改为“其余 3 任务”。打包前后除 `ppt/slides/slide8.xml` 外所有包条目逐字节一致；ZIP CRC、25 页 PDF、第 9/13 页实际渲染、字体与行距复核通过。当时 PPT SHA256=`66ca40e7a36dd515c5e55c604c69b770a5dbb9c1b8d8b0ea12d51b79d66f79bc`，已重新备份至 `/teams/.../delivery/20261027/`，远端哈希一致。

### 12.9 degradation 双 split 机制页（2026-10-27）

- degradation random/family 六状态已完成。random 完整 test=431 条序列、29,308 token，LoRA/full PCC=0.541539/0.546761、MCRMSE=0.614810/0.613951；family=238 条、16,184 token，PCC=0.396906/0.402725、MCRMSE=0.817258/0.816726。post 均恢复 best-val 并通过 full-test 对账，结果仅限定 seed17。
- 在 SSP 页后插入 degradation 机制页，演示顺序第 14 页，全稿 26 页。每状态 1,024 个连续未分箱 token，颜色为 `deg_Mg_pH10`；双 split 共用 1–99 百分位显示色轴，极值饱和并保留 raw range，不计算分类 silhouette。副标题仅陈述本次 full 在双 split 的 PCC 均略高于 LoRA，不扩写为普遍规律。
- 新增 `add_mechanism_slide.py` 支持任务完成后按语义顺序插入：degradation 可先行交付，后续 SpliceAI 会插到它前面，SSI 插到它后面，不重排或覆盖用户已有页面。新增 slide26/rId32 与媒体；除 presentation、rels、content types、slide8 计数及新增文件外，原有包条目逐字节不变。
- ncRNA 页副标题和页脚的剩余任务数由 3 改为 2。ZIP CRC、26 页 PDF、第 9/14 页实际渲染、Microsoft YaHei、1.5 倍行距、图例/色轴/指标匹配均通过。当时 26 页 PPT SHA256=`e2b1c34bfb4187e5410f52040060c38a136a456a7305dcc6a770bb9460943143`。

### 12.10 SSI 双 split 机制页（2026-10-27）

- SSI random/family 六状态已完成。random 为 3,095 条记录、3,093 个唯一序列、309,500 个有效 token，LoRA/full PCC=0.635054/0.633023、MCRMSE=0.213841/0.213037；family 为 1,881 条、188,100 token，PCC=0.598604/0.598510、MCRMSE=0.216958/0.216982。均通过 full-test、checkpoint 与 split 证据对账，结果仅限定 seed17。
- 在 degradation 页后插入 SSI 机制页，演示顺序第 15 页，全稿 27 页。每状态 1,024 个连续 `struct_true` token，双 split 共用 0–1 色轴，不计算分类 silhouette。副标题仅说明本次 LoRA 与 full 接近，不宣称三种子一致或机制等价。random 的同序列不同标签记录保留 record-level identity，family cluster 三方零重叠。
- 新增 slide27/rId33 与媒体；ncRNA 页剩余任务数由 2 改为 1。除 presentation、rels、content types、slide8 与新增文件外，原有包条目逐字节不变。ZIP CRC、27 页 PDF、第 9/14/15 页实际渲染、Microsoft YaHei、1.5 倍行距和图文匹配均通过。当时 27 页 PPT SHA256=`ef96a2ed51ac661baea0cb4cc9f9e0cef95d2c82ba086aa8aace97cb3499849c`。

### 12.11 SpliceAI 与 8 任务机制图闭环（2026-10-27）

- SpliceAI random/family 六状态已完成。random 完整 test=15,642 条序列、1,564,200 token，LoRA/full macro-F1=0.431162/0.349766、micro-F1=0.999664/0.999655；family=17,079 条、1,707,900 token，macro-F1=0.490382/0.450522、micro-F1=0.999681/0.999691。macro/micro 均与源 result 对账，ROC-AUC 仅作辅助。结果仅限定 seed17。
- 在 SSP 后、degradation 前插入 SpliceAI 机制页，演示顺序第 14 页；degradation/SSI 顺延为第 15/16 页，全稿 28 页。每状态 random 1,058、family 1,056 个 token，negative/acceptor/donor 类别语义与 B20 base/token 位置均已核验。类别均衡仅用于显示，pre 为 seed201 参考头。
- 新增 slide28/rId34 与媒体。ncRNA 页改为“8 任务机制图已补齐（seed17）”，页脚保留 sequence/token/pair 输出语义边界。首次渲染发现副标题换行裁切，已缩短为单行并复核；第 9、14、15、16 页实际渲染、ZIP CRC、28 页 PDF、Microsoft YaHei、1.5 倍行距和图文匹配均通过。当前 PPT SHA256=`26a6fdd7b030bd3789ffa83952ec20a8df59d4f7e08e18665186f7f1fd5878e2`。
- 至此 8 任务双 split 三状态机制图全部完成。该闭环只覆盖 RiNALMo-micro、seed17 的描述性诊断，不替代结论②–⑤的三种子、学习率、rank、数据量与成本矩阵，也不把 t-SNE 结构解释为机制因果。

## 13. 2026-10-28 本轮续接基底与页面边界

1. 用户指定的本地 `ppt/RNA_LM微调策略评测-结果版.pptx` 修改时间为 2026-10-26 21:47:23，共 20 页，SHA256=`464171622dd75d3946f0d4aa0fea18c78c9531bfc362febd6110e752b3c1faf9`；它早于 §12 的 28 页阶段交付，不能覆盖或回滚后续机制页。
2. 当前续接基底为 `/teams/HoulabData_1788502323/liucunyu/rna-ft-eval/delivery/20261027/RNA_LM微调策略评测-导师讨论修订版.pptx`，共 28 页，SHA256=`26a6fdd7b030bd3789ffa83952ec20a8df59d4f7e08e18665186f7f1fd5878e2`。其中第 4 页已是 8 任务地图，第 8 页已是三任务阶段扩展，第 9–16 页已是 8 任务双 split 三状态机制图；不得重复新增。
3. 任务地图必须维持官方语义：序列级分类 3（ncRNA/CRISPR/modification）、序列级回归 1（MRL）、碱基级分类 2（SpliceAI/SSP）、碱基级回归 2（degradation/SSI）。SSP 当前实现为 pair-level 碱基对预测，页面不得写成“逐碱基结构状态”；modification 的 m6A 为索引 7，不写成容易误解的“第 7 个标签”。
4. 结论③的 micro rank8 六格已经验收，不再重跑；结论②、③、④、⑤、⑤b、⑤c、⑤d 的完整 8 任务图仍须等待同协议正式矩阵。阶段版只呈现已有证据并明确待补范围，不能把 pending 画成 0、不能用 legacy 点填空、不能把不同主指标合成统一分数。
5. 每次只修改目标页；其他页面沿用用户手调内容。正文保持 Microsoft YaHei 与 1.5 倍行距，表格按既定紧凑排版。交付独立修订版，保留原始 20 页与 28 页基底及其哈希。
6. 所有替换图须同时保存原始 CSV/JSON、RID/result 路径、协议代际、绘图脚本、PNG/PDF 与 metadata；旧图和废弃源数据先核引用后归档，不删除实验证据。

## 14. 2026-10-28 最终阶段交付与验收

1. 最终文件为 `RNA_LM微调策略评测-导师讨论修订版_20261028.pptx`，共 28 页，SHA256=`09853a8cec9557b3b50400e6580527e82909a894d1a13396aa3e0731f7e336b5`；同名 PDF 的 SHA256=`1d44603aecd83ed3337ced7ccde8e08301e868855b5d78afc2ff880095fb8ce9`。用户原 20 页文件和 28 页基底均未覆盖。
2. 共替换 10 张图：modification/MRL best-val 四柱、三任务扩展、ncRNA/MRL Δ、LR、E3、两张数据量等价图、ncRNA 显存、MRL 时间×性能。18:10 数据刷新后 micro modification LoRA 6/6 已入图，mega 的 n<3 与其余 NA 按真实 proof 显示。
3. 任务地图 SSP 改为 pair-level/pair-F1，modification 写明索引 7；结论②③④⑤与进度页明确历史矩阵、当前扩展和未闭合项。高低预算图直接标 full(n)/LoRA(m)，资源图明确 ncRNA legacy 与 MRL best-val 不跨协议比较。
4. 验收：编辑页 `validate_layout.py` Issues=0；28 页 PDF 实际渲染无中文缺字；PPT 全部可编辑文本为 Microsoft YaHei、非空段落 1.5 倍行距；ZIP CRC 正常；10 张嵌图与源 PNG 哈希一致；文本 diff 仅包含预期页 2/4/6/7/8/14/15/16/17/18/19/21/22/23/24/25/27/28，其他页未改。
5. 任务地图卡片曾两次出现最后一行裁切，最终仅将左上卡片标题降 1pt、说明文字降 1pt并调整文本框，第三轮渲染完整可见。其余卡片未改。
6. 绘图源数据包为 `figure_source_data_20261028/`，共 74 个文件，manifest SHA256=`a06973d93f314089f666bb5a076867f042e49eadb861f561a10b82d2994b6ce9`。参数化脚本 `plot_report_20261028.py` 已提交 `/home` `b768006` 并上传 GitHub 扩展分支 `2ab81ab225c59bf4ec551adea7d09365df31680e`。
7. 当前文件是导师讨论阶段版，不代表结论②③④⑤、C5b/C5c/C5d 的完整 8 任务矩阵已收口。后续新结果须先过三轮 result/ledger/proof 对账，再按本文件 §13–14 增量更新，禁止把旧归档 m6A 或 official E6 数值带回。

## 15. 2026-10-29 ncRNA 训练顺序事故修订版

1. 新交付文件为 `RNA_LM微调策略评测-导师讨论修订版_20261028_夜间复核.pptx`，共 28 页，SHA256=`536b5e4ae5477aed06e07530f772e5b3691f544c4fbfa042fa43fcae04039b9b`；同名 PDF SHA256=`e7a7df980f836b2b7a8daa069f6d81e92326d1c7ba3b8d5a9e4163c583669873`。未覆盖 §14 的 28 页基底或用户 20 页文件。
2. 严格 `finetune_one/max_len512` A/B 证明：在模型、任务、family split、LoRA rank8、LR、batch、seed 和 best-val 均一致时，仅关闭逐 epoch shuffle 即将 ACC 从 0.894860 降为 0.095794。第 5 页改为标签顺序、validation 曲线和 test ACC 三联图；旧 pre-shuffle ncRNA family 及其 Δ、E3、规模谱和等价点全部撤下，不再跨页引用。
3. 第 17、21、23、24 页仅保留明确标注的 MRL legacy 描述；第 20 页改为 full(n)↔LoRA(m) 比较协议图，不画虚构等价曲线；第 22 页改为旧点隔离与补测状态表。第 19 页 rank8 从“旧低值未复现”更新为“严格 A/B 已定位训练顺序伪影”。进度页 E1/E2/E3/E4/1014 同步去除旧结论残留，并恢复八任务行在页内完整可见。
4. 任务地图、8 个机制页及其他用户手调内容未改。未修改页 XML 与 rels 逐文件 diff 为空；实际编辑的 XML slide 为 2/4/6/9/11/12/13/14/15/16/19/20，对应演示页 2/5/7/17/19/20/21/22/23/24/27/28。
5. 验收完成：`validate_layout.py` 编辑页 Issues=0；`pptx_lint.py` PASS；`fix_pptx.py` 无问题；markitdown 逐页内容复核通过；7 张嵌图与源 PNG 哈希一致；独立 fontconfig + Microsoft YaHei 实际 PDF 渲染中文正常；图框宽高比与页码框已二次校正。正文 1.5 倍行距和微软雅黑保持不变。
6. 新版源包 revision=`20261029_ncrna_shuffle_quarantine_v1`，现有 95 个登记文件并全部哈希通过，manifest SHA256=`286e19cdd66812ad918c367a66ac1b77952a6e303077b3c76ee3e5daf57ee81b`。严格 A/B 原始 JSON、曲线、标签顺序、图源 CSV、脚本、旧图隔离副本和基线 manifest 均已保存；另保存 320 个唯一 RID 的 best-val 原始台账和 ERNIE-RNA 18 格统计表，4 个 smoke 拒绝项单列。当前仍为阶段讨论版，八任务结论②③④⑤及 C5b/C5c/C5d 继续按实时 proof 补测，不宣称全量完成。

## 16. 2026-10-29 六柱扩展与⑤d状态校正

1. 当前交付为 `RNA_LM微调策略评测-导师讨论修订版_20261029_六柱扩展与状态校正.pptx`，共29页，SHA256=`acbb01c5ba4b501eb492ee885ca6e2b20367cefb781238f655221c0e98be6157`；同名 PDF SHA256=`0c2afab83ba9331ff836e599dff5d3f9be9e137b98207f46e5e30b0a0b4651ea`。此前20页、28页和29页版本均未覆盖。
2. 仅修改演示页2、8、23。第8页以 frozen/LoRA/full × random/family 六柱替代混合微调四柱，数值标签碰撞已二次修复；第23页图内状态和页脚同步为33M/148M random×LoRA 五档已闭合，其余臂仍待补。其他 slide XML/rels 语义无差异。
3. `fix_pptx`、编辑页 layout Issues=0、markitdown、ZIP CRC、嵌图哈希、Microsoft YaHei、1.5倍行距与29页独立 fontconfig 渲染均通过。六柱图18行108单元对账通过，源包 v11 共101文件哈希通过，旧四柱图及源表已归档。
4. 本版仍是阶段讨论版，不替代结论②③④⑤及⑤b/⑤c/⑤d 的8任务正式矩阵。绘图代码已推送 GitHub `7a24117`；teams v11 同步和实时训练 proof 待 SSH 恢复后执行。

## 17. 2026-10-29 数值等价线更新

1. 当前交付为 `RNA_LM微调策略评测-导师讨论修订版_20261029_等价线更新.pptx`，共29页，SHA256=`3a7d737706fbaae9fe36cd746b1d18675af7ce1b2be656c8716b315cbd784d18`；PDF SHA256=`1f3789308f5d13e10773bc21f9bb6fd6b0f4826cb1693812b4e1694c81b6415a`。仅修改第20页，其他slide XML/rels语义无差异。
2. 第20页由比较协议示意改为 ncRNA random 的真实五档等价图：full@2500≈LoRA@1500 为2/3 seeds最近，full@2000≈LoRA@1000 为1/3 seeds最近；标题、图内候选和页脚均明确“非唯一”，不插值、不外推其他任务或split。
3. 正式输入为400个accepted RID，旧385行不变，新15行为 micro-full 五档；30个等价源RID和逐seed配对独立复核通过。layout Issues=0、markitdown、29页Microsoft YaHei渲染、嵌图和源包104文件哈希通过；本地与teams重算的 data/pairs/meta 一致。
4. 绘图代码 `/home` commit=`f870f8c`、GitHub commit=`9aee3d4`，385 tests通过。其余7任务、family split、650M和其他 C5c 臂仍待补，本页不是8任务等价线终版。

## 18. 2026-10-30 续接与逐页复核

1. 现行续接文件仍为§17的29页等价线更新版，本地重新下载后SHA256=`3a7d737706fbaae9fe36cd746b1d18675af7ce1b2be656c8716b315cbd784d18`，与记录一致。用户20页文件保持原样，不覆盖、不回滚；任务地图、C5c五档页和8个机制页不重复插入。
2. 已对29页逐页核对标题、图、读图句、关键数值与前后文；任务地图与后续任务/指标对应，机制页顺序为ncRNA、MRL、modification、CRISPR、SSP、SpliceAI、degradation、SSI，结论④与⑤c的局部等价/非等价表述没有混写。未发现需立即修改的图文错配。
3. 基线验收：markitdown全文提取通过；`validate_layout.py`全29页Issues=0；ZIP CRC正常，slide XML=29、media=25；使用独立fontconfig与Microsoft YaHei实际渲染PDF，中文正常，总览与分组高清图未见重叠、越界或裁切。
4. 机制方法已直接对照RiNALMo论文Fig.2：classification token embeddings + t-SNE + 真实标签/家族。现有页面保留各任务相应预测头输入、双split三状态、联合投影、样本数和full-test指标，只作描述性诊断，不补写因果结论。
5. 当前仍是阶段讨论版。结论②③④⑤及⑤b/⑤c/⑤d只在实时proof闭合后增量更新；其他用户手调内容不改。后续交付另存新文件并保留本版哈希，所有新图与源数据同步升revision。

## 19. 2026-10-30 MRL第7页与v13源包更新

1. 新交付为 `RNA_LM微调策略评测-导师讨论修订版_20261030_MRL更新.pptx`，共29页，SHA256=`6ce9554a2f56daad356a471ba3a442741daeeede8af195b6e4ce27bdc7ae7724`；同名PDF SHA256=`e86f2c6d4a48b7cc6599bf7febe422fb82d75df660b4237efbe8d74b5c166bb1`。仅改演示第7页，其他包条目逐字节/XML语义无差异。
2. best-val导出从400增至408 accepted；新增650M MRL frozen random seeds29/43，当前mean=0.731394、n=2。第7页沿用六柱图，650M frozen random以斜线显示，其余未闭合项仍NA；读图句明确n=2，未写成三颗种子或全模型结论。
3. 验收完成：fix_pptx、编辑页layout Issues=0、markitdown、项目pptx_lint PASS、ZIP CRC、嵌图SHA一致、29页独立fontconfig渲染与第7页高清视觉检查通过。全部文本run为Microsoft YaHei，非空段落1.5倍行距；包级diff仅slide6.xml和mrl_bestval_official_fourbar.png。
4. 源包revision=`20261030_bestval_408_mrl_n2_v13`，104个文件哈希全通过，manifest SHA256=`2e8234ed90d59d19fd8cf02be8ced38c65e508468ce9610c47ad9af27a2c7078`。旧400行、旧MRL表和旧图已归档到 `archive_20261028/绘图数据/bestval_400_v12_20261030/`；新版PPT/PDF和源包已备份至 `/teams/HoulabData_1788502323/liucunyu/rna-ft-eval/delivery/20261030/` 并逐文件验算。

## 20. 2026-10-30 夜间八任务扩展版（30 页）

1. **基底与交付**：以 §19 的 29 页 v13 版（SHA256=`6ce9554a2f56daad356a471ba3a442741daeeede8af195b6e4ce27bdc7ae7724`）为唯一基底增量修改，产出 `RNA_LM微调策略评测-导师讨论修订版_20261030_八任务扩展.pptx`，共 **30 页**，SHA256=`8a3ea9af835fba5a9d2647a9e9e1483bef08f0f0d0b0647fa6d033acbb5328ff`；同名 PDF SHA256=`152c046bdaa7f874d526c7209f5e67df5c296bb0f5ecec18f0f04552a61aa21d`。用户 20 页 `RNA_LM微调策略评测-结果版.pptx`（SHA256=`464171622dd75d3946f0d4aa0fea18c78c9531bfc362febd6110e752b3c1faf9`）保持原样，不覆盖、不回滚。
2. **为什么不是直接改 20 页文件**：20 页版是 10-26 的旧线，缺少已验收的任务地图页与 8 个机制页；29 页版本身是在同一 20 页基底上增量累积而来（§12–§19），已保留用户手调样式。直接在 20 页上重做会重复插入任务地图/机制页并丢失已验收页，故本轮沿 29 页线继续。
3. **修改范围（文本 diff 仅这些页）**：演示页 4（任务地图口径改为「4 类 = 3+1+2+2」并压缩首卡文案）、8（①a-4 换图换文）、18（②状态）、19（③状态）、21（⑤状态）、23（⑤d 换图）、26（⑤b-1 换图换文）；新增第 27 页（⑤b-2 显存）；原 27–29 顺延为 28–30，其中总结页（现第 29 页）证据范围一句同步更新。其余页面 XML 与图片未动。
4. **新图 4 张**（全部重新生成，源数据见 `figure_source_data_20261030/`）：
   - ①a-4 `eight_task_sixbar.png`：其余 5 任务（CRISPR/SpliceAI/SSP/degradation/SSI）× 5 官方模型 × 六柱；颜色/斜线/留白与 ①a-2/①a-3 一致，值标签仅在 n≥3 时显示。
   - ⑤b-1 `eight_task_time_perf.png`：8 任务 random split，形状=模型、颜色=策略，横轴中位 wall、纵轴任务主指标。
   - ⑤b-2 `peak_memory.png`：5 模型 × 3 策略跨 8 任务峰值中位 + min–max；24 GB 参考线。
   - ⑤d `bigmodel_coverage.png`：148M/650M 逐任务逐臂已完成种子数热图，0 = 未闭合。
5. **口径修正**：旧 ①a-4 三面板（B20 阶段表，含 NucleicBERT、NA 文本柱）与 §19 的「LoRA ≈ frozen 成本、650M full 超 24GB」表述按实测弃用；实测为 Frozen < LoRA < Full-FT（LoRA ≈ 2.4–3.3× Frozen、Full ≈ 1.5× LoRA），650M full 尚无 run。
6. **验收**：30 页 ZIP CRC 正常、layout 越界 0、全部文本 run 为 Microsoft YaHei、非空段落 1.5 倍行距、表格 1.15；独立 fontconfig + 微软雅黑实际渲染 30 页中文正常；图片按原始宽高比嵌入（①a-4 3754×1396、⑤b-1 3754×1396 近似、⑤b-2、⑤d）。页码框统一右对齐并按文字长度定宽，`02a/03a2/degradation/SpliceAI` 不再折行。
7. **源包**：`交接文档/绘图数据/current/figure_source_data_20261030_eight_task_v14/`，revision=`20261030_eight_task_expansion_v14`，17 个文件，manifest SHA256=`5c9ee9aa3da92360aa7996d357181e42f874087444050b3ab5fbc579d6938827`；生成脚本 `build_8task_sixbar.py`、`build_time_perf_coverage.py` 均为参数无关的本地可复现脚本（字体 `~/Library/Fonts/msyh.ttc`）；已在 `/home/cunyuliu/rna-ft-eval` 提交 `ad4c637` 并推送 GitHub `Cunyu-Liu/RNA_finetune_methods` 分支 `rnaft-expansion-20261027`（`b14b1c3` / `e14aaed`）。
8. **边界**：本版仍是阶段讨论版。①a-4 中 SpliceAI/degradation/SSI 的 LoRA/full 仅 seed17；②③⑤ 的 8 任务正式矩阵仍未闭合；⑤d 只陈述覆盖；不得把本版当作 8 任务全部完成的证明。

## 21. 2026-10-31 数据刷新与 ⑤d 口径校正

1. **台账**：`bestval_ledger_export_20261031.csv` 由 `scripts/export_bestval_delta.py` 生成（408 已验收基座 + 95 增量 = **503 accepted**，0 rejected）。增量导出只对新 done 行做 artifact 存在性与 metric 校验，不重复加载 408 个 checkpoint；全量 `export_bestval.py` 仍在后台跑，用于最终冻结。
2. **图刷新**：①a-4 六柱、⑤d 覆盖热图、⑤b-1 时间×性能、⑤b-2 显存四张图全部按 **全量证明导出 496 accepted + 4 smoke rejected** 重绘（delta 503 版仅作快速路径，已被全量版取代）。CRISPR 由 13 格三种子升到 24/30，SSP 10→18/30；148M 六臂闭合任务由 4 个变为 **5 个**（新增 SSP）。
3. **口径校正**：⑤d 标题与读图句由「148M 闭合 4 个任务」改为「5 个」，并明确 650M 仅有 LoRA 与 B20 阶段表 frozen；覆盖热图与 ①a-4 现在共用同一过滤口径（排除 smoke/diag/rank 变体/seed101/C5c 数据档/错根格），两页不再自相矛盾。
4. **过滤口径固化**：`build_8task_sixbar.py`、`build_time_perf_coverage.py` 新增 `keep_row()`：排除 `_noshuffle/_smoke/_diag`、`_r4_/_r16_`、seed∉{17,29,43}、`_e3\d+_`（C5c 档）、以及 23:11–00:05 错 artifact 根写出的格；改为自动选择最新 `bestval_ledger_export_*.csv`，图内来源标签随文件名动态生成。
5. **交付**：PPT SHA256=`8a3ea9af835fba5a9d2647a9e9e1483bef08f0f0d0b0647fa6d033acbb5328ff`，30 页；PDF SHA256=`152c046bdaa7f874d526c7209f5e67df5c296bb0f5ecec18f0f04552a61aa21d`。验收：CRC 正常、越界 0、177 段 1.5 倍行距、全部 Microsoft YaHei、独立 fontconfig 渲染正常。
6. **源包**：`figure_source_data_20261030_eight_task_v14/` 升 revision=`20261031_refresh_v15b_fullproof`，19 文件，manifest SHA256=`885ab306f432cf331f3ff62bca46898da99fbba88aeee8e0eaf0270103598992`。

## 22. 2026-10-31 01:xx 三条补测车道、② 页受控 LR 证据与 PDF 字体修复

1. **A 线（ncRNA 全参坍缩归因，8 格）**：`ft_rinalmomicro_noncodingrnafamily_full_s101_{random,family}` × lr{3e-4,1e-4,3e-5,1e-5}。这 8 格原有 ledger 行 `done` 但产物缺失（§10.38-⑩ 错根事故），队列判 `conflict` 永不派发；把旧行改 `stale_missing_artifacts` 后重跑。已回：random 3e-4=0.0956（≈1/13，best_epoch=0，val loss 单调升）、random 1e-4=0.8706、family 1e-5=0.8703。**结论：ncRNA 全参坍缩是学习率造成的真坍缩，不是测评口径问题（同数据同 split 只改 LR 即恢复）。**
2. **② 页文案**：副标题改为「受控新增：ncRNA 33M full 同数据同 split 只改 LR——random 3e-4→0.096、1e-4→0.871；family 1e-5→0.870。坍缩源于 LR 而非测评。」；读图句补「ncRNA 33M full 8 格 LR 网格再补 random 3e-5/1e-5 与 family 3e-4/1e-4」。图本身未动。
3. **B 线（结论④ 等价线分层，420 格）**：其余 7 任务 × micro full@1e-5 / mega LoRA@3e-4 × {1000,1500,2000,2500,3000} × 双 split × 3 seeds，4 worker；SSP n=2000 与其全量同格，12 个重复按 `complete proof` 自动 skip。④ 页读图句补「其余 7 任务 420 格分层已起跑，逐任务闭合再出面板」。
4. **C 线（SpliceAI 修复）**：2 格在 15:50 UTC 被 SIGTERM（rc=-15，plateau 仍 RUNNING），重跑时发现 23:06 起的 orphan 仍在跑 → 出现同 RID 三开并发写同一 `best.ckpt/plateau.json`；kill 较晚两份、保留 orphan。**教训：manifest 的 `failed` 只代表「新父的子进程被杀」，不能作为「格已死」判据，必须 `/proc` 实测。**
5. **台账与图**：delta 导出 496+27=**523 accepted**（0 rejected）；四图按新台账重绘（CRISPR 24→25/30、SSP 18→19/30）。
6. **PDF 中文空白修复**：`fc-match "Microsoft YaHei"` 解析到 `PingFang.ttc`，LibreOffice 无法嵌入 `.ttc` → CJK 全空白；在 `ppt/work/fc/fonts.conf` 加 `<rejectfont><glob>*/*.ttc</glob></rejectfont>`，改走 `msyh_regular.ttf`（cmap 29898/CJK 20992），PDF 中文恢复。pptx 内字体名仍是 Microsoft YaHei。
7. **交付**：30 页；PPT SHA256=`fc01c794797e04a7…`，PDF SHA256=`76412bbe20eefc02…`（第 2 页进度表同步为 2026-10-31 夜间版，⑤c-0/⑤d/⑤b-2 按用户决定写明 650M 显存受限本轮不测）；验收 CRC 正常、越界 0、177 段 1.5 倍行距、全部 Microsoft YaHei、PDF 第 18 页中文可提取（64 字）。
8. **源包**：revision=`20261031_refresh_v16_lanes`，24 文件，manifest SHA256=`dbacbc26e7a0639ae01ca8b63729ac222628d0c05c8007c10240e1e17ecb1900`。
