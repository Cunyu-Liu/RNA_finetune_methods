"""Patch multimolecule modeling files for transformers 5.0 compatibility.

Fixes (idempotent, applied to pypath install):
1. create_*_mask(...inputs_embeds=X) -> input_embeds=X (kwarg rename
   at call sites; transformers 5.0 masking_utils signature).
2. import guard for merge_with_config_defaults / capture_outputs when
   older/newer transformers mismatch (wrapped in try/except).

Usage:
  python patch_multimolecule.py [pypath]
  (default pypath = /mnt/cunyuliu/rna-ft-eval/pypath)
"""
from __future__ import annotations

import glob
import os
import re
import sys


def patch_call_kwargs(src: str) -> str:
    pattern = re.compile(
        r"(create_(?:bidirectional|causal|custom)_mask\()((?:[^()]|\([^()]*\))*?)\)",
        re.S)

    def repl(m):
        inner = re.sub(r"\binputs_embeds=", "input_embeds=", m.group(2))
        return m.group(1) + inner + ")"

    return pattern.sub(repl, src)


def patch_import_guards(src: str) -> str:
    if "merge_with_config_defaults" in src and "_RNAFT_PATCH" not in src:
        guard = ("try:\n    from transformers.configuration_utils import"
                 " merge_with_config_defaults\nexcept ImportError:\n"
                 "    def merge_with_config_defaults(*a, **k):\n"
                 "        return a[0] if a else k.get(\"config\")\n"
                 "try:\n    from transformers.modeling_utils import"
                 " capture_outputs\nexcept ImportError:\n"
                 "    def capture_outputs(x):\n        return x\n"
                 "# _RNAFT_PATCH")
        src = src.replace("from transformers.configuration_utils import"
                          " merge_with_config_defaults", guard, 1)
    return src


def main() -> int:
    pypath = sys.argv[1] if len(sys.argv) > 1 else \
        "/mnt/cunyuliu/rna-ft-eval/pypath"
    mm = os.path.join(pypath, "multimolecule", "models")
    files = glob.glob(os.path.join(mm, "*", "modeling_*.py"))
    patched = 0
    for fp in files:
        src = open(fp).read()
        out = patch_call_kwargs(src)
        out = patch_import_guards(out)
        if out != src:
            open(fp, "w").write(out)
            patched += 1
    print("patched %d/%d modeling files under %s" % (patched, len(files), mm))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
