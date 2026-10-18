# STATUS SNAPSHOT 2026-10-18 晚（新集群 RTX 5090 环境重建 + 恢复 + 队列重启 + 8 任务扩展讨论）

> 新集群：px2-jcy.matpool.com:29375（matpool 容器，**单卡 RTX 5090 32G**，16 核 60G RAM，/ 300G overlay，/teams fx 网络盘 92G 剩余）
> 代码：/home/cunyuliu/rna-ft-eval（GitHub HEAD `7a77f63`）+ /home/cunyuliu/rna-sc（HEAD `aca9a2c`）
> 运行时：/root/rnaft（ledger 2293→2315 行，随 q5090 增长）；权重 /root/hf_home + /root/rna-sc/runs

## 一、本轮 session 完成的恢复链（全部验证过）

| 项 | 结果 | 验证证据 |
|---|---|---|
| SSH 接入 | ✅ 密码认证（"hi," 是密码前缀） | 登录成功 + hostname ZDLg6Y |
| conda 环境 | ✅ llr_env 重建：**torch 2.11.0+cu128**（RTX 5090 sm_120 需要，老 torch 2.5.1+cu121 不支持 Blackwell）+ transformers 4.45.2 + numpy 2.2.6 + datasets + torchmetrics + torchdata | `torch.cuda.is_available()=True`，compute capability (12,0)，真 CUDA 张量计算 8.0 |
| 代码 | ✅ GitHub 拉取 | RNA_finetune_methods HEAD 7a77f63；RNA-scaling HEAD aca9a2c（比备份快照新 3 commits） |
| 2ceping.zip 解压 | ✅ 94G → /root/rnaft_restore（03 rna-sc 94G + 04 rna-ft-eval 8.4G） | du 实测 |
| ledger + artifacts + data | ✅ 2293 行 + 2237 artifacts + family_splits/beacon_raw/e3_subsets | wc -l + ls 抽查 |
| pypath vendored | ✅ peft 0.13.2 全套（9592 文件） | ls pypath/peft |
| HF 10 模型 | ✅ hf-mirror 重下 27G 全部成功（rinalmo×3/ernie/rnafm/splicebert/utrlm/mrnabert/AIDO/RiboSpan），布局 models/<repo--name>/snapshots/main/（**注意 hub 命名是双横线**） | snapshot_download 10/10 OK + du 实尺寸 |
| AIDO/RiboSpan vendored loader py | ✅ gbrna_pkg/ribospan_pkg 拷入 snapshot | ls 确认 |
| RNA-Sc 7 终版 ckpt | ✅ 27G，文件名与迁移指南 §三 3c **逐一对上**（1M nt1900121822 / 10M nt1900171155 / 30M nt1900121822 / 100M+300M+650M nt1900122218 / b59 nt5800296014） | ls + nt 排序核对 |
| NucleicBERT | ✅ pretrained.pt 1616879490 字节，md5 `170a248d...` 与备份总账一致 | md5sum |
| 路径补丁 | ✅ 代码内 43 处 `/mnt/cunyuliu` → `/root`（sed 全仓）+ /home/cunyuliu/llr_env 软链 | grep 0 残留 |
| 单格复算 | ✅ **RiNALMo-micro frozen s17 random 500样本 2ep → ACC 0.7366**（历史 e33500 值 0.739，同任务同 seed 同切分协议——**科学数值在新硬件复现**） | ledger done 行 + result.json |
| 模型加载冒烟 | ✅ NB/RNA-Sc-100M/300M/b59 直接 OK；RiNALMo 系 OK（load+forward 验证过，之前 FAIL 是测试脚本张量转换问题）；AIDO/RiboSpan/mRNABERT 有三个已知适配项（见 §三） | 见 §三 |

## 二、队列与监控（当前在飞）

1. **q5090.sh**（scripts/，setsid 后台）：audit_1016 实测 22 缺格（mega e3 尾 8 + 650M e3 尾 13 + AIDO mrl s43 1）按 bs 协议串行跑——**首格 mega lora e3-3000 已在收敛**（epoch 0→7 loss 2.50→0.58，显存 31.5G/32G 占满）
2. **monitor_loop.sh**（scripts/）：容器无 crontab → 用 while-true 守护（15min）：GPU/ledger/worker 存活快照 + worker 死亡自动重拉 q5090 + **S0 文件哨兵**（见下）
3. **E6 官方 18 runs**（ERNIE/RNA-FM/NB × {lora@3e-4, full@1e-5} × 3 种子）：ledger 已注册 18 pending 行（我方派发协议与 §11.3-B 一致）；**阻塞在 S0 数据文件**（见 §三-1），monitor 的哨兵逻辑会在文件就位后自动启动队列
4. 磁盘策略：/teams fx 盘 92G 剩余且配额敏感 → 大型权重/运行时全留 /root（300G 本地盘），代码在 /home（git 仓可提交）；用户要求"大文件放 /teams 项目文件夹"与磁盘现实冲突，已在报告中说明

## 三、发现的问题（三件需要用户处理 + 两件已自愈）

