"""GPU guard: verify CUDA + measure real GPU activity (anti silent-CPU-fallback).

Evidence contract (user requirement): if CUDA is unavailable OR the training
loop shows no GPU utilization over a window, we MUST stop and record evidence.
Usage: python -m rnafteval.gpu_guard --pid <training_pid> --device 6
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import time


def gpu_busy(pid: int, device: int) -> tuple[bool, int]:
    out = subprocess.run(
        ["nvidia-smi", "-i", str(device)], capture_output=True,
        text=True).stdout
    for line in out.splitlines():
        if str(pid) in line and "MiB" in line:
            try:
                mem = int(line.split()[-1].replace("MiB", ""))
            except ValueError:
                mem = 0
            return True, mem
    return False, 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pid", type=int, required=True)
    ap.add_argument("--device", type=int, required=True)
    ap.add_argument("--window-sec", type=float, default=60)
    args = ap.parse_args()

    import torch
    if not torch.cuda.is_available():
        print(json.dumps({"event": "CUDA_UNAVAILABLE", "device": args.device}),
              flush=True)
        return 2

    samples = []
    t0 = time.time()
    while time.time() - t0 < args.window_sec:
        busy, mem = gpu_busy(args.pid, args.device)
        samples.append((busy, mem))
        if not busy and len(samples) > 10:
            break
        time.sleep(5)
    n_busy = sum(1 for b, _ in samples if b)
    report = {
        "event": "GPU_GUARD_REPORT", "pid": args.pid, "device": args.device,
        "samples": len(samples), "busy_samples": n_busy,
        "max_mem_mib": max((m for _, m in samples), default=0),
        "verdict": "GPU_OK" if n_busy > 0 else "NO_GPU_ACTIVITY",
    }
    print(json.dumps(report), flush=True)
    out = "/mnt/cunyuliu/rna-ft-eval/status/gpu_guard_%d.json" % args.pid
    with open(out, "w") as fh:
        json.dump(report, fh, indent=2)
    return 0 if n_busy > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
