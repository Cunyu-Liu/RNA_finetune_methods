#!/bin/bash
# e3rank keepalive（1009b）：e3rank_1009 队列 worker 死亡时重拉（共享卡锁协议不变）
# cron */10
R=/mnt/cunyuliu/rna-ft-eval
PLAN=scripts/p2_e3rank_1009_plan.json
LOG=$R/logs/keepalive_e3rank.log
cd /home/cunyuliu/rna-ft-eval
PY=/home/cunyuliu/llr_env/bin/python

# 统计 missing
MISSING=$($PY - << 'PYEOF'
import json
rows = [json.loads(l) for l in open("/mnt/cunyuliu/rna-ft-eval/ledger.jsonl")]
plan = json.load(open("/home/cunyuliu/rna-ft-eval/scripts/p2_e3rank_1009_plan.json"))["runs"]
def is_done(rr):
    for r in rows:
        if (r.get("model")==rr["model"] and r.get("task")==rr["task"] and r.get("strategy")==rr["strategy"]
            and r.get("seed")==rr.get("seed") and r.get("split")==rr.get("split") and r.get("status")=="done"
            and not r.get("smoke")):
            if rr.get("rank") is not None and int(rr["rank"]) != 8:
                if not r.get("run_id","").endswith("_r%d" % int(rr["rank"])):
                    continue
            if rr.get("n_train"):
                if "_e3%d" % int(rr["n_train"]) not in r.get("run_id",""):
                    continue
            if rr.get("strategy")=="full" and rr.get("lr") is not None:
                try:
                    if abs(float(r.get("lr",0))-float(rr["lr"]))>1e-12: continue
                except Exception: continue
            return True
    return False
print(sum(0 if is_done(rr) else 1 for rr in plan))
PYEOF
)
WORKERS=$(pgrep -fc "q_fill.py.*p2_e3rank_1009_plan")
echo "$(date '+%a %b %d %H:%M:%S %Y') e3rank missing=$MISSING workers=$WORKERS" >> $LOG
if [ "$MISSING" -gt 0 ] && [ "$WORKERS" -lt 4 ]; then
  for s in $(seq 0 3); do
    if ! pgrep -f "q_fill.py $s 4.*p2_e3rank" > /dev/null; then
      setsid nohup $PY scripts/q_fill.py $s 4 scripts/p2_e3rank_1009_plan.json > /dev/null 2>&1 &
      echo "$(date '+%a %b %d %H:%M:%S %Y') restarted e3rank s$s (missing=$MISSING)" >> $LOG
    fi
  done
fi
