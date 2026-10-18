#!/bin/bash
# cron_5090_status: monitor training progress + queue health + GPU (for RTX 5090 single-card cluster)
R=/root/rnaft
cd /home/cunyuliu/rna-ft-eval
{
echo "=== 5090 status $(date '+%F %T') ==="
echo "GPU: $(nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader)"
echo "ledger: $(wc -l < $R/ledger.jsonl) rows, done=$(grep -c '\"status\": \"done\"' $R/ledger.jsonl 2>/dev/null || echo NA)"
echo "--- q5090 tail ---"
tail -4 $R/logs/q5090.log 2>/dev/null
echo "--- e6 official tail ---"
tail -3 $R/logs/e6_official_5090.log 2>/dev/null
echo "--- worker alive ---"
ps aux | grep -cE '[f]inetune_one|[e]6_forget'
} >> $R/logs/cron_5090_status.log 2>&1