1. **S0 held-out 数据文件缺失**（E6 遗忘轴全部 18 格阻塞）：`release22_split_8080.parquet`（6.3G，3,357,201 行，含 canonical_sequence + split_membership）不在 2ceping.zip 内；zip 里仅有 `release22_cluster_split.parquet`（cluster_id+split 两列，md5 与老备份一致 ✅）和 `r22_train_rfamcap.parquet`（**但只有 train 档 566077 行**——test/family_test 的序列不在）。尝试用 r22_train_rfamcap 重建 S0 失败（无 test 序列）。zip 内 `rinalmo_corpus_v1.parquet` / `r22_train_reweighted.parquet` 两个大文件**尾部损坏**（PAR1 头无 footer，重解压 md5 相同仍不可读——疑似 10-15 备份时文件仍在写入）。→ **需要用户从 orico 盘 07_tokenizer-benchmark 目录补传 release22_split_8080.parquet**（或允许用替代池重建——但那样 pre_nll 与老集群不可比，不推荐）。
2. **orico 外置盘本机 TCC 读权限被闸**：/Volumes/orico-disc 对当前 shell 全部 Operation not permitted（tccutil reset 无效，Finder 也拿不到）。我这边无法直接从盘上取文件——需要用户在 Finder/终端手动授权"完全磁盘访问"或将文件拖到工作目录。
3. **HydraRNA 3 权重（965M）不在 2ceping.zip**（在 orico 08_hf_home，未打包）——SSM 观察臂，不阻塞预印本主线，但 16 架构里它缺席。
4. 自愈：conda 阿里源 404 → 换清华源；fuse 盘不支持 symlink/bind-mount → 改 sed 全仓路径补丁方案（比复制 60G 数据快 10 倍）；RTX 5090 需 cu128 → torch 2.11（**注意：老集群是 torch 2.5.1，新集群是 2.11+cu128，transformers 4.45.2 不变——AIDO/RiboSpan vendored loader 对 torch≥2.6 的 .bin 手工加载补丁在新 torch 下需要复测**，正是 §一 冒烟 FAIL 的三个模型）。
5. **AIDO.RNA-1.6B / RiboSpan-1K-40 / mRNABERT 三模型加载待适配复核**（pypath 的 multimolecule 在新 torch 下 forward OK；AIDO/RiboSpan 报 tokenizer 错 'Invalid key...backend Encoding'——是 slow tokenizer 在新 transformers/torch 下的行为变化，需按 0926 老补丁思路修 _load_vendored；mRNABERT 报 transformers_modules.main.bert_layers 缺失——custom loader 的模块搜索路径问题）。q5090 队列里 AIDO mrl 格会在跑到时暴露同一问题，届时修复（不阻塞 mega/650M 20 格）。

## 四、8 任务扩展（用户 10-18 新指令，等待拍板）

用户要求：PPT 全部结论从 3 任务（ncRNA/MRL/m6A）扩到 **4 类 × 2 = 8 任务**（补碱基级回归类 + 每类再补 1 个），贯穿每个结论图。已发选型讨论稿：
- 序列级分类：ncRNA + **RBP 结合二分类**（BEACON/eCLIP）
- 序列级回归：MRL + **mRNA 降解回归**（OpenVaccine）
- 碱基级分类：m6A + **剪接位点 3 分类**（SpliceAI）
- 碱基级回归（新类）：**候选 a) eCLIP 信号强度回归**（科学干净，需接数据）或 **b) bpRNA 配对概率回归**（数据现成，GT 是 0/1 有被质疑风险）——**推荐 a，等用户拍板**
新增 3 任务均可从 BEACON 复用（家族切分协议延续）。其余 5 个 PPT 问题（rk=8 重测/配方含义/ncRNA 坍缩剖析/等价线数据量扫描/机制可视化 3 模型×6 任务）全部在 8 任务数据落地后执行。

## 五、下一步（优先级序）

1. **用户拍板 8 任务第 4 类选型** → 写 3+1 个 dataset adapter + runner 扩展 → 派 8 任务矩阵队列（先小模型全任务，再大模型关键臂）
2. **用户补传 S0 文件**（orico 07_tokenizer-benchmark/data/derived/split/release22_split_8080.parquet）→ monitor 哨兵自动启动 E6 官方 18 格
3. q5090 22 格跑完（预计 2-3 天）→ audit_1016 归零 → 刷 E3 大模型车道图 → PPT s10 换图
4. AIDO/RiboSpan/mRNABERT 新 torch 适配修复（跑 q5090 到 AIDO 格前完成）
5. 每 15min monitor 快照 + 每日 TRAINING_LOG 追加；代码提交 GitHub（q5090.sh / monitor_loop.sh / cron_5090.sh / 路径补丁）

## 六、交接检查清单（下一执行人）

- [ ] 读本文件 + 8 任务讨论稿（等用户拍板结果）
- [ ] `tail /root/rnaft/logs/q5090.log` 看队列进度；`ps aux | grep finetune_one` 看 worker
- [ ] monitor_loop 活着：`pgrep -f monitor_loop`
- [ ] audit_1016 缺口：`PYTHONPATH=... python scripts/audit_1016.py`（当前 22 → 目标 0）
- [ ] AIDO/RiboSpan/mRNABERT 适配（§三-5）
- [ ] S0 哨兵：文件到位后 E6 自动开跑（看 e6_official_5090.log 的 E6_OFFICIAL_RUNNING 标记）
- [ ] 纪律一至七条全部延续（真 CUDA / smoke 不当结论 / B23 双证 / need 同 bs / ledger 原始行 / tag 分段 / 换图双重验证）
