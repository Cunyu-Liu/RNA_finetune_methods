#!/usr/bin/env python3
"""Generic E1 fill worker driven by a JSON plan (newly integrated models).

usage: q_fill.py <shard> <nshards> <plan.json>
plan: {"lockdir": str, "slots": int, "runs": [{task,model,strategy,split,seed,lr,need}]}
Protocol: frozen/lora default LR (3e-4); full uses the model-family tuned LR
(published RNA-LM -> 1e-5; controlled RNA-Sc -> 3e-5). done-skip by ledger fields,
pending-clear retry, per-card-slot atomic locks, real-CUDA assertion.
"""
import os, sys, json, time, fcntl, subprocess, datetime

SHARD = int(sys.argv[1]); NS = int(sys.argv[2]); PLAN = sys.argv[3]
P = json.load(open(PLAN))
LOCKDIR = P["lockdir"]; SLOTS = int(P.get("slots", 1)); RUNS = P["runs"]
TIMEOUT_S = int(P.get("timeout_s", 14400))
R = "/mnt/cunyuliu/rna-ft-eval"; LEDGER = R + "/ledger.jsonl"
PY = "/home/cunyuliu/llr_env/bin/python"
os.makedirs(LOCKDIR, exist_ok=True); os.makedirs(R + "/logs", exist_ok=True)
TAG = os.path.basename(PLAN).replace(".json", "")
LOG = open("%s/logs/q_fill_%s_s%d.log" % (R, TAG, SHARD), "a", buffering=1)
for k, v in {"PYTHONPATH": "/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval",
             "HF_HOME": "/mnt/cunyuliu/hf_home", "HF_ENDPOINT": "https://hf-mirror.com",
             "PYTORCH_CUDA_ALLOC_CONF": "expandable_segments:True"}.items():
    os.environ[k] = v

def log(*a):
    print("[%s] %s s%d %s" % (datetime.datetime.now().strftime("%m-%d %H:%M:%S"), TAG, SHARD,
                              " ".join(str(x) for x in a)), file=LOG)

_rows = None
def refresh():
    global _rows
    _rows = []
    for l in open(LEDGER):
        l = l.strip()
        if not l: continue
        try: _rows.append(json.loads(l))
        except Exception: pass

def is_done(task, model, strat, seed, split, lr):
    refresh()
    for r in _rows:
        if (r.get("model") == model and r.get("task") == task and r.get("strategy") == strat
                and r.get("seed") == seed and r.get("split") == split and r.get("status") == "done"):
            if strat == "full" and lr is not None:
                try:
                    if abs(float(r.get("lr", 0)) - float(lr)) > 1e-12: continue
                except Exception: continue
            return True
    return False

def is_busy(task, model, strat, seed, split):
    # live finetune process with these exact flags == in-flight (e.g. orphan)
    try:
        out = subprocess.check_output(["ps", "-eo", "args"], text=True)
    except Exception:
        return False
    for l in out.splitlines():
        if (("--model %s " % model) in l
                and ("--strategy %s " % strat) in l
                and ("--seed %d " % seed) in l
                and ("--split %s " % split) in l
                and "rnafteval.finetune" in l):
            return True
    return False

