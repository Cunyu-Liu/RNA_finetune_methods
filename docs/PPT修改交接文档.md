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
7. **交付**：30 页；PPT SHA256=`ca08411dd97105fd…`，PDF SHA256=`04fc45052395295f…`（第 2 页进度表同步为 5 任务分层闭合、650M 搁置）（第 2 页进度表同步为 2026-10-31 夜间版，⑤c-0/⑤d/⑤b-2 按用户决定写明 650M 显存受限本轮不测）；验收 CRC 正常、越界 0、177 段 1.5 倍行距、全部 Microsoft YaHei、PDF 第 18 页中文可提取（64 字）。
8. **源包**：revision=`20261031_refresh_v16_lanes`，24 文件，manifest SHA256=`dbacbc26e7a0639ae01ca8b63729ac222628d0c05c8007c10240e1e17ecb1900`。

## 23. 2026-10-31 12:0x 夜间数据集刷新（v3 台账）

1. **台账**：v2（523）→ v3（**800 accepted**，+277，2 rejected）。六臂满数据覆盖 451→572/720：SSP 18→25、SpliceAI 5→8、SSI 7→8、CRISPR 24→25。
2. **图**：①a-4 / ⑤b-1 / ⑤b-2 / ⑤d 四图全部按 v3 重绘；页面文案只改「SpliceAI/降解/SSI 目前只有 frozen 满三种子，LoRA/full 多为 seed17 单点或未闭合」一句。
3. **⑤d 口径纠偏**：阶段表补充条件收紧为仅 `frozen`，修复「⑤d 显示 3 seeds、①a-4 同格却是斜线」的两页矛盾；热图内降解/SSI 的 LoRA 列恢复为 0（未闭合），脚注同步。
4. **等价线首图**：新增 `build_equivalence_8task.py`，8 面板口径为 33M-full@1e-5 vs 148M-LoRA@3e-4、逐档 ≥3 seeds；当前 3 面板可判，CRISPR 标「正例过少」。图暂不入正文，等 ≥6 面板替换 ④ 页。
5. **交付**：30 页；ZIP CRC 正常、越界 0、177 段 1.5 倍行距、全部 Microsoft YaHei。PPT SHA256=`6ce4fb60320f1c1c…`、PDF SHA256=`69f09fa5307bb9b0…`。
6. **源包**：revision=`20261031_refresh_v17_v3ledger`，29 文件，manifest SHA256=`581c98314215e8fb97a975c65402cca1578e986a17230bf5ac6d6b33eb5020ed`。

## 24. 2026-10-31 22:0x v4 台账与 ⑤c 换图

1. **台账**：v3（800）→ v4（**994 accepted**，+194，1 rejected）；六臂满数据在 ncRNA/CRISPR/modification/MRL/SSP 五任务上 5 模型 × 3 seeds 全齐。
2. **⑤c-0 页（第 22 页）换图**：由「ncRNA 单任务五档曲线」改为 `data_volume_8task.png`——33M-full@1e-5 / 33M-LoRA@3e-4 / 148M-LoRA@3e-4 三臂 × 5 档 × 3 seeds；4 面板闭合（ncRNA/modification/MRL/SSP）、CRISPR 按正例率 0.59% 标「正例过少」、SpliceAI/降解/SSI 标「待补」。标题、副标题、读图句同步改写，旧图内「650M and all other C5c arms remain pending」脚注随图替换消失。
3. **结论④ 等价线**：4/8 面板可判，已有明确等价对（ncRNA 3000→2500、MRL 3000→2000、SSP 3000→1000）；图仍留在 fig 目录，等 ≥6 面板再替换正文。
4. **交付**：30 页；CRC 正常、越界 0、177 段 1.5 倍行距、全 Microsoft YaHei。PPT SHA256=`35a9a679e556abc2…`、PDF SHA256=`3eb3444959160f54…`。
5. **源包**：revision=`20261031_refresh_v18_v4ledger`，34 文件，manifest SHA256=`73d36f10e3a9a9db585002dc350bcde6b7d01a883a8539d662e9f044b2b6637c`。

## 25. 2026-10-31 23:2x 用户并发编辑合并版

1. **为什么用户没看到更新**：23:08 用户保存的同名文件覆盖了 23:0x 构建，且这次保存把 24 张 media 图片全部写坏（CRC 全错、LibreOffice 渲染 p18/p22 空白）。
2. **合并口径**：以图片完好的构建为主体，把用户 18 个批注框（页面外左侧）与 p26 手工版式（图上移放大、读图框下移）原样搬入；用户批注一字未改。
3. **本版新增/修正**：p2 进度表（5 任务分层闭合、650M 搁置）＋页脚「目的」一句；p18 读图句补「3e-4 是四个 runner 的 argparse 缺省（非搜参）；MRL 唯一负值 −0.112 来自 micro-full s101@3e-4 坍缩格，只用于选档」；p22 换 8 任务三臂图并写明「与 ④ 同一批数据、两种问法」；p26 图回缩到 11.4 in、读图框 6.80，避免压字。
4. **验收**：30 页、ZIP CRC 正常、非批注越界 0、177 段 1.5 倍行距、全部 Microsoft YaHei、PDF 30 页且图片完整。
5. **交付**：PPT SHA256=`971d8fbabb395b30…`、PDF SHA256=`275435d75023ac8a…`。

## 26. 2026-11-01 导师逐页反馈修订与当前边界

1. **基底与当前文件**：用户最新保存的 30 页原文件 SHA256=`f4277d59af9f1c2436c3e8e0b99feffffaf0af13443b18088fb3b7984c1d7025`，不覆盖原件。当前阶段修订文件为 `ppt/RNA_LM微调策略评测-导师讨论修订版_20261101_导师反馈修订.pptx`，**30 页**，v52 阶段 SHA256=`1ea24b847e64bdb77238c914de0f8f98b4620363a9236363d622272e48b46505`；对应 PDF 位于 `ppt/work/review_20261101/revised/`，SHA256=`ed4c7b224e3a846f80022f9a9242714070bfe41d01ac48915835d564ff73d74c`。实验未闭合前不得视为最终科学版。
2. **八任务与结论①**：页 2 明确八任务用于检验任务粒度、分类/回归、类别不平衡与 split 对策略结论的调节作用，不是堆数量。页 5 解释 shuffle 是逐 epoch 重排训练样本、不是改标签/split；no-shuffle 的 epoch0–3 是 best0+patience3 的完整早停曲线。页 6 改为“modification family 高 AUC 但非免疫”，页 7 改为“MRL 的 RiNALMo 规模收益饱和”。结论①主矩阵是固定 LR 对照，逐任务 validation 选 LR 归结论②。
3. **结论②核查与 interim 选档**：3e-4 是 runner argparse 工程缺省而非最优。当前全参 tuning 为 75/320 格，18/80 组四档完整、另 1 组 3/4；已完成组均未选择 3e-4，3e-5/1e-4 各 8 组、1e-5 两组。选择只最小化 held-out best_val，test 不参与；待 80 组全闭合和正式种子复测后再下结论。MRL seed101 micro-full@3e-4 的 −0.112 已独立 CUDA 重评一致，预测 SD=6.25×10⁻⁷，属输出近常数坍缩，不是评测算错；证据在 `status/revalidation/mrl_negative_20261101/`。
4. **分类组合图已闭合**：ncRNA/modification/CRISPR/SSP 已把三状态投影与同 seed17、同 split 的 full-test 性能放在同图。**SpliceAI random/family 的 seed17/29/43 pre/LoRA/full 均完成**，现为连续两页三种子组合图；最后 LoRA-family 源格 macro-F1=0.419940687，best_epoch=0、4 epochs 后按 patience=3 收敛。回归机制页全部保留。分类源包含 53 个登记文件，revision=`20261101_classification_composite_v2`，manifest SHA256=`308c692ba2fdd1a143721c1933b43a5adffa80025c1f6154a59fbf8c8b5cee5d`。
5. **④/⑤/⑥/⑦结构**：④只比较同家族 small-full(n) vs large-LoRA(m)，⑤只比较模型内数据量 scaling；旧⑤c-1/⑤c-2 移入④并标 legacy，旧⑤的重复曲线页删除。时间×性能/显存独立为⑥，遗忘为⑦。等价候选必须逐 seed |Δ|≤0.02 且 95% CI 覆盖 0；近随机两臂不算有效等价。当前④/⑤均为 **6/8 可判**。degradation 三臂五档；SSI 33M-full/LoRA 已五档，148M-LoRA 两档，④候选仍为 full2000≈LoRA1500，其他最近配对未等价。
6. **遗忘图**：A 轴=`ΔNLL=post−pre`，正=遗忘、负=反向增益；散点为单 run、连线为均值。controlled 30 格、每组 3 seeds，30M worst-seed 比=7.7576×；official fixed-mask 分协议不混入。图源=`figure_source_data_20261101_e6/`，代码提交 `4032b5f`。
7. **v52 数据与候选**：当前 PPT 输入为 **1276 accepted、1 rejected**，18 个新增格均 proof=complete。图内来源为 `bestval_ledger_export_20261101_v52`。SSI 仅 full2000≈LoRA1500 合格，Δ=−0.000599762、CI=0.002969352；其他近值 CI 不覆盖 0，不写等价。①a-4 五种任务三种子单元为 25/26/17/13/14。当前源包 revision=`20261101_refresh_v64_v52ledger_source_provenance_fix`，150 个登记文件，manifest SHA256=`8003394a861f801d70d057f5b246600c366ea4b5e335e529f94220ae3087ffcc`。
8. **当前验收**：30 页 ZIP CRC、`pptx_lint.py`、`validate_report_layout.py` 全部通过；Microsoft YaHei、正文 1.5 倍行距和 LibreOffice 实际渲染通过。六张更新图的嵌图 SHA 与源 PNG 一致；第25页图片/读图框重叠已修复，显存图脚注与元数据已自动引用 v52。④/⑤候选、图文一致性和 cap 均已核对，未修改页保留用户手调内容。主矩阵、LR/rank、Frozen scaling、CRISPR 信号档、RNA-Sc 等价线和 E6 余格继续按真实 proof 推进，最终科学验收尚未完成。

