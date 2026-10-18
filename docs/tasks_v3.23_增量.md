# tasks 增量回填 v3.23（2026-10-18 · 新集群恢复 + 8 任务扩展启动）

> 本文件为本地 tasks.md（交接文档/）的增量补丁文档。本地目录当前被 macOS TCC 闸住（Operation not permitted），无法直接编辑原文件；本补丁先落工作目录 + 服务器 docs/，待权限恢复后合并回 ~/Documents/.../交接文档/tasks.md 并升 v3.23。

## A. 新集群环境重建（RTX 5090 单卡，全部完成 ✅）

- [x] 环境重装：torch 2.11.0+cu128（**Blackwell sm_120 必需**——老 2.5.1+cu121 不认 5090）+ transformers 4.45.2 等 + datasets/torchmetrics/torchdata 补齐
- [x] 代码恢复：GitHub HEAD 7a77f63（rna-ft-eval）+ aca9a2c（rna-scaling，比备份新 3 commits）
- [x] 2ceping.zip 94G 解压 + 布局重排（/root/rnaft 运行时 + /root/hf_home 27G + /root/rna-sc/runs 27G）
- [x] RNA-Sc 7 ckpt 文件名逐一对上迁移指南期望；NB pretrained.pt md5 一致；S0 cluster_split md5 一致
- [x] 路径策略：fuse 盘禁 symlink/bind → sed 全仓 43 处 /mnt/cunyuliu→/root + llr_env 软链（/home 是 overlay 可用）
- [x] **单格复算：micro frozen s17 random ACC 0.7366 ≈ 历史 0.739 —— 数值复现 ✅**（迁移指南 §四.3 验收通过）

## B. 队列与监控（在飞）

- [x] q5090.sh：audit_1016 22 缺格串行队列（mega e3 8 + 650M e3 13 + AIDO mrl 1），首格收敛中，显存 31.5/32G
- [x] monitor_loop.sh：容器无 cron → 15min 守护（快照 + worker 死亡自动重拉 + S0 哨兵自动启 E6）
- [x] E6 官方 18 格：ledger 已注册 18 pending（ERNIE/RNA-FM/NB × lora@3e-4/full@1e-5 × 3 种子，§11.3-B 协议）；**阻塞待 S0 文件**（见 D）

## C. 8 任务扩展（用户 10-18 指令，等拍板）

- [x] 选型讨论稿发出（RBP 二分类 / 降解回归 / 剪接 3 分类 / 碱基级回归 a-eCLIP 或 b-配对概率）
- [ ] 用户拍板第 4 类 → dataset adapter × 4 + runner 扩展 → 8 任务矩阵队列派发
- [ ] 结论①-⑥ 全部图升 8 任务口径（含问题 2/3/4/5/6 处置）
- [ ] E6 补官方模型 18 格（遗留任务）落地 → e6 表刷新 → 结论⑤B/⑥ 升级

## D. 缺失资产清单（需用户动作）

- [ ] **S0 文件**：orico `07_tokenizer-benchmark/data/derived/split/release22_split_8080.parquet`（6.3G）——E6 全部 18 格的前置；zip 内无、r22_train_rfamcap 只有 train 档、zip 内两个大 corpus parquet 尾部损坏（PAR1 无 footer）
- [ ] **HydraRNA 3 权重**：orico `08_hf_home/models--hydrarna/`（965M，md5 2a805ae7/63664eb9/c168ac98）——16 架构第 16 席
- [ ] 本地 TCC：~/Documents/课题idea 目录 + /Volumes/orico-disc 均被闸（tccutil reset 无效）——需要用户在系统设置给终端/IDE 授"完全磁盘访问"，或手动把上述文件拷到工作目录

## E. 已知适配项（下一 session）

- [ ] AIDO/RiboSpan slow tokenizer 新 torch 行为（'Invalid key...backend Encoding'）——按 0926 _load_vendored 补丁思路修
- [ ] mRNABERT transformers_modules 搜索路径（bert_layers 缺失）
- [ ] q5090 跑完 22 格 → audit 归零 → E3 大模型车道图 → PPT s10
- [ ] 代码提交 GitHub：q5090.sh / monitor_loop.sh / cron_5090.sh / 路径补丁 commit

**纪律一至七条全部延续**；新增第八条：**新集群硬件换档（A100-40G×8 → RTX5090-32G×1）后，任何跨集群数值对比必须先过单格复算基准（micro frozen 0.7366 已建立），大格 bs 协议按 32G 卡重标**。
