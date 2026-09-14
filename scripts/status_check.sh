#!/bin/bash
# 服务器端巡检脚本: 下载/环境/训练/磁盘 一站式状态
R=/mnt/cunyuliu/rna-ft-eval
echo "===== RNA-Ft-Eval 巡检 $(date '+%F %T') ====="

echo "--- [1] 下载进度 ---"
if ps aux | grep -q "[d]ownload_all.py"; then
  echo "downloader: RUNNING"
  tail -5 $R/logs/download_all.log 2>/dev/null
else
  echo "downloader: not running"
  tail -3 $R/logs/download_all.log 2>/dev/null
fi
du -sh $R/data/beacon_raw/* 2>/dev/null | head -15
du -sh /mnt/cunyuliu/hf_home 2>/dev/null

echo "--- [2] rnaft 环境 ---"
/home/cunyuliu/miniconda3/envs/rnaft/bin/python -c "
mods = ['torch','transformers','peft','sklearn','lightgbm','datasets']
import importlib
ok = []
for m in mods:
    try:
        mod = importlib.import_module(m)
        ok.append(m + '=' + getattr(mod,'__version__','?'))
    except Exception:
        ok.append(m + '=MISSING')
print(' '.join(ok))
import torch
print('cuda:', torch.cuda.is_available())
" 2>&1

echo "--- [3] ledger 状态 ---"
cat $R/ledger.jsonl 2>/dev/null | python3 -c "
import json,sys,collections
c = collections.Counter()
for line in sys.stdin:
    try:
        r = json.loads(line)
        c[(r.get('strategy'), r.get('status'))] += 1
    except Exception:
        pass
print(dict(c) if c else 'ledger empty')
"

echo "--- [4] 训练进程 ---"
ps aux | grep -E "[r]nafteval|[f]inetune_one" | head -10 || echo "无训练进程"

echo "--- [5] GPU ---"
nvidia-smi --query-gpu=index,memory.used,memory.total,utilization.gpu --format=csv,noheader

echo "--- [6] 磁盘 ---"
df -h /home/cunyuliu /mnt/cunyuliu 2>/dev/null | tail -2
du -sh /home/cunyuliu 2>/dev/null
echo "===== 巡检结束 ====="