## 27. 2026-11-01 当前 v53 阶段交付

1. 当前 PPT 仍为 `ppt/RNA_LM微调策略评测-导师讨论修订版_20261101_导师反馈修订.pptx`，30 页，SHA256=`f8151e1604663948ece241e6115cf20cd02e594a2ca4390db5759fdacd1ca5da`；PDF SHA256=`cfd9726650767e7258cc9648b15603a15f2f653775fe8e215f583330fd6a6ec8`。原始 30 页基底未覆盖。
2. 当前输入为 **1292 accepted、1 rejected**，16 个新增格均 proof=complete。④/⑤均 6/8；SSI 33M-full/LoRA 五档、148M-LoRA 四档。④现有三组候选：full2000≈LoRA1500、full2500≈LoRA2000、full3000≈LoRA2000，均通过逐 seed 差值和 CI 复算，页面已写“候选非唯一”。
3. 当前源包 revision=`20261101_refresh_v65_v53ledger_ssi_four_tier_candidates`，152 个登记文件，manifest SHA256=`1b9aeb2c0f41bc7786d06faffdb88f24fcd7102f0e7881fa695abce127491d12`。图、CSV、metadata、脚本与 v53 台账一致，六张嵌图 SHA、30 页 lint/layout/CRC 和实际渲染通过。
4. 实时 proof 审计为 per-base 105/270、LR 76/320、rank4/16 65/96；只作队列进度。主矩阵、family、Frozen scaling、LR/rank、CRISPR 信号档、RNA-Sc 与 E6 仍未完成，当前文件不是最终科学版。

## 28. 2026-11-01 当前 v54 阶段交付

1. 当前 PPT 为 30 页，SHA256=`6936bc7bce748962f7947b243aa2a11258b77f4cde00c4846ec180e5984584d6`；PDF SHA256=`94f453080ed96290b74f715db7b02b915943854d41c8256d8cd059fc9db8ad23`。当前输入 **1315 accepted、1 rejected**，23 个新增格均 proof=complete。
2. ④/⑤均 6/8；degradation 与 SSI 三臂均五档。SSI ④仍为 full2000≈LoRA1500、full2500≈LoRA2000、full3000≈LoRA2000 三组候选，n3000 新点未增加候选。①a-4 的五种任务三种子单元为 25/26/17/14/14。
3. 第19页 LR interim 更新为 19/80 组四档完整，3e-5/1e-4 各 8 组、1e-5 三组，3e-4 为 0；仍需全量和正式种子复测。v54 registry accepted 为 per-base 106/270、complementary 280/324、LR 76/320、rank 65/96。
4. 当前源包 revision=`20261101_refresh_v66_v54ledger_ssi_three_arm_closure_lr19`，154 个登记文件，manifest SHA256=`8849f8c6ccc7df35b7f37a14e551e21031469b459e2aaa9d82e0d8dc64f86cca`。嵌图、30 页 lint/layout/CRC 和实际渲染通过；全实验与最终科学验收尚未完成。

## 29. 2026-11-01 当前 v55 阶段交付与队列边界

1. 当前 PPT 为 30 页，SHA256=`e61f2469b78054583ab0e840426c6696b3d2c5b6334358cd0d186477e0b05034`；PDF SHA256=`7067c6bd7fd514630a7791678be3fbd695e89069e964dd33b0e3d06211f0a5da`。输入 **1324 accepted、1 rejected**，9 个新增格最终均 proof=complete。
2. ERNIE degradation LoRA-family 正式三种子替换阶段表，覆盖计数仍 14/30；SSI family full/micro-LoRA 五档、mega-LoRA 三档。当前 random④/⑤仍 6/8、三组候选不变，未把 family 进展混入 random 面板。
3. 两个 SSI 注册表曾在 pre-ledger 窗口重复派发。冲突 manifest 已排除，只有最终完整 proof 入库；另一起双跑保留较早进程、终止较晚进程。三个重叠父队列已停止，统一 equiv/lora_tiers 保留，复核 0 重复。证据=`status/queue_actions/ssi_queue_consolidation_20261101.json`。
4. 当前源包 revision=`20261101_refresh_v67_v55ledger_family_proof_queue_consolidation`，157 个登记文件（含队列证据），manifest SHA256=`485ac4887b0e6f1b854bc3dd72f88c0ea867cdbfcf2882b44690a53f9c1f2752`。嵌图、30 页 lint/layout/CRC 与实际渲染通过；最终科学验收未完成。

## 30. 2026-11-01 当前 v58：32 页 random+family 对照

1. 当前 PPT 为 **32 页**，SHA256=`eab7aabfe732088073df37cf7cf784761335b77702049eb1e38e8f32fd4b067a`；PDF SHA256=`01a1371f9af0d686bf68fb7935a9a74add84fa0187fe06b67ea53861154a5990`。新增第22页 family④和第26页 family⑤，random 页保持原位置和内容。
2. family④/⑤均 5/8。MRL、degradation、SSI 有各自等价候选，modification/SSP 未观测到；degradation cap=1680，候选非唯一。两 split 不合并且不互套配对。页 2 状态改为 random 6/8、family 5/8。
3. ①a-4 的 SSI 正式覆盖修正为 13/30，阶段表不再替代未齐的 ERNIE frozen-random best-val 种子。LR 为 77/320、19/80 组完整，选档分布不变。
4. 克隆关系 ID 已改为显式映射，family 克隆移至删除旧页前，ZIP 无重复 slide31 条目。32 页 lint/layout/CRC、Microsoft YaHei、正文 1.5 倍行距、八张嵌图 SHA 与实际渲染通过。
5. 当前源包 revision=`20261101_refresh_v68_v58ledger_family_scaling_5of8`，176 个登记文件，manifest SHA256=`abf4607438d886299eba5e3d5b15ad30f8c621b246a1b42bba5cf5d980232b10`。全实验与最终科学验收仍未完成。

## 31. 2026-11-01 当前 v59：family 五档更新

1. 当前 PPT 为 32 页，SHA256=`ef56c08380dbf7afd680e105c5759eaa3075376468fc7fa2a29aeeb704af951f`；PDF SHA256=`6d4f49e7f0ab7b646b62b29be5e512c7650ff8edbd41c6425d6cc70894d52bfd`。输入 **1340 accepted、1 rejected**，8 个新增格均 proof=complete。
2. 第26页 family⑤：SSI 三臂五档，degradation 三臂 5/5/4 档；modification/MRL/SSP 三臂五档。family④/⑤均保持 5/8，random 不变。
3. 第22页 family④：degradation full1500及 cap 后2000–3000均≈LoRA1000；requested 2000–3000 同 actual=1680，不重复计数据收益。MRL/SSI 候选不变，modification/SSP 未观测到。
4. 当前源包 revision=`20261101_refresh_v69_v59ledger_family_five_tier_closure`，178 个登记文件，manifest SHA256=`600f1499061c83e2589babf240ec4ebd6b7e7b5854e23b78a26caf1f316c1e68`。嵌图、32 页 lint/layout/CRC 与实际渲染通过。v58 提交 `af3de2f` 因网络超时待补推，全实验尚未完成。

## 32. 2026-11-01 当前 v60：SSI 正式闭合与 LR 20 组

1. 当前 PPT 为 32 页，SHA256=`33f45133c73355f6cf29e24cf6280dcb8374a2139bc978ba983a14a700aa2e0d`；PDF SHA256=`d49998702494246a37793cee54823dcdacabe509c9cd9cd8b0a5bbbf36b488dc`。输入 **1344 accepted、1 rejected**，4 个新增格均 proof=complete。
2. 第8页①a-4：ERNIE SSI frozen-random 三种子正式闭合，五种任务覆盖为 25/26/17/14/14，按 best-val 计数，不用阶段表补齐。
3. 第19页 LR：80/320、20/80 组四档完整；新增 ERNIE CRISPR full-random 组 validation 选 1e-5，选档分布为 3e-5/1e-4 各 8 组、1e-5 四组、3e-4 为 0，test 不参与。
4. 当前源包 revision=`20261101_refresh_v70_v60ledger_formal_ssi_closure_lr20`，180 个登记文件，manifest SHA256=`9b385523ccc243af8fb643a26cb337fd726efe36cdc01b54667f667e55a81102`。random/family④/⑤不变；嵌图、32 页 lint/layout/CRC 与实际渲染通过。GitHub 欠推 af3de2f/2050a24，全实验未完成。

## 33. 2026-11-01 当前 v64：路径恢复与 LR 21 组

1. 当前 PPT 为 32 页，SHA256=`704ae8f0d45c6298bff1c35b08b9de62807236df3085b20e10e2fdd8b0b8ca6a`；PDF SHA256=`f7c5332c4030139a948057e4d721fe066a9b46cbe5ee669faa47bfafa652affc`。输入 **1352 accepted、0 rejected**。
2. 长期 rejected 的 mega SpliceAI frozen-family/seed17 已找到 teams 完整副本，前后 proof=complete，仅修 ledger out_dir，不重跑。三种子正式闭合，①a-4 的 SpliceAI 为 18/30；SSI 仍 14/30。
3. 第19页 LR 更新为 84/320、21/80 组；ERNIE CRISPR full-family 选 1e-5，选档分布 8/8/5/0，test 不参与。
4. 当前源包 revision=`20261101_refresh_v71_v64ledger_ledger_path_recovery_lr21`，189 个登记文件，manifest SHA256=`0131b8eb5b175ecda8aa968c7d822306d77fa4662e553dfc953db7acc625658e`。路径修复证据、v61–v64 台账、图和脚本一致；嵌图、32 页 lint/layout/CRC 与实际渲染通过。

