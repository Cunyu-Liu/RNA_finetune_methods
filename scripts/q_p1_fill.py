#!/usr/bin/env python3
"""P1 E1 gap-fill parallel worker (ledger-verified 37 groups x 3 seeds = 111 runs).

Protocol follows each runner exactly: frozen/LoRA use runner default LR (3e-4);
full FT uses family-tuned LR (RiNALMo -> 1e-5 ; controlled RNA-Sc -> 3e-5).

Concurrency: N shard workers. Each run: pick a card that has both enough free
memory (>= measured need) and a free *slot* (SLOTS concurrent jobs per card),
grab a per-card-slot atomic lock (mkdir), re-check memory, run, release.
Excludes MIG 1g.5gb (total<20GiB) -- physical, not a policy gate.
done-skip + pending-clear retry. Real-CUDA assertion at start.

usage: q_p1_fill.py <shard> <nshards>
"""
import os, sys, json, time, fcntl, subprocess, datetime

SHARD = int(sys.argv[1]); NS = int(sys.argv[2])
SLOTS = 2
R = "/mnt/cunyuliu/rna-ft-eval"
LEDGER = R + "/ledger.jsonl"
PY = "/home/cunyuliu/llr_env/bin/python"
LOCKS = "/tmp/p1_locks"
os.makedirs(LOCKS, exist_ok=True)
os.makedirs(R + "/logs", exist_ok=True)
LOG = open("%s/logs/q_p1_fill_s%d.log" % (R, SHARD), "a", buffering=1)

for k, v in {
    "PYTHONPATH": "/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval",
    "HF_HOME": "/mnt/cunyuliu/hf_home",
    "HF_ENDPOINT": "https://hf-mirror.com",
    "PYTORCH_CUDA_ALLOC_CONF": "expandable_segments:True",
}.items():
    os.environ[k] = v

def log(*a):
    print("[%s] s%d %s" % (datetime.datetime.now().strftime("%m-%d %H:%M:%S"), SHARD,
                           " ".join(str(x) for x in a)), file=LOG)

def cells():
    out = []
    for st in ("frozen", "lora", "full"):
        for sp in ("random", "family"):
            out.append(("mrl", "RNA-Sc-1M", st, sp, ("3e-05" if st == "full" else None), 6))
    for sp in ("random", "family"):
        out.append(("modification", "RiNALMo-mega", "frozen", sp, None, 12))
    for st in ("frozen", "lora", "full"):
        out.append(("modification", "RNA-Sc-1M", st, "family", ("3e-05" if st == "full" else None), 6))
    for m, need in (("RNA-Sc-30M", 6), ("RNA-Sc-100M", 8)):
        for sp in ("random", "family"):
            out.append(("modification", m, "frozen", sp, None, need))
    for st in ("frozen", "lora"):
        for sp in ("random", "family"):
            out.append(("secondary-structure", "RiNALMo-mega", st, sp, None, 12))
    for m, need in (("RNA-Sc-1M", 6), ("RNA-Sc-30M", 6), ("RNA-Sc-100M", 8)):
        for st in ("frozen", "lora", "full"):
            for sp in ("random", "family"):
                out.append(("secondary-structure", m, st, sp, ("3e-05" if st == "full" else None), need))
    return out

RUNS = [(c[0], c[1], c[2], seed, c[3], c[4], c[5]) for c in cells() for seed in (17, 29, 43)]
log("worklist", len(RUNS), "runs; shard", SHARD, "/", NS)

def is_done(task, model, strat, seed, split, lr):
    for l in open(LEDGER):
        l = l.strip()
        if not l:
            continue
        try:
            r = json.loads(l)
        except Exception:
            continue
        if (r.get("model") == model and r.get("task") == task and r.get("strategy") == strat
                and r.get("seed") == seed and r.get("split") == split and r.get("status") == "done"):
            if strat == "full" and lr is not None:
                try:
                    if abs(float(r.get("lr", 0)) - float(lr)) > 1e-12:
                        continue
                except Exception:
                    continue
            return True
    return False

