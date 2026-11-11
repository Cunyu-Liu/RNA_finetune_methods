import json
import os
from pathlib import Path
import runpy
import sys

import torch


def main():
    if len(sys.argv) < 2:
        raise SystemExit("usage: revalidate_lora_memory.py <diagnostic-module> [args...]")
    module = sys.argv[1]
    sys.argv = [module] + sys.argv[2:]
    assert torch.cuda.is_available(), "CUDA_UNAVAILABLE_ABORT"
    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()
    try:
        runpy.run_module(module, run_name="__main__")
    finally:
        summary = {
            "rid": os.environ["REVALIDATION_RID"],
            "peak_mem_mb": torch.cuda.max_memory_allocated() / 1024 ** 2,
            "cuda_device_name": torch.cuda.get_device_name(0),
            "cuda_runtime": torch.version.cuda,
            "source_module": module,
            "artifact_root": os.environ["RNAFT_ARTIFACT_ROOT"],
        }
        output = Path(os.environ["REVALIDATION_OUT"])
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(summary, indent=2) + "\n")
        print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