def clear_pending(task, model, strat, seed, split):
    with open(LEDGER) as f:
        fcntl.flock(f, fcntl.LOCK_EX); rows = [l for l in f]
    out = []
    for l in rows:
        s = l.strip()
        if not s: continue
        try: r = json.loads(s)
        except Exception: out.append(l); continue
        if (r.get("model") == model and r.get("task") == task and r.get("strategy") == strat
                and r.get("seed") == seed and r.get("split") == split and r.get("status") == "pending"):
            continue
        out.append(l)
    with open(LEDGER, "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX); f.writelines(out)

import torch
def mem(g):
    try: return torch.cuda.mem_get_info(g)
    except Exception: return (0, 0)
def free_slots(g):
    return sum(1 for s in range(SLOTS) if not os.path.exists("%s/gpu_%d_slot_%d" % (LOCKDIR, g, s)))
def pick_target(need):
    c = []
    for i in range(torch.cuda.device_count()):
        free, total = mem(i)
        if total < 20 * 2**30 or free < need * 1e9: continue
        if free_slots(i) < 1: continue
        c.append((free, i))
    return -1 if not c else sorted(c, reverse=True)[0][1]
def grab(g, need):
    for s in range(SLOTS):
        lk = "%s/gpu_%d_slot_%d" % (LOCKDIR, g, s)
        try: os.mkdir(lk)
        except FileExistsError: continue
        free, total = mem(g)
        if total >= 20 * 2**30 and free >= need * 1e9: return lk
        try: os.rmdir(lk)
        except Exception: pass
    return None
def build_cmd(task, model, strat, seed, split, lr, dev, bs=None, max_len=None):
    if task == "mrl":
        mod = "rnafteval.finetune_mrl"; extra = ["--epochs", "3", "--n-train", "20000", "--batch-size", "32"]
    elif task == "modification":
        mod = "rnafteval.finetune_base"; extra = ["--task", "modification", "--epochs", "3", "--n-train", "20000", "--batch-size", "32"]
    elif task == "secondary-structure":
        mod = "rnafteval.finetune_ssp"; extra = ["--epochs", "3", "--n-train", "3000", "--n-test", "500", "--batch-size", "4"]
    elif task == "noncoding-rna-family":
        mod = "rnafteval.finetune_one"; extra = ["--task", "noncoding-rna-family", "--epochs", "10"]
    else:
        raise SystemExit("unknown task " + task)
    cmd = [PY, "-m", mod, "--model", model, "--strategy", strat, "--seed", str(seed),
           "--split", split, "--device", str(dev)] + extra
    if lr is not None: cmd += ["--lr", lr]
    if bs is not None: cmd += ["--batch-size", str(bs)]
    if max_len is not None: cmd += ["--max-len", str(max_len)]
    return cmd

assert torch.cuda.is_available(), "CUDA not available - stopping"
log("CUDA ok;", torch.cuda.device_count(), "devices; runs", len(RUNS))
todo = [r for i, r in enumerate(RUNS) if i % NS == SHARD]
log("shard todo", len(todo))
for rr in todo:
    task, model, strat, split = rr["task"], rr["model"], rr["strategy"], rr["split"]
    seed, lr, need = rr["seed"], rr.get("lr"), rr.get("need", 6)
    tag = "%s|%s|%s|s%s|%s%s" % (task, model, strat, seed, split, ("|lr" + lr) if lr else "")
    if is_done(task, model, strat, seed, split, lr):
        log("skip(done)", tag); continue
    if is_busy(task, model, strat, seed, split):
        log("skip(busy)", tag); continue

    att = 0; finished = False
    while att < 60 and not finished:
        g = pick_target(need)
        if g < 0:
            log("wait(no card)", tag); time.sleep(180); continue
        lk = grab(g, need)
        if lk is None:
            log("card%d no slot/shrunk" % g, tag); time.sleep(20); continue
        try:
            log("RUN", tag, "GPU%d need%dG" % (g, need))
            t0 = time.time()
            p = subprocess.run(build_cmd(task, model, strat, seed, split, lr, g,
                                         rr.get("bs"), rr.get("max_len")),
                               cwd="/home/cunyuliu/rna-ft-eval", timeout=TIMEOUT_S,
                               stdout=LOG, stderr=subprocess.STDOUT)
            log("exit", p.returncode, tag, "%.0fs" % (time.time() - t0))
            if p.returncode == 0: finished = True
            else: clear_pending(task, model, strat, seed, split); att += 1
        except subprocess.TimeoutExpired:
            log("TIMEOUT", tag); clear_pending(task, model, strat, seed, split); att += 1
        finally:
            try: os.rmdir(lk)
            except Exception: pass
    if not finished: log("GAVEUP", tag)
log("SHARD %d DONE" % SHARD)
