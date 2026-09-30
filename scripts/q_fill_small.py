#!/usr/bin/env python3
"""小格旁路填谷 worker（1001 凌晨）：跳过被大格阻塞的小 need 格。

问题：q_fill 严格按 plan 顺序处理——NB(23G)/650M(24G) 等大格卡在头部时，
后面 need<=12G 的小格（RNA-Sc-1M/10M/30M mod/mrl/SSP、mega mod/mrl、
SpliceBERT/ERNIE/RNA-FM SSP 等 36 格）无法利用 14-16G 的空闲卡。

方案：本 worker 只挑 need <= MAXG 的 missing 格跑（逆序遍历，避开主 shard
正在处理的头部格——is_busy 检查 + done-skip 双保险防双跑）。

用法: q_fill_small.py <shard> <nshards> <plan.json> [max_need_gb]
"""
import os
import sys
import json
import time
import subprocess
import datetime

SHARD = int(sys.argv[1])
NS = int(sys.argv[2])
PLAN = sys.argv[3]
MAXG = float(sys.argv[4]) if len(sys.argv) > 4 else 12.0

P = json.load(open(PLAN))
LOCKDIR = P.get("lockdir", "/tmp/rnaft_shared_locks")
TIMEOUT_S = int(P.get("timeout_s", 21600))
R = "/mnt/cunyuliu/rna-ft-eval"
LEDGER = R + "/ledger.jsonl"
PY = "/home/cunyuliu/llr_env/bin/python"
CARD = [PY, "/home/cunyuliu/rna-ft-eval/scripts/rnaft_card.py"]
os.environ.update({
    "PYTHONPATH": "/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval",
    "HF_HOME": "/mnt/cunyuliu/hf_home",
    "HF_ENDPOINT": "https://hf-mirror.com",
    "PYTORCH_CUDA_ALLOC_CONF": "expandable_segments:True",
})
TAG = os.path.basename(PLAN).replace(".json", "")
LOG = open("%s/logs/q_small_%s_s%d.log" % (R, TAG, SHARD), "a", buffering=1)


def log(*a):
    print("[%s] small %s s%d %s" % (datetime.datetime.now().strftime("%m-%d %H:%M:%S"),
                                    TAG, SHARD, " ".join(str(x) for x in a)), file=LOG)


_rows = None


def refresh():
    global _rows
    _rows = []
    for l in open(LEDGER):
        l = l.strip()
        if not l:
            continue
        try:
            _rows.append(json.loads(l))
        except Exception:
            pass


def is_done(task, model, strat, seed, split, lr):
    refresh()
    for r in _rows:
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


def is_busy(task, model, strat, seed, split):
    try:
        out = subprocess.check_output(["ps", "-eo", "args"], text=True)
    except Exception:
        return False
    for l in out.splitlines():
        if (("--model %s " % model) in l and ("--strategy %s " % strat) in l
                and ("--seed %d " % seed) in l and ("--split %s " % split) in l
                and "rnafteval.finetune" in l):
            return True
    return False


def build_cmd(task, model, strat, seed, split, lr, dev, bs=None, max_len=None):
    if task == "mrl":
        mod = "rnafteval.finetune_mrl"
        extra = ["--epochs", "3", "--n-train", "20000", "--batch-size", "32"]
    elif task == "modification":
        mod = "rnafteval.finetune_base"
        extra = ["--task", "modification", "--epochs", "3", "--n-train", "20000", "--batch-size", "32"]
    elif task == "secondary-structure":
        mod = "rnafteval.finetune_ssp"
        extra = ["--epochs", "3", "--n-train", "3000", "--n-test", "500", "--batch-size", "4"]
    elif task == "noncoding-rna-family":
        mod = "rnafteval.finetune_one"
        extra = ["--task", "noncoding-rna-family", "--epochs", "10"]
    else:
        raise SystemExit("unknown task " + task)
    cmd = [PY, "-m", mod, "--model", model, "--strategy", strat, "--seed", str(seed),
           "--split", split, "--device", str(dev)] + extra
    if lr is not None:
        cmd += ["--lr", lr]
    if bs is not None:
        cmd += ["--batch-size", str(bs)]
    if max_len is not None:
        cmd += ["--max-len", str(max_len)]
    return cmd


import torch

assert torch.cuda.is_available(), "CUDA not available - stopping"
log("CUDA ok;", torch.cuda.device_count(), "devices; max_need", MAXG, "GB")

todo = [c for c in P["runs"] if c.get("need", 99) <= MAXG]
todo = [c for i, c in enumerate(todo) if i % NS == SHARD]
log("small-cell todo:", len(todo))
for rr in todo:
    task, model, strat, split = rr["task"], rr["model"], rr["strategy"], rr["split"]
    seed, lr, need = rr["seed"], rr.get("lr"), rr.get("need", 6)
    tag = "%s|%s|%s|s%s|%s" % (task, model, strat, seed, split)
    if is_done(task, model, strat, seed, split, lr):
        log("skip(done)", tag)
        continue
    if is_busy(task, model, strat, seed, split):
        log("skip(busy)", tag)
        continue
    att = 0
    finished = False
    while att < 60 and not finished:
        out = subprocess.run(CARD + ["pick", str(need)], capture_output=True, text=True)
        gs = out.stdout.strip()
        if not gs:
            log("wait(no card)", tag)
            time.sleep(240)
            continue
        G, SL = gs.split()
        try:
            if is_done(task, model, strat, seed, split, lr):
                subprocess.run(CARD + ["release", G, SL])
                finished = True
                break
            log("RUN", tag, "GPU%s.%s" % (G, SL))
            t0 = time.time()
            p = subprocess.run(build_cmd(task, model, strat, seed, split, lr, G,
                                         rr.get("bs"), rr.get("max_len")),
                               cwd="/home/cunyuliu/rna-ft-eval", timeout=TIMEOUT_S,
                               stdout=LOG, stderr=subprocess.STDOUT)
            log("exit", p.returncode, tag, "%.0fs" % (time.time() - t0))
            if p.returncode == 0:
                finished = True
            else:
                att += 1
                time.sleep(20)
        except subprocess.TimeoutExpired:
            log("TIMEOUT", tag)
            att += 1
        finally:
            subprocess.run(CARD + ["release", G, SL])
    if not finished:
        log("GAVEUP", tag)
log("SMALL SHARD %d DONE" % SHARD)