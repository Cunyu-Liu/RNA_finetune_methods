#!/bin/bash
# 服务器端 cron 巡检: 每30分钟写 status 快照 + ledger 汇总 + E6 训练进程/待办格
R=/mnt/cunyuliu/rna-ft-eval
mkdir -p $R/status
OUT=$R/status/status_$(date +%Y%m%d_%H%M).md
{
echo "# RNA-Ft-Eval 服务器巡检 $(date)"
echo "## GPU"
nvidia-smi --query-gpu=index,memory.used,memory.total,utilization.gpu --format=csv,noheader
echo "## ledger 汇总"
python3 -c "
import json, collections
c = collections.Counter(); rows = []
for line in open('$R/ledger.jsonl'):
    try:
        r = json.loads(line); c[(r.get('strategy'), r.get('status'))] += 1; rows.append(r)
    except: pass
print(dict(c))
for r in rows[-5:]:
    print(r.get('run_id'), r.get('status'), r.get('value'), r.get('wall_sec'))
"
echo "## E6 未完成格"
python3 -c "
import json
for line in open('$R/ledger.jsonl'):
    try:
        r=json.loads(line)
        if 'e6forgetting' in r.get('run_id','') and r.get('status')!='done':
            print(r.get('status'), r.get('run_id'))
    except: pass
"
echo "## E6 训练进程"
ps aux | grep -E "[e]6_forget" | awk '{print $2, $13, $14, $15, $16, $17, $18}' | head -10
echo "## 队列 worker"
ps aux | grep -E "[q]_e6_ext" | awk '{print $2, $12, $13, $14}' | head -10
echo "## 磁盘"
df -h /home/cunyuliu /mnt/cunyuliu | tail -2
} > $OUT 2>&1
ls -t $R/status/status_*.md 2>/dev/null | tail -n +200 | xargs rm -f 2>/dev/null