## 34. 2026-11-01 当前 v65：ERNIE SSI family 闭合

1. 当前 PPT 为 32 页，SHA256=`b89a50417f293bb7e7e3148f99f6c7d89fb87e454ddb47aef018704b07790540`；PDF SHA256=`53d93740ef9171d56156831e7938c85a5613c7e629d14339d7f61050947dc6d6`。输入 **1356 accepted、0 rejected**，4 个新增格均 proof=complete。
2. ERNIE SSI frozen-family 三种子 PCC=0.554263229/0.555498222/0.558825956，mean=0.556195802，正式闭合；①a-4 的 SSI 为 15/30，五种任务为 25/26/18/14/15。
3. RNA-FM CRISPR full-random 仅两档，LR 86/320、完整组仍 21/80；SpliceAI 低信号，random/family④/⑤不变。
4. 当前源包 revision=`20261101_refresh_v72_v65ledger_ernie_ssi_family_closure`，191 个登记文件，manifest SHA256=`f875cd1392b2e2e871c5c706ed3cd8af6f5ad9a727d50f501bdfe4ac8773505d`。嵌图、32 页 lint/layout/CRC 与实际渲染通过，最终科学验收未完成。

## 35. 2026-11-01 当前 v66：RNA-FM CRISPR LR 第 22 组

1. 当前 PPT 为 32 页，SHA256=`63ae89e3c4864588999f5d0cd5827f4247fce7921f588f4ee16e290643b06645`；PDF SHA256=`46fb153cdcdd541806f1896e1ee4375843b9d935e8469549384f93631978b193`。输入 **1359 accepted、0 rejected**，3 个新增格均 proof=complete。
2. RNA-FM CRISPR full-random 四档闭合，validation 选 3e-5（best_val=0.025089）；LR 88/320、22/80 组，选档分布 3e-5 九组、1e-4 八组、1e-5 五组、3e-4 为 0，test 不参与。
3. ①a-4 保持 25/26/18/14/15，random/family④/⑤不变；SpliceAI 仍低信号。
4. 当前源包 revision=`20261101_refresh_v73_v66ledger_lr22_rnafm_crispr`，193 个登记文件，manifest SHA256=`10d08978c5cccd93662e4949e9474d78c303a9021a23cb47b0ef74319d1dd366`。嵌图、32 页 lint/layout/CRC 与实际渲染通过。

## 36. 2026-11-01 当前 v68：RNA-FM family LR 第 23 组

1. 当前 PPT 为 32 页，SHA256=`51810eee3fa4f125d5c41a7db55eaf93e5b51b1a68837bdaf4e1e35625f224ce`；PDF SHA256=`3b3acaa39bed1bb86d70fd3eaae0b83fbf062d41f4435af2817635a31ad45d4c`。输入 **1367 accepted、0 rejected**，3 个新增格均 proof=complete。
2. RNA-FM CRISPR full-family 四档闭合，validation 选 1e-4（best_val=0.028884）；LR 92/320、23/80 组，选档分布 3e-5 九组、1e-4 九组、1e-5 五组、3e-4 为 0，test 不参与。
3. ERNIE SSI LoRA-random 为 2/3，①a-4 和④/⑤不变；SpliceAI 仍低信号。
4. 当前源包 revision=`20261101_refresh_v74_v68ledger_lr23_rnafm_family`，197 个登记文件，manifest SHA256=`521dfaf63b5c46c8508c11db118fe8b15f75a931049bdd0ae83ea1d5e585f097`。嵌图、32 页 lint/layout/CRC 与实际渲染通过。

## 37. 2026-11-01 当前 v69：ERNIE SSI LoRA 闭合

1. 当前 PPT 为 32 页，SHA256=`8912ed078a327135503d1f4d24b2635f9a5996bdf879baec4acdfb2b19a59019`；PDF SHA256=`ed337eb4eb9af7a2566e9c47ab12f1c39d6fda3c9d218352dcdb8574c5aa5547`。输入 **1371 accepted、0 rejected**，4 个新增格均 proof=complete。
2. ERNIE SSI LoRA-random 三种子 PCC=0.656606981/0.659070557/0.656716318，正式闭合；①a-4 的 SSI 为 16/30，五种任务为 25/26/18/14/16。
3. per-base 120/270、rank4/16 66/96、LR 93/320（完整组仍 23/80）。MRL mega-full default 的 −0.079980258 仅作 tuning 诊断，不写成正式三种子或最终 LR 结论；④/⑤不变。
4. 当前源包 revision=`20261101_refresh_v75_v69ledger_ernie_ssi_lora_closure`，199 个登记文件，manifest SHA256=`4b96b214f5d4bf3cb035e8039c50d3e57dec3ddf44b2c16b352c63725ce9c32d`。嵌图、32 页 lint/layout/CRC 与实际渲染通过。

## 38. 2026-11-01 当前 v76：主矩阵与 650M frozen 大批更新

1. 当前 PPT 为 32 页，SHA256=`b4c4138d3806d2bfaaccefe95520d794ad2d6df1d8fe9cb96db7ec3629841b17`；PDF SHA256=`8a720537b145f26012b5d451b586b48414c9b15ef512843f2f170ae7befd743a`。输入 **1424 accepted、0 rejected**，47 格均 proof=complete。
2. 第8页①a-4 为 27/26/18/17/16；per-base 142/270、complementary 297/324、rank 67/96。650M frozen 新增 17 格入库，LoRA/full 未强行启动。
3. 第7页 MRL 的 650M frozen 双 split 均三种子；第6页 modification 的 650M frozen random 三种子、family 为 n=1 斜线。两张官方图已用 v76 动态重绘，除预期单元外逐格一致，文字与嵌图同时更新。
4. 第19页 LR 为 103/320、24/80 组；mega MRL full-random 选 3e-5 后 r=0.798969709，选档分布 10/9/5/0，test 不参与。
5. 当前源包 revision=`20261101_refresh_v77_v76ledger_official_sixbar_dynamic`，227 个登记文件，manifest SHA256=`c2c9df3680940631288228a6cf8ecdb8cb32c09065c7e0d917b39815ab09c3dd`。十张关键嵌图 SHA、32 页 lint/layout/CRC 与实际渲染通过。

## 39. 2026-11-01 当前 v77：SpliceAI full 与 modification n=2

1. 当前 PPT 为 32 页，SHA256=`d803f96747c06f9a423e813173ed309d6ba70861930ae6522aa771953962c6ea`；PDF SHA256=`85060f303a4516cdb4a176bd709e12c1b57039c7c3158dbe5b46a03a10f37a83`。输入 **1428 accepted、0 rejected**，4 格均 proof=complete。
2. mega SpliceAI full-random 三种子 macro-F1=0.354690642/0.547941423/0.598939701，正式闭合；①a-4 的 SpliceAI 为 19/30。
3. 650M modification frozen-family 为 2/3，页面改为 n=2 斜线；random 三种子不变。MRL 图和④/⑤不变；RNA-FM SSI LoRA-random 为 1/3。
4. 当前源包 revision=`20261101_refresh_v78_v77ledger_spliceai_full_closure_mod_n2`，229 个登记文件，manifest SHA256=`66dc9eb61ae3e09bf75d713d3e687e94da168e2de5eba20659497a4c653c507c`。per-base 144/270、complementary 298/324、LR 104/320（完整组仍 24/80）；嵌图、32 页 lint/layout/CRC 与实际渲染通过。

## 40. 2026-11-01 当前 v78：650M modification 双 split 闭合

1. 当前 PPT 为 32 页，SHA256=`fcde2a2d92eeb5927b09618304c8ae723aa2b9d099c23928bb0923f45ba1f3a0`；PDF SHA256=`fed444a6657773ac27af0d95ad0fe1daaf0dbd25c0584d379be41ed1a680f941`。输入 **1430 accepted、0 rejected**，2 格均 proof=complete。
2. 650M modification frozen-family 三种子 AUC=0.663015924/0.657170378/0.660444625，mean=0.660210309，正式闭合；random 也已闭合，页面改为双 split 三种子，其余未闭合项仍为 NA。
3. RNA-FM SSI LoRA-random 为 2/3，未新增单元；per-base 145/270、complementary 299/324、LR 104/320（完整组仍 24/80）、rank 67/96，④/⑤不变。
4. 当前源包 revision=`20261101_refresh_v79_v78ledger_modification_650m_closure`，231 个登记文件，manifest SHA256=`780b8fc039487a9c7a086e7097f00777a20fdad61403e577e76a700fddfb774a`。嵌图、32 页 lint/layout/CRC 与实际渲染通过。

## 41. 2026-11-01 当前 v80：RNA-FM SSI 与 650M SSP 首点

1. 当前 PPT 为 32 页，SHA256=`6049a44feca49f0bf1823d4c84669dadbc0b3bd77a0b749fd0de789536887ae0`；PDF SHA256=`b405175eea336c4f34b0a4303a10ee661e699fd60c7f1e72197688104b32955c`。输入 **1433 accepted、0 rejected**，2 格均 proof=complete。
2. RNA-FM SSI LoRA-random 三种子 mean=0.630093485，正式闭合；①a-4 的 SSI 为 17/30。650M SSP frozen-random/seed17 pair-F1=0.2448，仅 1/3，SSP 仍 26/30。
3. per-base 146/270、complementary 300/324、LR 105/320（完整组仍 24/80）、rank 67/96，④/⑤不变。
4. 当前源包 revision=`20261101_refresh_v80_v80ledger_rnafm_ssi_closure_650m_ssp_first`，235 个登记文件，manifest SHA256=`3198fd091d726d53bb11935016a27cbd1dfacfd6baabcf69b2adec2c7fa71ab4`。嵌图、32 页 lint/layout/CRC 与实际渲染通过。

