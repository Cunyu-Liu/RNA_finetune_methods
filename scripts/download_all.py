"""BEACON data + RNA-LM checkpoints downloader (hf-mirror, requests-based).

Run on server:  PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath python3 download_all.py
"""
import os
import sys
import time

import requests
import urllib3

urllib3.disable_warnings()

ROOT = "/mnt/cunyuliu/rna-ft-eval"
DATA = os.path.join(ROOT, "data", "beacon_raw")
HF_HOME = "/mnt/cunyuliu/hf_home"

DATASETS = [
    "secondary-structure", "contact-map", "distance-map",
    "structural-score-imputation", "spliceai", "isoform",
    "noncoding-rna-family", "modification", "mean-ribosome-loading",
    "degradation", "programmable-rna-switches", "crispr-on-target",
    "crispr-off-target",
]
MODELS = [
    "multimolecule/ernierna",
    "multimolecule/splicebert",
    "multimolecule/rnafm",
    "lmzb-bupt/RiNALMo",
    "gyx1130/SpliceBERT-human510",
]


def fetch_tree(kind: str, repo: str) -> list[dict]:
    url = "https://hf-mirror.com/api/%s/%s/tree/main?recursive=true" % (kind, repo)
    r = requests.get(url, timeout=30, verify=False)
    r.raise_for_status()
    return r.json()


def download_file(url: str, out: str, size: int) -> bool:
    if os.path.exists(out) and os.path.getsize(out) == size:
        return False
    os.makedirs(os.path.dirname(out), exist_ok=True)
    for attempt in range(4):
        try:
            with requests.get(url, stream=True, timeout=600, verify=False) as resp:
                resp.raise_for_status()
                with open(out + ".part", "wb") as fh:
                    for chunk in resp.iter_content(1 << 20):
                        fh.write(chunk)
            os.replace(out + ".part", out)
            return True
        except Exception as e:
            print("  retry", attempt, os.path.basename(out), repr(e)[:120], flush=True)
            time.sleep(6)
    print("  FAILED", url, flush=True)
    return False


def skip(rel: str) -> bool:
    bad = (".", "onnx", "msgpack", "rust_model", "flax_model")
    return rel.startswith(".") or any(b in rel for b in bad[1:]) or rel.endswith(".h5")


def main() -> int:
    print("=== datasets ===", flush=True)
    for t in DATASETS:
        repo = "jiahaozhang2003/beacon-%s" % t
        try:
            files = fetch_tree("datasets", repo)
        except Exception as e:
            print(t, "API FAIL", repr(e)[:120], flush=True)
            continue
        n = 0
        for f in files:
            if f.get("type") != "file" or skip(f["path"]):
                continue
            rel = f["path"]
            out = os.path.join(DATA, t, rel)
            if download_file(
                    "https://hf-mirror.com/datasets/%s/resolve/main/%s" % (repo, rel),
                    out, f["size"]):
                n += 1
        print(t, "downloaded", n, "files", flush=True)

    print("=== models ===", flush=True)
    for repo in MODELS:
        try:
            files = fetch_tree("models", repo)
        except Exception as e:
            print(repo, "API FAIL", repr(e)[:120], flush=True)
            continue
        n = 0
        for f in files:
            if f.get("type") != "file" or skip(f["path"]):
                continue
            rel = f["path"]
            out = os.path.join(HF_HOME, "models", repo.replace("/", "--"),
                               "snapshots", "main", rel)
            if download_file(
                    "https://hf-mirror.com/%s/resolve/main/%s" % (repo, rel),
                    out, f["size"]):
                n += 1
        print(repo, "downloaded", n, "files", flush=True)
    print("ALL DONE", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
