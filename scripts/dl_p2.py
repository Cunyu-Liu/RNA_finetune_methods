#!/usr/bin/env python3
"""P2 checkpoint downloader (hf-mirror, requests-based, resumable) -> HF_HOME layout."""
import os, sys, time, requests, urllib3
urllib3.disable_warnings()
BASE = "/mnt/cunyuliu/hf_home"
repos = sys.argv[1:]
for repo in repos:
    api = "https://hf-mirror.com/api/models/%s/tree/main?recursive=true" % repo
    try:
        r = requests.get(api, timeout=30, verify=False); r.raise_for_status(); files = r.json()
    except Exception as e:
        print(repo, "TREE-FAIL", e, flush=True); continue
    if isinstance(files, dict):
        print(repo, "TREE-ERR", files.get("error"), flush=True); continue
    n = 0
    for f in files:
        if f.get("type") != "file":
            continue
        rel = f["path"]
        if rel.startswith(".") or "onnx" in rel or "msgpack" in rel or "rust_model" in rel or rel.endswith(".h5") or "flax_model" in rel:
            continue
        if rel.startswith("docs/"):
            continue
        out = os.path.join(BASE, "models", repo.replace("/", "--"), "snapshots", "main", rel)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        if os.path.exists(out) and os.path.getsize(out) == f.get("size"):
            continue
        url = "https://hf-mirror.com/%s/resolve/main/%s" % (repo, rel)
        for a in range(3):
            try:
                with requests.get(url, stream=True, timeout=600, verify=False) as resp:
                    resp.raise_for_status()
                    with open(out + ".part", "wb") as fh:
                        for chunk in resp.iter_content(1 << 20):
                            fh.write(chunk)
                os.replace(out + ".part", out); n += 1
                print(repo, "ok", rel, f.get("size"), flush=True)
                break
            except Exception as e:
                print(repo, rel, "retry", a, e, flush=True); time.sleep(5)
    print(repo, "DONE files=%d" % n, flush=True)