## 42. 2026-11-01 当前 v86：650M SSP frozen-random 闭合

1. 当前 PPT 为 32 页，SHA256=`83a708ab22ae2f93be732bb4bd622b26239e4d6cd684d3c0feded2d87f503e56`；PDF SHA256=`fa11997cbd00e02bba9f24514c24adbfc261e08227c46f7e007cfa184c10a1a7`。输入 **1438 accepted、0 rejected**，新增格 proof=complete。
2. 第8页①a-4：650M SSP frozen-random 三种子 pair-F1=0.2448/0.2445/0.2636，mean≈0.250967，正式闭合；SSP 覆盖升为 27/30，五种任务为 27/27/19/17/17。图、图注和覆盖文字同步更新，其他用户手调内容不改。
3. per-base 146/270、complementary 302/324、LR 107/320（完整组仍 24/80）、rank 67/96，random/family④/⑤不变。
4. 当前源包 revision=`20261101_refresh_v81_v86ledger_650m_ssp_closure`，247 个登记文件，manifest SHA256=`845920a3c818a40258ad9fe2c3da6d6dbe1b312a62e84b21ea88c6cb462a8189`。十张关键嵌图 SHA、32 页 lint/layout/CRC、Microsoft YaHei、正文 1.5 倍行距与实际渲染通过；原始 PPT 未覆盖，最终科学验收未完成。

## 43. 2026-11-01 当前 v87：LR 完整组漏计更正

1. 当前 PPT 为 32 页，SHA256=`4763f848d14edb56370d06c233e46f43762f1529b99e2e9b92772fdb7ce362c2`；PDF SHA256=`49fb729fcd327741302774b2ab563796c20fc3f28fe57dab2b1d36b65af475b4`。输入 **1443 accepted、0 rejected**，5 个新增格均 proof=complete，但未形成新三种子科学单元，①a-4 与④/⑤不变。
2. 第19页 LR 更正为 **25/80 组**，选档分布 3e-5 十一组、1e-4 九组、1e-5 五组、3e-4 为 0。逐格 proof 和逐版台账证明第25组是 v79 已闭合的 ERNIE MRL full-random，validation 选 1e-5；此前漏计，并非 v87 新实验。80 组全闭合前不冻结 tuned 正式矩阵。
3. 当前 per-base 148/270、complementary 302/324、LR 108/320、rank 68/96。源包 revision=`20261101_refresh_v82_v87ledger_lr25_proof_recount`，250 个登记文件，manifest SHA256=`b0c2e75bc1caa3c803a0431ccb6822329fa029486103515234c9f9466c064876`，含完整 LR interim 证明。
4. 本页文字与图意仍一致，只更新计数及漏计说明；十张关键嵌图 SHA、32 页 lint/layout/CRC、Microsoft YaHei、正文 1.5 倍行距和实际渲染通过，其他手调内容未改。

## 44. 2026-11-01 当前 v88：RNA-FM SSI LoRA-family 闭合

1. 当前 PPT 为 32 页，SHA256=`20b3ffd36d099cea82367892d181e7d7ed4b12866ba9a25c5ce792818cd866fc`；PDF SHA256=`3701d2bbba135f33beccc069cc722977d42bf84642b9814f1157407c2c782b80`。输入 **1446 accepted、0 rejected**，3 个新增格均 proof=complete。
2. 第8页①a-4：RNA-FM SSI LoRA-family 三种子 PCC=0.593009039/0.592436075/0.592805270，mean≈0.592750128，正式闭合；SSI 覆盖升为 18/30，五种任务为 27/27/19/17/18。
3. 第27页覆盖图补入 650M SSP frozen-family/seed17（pair-F1=0.3237），但仅 1/3，不写闭合；第28/29页成本图同步到 v88。per-base 150/270、complementary 303/324、LR 108/320（25组）、rank 68/96，④/⑤不变。
4. 当前源包 revision=`20261101_refresh_v83_v88ledger_rnafm_ssi_family_closure`，252 个登记文件，manifest SHA256=`3ef91e4553c1f874c5d64362fcfe64a961d4da643b8c951aaafa6686f7c49b7e`。十张关键嵌图 SHA、32 页 lint/layout/CRC、Microsoft YaHei、正文 1.5 倍行距与第8/27/28/29页实际渲染通过。

## 45. 2026-11-01 v89 staging：展示版保持 v88

1. v89 为 **1447 accepted、0 rejected**；新增 mega SpliceAI LoRA-family/n3000/seed17，macro-F1=0.333280238，proof=complete、CUDA 收敛，仍近随机。
2. 未形成新三种子单元、完整 LR 组或有效④/⑤结果，故 PPT 与 v83 源包继续保持 v88，不重画无科学变化的页面。v89 台账和独立证明保存在 teams，下一次可见更新一并纳入。
3. 当前展示版仍为 32 页，PPT SHA256=`20b3ffd36d099cea82367892d181e7d7ed4b12866ba9a25c5ce792818cd866fc`，PDF SHA256=`3701d2bbba135f33beccc069cc722977d42bf84642b9814f1157407c2c782b80`。

## 46. 2026-11-01 v90：无新增与计数审计

1. v90 新增 0，仍为 **1447 accepted、0 rejected**，没有页面内容变化，PPT 和 v83 源包继续保持 v88。
2. 注册表 RID 精确对账为 per-base 149/270、complementary 303/324、LR 108/320、rank 68/96、equiv 417/420、650M frozen 23/25。per-base 的 v86/v88/v89 权威值为 147/149/149，替代此前阶段估算偏差；这些计数未写在 PPT 页面中，不影响现有图文。
3. 审计证据=`status/registry_accepted_recount_20261101_v90.json`，SHA256=`8082d0df53c3e17c487c54f7c84e8cf35da4e835fa927ce05dcf00aa172c7f82`。

## 47. 2026-11-01 v91 staging：展示版保持 v88

1. v91 为 **1448 accepted、0 rejected**；新增 micro SpliceAI full-family/n3000/seed17，macro-F1=0.333280238，proof=complete、CUDA 收敛，仍近随机。
2. equiv 进度升为 418/420，但无新三种子单元、完整 LR 组或有效④/⑤结果，因此 PPT 与 v83 源包保持 v88。当前 PPT/PDF SHA256 仍为 `20b3ffd36d099cea82367892d181e7d7ed4b12866ba9a25c5ce792818cd866fc` / `3701d2bbba135f33beccc069cc722977d42bf84642b9814f1157407c2c782b80`。

## 48. 2026-11-01 当前 v92：650M SSP frozen-family n=2

1. 当前 PPT 为 32 页，SHA256=`2dfc707a9030c173ea3399662ecdfaa8094bdfdfdc281fd021142b28d2eb385a`；PDF SHA256=`acb07573ab8e97f4712c502908963459da6482cf7239db808ba5c6f069815339`。输入 **1449 accepted、0 rejected**，新增格 proof=complete。
2. 650M SSP frozen-family 的 seed17/29 pair-F1=0.3237/0.2711，目前 2/3。第27页覆盖热图显示 2，第8页对应柱仍为 n<3 斜线，不写三种子闭合；第28/29页成本图同步至 v92。
3. 当前 per-base 149/270、complementary 303/324、LR 108/320（25组）、rank 68/96、equiv 418/420、650M frozen 24/25；①a-4 与④/⑤不变。
4. 当前源包 revision=`20261101_refresh_v84_v92ledger_650m_ssp_family_n2`，264 个登记文件，manifest SHA256=`508c6387ab079e36130d938c81de2ceb2ef30860e139b7827f31d9cf3b193d1c`。十张关键嵌图 SHA、32 页 lint/layout/CRC、Microsoft YaHei、正文 1.5 倍行距与第8/27/28/29页实际渲染通过。

## 49. 2026-11-01 v93 staging：展示版保持 v92

1. v93 为 **1451 accepted、0 rejected**；mega SpliceAI family/n3000/seed43 仍近随机，equiv 419/420，不形成有效④/⑤结果。
2. ERNIE MRL full-family 的 3e-5 tuning 格 r=0.699845973；该组仍缺 1e-5，LR 109/320、完整组保持25/80，不提前选档。
3. 无新三种子科学单元或完整 LR 组，PPT 和 v84 源包保持 v92；PPT/PDF SHA256 仍为 `2dfc707a9030c173ea3399662ecdfaa8094bdfdfdc281fd021142b28d2eb385a` / `acb07573ab8e97f4712c502908963459da6482cf7239db808ba5c6f069815339`。

## 50. 2026-11-01 v94：在训状态，不更新展示版

1. v94 新增 0，仍为 **1451 accepted、0 rejected**，PPT 和 v84 源包保持 v92。
2. SSP seed43、equiv degradation 和长时 SpliceAI full-family 均有 plateau 推进；另一 LR 格处于 pre-plateau。以上只证明在训，不构成收敛或页面结论，故不修改图片或文字。
3. 在训证据=`status/inflight_progress_20261101_v94.json`，SHA256=`b674a7cf5c9e09e2cbfabb9c60c25d5986c2482b64d6e0ce3721e10491246848`。

## 51. 2026-11-01 当前 v96：equiv canonical 与 family 五档

