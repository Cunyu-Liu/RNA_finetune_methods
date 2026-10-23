#!/bin/bash
# monitor_loop v2: 15-min watchdog for RTX5090 cluster.
# Adds (vs v1): stale-running ledger cleanup, per-lane worker respawn, convergence audit hook,
# GPU-fill discipline check (log warning when <20G used and no finetune procs).
cd /home/cunyuliu/rna-ft-eval
LOG=/root/rnaft/logs/monitor_loop.log
PY=/root/miniconda3/envs/llr_env/bin/python
export PYTHONPATH=/root/rnaft/pypath:/home/cunyuliu/rna-ft-eval:/home/cunyuliu/rna-sc
export HF_HOME=/root/hf_home
export HF_ENDPOINT=https://hf-mirror.com

LANES="q_splmore q_splfull2 q_splfull3 q_crisprfam q_degrfull q_nblane q_splfrozen q_spl650 q_splmega2 q_splnbfroz"

while true; do
  {
  echo "=== monitor v2 $(date '+%F %T') ==="
  used=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1)
  util=$(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits | head -1)
  echo "GPU: ${used}MiB ${util}%"
  echo "ledger rows=$(wc -l < /root/rnaft/ledger.jsonl) done=$(grep -c '\"status\": \"done\"' /root/rnaft/ledger.jsonl)"

  # 1) stale running cleanup (was cron-only on old cluster; container has no cron)
  $PY scripts/reset_stale_cron.py 2>&1 | head -2

  # 2) per-lane worker respawn: if lane not finished (no DONE marker) and no bash process, restart
  for L in $LANES; do
    SCRIPT=/home/cunyuliu/rna-ft-eval/scripts/$L.sh
    LLOG=/root/rnaft/logs/$L.log
    [ -f $SCRIPT ] || continue
    if ! ps aux | grep -v grep | grep -q "bash.*$L.sh"; then
      if ! grep -q "DONE" $LLOG 2>/dev/null; then
        echo "RESPAWN $L (worker dead, not done)"
        setsid nohup bash $SCRIPT >> /dev/null 2>&1 < /dev/null &
      fi
    fi
  done

  # 3) finetune procs alive + latest epoch losses (convergence visibility)
  nfin=$(ps aux | grep -cE '[f]inetune')
  echo "finetune_procs=$nfin"
  if [ "$nfin" -eq 0 ]; then
    miss=$($PY scripts/audit_1016.py 2>/dev/null | tail -1)
    echo "audit_1016_missing=$miss"
  fi

  # 4) GPU fill discipline: warn if under-used and no work
  if [ "$used" -lt 20000 ] && [ "$nfin" -lt 2 ]; then
    echo "WARN: GPU under-used (${used}MiB, ${nfin} procs) — consider adding a lane"
  fi

  # 5) q_master heartbeat
  if ! ps aux | grep -v grep | grep -q "q_master.sh"; then
    echo "RESPAWN q_master"
    setsid nohup bash /home/cunyuliu/rna-ft-eval/scripts/q_master.sh >> /root/rnaft/logs/q_master_outer.log 2>&1 < /dev/null &
  fi
  } >> $LOG 2>&1
  sleep 900
done
