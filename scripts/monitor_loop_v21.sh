#!/bin/bash
# monitor_loop v2.1: fix double-start race (B27 discipline)
# - pgrep -f full-match liveness (both abs & rel path forms)
# - spawn lock per lane (mkdir atomic) so only one instance ever respawns
# - remove v1 legacy respawn bugs
cd /home/cunyuliu/rna-ft-eval
LOG=/root/rnaft/logs/monitor_loop.log
PY=/root/miniconda3/envs/llr_env/bin/python
export PYTHONPATH=/root/rnaft/pypath:/home/cunyuliu/rna-ft-eval:/home/cunyuliu/rna-sc
export HF_HOME=/root/hf_home
export HF_ENDPOINT=https://hf-mirror.com

LANES="q_splmore q_splfull2 q_splfull3 q_crisprfam q_degrfull q_nblane q_splfrozen q_spl650 q_splmega2 q_splnbfroz q_spl_s17_retry q_splfroz2 q_splfroz3 q_splfill4 q_degrfroz q_ssifill q_crisprfill"

while true; do
  {
  echo "=== monitor v2.1 $(date '+%F %T') ==="
  used=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1)
  util=$(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits | head -1)
  echo "GPU: ${used}MiB ${util}%"
  echo "ledger rows=$(wc -l < /root/rnaft/ledger.jsonl) done=$(grep -c '\"status\": \"done\"' /root/rnaft/ledger.jsonl)"

  # 1) stale running cleanup
  $PY scripts/reset_stale_cron.py 2>&1 | head -2

  # 2) lane respawn with pgrep -f full match + spawn lock
  for L in $LANES; do
    SCRIPT=/home/cunyuliu/rna-ft-eval/scripts/$L.sh
    LLOG=/root/rnaft/logs/$L.log
    [ -f $SCRIPT ] || continue
    if ! pgrep -f "$L\.sh" > /dev/null; then
      if ! grep -q "DONE" $LLOG 2>/dev/null; then
        LOCK=/tmp/respawn_$L.lock
        if ! mkdir $LOCK 2>/dev/null; then
          echo "skip respawn $L (lock held)"
        else
          echo "RESPAWN $L (pgrep confirmed dead, not done)"
          setsid nohup bash $SCRIPT >> /dev/null 2>&1 < /dev/null &
          # release lock after 5 min (enough for lane to appear in pgrep)
          (sleep 300; rmdir $LOCK 2>/dev/null) &
        fi
      fi
    fi
  done

  # 3) finetune procs
  nfin=$(pgrep -fc "rnafteval.finetune" 2>/dev/null || echo 0)
  echo "finetune_procs=$nfin"

  # 4) GPU fill discipline
  if [ "$used" -lt 20000 ] && [ "$nfin" -lt 2 ]; then
    echo "WARN: GPU under-used (${used}MiB, ${nfin} procs)"
  fi

  # 5) q_master heartbeat
  if ! pgrep -f "q_master.sh" > /dev/null; then
    echo "RESPAWN q_master"
    setsid nohup bash /home/cunyuliu/rna-ft-eval/scripts/q_master.sh >> /root/rnaft/logs/q_master_outer.log 2>&1 < /dev/null &
  fi
  } >> $LOG 2>&1
  sleep 900
done