1. v95 无新增；v96 输入 **1452 accepted、0 rejected**。最后一个 equiv canonical 格 proof=complete，equiv=420/420；dense 诊断不计入。PPT SHA256=`0efc70be20c74dbb0e496cf6d60fb5b8a40b1c1af71805f8e5ee6a07f7f7d4a0`，PDF SHA256=`418215d64737eeab55a3a662de939d4c3e0f911c4ec38eb225dd47b47778cb75`。
2. 第26页 family⑤ 改为 modification/MRL/SSP/degradation/SSI 三臂均五档；degradation 原“5/5/4”已更正为“5/5/5”。第22页 family④ 候选不变，cap 后2000–3000仍同 actual=1680；第21/25页 random 结论不变。
3. 当前 per-base 149/270、complementary 303/324、LR 109/320（25组）、rank 68/96、650M frozen 24/25；①a-4 不变。
4. 当前源包 revision=`20261101_refresh_v85_v96ledger_equiv420_family_degradation_five_tiers`，275 个登记文件，manifest SHA256=`804d3822db3174de2e24628468f3ce52fefc42a99fc37ef790dd2350389fc5fe`。十张关键嵌图 SHA、32 页 lint/layout/CRC、Microsoft YaHei、正文 1.5 倍行距与第21/22/25/26页实际渲染通过。

## 52. 2026-11-01 当前 v97：ERNIE MRL family LR 第26组

1. 当前 PPT 为 32 页，SHA256=`f30bbce2e888c33c80035df18db0e52c1a42f92a1a7065cafd1853e4c273ae8c`；PDF SHA256=`096bb834d6906d765523abc38f1b39b179b70309372ce5d5ec2cf4bdfb85a363`。输入 **1453 accepted、0 rejected**，新增格 proof=complete。
2. 第19页 LR 更新为 **26/80 组**，选档分布3e-5十二组、1e-4九组、1e-5五组、3e-4为0。ERNIE MRL full-family 四档闭合，validation 选3e-5（best_val=0.516094），test r=0.699845973仅报告，不参与选档。
3. 当前 per-base 149/270、complementary 303/324、rank 68/96、equiv 420/420、650M frozen 24/25；①a-4 与④/⑤不变。
4. 当前源包 revision=`20261101_refresh_v86_v97ledger_lr26_ernie_mrl_family`，279 个登记文件，manifest SHA256=`f7abfe573cf4c5577a1c6a662da644038ca9e089863c624f2e7f6d26ff609117`。十张关键嵌图 SHA、32页 lint/layout/CRC、Microsoft YaHei、正文1.5倍行距与 LR 页实际渲染通过。

## 53. 2026-11-01 当前 v98：650M SSP frozen-family 闭合

1. 当前 PPT 为32页，SHA256=`cb3ed7103fec5dd578e45b01c886c5b0265d3e8cc722c3bfea1ba197f6f0ad48`；PDF SHA256=`e3a1a1d507b82bd0da0b2f7e976ae66994834546296c02dae1db02161ed2c024`。输入 **1455 accepted、0 rejected**，两个新增格均 proof=complete。
2. 第8页①a-4：650M SSP frozen-family 三种子 pair-F1=0.3237/0.2711/0.2802，mean≈0.291666667，正式闭合；SSP覆盖28/30，五种任务为27/28/19/17/18。第27页热图对应格显示3，第28/29页成本图同步至v98。
3. RNA-FM MRL full-random default tuning 仅1/4档，LR 111/320、完整组仍26/80；per-base 149/270、complementary 304/324、rank 68/96、equiv 420/420、650M frozen 25/25，④/⑤不变。
4. 当前源包 revision=`20261101_refresh_v87_v98ledger_650m_ssp_family_closure`，282 个登记文件，manifest SHA256=`81fccb0f004ab613475bd586273f4118769334fdffcf936f9f29e5decaa4cb2a`。十张关键嵌图 SHA、32页 lint/layout/CRC、Microsoft YaHei、正文1.5倍行距与第8/27/28/29页实际渲染通过。

## 54. 2026-11-01 v99 staging：展示版保持 v98

1. v99 为 **1456 accepted、0 rejected**；RNA-FM MRL full-random 的1e-4格 r=0.771872145、best_val=0.506725，proof=complete、CUDA 收敛。
2. 该组仅完成两档，仍缺3e-5/1e-5；LR 112/320、完整组保持26/80，不提前选档。无新三种子单元，PPT 与 v87 源包保持 v98。
3. 当前 PPT/PDF SHA256 仍为 `cb3ed7103fec5dd578e45b01c886c5b0265d3e8cc722c3bfea1ba197f6f0ad48` / `e3a1a1d507b82bd0da0b2f7e976ae66994834546296c02dae1db02161ed2c024`。

## 55. 2026-11-02 当前 v100：LR 第28组与 rank16 阶段结果

1. 当前 PPT 为32页，SHA256=`e875cc79c4fe811eb0f01390763612bac0cb75cc7094a649f7ee514e4f10d0a2`；PDF SHA256=`49baa9f9670427aad9f7231ef5b2bb37707c1290b60026366db49f7baa6cc7d5`。输入 **1466 accepted、0 rejected**，10 个新增格均 proof=complete。
2. 第19页 LR 更新为 **28/80 组**，分布3e-5十三组、1e-4九组、1e-5六组、3e-4为0。RNA-FM MRL random 选1e-5、family 选3e-5，test 不参与。第20页写入 SpliceAI random rank16 三种子 mean=0.481795666，rank4/16=69/96；保留 legacy 图与未闭合边界，不与 rank8 直接排名。
3. mega SpliceAI full-family/seed17 macro-F1=0.522046068，仅1/3；第27页覆盖热图由0改为1，第8页仍保留斜线，SpliceAI三种子单元仍为19/30。per-base 150/270、complementary 304/324、equiv 420/420、650M frozen 25/25。
4. 当前源包 revision=`20261102_refresh_v88_v100ledger_lr28_rank16_spliceai`，289 个登记文件，manifest SHA256=`7e318f82cf327cbae2787d11e274cecbcb5de48cd36667ad5c9be687c9c6f93f`。十张关键嵌图 SHA、32页 lint/layout/CRC、Microsoft YaHei、正文1.5倍行距与第8/19/20/27/28/29页实际渲染通过。

## 56. 2026-11-02 v101：650M LoRA 启动，展示版保持 v100

1. v101 新增 0，仍为 **1466 accepted、0 rejected**，PPT 和 v88 源包保持 v100。
2. 唯一未完成的 650M LoRA 为 CRISPR family/seed43，已在自然显存窗口以单格队列启动，父 PID=4122509、训练子 PID=4122556，真实 `--device 0`。启动不等于完成，不修改覆盖热图或性能柱。
3. 证据=`status/complementary_650m_lora_20261102/launch_evidence.json`，SHA256=`b9d1fe1e4e988b7d45a2005031b9172ce4ca1de5dd1b7e424c5f59c6256547df`。

## 57. 2026-11-02 当前 v102：micro SpliceAI family LR 第29组

1. 当前 PPT 为32页，SHA256=`e545b825f661ea8b93a3c551a0515ec9544305ef573a12114d57f719e5f2b15e`；PDF SHA256=`285d7aecd13fa50f21e6c3d4f84c9ca12d6206d6e87ff765598e4ba3501028bf`。输入 **1468 accepted、0 rejected**，两个新增格均 proof=complete。
2. 第19页 LR 更新为 **29/80组**，分布3e-5十四组、1e-4九组、1e-5六组、3e-4为0。micro SpliceAI full-family 四档闭合，validation 选3e-5（best_val=0.001168），test macro-F1=0.338468501仅报告。
3. micro degradation random default 仅1/4档；per-base 150/270、complementary 304/324、rank 69/96、equiv 420/420、650M frozen 25/25。650M CRISPR LoRA 在训，不修改其覆盖或性能图。
4. 当前源包 revision=`20261102_refresh_v89_v102ledger_lr29_micro_spliceai_family`，296 个登记文件，manifest SHA256=`46728646ba0b8d54ded25b38ed04a1c517d5fc5d1a410af57b0921bf3308ff73`。十张关键嵌图 SHA、32页 lint/layout/CRC、Microsoft YaHei、正文1.5倍行距与 LR 页实际渲染通过。

## 58. 2026-11-02 当前 v103：主矩阵、rank 与 LR 批量更新

1. 当前 PPT 为32页，SHA256=`9274ee5e25f812e50beefbc60428e83944a74e8851826e231de178e04fcd0291`；PDF SHA256=`f3fd759639c84ef4e839aee0019ccccc10e05a81ceb9cc4a696c46a8ef080285`。输入 **1537 accepted、0 rejected**，69 个新增格均 proof=complete。
2. 第8页①a-4为 **28/28/20/17/18**：650M CRISPR LoRA-family 和 mega SpliceAI LoRA-random 三种子闭合。第27页同步覆盖，第28/29页成本图使用v103。per-base 153/270、complementary 306/324。
3. 第19页 LR 更新为 **41/80组**，分布3e-5十九、1e-4十二、1e-5九、3e-4一组。RNA-FM modification family 默认档最优，页面明确“必须逐组validation”，不再沿用旧的“默认未被选择”表述；test 不参与。
4. 第20页 rank 更新为 **88/96、29/32组三种子闭合**，写入 degradation 双split、SpliceAI family rank16 和 SSI random rank4 的阶段均值；现有图仍标 legacy，不与rank8直接排名。
5. 当前源包 revision=`20261102_refresh_v90_v103ledger_lr41_main_rank_closure`，301 个登记文件，manifest SHA256=`fcd8022436870149f0a5c97d4d429a3fc240e9462436479390dd09d011244fc3`。十张关键嵌图 SHA、32页 lint/layout/CRC、Microsoft YaHei、正文1.5倍行距与第8/19/20/27/28/29页实际渲染通过。

## 59. 2026-11-02 当前 v104：rank 89/96