def clear_pending(task, model, strat, seed, split):
    with open(LEDGER) as f:
        fcntl.flock(f, fcntl.LOCK_EX); rows = [l for l in f]
    out = []
    for l in rows:
        s = l.strip()
        if not s:
            continue
        try:
            r = json.loads(s)
        except Exception:
            out.append(l); continue
        if (r.get("model") == model and r.get("task") == task and r.get("strategy") == strat
                and r.get("seed") == seed and r.get("split") == split and r.get("status") == "pending"):
            continue
        out.append(l)
    with open(LEDGER, "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX); f.writelines(out)

import torch
def mem(g):
    try:
        return torch.cuda.mem_get_info(g)
    except Exception:
        return (0, 0)

def free_slots(g):
    n = 0
    for s in range(SLOTS):
        if not os.path.exists("%s/gpu_%d_slot_%d" % (LOCKS, g, s)):
            n += 1
    return n

def pick_target(need):
    cands = []
    for i in range(torch.cuda.device_count()):
        free, total = mem(i)
        if total < 20 * 2**30 or free < need * 1e9:
            continue
        if free_slots(i) < 1:
            continue
        cands.append((free, i))
    if not cands:
        return -1
    cands.sort(reverse=True)
    return cands[0][1]

def grab(g, need):
    for s in range(SLOTS):
        lk = "%s/gpu_%d_slot_%d" % (LOCKS, g, s)
        try:
            os.mkdir(lk)
        except FileExistsError:
            continue
        free, total = mem(g)
        if total >= 20 * 2**30 and free >= need * 1e9:
            return lk
        try: os.rmdir(lk)
        except Exception: pass
    return None

def build_cmd(task, model, strat, seed, split, lr, dev):
    if task == "mrl":
        mod = "rnafteval.finetune_mrl"; extra = ["--epochs", "3", "--n-train", "20000", "--batch-size", "32"]
    elif task == "modification":
        mod = "rnafteval.finetune_base"; extra = ["--task", "modification", "--epochs", "3", "--n-train", "20000", "--batch-size", "32"]
    elif task == "secondary-structure":
        mod = "rnafteval.finetune_ssp"; extra = ["--epochs", "3", "--n-train", "3000", "--n-test", "500", "--batch-size", "4"]
    else:
        raise SystemExit("unknown task " + task)
    cmd = [PY, "-m", mod, "--model", model, "--strategy", strat, "--seed", str(seed),
           "--split", split, "--device", str(dev)] + extra
    if lr is not None:
        cmd += ["--lr", lr]
    return cmd

assert torch.cuda.is_available(), "CUDA not available - stopping"
log("CUDA ok;", torch.cuda.device_count(), "devices")

todo = [r for i, r in enumerate(RUNS) if i % NS == SHARD]
log("shard todo", len(todo))
for (task, model, strat, seed, split, lr, need) in todo:
    tag = "%s|%s|%s|s%d|%s%s" % (task, model, strat, seed, split, ("|lr" + lr) if lr else "")
    if is_done(task, model, strat, seed, split, lr):
        log("skip(done)", tag); continue
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
            p = subprocess.run(build_cmd(task, model, strat, seed, split, lr, g),
                               cwd="/home/cunyuliu/rna-ft-eval", timeout=14400,
                               stdout=LOG, stderr=subprocess.STDOUT)
            dt = time.time() - t0
            log("exit", p.returncode, tag, "%.0fs" % dt)
            if p.returncode == 0:
                finished = True
            else:
                clear_pending(task, model, strat, seed, split); att += 1
        except subprocess.TimeoutExpired:
            log("TIMEOUT", tag); clear_pending(task, model, strat, seed, split); att += 1
        finally:
            try: os.rmdir(lk)
            except Exception: pass
    if not finished:
        log("GAVEUP", tag)
log("SHARD %d DONE" % SHARD)
