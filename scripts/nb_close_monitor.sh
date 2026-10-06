#!/bin/bash
# 1007a: NB backfill close monitor — when the 3 NB cells land, refresh c4_table + report.
R=/mnt/cunyuliu/rna-ft-eval
C=/home/cunyuliu/rna-ft-eval
PY=/home/cunyuliu/llr_env/bin/python
LOG=$R/logs/nb_close_monitor.log
N_DONE=$($PY - << 'PYEOF'
import json
rows=[json.loads(l) for l in open("/mnt/cunyuliu/rna-ft-eval/ledger.jsonl")]
def ok(m,t,s,se,sp):
    return any(r.get("model")==m and r.get("task")==t and r.get("strategy")==s and r.get("seed")==se
               and r.get("split")==sp and r.get("status")=="done" and not r.get("smoke") for r in rows)
n=ok("NucleicBERT","noncoding-rna-family","lora",29,"random")+ok("NucleicBERT","noncoding-rna-family","frozen",17,"random")+ok("NucleicBERT","modification","lora",29,"random")
print(n)
PYEOF
)
echo "$(date '+%m-%d %H:%M') NB cells done: $N_DONE/3" >> $LOG
if [ "$N_DONE" -eq 3 ]; then
  if [ ! -f $R/.nb_close_1007 ]; then
    touch $R/.nb_close_1007
    cd $C
    PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval $PY -m rnafteval.export_c4 >> $LOG 2>&1
    echo "$(date '+%m-%d %H:%M') NB CLOSE: c4_table refreshed" >> $LOG
  fi
fi