1. 当前 PPT 为32页，SHA256=`9c1b76dd2fa9cbc8a2621aa54af8d0df9cee2e4beaffdea2d159027800341f5d`；PDF SHA256=`28b25d044d13d09c80de1e45f343ccd0c84146b3ce8075429a61e7e54f49e07d`。输入 **1539 accepted、0 rejected**，两个新增格均 proof=complete。
2. 第20页 rank 更新为 **89/96、29/32组三种子闭合、剩余7格**。SSI family rank4 仅2/3，不写成闭合；现有图仍标legacy，其他阶段均值和结论不变。
3. ERNIE SSP random 仅2/4档，LR 170/320、完整组仍41/80；per-base 153/270、complementary 306/324、equiv 420/420、650M frozen 25/25，①a-4与④/⑤不变。
4. 当前源包 revision=`20261102_refresh_v91_v104ledger_rank89_ssi_family_n2`，305 个登记文件，manifest SHA256=`95c0e22718e7ebe7be6aa20a11391ec3c14dd939bb23ca7eba68b4cc1ab3e501`。十张关键嵌图 SHA、32页 lint/layout/CRC、Microsoft YaHei、正文1.5倍行距与 rank 页实际渲染通过。

## 60. 2026-11-02 v105–v106：在训与资源门

1. v105/v106 均无新增完成格，仍为 **1539 accepted、0 rejected**，PPT 和 v91 源包保持 v104。
2. rank 剩余7格全部属于SSI；有界等待未生成result，不修改页面。资源核查时空闲22.45GiB，低于650M full的28GiB预算，未强行启动大格。
3. 当前仍有 per-base/LR/rank 的真实训练在运行，待完整证明或自然大模型窗口后再更新。

## 61. 2026-11-02 v107 staging：展示版保持 v104

1. v107 为 **1540 accepted、0 rejected**；ERNIE SSP full-family default tuning pair-F1=0.2127、best_val=0.500993，best_epoch=12、16 epochs，proof=complete、CUDA 收敛。
2. 该组仅一档，LR 171/320、完整组仍41/80，不提前选档。无新三种子单元，PPT 和 v91 源包保持 v104。
3. 当前 PPT/PDF SHA256 仍为 `9c1b76dd2fa9cbc8a2621aa54af8d0df9cee2e4beaffdea2d159027800341f5d` / `28b25d044d13d09c80de1e45f343ccd0c84146b3ce8075429a61e7e54f49e07d`。

## 62. 2026-11-02 当前 v108：SSI family rank4 闭合

1. 当前 PPT 为32页，SHA256=`bbd35c8f9b5fc6b4d795a98c226f956b741036ced8c83cee20239d7a4eace0c8`；PDF SHA256=`610ebaa27e446e08ed7c407ac43d5f577f6e80d3e953f5ff76b2fd69d7eee6e4`。输入 **1541 accepted、0 rejected**，新增格 proof=complete。
2. 第20页 rank 更新为 **90/96、30/32组三种子闭合、剩余6格**。SSI family rank4 三种子 mean=0.597495111，已加入阶段文字；现有图仍标legacy，不与rank8直接排名。
3. 当前 per-base 153/270、complementary 306/324、LR 171/320（41组）、equiv 420/420、650M frozen 25/25；①a-4、④/⑤和 LR 选档不变。
4. 当前源包 revision=`20261102_refresh_v92_v108ledger_rank90_ssi_family_r4`，316 个登记文件，manifest SHA256=`e79a4715075160608f825f5d81cd28e4140b05a69edf48af111d9f4847564676`。十张关键嵌图 SHA、32页 lint/layout/CRC、Microsoft YaHei、正文1.5倍行距与 rank 页实际渲染通过。

## 63. 2026-11-02 当前 v109：mega SpliceAI LoRA-family 首点

1. 当前 PPT 为32页，SHA256=`bed1e634abd53e58c0bcc415740c4d03a3e2da762701b4af3962983de68f716e`；PDF SHA256=`be6a6481d5d996e06a5801a9be0903ef96b6196a5753608bbc4e4dadfe787bd2`。输入 **1543 accepted、0 rejected**，两个新增格均 proof=complete。
2. mega SpliceAI LoRA-family/seed17 macro-F1=0.528533981，仅1/3。第27页覆盖热图由0改为1，第8页仍为 n<3 斜线，SpliceAI三种子覆盖仍20/30；第28/29页成本图同步至v109。
3. ERNIE SSP full-family 的1e-4档完成，当前2/4档，LR 172/320、完整组仍41/80；per-base 154/270、complementary 306/324、rank 90/96、equiv 420/420、650M frozen 25/25。
4. 当前源包 revision=`20261102_refresh_v93_v109ledger_mega_spliceai_family_n1`，319 个登记文件，manifest SHA256=`25dcc3bea404cb05b8daaf51f7edcbb4301c387a6d5077062c98ee953ef8ea88`。十张关键嵌图 SHA、32页 lint/layout/CRC、Microsoft YaHei、正文1.5倍行距与第8/27/28/29页实际渲染通过。

## 64. 2026-11-02 当前 v110：SSI random rank16 首点

1. 当前 PPT 为32页，SHA256=`4c01e9c2f1122da9aead1c2722b53edfb35db1e387f3055e0d01398e515e3243`；PDF SHA256=`151d548f7f202ef38e0c39d4cae8438e25976678a9189b893a5a46c2801019e4`。输入 **1544 accepted、0 rejected**，新增格 proof=complete。
2. 第20页 rank 更新为 **91/96、30/32组三种子闭合、剩余5格**。SSI random rank16/seed17 PCC=0.634591544，仅1/3，不写成闭合；现有图仍标legacy，其他阶段均值不变。
3. 当前 per-base 154/270、complementary 306/324、LR 172/320（41组）、equiv 420/420、650M frozen 25/25；①a-4、④/⑤和 LR 选档不变。
4. 当前源包 revision=`20261102_refresh_v94_v110ledger_rank91_ssi_random_r16_n1`，323 个登记文件，manifest SHA256=`f1d3d5f8b2de180ba2d16d2e2ad6a1836d435b0644aa6ce7ab2f3b528ebd9875`。十张关键嵌图 SHA、32页 lint/layout/CRC、Microsoft YaHei、正文1.5倍行距与 rank 页实际渲染通过。

## 65. 2026-11-02 v111 staging：展示版保持 v110

1. v111 为 **1545 accepted、0 rejected**；ERNIE SSP full-family 的3e-5格 pair-F1=0.2438、best_val=0.445255，proof=complete、CUDA 收敛。
2. 该组已有三档、缺1e-5，LR 173/320、完整组仍41/80，不提前选档。无新三种子单元，PPT 与 v94 源包保持 v110。
3. 当前 PPT/PDF SHA256 仍为 `4c01e9c2f1122da9aead1c2722b53edfb35db1e387f3055e0d01398e515e3243` / `151d548f7f202ef38e0c39d4cae8438e25976678a9189b893a5a46c2801019e4`。

## 66. 2026-11-02 当前 v112：SSI random rank16 第二种子

1. 当前 PPT 为32页，SHA256=`417c5b50358cef089baa6d598103c6e0dd0a1704f5dede02c47042a790b9095e`；PDF SHA256=`90f2f0b7424a5e7b5a11907680c138b15d573ece1ea970d752044281332bc468`。输入 **1546 accepted、0 rejected**，新增格 proof=complete。
2. 第20页 rank 更新为 **92/96、30/32组三种子闭合、剩余4格**。SSI random rank16 的 seed17/29=0.634591544/0.635330892，当前2/3，不写成闭合；现有图仍标legacy，其他阶段均值不变。
3. 当前 per-base 154/270、complementary 306/324、LR 173/320（41组）、equiv 420/420、650M frozen 25/25；①a-4、④/⑤和 LR 选档不变。
4. 当前源包 revision=`20261102_refresh_v95_v112ledger_rank92_ssi_random_r16_n2`，330 个登记文件，manifest SHA256=`fb9ee5b869877e551e1327acff1dfb615f870a35a4e68adb93ad7b07149b8b16`。十张关键嵌图 SHA、32页 lint/layout/CRC、Microsoft YaHei、正文1.5倍行距与 rank 页实际渲染通过。

## 67. 2026-11-02 当前 v113：ERNIE SSP family LR 第42组

1. 当前 PPT 为32页，SHA256=`3e5c3b95c440293d203f5262d94e6bb156738e7c0e84ab8b39cd7e3e58e803a4`；PDF SHA256=`9e4c0be9e0d1e8d51b6efbca3332bece0b8c10a6a720174132aed75e5be22500`。输入 **1547 accepted、0 rejected**，新增格 proof=complete。
2. 第19页 LR 更新为 **42/80组**，分布3e-5十九组、1e-4十三组、1e-5九组、3e-4一组。ERNIE SSP full-family 四档闭合，validation 选1e-4（best_val=0.388270），test pair-F1=0.2975仅报告。
3. 当前 per-base 154/270、complementary 306/324、rank 92/96、equiv 420/420、650M frozen 25/25；①a-4、④/⑤和默认档反例结论不变。
4. 当前源包 revision=`20261102_refresh_v96_v113ledger_lr42_ernie_ssp_family`，334 个登记文件，manifest SHA256=`eb7a3065eef5fba25eb025a4f931075396189de33f6c94251fa9fa6d512c78d2`。十张关键嵌图 SHA、32页 lint/layout/CRC、Microsoft YaHei、正文1.5倍行距与 LR 页实际渲染通过。

## 68. 2026-11-02 当前 v114：SSI random rank16 闭合

1. 当前 PPT 为32页，SHA256=`2064f15759c017dd664dace4230cf1de7e0a1bbdcab124d4c3c3350a971eb492`；PDF SHA256=`2d9a0f8693d92e7c754bd10d77b5bdb44eaf9680218afd377c0b734ab3c212fb`。输入 **1549 accepted、0 rejected**，两个新增格均 proof=complete。
2. 第20页 rank 更新为 **93/96、31/32组三种子闭合、剩余3格**。SSI random rank16 三种子 mean=0.634602631，已加入阶段文字；仅剩 family rank16，现有图仍标legacy，不与rank8直接排名。
3. RNA-FM SSP random default 仅1/4档，LR 175/320、完整组仍42/80；per-base 154/270、complementary 306/324、equiv 420/420、650M frozen 25/25；其他结论不变。
4. 当前源包 revision=`20261102_refresh_v97_v114ledger_rank93_ssi_random_r16_closure`，338 个登记文件，manifest SHA256=`711969fb0eeb7eb7534f1f2068b3c823242755d3f9adc75e21f82d163454a895`。十张关键嵌图 SHA、32页 lint/layout/CRC、Microsoft YaHei、正文1.5倍行距与 rank 页实际渲染通过。

