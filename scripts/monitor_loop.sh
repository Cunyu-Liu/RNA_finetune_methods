#!/bin/bash
# monitor_loop: persistent monitoring loop (cron unavailable in this container) — runs every 15 min,
# logs status, restarts q5090 if all workers dead and cells remain, triggers e6-official when S0 file appears.
cd /home/cunyuliu/rna-ft-eval
LOG=/root/rnaft/logs/monitor_loop.log
while true; do
  {
  echo "=== monitor $(date '+%F %T') ==="
  nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader
  echo "ledger rows=$(wc -l < /root/rnaft/ledger.jsonl) done=$(grep -c '\"status\": \"done\"' /root/rnaft/ledger.jsonl)"
  alive=$(ps aux | grep -cE '[f]inetune_one|[e]6_forget')
  echo "workers_alive=$alive"
  tail -2 /root/rnaft/logs/q5090.log 2>/dev/null
  if [ "$alive" -eq 0 ]; then
    # count remaining missing cells
    miss=$(PYTHONPATH=/root/rnaft/pypath:/home/cunyuliu/rna-ft-eval:/home/cunyuliu/rna-sc HF_HOME=/root/hf_home /root/miniconda3/envs/llr_env/bin/python scripts/audit_1016.py 2>/dev/null)
    echo "missing_after_q=$miss"
    if [ "${miss:-99}" -gt 0 ] && ! grep -q "q5090 ALL DONE" /root/rnaft/logs/q5090.log 2>/dev/null; then
      echo "RESTART q5090 (workers dead, ${miss} cells missing)"
      setsid nohup bash /home/cunyuliu/rna-ft-eval/scripts/q5090.sh >> /tmp/q5090_outer.log 2>&1 < /dev/null &
    fi
  fi
  # S0 file sentinel: when user provides release22_split_8080.parquet with correct schema, start e6 official queue
  if [ -f /root/tokenizer-benchmark/data/derived/split/release22_split_8080.parquet ]; then
    ok=$(/root/miniconda3/envs/llr_env/bin/python -c "
import pandas as pd
try:
    df = pd.read_parquet('/root/tokenizer-benchmark/data/derived/split/release22_split_8080.parquet', columns=['canonical_sequence','split_membership'])
    held = df['split_membership'].isin(['test','family_test']).sum()
    print('OK' if held > 5000 else 'BAD')
except Exception as e:
    print('BAD')
" 2>/dev/null)
    if [ "$ok" = "OK" ]; then
      if ! grep -q "E6_OFFICIAL_RUNNING" /root/rnaft/logs/e6_official_5090.log 2>/dev/null; then
        echo "S0 file valid — starting E6 official 18 runs"
        echo "E6_OFFICIAL_RUNNING $(date -u +%FT%TZ)" >> /root/rnaft/logs/e6_official_5090.log
        setsid nohup bash /tmp/s13.sh >> /tmp/s13_outer.log 2>&1 < /dev/null &
      fi
    fi
  fi
  } >> $LOG 2>&1
  sleep 900
done
