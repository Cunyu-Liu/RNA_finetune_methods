#!/usr/bin/env python3
"""audit_1016: authoritative missing count for 1016 plans (dual-format e3 + rank + lr exact)"""
import json
rows=[json.loads(l) for l in open("/root/rna-ft-eval/ledger.jsonl")]
def is_done_fixed(rr):
    task,model,strat,seed,split=rr["task"],rr["model"],rr["strategy"],rr["seed"],rr["split"]
    lr,n_train,rank=rr.get("lr"),rr.get("n_train"),rr.get("rank")
    if n_train:
        base="ft_%s_%s_%s_s%d_%s"%(model.lower().replace("-","").replace(".","").replace(" ",""),task.replace("-",""),strat,seed,split)
        lrtag=("_lr%s"%lr) if (lr is not None and strat=="full") else ""
        e3tag="_e3%d"%int(n_train)
        for want in (base+lrtag+e3tag, base+e3tag+lrtag):
            for r in rows:
                rid=r.get("run_id","")
                if (rid==want or (rid.startswith(want) and set(rid[len(want):].split("_"))<={"r8",""})) and r.get("status")=="done" and not r.get("smoke"):
                    return True
        return False
    if rank is not None and int(rank)!=8:
        rid="ft_%s_%s_%s_s%d_%s%s_r%d"%(model.lower().replace("-","").replace(".","").replace(" ",""),task.replace("-",""),strat,seed,split,("_lr%s"%lr) if (lr is not None and strat=="full") else "",int(rank))
        return any(r.get("run_id")==rid and r.get("status")=="done" and not r.get("smoke") for r in rows)
    for r in rows:
        if (r.get("model")==model and r.get("task")==task and r.get("strategy")==strat and r.get("seed")==seed and r.get("split")==split and r.get("status")=="done" and not r.get("smoke")):
            if strat=="full" and lr is not None:
                try:
                    if abs(float(r.get("lr",0))-float(lr))>1e-12: continue
                except: continue
            return True
    return False
tot=0
for pf in ["/home/cunyuliu/rna-ft-eval/scripts/p2_1016_mega_e3_plan.json","/home/cunyuliu/rna-ft-eval/scripts/p2_1016_bigtail_plan.json"]:
    plan=json.load(open(pf))
    tot+=sum(0 if is_done_fixed(r) else 1 for r in plan["runs"])
print(tot)