## 69. 2026-11-02 新增 ncRNA 性能总览页（33页）

1. 用户指出原结构只保留机制诊断、缺少修正后的 ncRNA 性能总览。现以 v114 正式台账补图：ncRNA **28/30** 个三种子单元，固定 LR 六柱、mean±SD、斜线=n<3、空白=NA；不是不能形成柱状结论，而是此前漏放。
2. 新增第5页“结论①a-1 ncRNA 性能总览”，原 shuffle/no-shuffle 机制页保留为第6页。双页分别回答“修正后性能如何”和“旧 family 崩溃为何隔离”，不再用机制页代替性能页。后续页顺延：①a-4第9页、LR第20页、rank第21页、覆盖第28页、成本第29/30页。
3. `build_8task_sixbar.py` 复用原六柱聚合与绘图逻辑生成单面板，源包 revision=`20261102_refresh_v98_v114ledger_ncrna_sixbar_overview`，344 个登记文件，manifest SHA256=`4498127752f24a2932529585a98fa43dc383d8ab8cfca8e82948beb4681f3d44`。
4. 克隆顺序导致的 slide33 重名已修复。最终 **33页**，ZIP无重复、CRC正常，lint/layout、Microsoft YaHei、正文1.5倍行距、11张关键嵌图 SHA 与双页实际渲染通过。PPT SHA256=`15dfbef9ffb10fd3776a9d969dbe96bcd18b31584d1e64cadd7c87d52c65cae9`，PDF SHA256=`70f5dfe1a1b00cba8fe92aedb3311f48e0454999b3ab5d1ee3c6cad6c786a0c4`。其他用户手调内容未改。

## 70. 2026-11-02 LR 小格优先调度记录

1. 本项为资源调度，不改变PPT内容。发现650M full队首阻塞后，先暂停旧父3431054并确认唯一子进程43189已 ledger=running，再仅终止父调度，训练不中断。
2. 全部320个 canonical 格按need_gb升序重排，RID/result_dir/need_gb不变，原表备份；以原state-dir启动新父45383，旧子继续，central ledger防重。
3. 新父正在proof扫描，不记训练完成。证据=`status/queue_actions/lr_small_first_rebalance_20261102.json`，SHA256=`f2261b6177f9f4ba85aff54ae7279d6a91fae6f43bdab3b0663956f75514882a`。

## 71. 2026-11-02 当前 v115：rank 95/96

1. 当前 PPT 为33页，SHA256=`eb957ab8c154c555d2b71be1135196038ee18ad3f0e5ff693cf565c1cd98d0e5`；PDF SHA256=`b4d04ecf675779911e10ab2758a53c7a2aede081f6a6dbc2fb1101082c4243ba`。输入 **1553 accepted、0 rejected**，4个新增格均 proof=complete。
2. 第21页 rank 更新为 **95/96、31/32组三种子闭合、剩余1格**。SSI family rank16 为2/3，仍缺seed43；现有图仍标legacy，其他阶段均值不变。
3. RNA-FM SSP random 已有三档、缺1e-5，LR 177/320、完整组仍42/80；per-base 154/270、complementary 306/324、equiv 420/420、650M frozen 25/25。
4. 当前源包 revision=`20261102_refresh_v99_v115ledger_rank95_ssi_family_r16_n2`，348 个登记文件，manifest SHA256=`2a48336dd0d650e82a11c0548c59affe4b0cec17851e08c7109b2f11ac3663b0`。11张关键嵌图 SHA、33页 lint/layout/CRC、Microsoft YaHei、正文1.5倍行距与 rank 页实际渲染通过。

## 72. 2026-11-02 当前 v116：rank 全闭合与 LR 第43组

1. 当前 PPT 为33页，SHA256=`f23c69ad533b139409c93c29e9eea52c0687937d3abca68a8635166a8fd27d3e`；PDF SHA256=`b90f166d5f71795917908dcc2aad104bd278bbfd2ffabf8b44bcca38dd190c32`。输入 **1558 accepted、0 rejected**，5个新增格均 proof=complete。
2. 第21页 rank 更新为 **96/96、32/32组全部闭合**；SSI family rank16 均值0.597398120，现有图仍标legacy，不与rank8直接排名。
3. 第20页 LR 更新为 **43/80组**，默认最优组增至2个。RNA-FM SSP random 默认3e-4最优（best_val=0.571500），test 不参与；LR 181/320，分布19/13/9/2。ERNIE degradation family 仍缺3e-5。
4. 当前源包 revision=`20261102_refresh_v100_v116ledger_rank96_lr43`，353 个登记文件，manifest SHA256=`9d0c18b2b209a411ebb5d93c48125218debd4b7d75cba24254a0e87eae6ec341`。11张关键嵌图 SHA、33页 lint/layout/CRC、Microsoft YaHei、正文1.5倍行距与第20/21页实际渲染通过。

## 73. 2026-11-02 当前 v117：degradation family LR 第44组

1. 当前 PPT 为33页，SHA256=`bad37b10d3fdfe5c421788452aec8fe200b257e30b7de0a48b39fb0e793d0e9d`；PDF SHA256=`d6430dc92cc0dbf32ea9e3abd324b56e161219a38e2a5cf536a74f08426bfe08`。输入 **1562 accepted、0 rejected**，4个新增格均 proof=complete。
2. 第20页 LR 更新为 **44/80组**，分布3e-5二十组、1e-4十三组、1e-5九组、3e-4两组。degradation family 选3e-5（best_val=0.205632），test 不参与；random default仍缺。
3. 计数审计：v113–v116 accepted=173/174/176/180，此前阶段文档均多1；v117=184。PPT仅显示完整组，图意与选档不受影响。
4. 当前源包 revision=`20261102_refresh_v101_v117ledger_lr44_ernie_degradation`，357 个登记文件，manifest SHA256=`4aea79e4e400a6d73045fe6d5dfe2bea5e1438de5307ac18956dc4aa39a5f7c1`。11张关键嵌图 SHA、33页 lint/layout/CRC、Microsoft YaHei、正文1.5倍行距与 LR 页实际渲染通过。

## 74. 2026-11-02 v118 staging：展示版保持 v117

1. v118 为 **1563 accepted、0 rejected**；ERNIE SSP full-random 的1e-4格 pair-F1=0.3052、best_val=0.439936，proof=complete、CUDA 收敛。
2. 该组已有三档、缺 default，LR 185/320、完整组仍44/80，不提前选档。无新三种子单元，PPT 与 v101 源包保持 v117。
3. 当前 PPT/PDF SHA256 仍为 `bad37b10d3fdfe5c421788452aec8fe200b257e30b7de0a48b39fb0e793d0e9d` / `d6430dc92cc0dbf32ea9e3abd324b56e161219a38e2a5cf536a74f08426bfe08`。

## 75. 2026-11-02 当前 v119：ERNIE SSP random LR 第45组

1. 当前 PPT 为33页，SHA256=`fd8908ae4071913292b4d177c22114d00cf87f83499eb92de599ad9377788eb6`；PDF SHA256=`8ed95f15f868db550dcd9322f3313b89d00ce481a88ddde981fb49da851e85d0`。输入 **1564 accepted、0 rejected**，新增格 proof=complete。
2. 第20页 LR 更新为 **45/80组**，分布3e-5二十组、1e-4十四组、1e-5九组、3e-4两组。ERNIE SSP full-random 四档闭合，validation 选1e-4（best_val=0.439936），test pair-F1=0.3052仅报告。
3. 当前 per-base 154/270、complementary 306/324、rank 96/96、equiv 420/420、650M frozen 25/25；①a-4、④/⑤和默认档反例结论不变。
4. 当前源包 revision=`20261102_refresh_v102_v119ledger_lr45_ernie_ssp_random`，364 个登记文件，manifest SHA256=`f52c318385550b1bd0227a1ee23f1eaa243553c05096af9c16fbd0eb9a6bfde0`。11张关键嵌图 SHA、33页 lint/layout/CRC、Microsoft YaHei、正文1.5倍行距与 LR 页实际渲染通过。

## 76. 2026-11-02 v120–v121：长训与资源复核

1. v120/v121 均无新增完成格，仍为 **1564 accepted、0 rejected**，PPT 和 v102 源包保持 v119。
2. SpliceAI seed29 的 plateau 为 RUNNING，best_epoch=0、stale=2/3，已有3个epoch记录；seed43和degradation random default 为pre-plateau，均不修改页面。
3. 资源核查时空闲23.36GiB，低于650M full的28GiB预算，未强行启动。证据=`status/inflight_progress_20261101_v121.json`，SHA256=`f475ef816c2c0b2f6a34a5545ffe2bfb184ac661cbfbb7217d87d47b7883ea21`。

## 77. 2026-11-02 当前 v123：mega SpliceAI LoRA-family 第二种子

