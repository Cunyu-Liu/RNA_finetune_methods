#!/bin/bash
# 1007d: AIDO 3e-05 backfill close monitor — on 3/3, refresh lr_grid + report.
R=/mnt/cunyuliu/rna-ft-eval
C=/home/cunyuliu/rna-ft-eval
PY=/home/cunyuliu/llr_env/bin/python
LOG=$R/logs/aido_close_monitor.log
N=$($PY - << 'PYEOF'
import json
rows=[json.loads(l) for l in open("/mnt/cunyuliu/rna-ft-eval/ledger.jsonl")]
n=sum(1 for s in (17,29,43) for r in rows
      if r.get("model")=="AIDO.RNA-1.6B" and r.get("task")=="noncoding-rna-family"
      and r.get("strategy")=="full" and r.get("split")=="random" and r.get("seed")==s
      and str(r.get("lr"))=="3e-05" and r.get("status")=="done" and not r.get("smoke"))
print(n)
PYEOF
)
echo "$(date '+%m-%d %H:%M') AIDO 3e-05 cells: $N/3" >> $LOG
if [ "$N" -eq 3 ] && [ ! -f $R/.aido_close_1007 ]; then
  touch $R/.aido_close_1007
  cd $C
  PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval $PY -m rnafteval.export_lr_grid >> $LOG 2>&1
  echo "$(date '+%m-%d %H:%M') AIDO CLOSE: lr_grid refreshed; 3-seed 3e-05 formal complete" >> $LOG
fi