1. 当前 PPT 为 **33页**，SHA256=`d942e4ff8442f0afd748dd9ceaa74894b685246206dc67c2c550bcbb1ddbaaa5`；PDF SHA256=`b2f4351c7b499ce21c294ab161f49547138601ffad02e1ef462cb509e4ec2413`。输入 **1565 accepted、0 rejected**，新增seed29 proof=complete，macro-F1=0.5265341727629625、best_epoch=0、4 epochs；独立证明 SHA256=`1bac2265fa7d309a5b284b51611004cc299d6c4ac3f2b38201ac4ccbe89ff534`。
2. mega SpliceAI LoRA-family 为 **2/3**（seed17=0.528533981、seed29=0.526534173），仍缺seed43；第9页保留n<3斜线，第28页该格由1改为2，SpliceAI三种子覆盖仍20/30，不提前写闭合。
3. 当前 per-base=154/270、complementary=306/324、LR=186/320（45/80组，20/14/9/2）、rank=96/96、equiv=420/420、650M frozen=25/25；ncRNA性能总览/机制双页和其他用户手调内容保持。
4. 当前源包 revision=`20261102_refresh_v103_v123ledger_mega_spliceai_family_n2`，374个登记文件，manifest SHA256=`8e50aa4789314dac72f50e6d3b2da99db37f50d02e69f63f030d98598f3116a6`。33页lint/layout/CRC、11张关键嵌图SHA和第9/28/29/30页实际渲染通过；成本图源与说明一致。

## 78. 2026-11-02 v124 staging：共享锁小格补位，展示版保持v123

1. v124新增0，仍为 **1565 accepted、0 rejected**；当前33页PPT/PDF及374文件源包均保持v123，不重写图片或科学结论。
2. 新补位父63074与旧per-base父3431052共享state-dir/model locks，仅处理34个need≤7GiB未完成格；注册表SHA256=`2031be076eae1908ea8e591b7c37e3d9d0f3b70f08f9953e8ec542d869788f35`。旧per-base与LR父45383不重启。
3. 新子63193为RNA-FM SpliceAI full-random/seed17/lr1e-5，device0、best-val协议。核查时GPU used/free=16061/16051MiB，下一格16GiB和650M full 28GiB均不强行启动。
4. 在训证据=`status/queue_actions/perbase_small_fill_20261102.json`，SHA256=`ef12ad58578a7067934422aaf11b2854fcf4e2e2deb66a8314d83c7091aa2cb7`；不是完成证明，后续完整proof通过才改图。

## 79. 2026-11-02 v126–v127 staging：历史图件归档，PPT不变

1. v126/v127新增0，仍为 **1565 accepted、0 rejected**；33页PPT/PDF保持v123，PPT SHA256=`d942e4ff8442f0afd748dd9ceaa74894b685246206dc67c2c550bcbb1ddbaaa5`。
2. 20261028源包仍被第6页ncRNA shuffle诊断、正式图CSV及分类组合图机制坐标引用，因此不整体归档。仅30个无现役引用的历史图件移至 `archive_20261102/绘图数据/figure_source_data_20261028_legacy_figures/`，11个现役图件/数据文件保留。
3. 移动前manifest和30文件哈希保留，moved manifest SHA256=`b762d3af8cd038dece84a9d01f572a0ba403961f58fa7c0193db6359bb24280e`；现役81文件manifest SHA256=`45fa55e9057eff66d19c2104991212114e10cf9b60ecc067e7ceaf4657177bc9`。
4. v14源包374文件、分类组合图53文件及归档30文件逐哈希通过；当前PPT ZIP CRC正常，页面、嵌图和用户手调内容均未改变。

## 80. 2026-11-02 v130 staging：在训 PID 映射纠偏，PPT不变

1. v130新增0，仍为 **1565 accepted、0 rejected**；33页PPT/PDF和v103源包保持v123。
2. `finetune_spl`命令行不含task，后续以PID/manifest为唯一映射依据。PID63193/58794/54448实际均为SpliceAI，不是degradation；此前交接文字已更正，无同RID重复训练。
3. mega seed43与ERNIE seed17已有epoch0，ERNIE seed101两轮stale=1/3，RNA-FM seed17 pre-plateau；均不修改性能图。历史degradation PID49138 OOM与当前SpliceAI PID54448不同RID。
4. 纠偏证据=`status/inflight_progress_20261101_v130.json`，SHA256=`7f29abe189eb26cbfceaff7b7c6119258cdf1ffff77b7ba9926aa1f538163c94`，替代v128错误任务映射。

## 81. 2026-11-02 v132 staging：GPU 进程实证，PPT不变

1. v132新增0，仍为 **1565 accepted、0 rejected**；33页PPT/PDF与v103源包保持v123。
2. nvidia-smi确认4个训练PID均实际占用GPU，显存分别为3926/3312/3312/3482MiB，无CPU静默降级。
3. 证据=`status/inflight_gpu_processes_20261102.json`，SHA256=`a517e11fab1d71c08e73bc0c656711b34aa50a0cc266007760a93dd904b686fa`；只证明运行设备，不修改性能图或完成计数。

## 82. 2026-11-02 调度修复与 OOM 恢复，PPT不变

1. v133新增0，仍为 **1565 accepted、0 rejected**；33页PPT/PDF与v103源包保持v123。
2. `expansion_queue.py`已改为外部模型锁占用时保留pending、跨模型继续、下轮重试；旧代码回归失败，修复后完整调度测试连续两次51 passed。提交`87d1c28`已推送。
3. OOM恢复父71153仅登记原degradation失败RID，共享LR state-dir/model locks；启动时free=14.677GiB、无子进程，等待显存和模型锁，不强行启动。注册表SHA256=`14cb904f637d82f29ffa2a9d06518117585e68ea07a903927375bfe0ace8650c`。
4. 在训证据=`status/queue_actions/lr_oom_recovery_20261102.json`，SHA256=`4dee861cb3fd11714aca9efb107f42d7ea3630b5985ff70dd12890b9efb6e383`；不改变任何性能图或完成计数。

## 83. 2026-11-02 v134–v135：生产等待验证，PPT不变

1. v134/v135新增0，仍为 **1565 accepted、0 rejected**；33页PPT/PDF与v103源包保持v123。
2. 恢复父71153正常，原OOM RID无新增manifest记录、无子进程，pending等待未被错误跳过，生产环境验证模型锁修复生效。
3. 证据=`status/queue_actions/lr_oom_recovery_wait_check_20261102.json`，SHA256=`99218d3f9cb6274327042e40d89f7e4629b14f98563e0877e5d548964682dbde`；只验证调度行为，不改变性能图。

## 84. 2026-11-02 v136–v137：在训 plateau 进展，PPT不变

1. v136/v137新增0，仍为 **1565 accepted、0 rejected**；33页PPT/PDF与v103源包保持v123。
2. ERNIE seed17第二轮loss降至0.003239；seed101三轮后stale=2/3，尚未收敛；mega与RNA-FM继续长epoch训练，不更新性能图。
3. 证据=`status/inflight_progress_20261101_v136.json`，SHA256=`d14c2e0e11bf67279740dcf17cfbb6342ef89cbedf62dae3b477023dbdf12d78`；stale=2/3不等于完成。

## 85. 2026-11-02 v140：日志与 plateau 分离验收，PPT不变

1. v140新增0，仍为 **1565 accepted、0 rejected**；33页PPT/PDF与v103源包保持v123。
2. mega epoch1 loss=0.001070；RNA-FM日志有epoch0/1，但plateau尚未更新，不能记收敛；ERNIE继续训练。
3. 证据=`status/inflight_progress_20261101_v140.json`，SHA256=`a84327420499adebc68aa5812855cee9a9402a607348ef2d036dc1b397b53f89`；日志进展不修改性能图或完成计数。

## 86. 2026-11-03 当前 v145：68 格集中闭合与中文渲染修复

1. 当前PPT为 **33页**，SHA256=`c8987fb49f832dea90b4a1938884127c44dc1a08aae863f7f493d7bdbd8e19a5`；PDF SHA256=`fd6125244ba2eef2fcaac0bd3e37c7e28215ef4be6cc78cbbd0c84ff8b4b601f`。v144/v145合计 **1633 accepted、0 rejected**，68格独立proof通过。
2. 第9页更新为CRISPR/SSP/SpliceAI/degradation/SSI=28/28/25/24/25；148M八任务全闭合。mega SpliceAI LoRA-family三种子均值0.505213649，其他未闭合格保持斜线或NA。
3. 第20页LR更新为 **194/320、47/80组**，选档20/14/11/2；ERNIE SpliceAI family/random均选1e-5，test不参与。第28页同步改为“148M八任务六臂均三种子闭合”，第29/30页图源更新至v145。
4. 源包revision=`20261103_refresh_v104_v145ledger_spliceai25_degradation24_ssi25_lr47`，429个登记文件，manifest SHA256=`792db6e9cef61eaf238b88d3aa82b76cb956f1421ca3d6bb5bc18c28ffd3ad98`。
5. lint/layout/ZIP CRC与嵌图SHA通过；第9/20/28/29/30页实际渲染通过。LibreOffice对原始PPT也缺中文，不是PPT内容故障；最终PDF由原生PowerPoint导出，中文、字号与布局正常。

## 87. 2026-11-03 当前 v146：650M SpliceAI LoRA-random 首点

1. 当前PPT为 **33页**，SHA256=`176a32ccc9b5517016c66546b226270ccdc0a827bca0b41c2d4b2adbfbe520a2`；PDF SHA256=`0188c6d005153949bfa6a723f8965cea362a80eebf116a1b8fe419f576f6d505`。输入 **1636 accepted、0 rejected**，3格proof=complete。
2. 650M SpliceAI LoRA-random/seed17 macro-F1=0.548525955，仅n=1；第9页斜线保留，第28页覆盖由0改1，不写三种子闭合。148M八任务全闭合说明保持。
3. per-base=216/270、complementary=306/324、LR=196/320；完整LR组47/80与选档20/14/11/2不变。ERNIE SSI负PCC只作tuning诊断。
4. 源包revision=`20261103_refresh_v105_v146ledger_650m_spliceai_lora_random_n1_lr196`，433个登记文件，manifest SHA256=`6c6457d748f277cb094232a4cc8a02d84573537ad951bb7ba841184d626c5f6b`。33页lint/layout/CRC与第9/28/29/30页原生渲染通过。
