#!/bin/bash
# RNA-LM model checkpoints download (hf-mirror, requests-based, SSL-safe)
export HF_ENDPOINT=https://hf-mirror.com
export HF_HOME=/mnt/cunyuliu/hf_home
mkdir -p $HF_HOME
LOG=/mnt/cunyuliu/rna-ft-eval/logs/download_models.log
PY=$( [ -x /home/cunyuliu/miniconda3/envs/rnaft/bin/python ] && echo /home/cunyuliu/miniconda3/envs/rnaft/bin/python || echo python3 )
echo "START v2 $(date)" >> $LOG
for repo in "multimolecule/ernierna" "multimolecule/splicebert" "multimolecule/rnafm" "lmzb-bupt/RiNALMo" "gyx1130/SpliceBERT-human510"; do
  $PY - "$repo" << 'EOF' >> $LOG 2>&1
import sys, os, time
import requests
import urllib3
urllib3.disable_warnings()
repo = sys.argv[1]
base = "/mnt/cunyuliu/hf_home"
api = "https://hf-mirror.com/api/models/%s/tree/main?recursive=true" % repo
r = requests.get(api, timeout=30, verify=False)
r.raise_for_status()
files = r.json()
n = 0
for f in files:
    if f.get("type") != "file":
        continue
    rel = f["path"]
    if rel.startswith(".") or "onnx" in rel or "msgpack" in rel or "rust_model" in rel or rel.endswith(".h5") or "flax_model" in rel:
        continue
    out = os.path.join(base, "models", repo.replace("/", "--"), "snapshots", "main", rel)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    if os.path.exists(out) and os.path.getsize(out) == f["size"]:
        continue
    url = "https://hf-mirror.com/%s/resolve/main/%s" % (repo, rel)
    for attempt in range(3):
        try:
            with requests.get(url, stream=True, timeout=300, verify=False) as resp:
                resp.raise_for_status()
                with open(out + ".part", "wb") as fh:
                    for chunk in resp.iter_content(1 << 20):
                        fh.write(chunk)
            os.replace(out + ".part", out)
            n += 1
            break
        except Exception as e:
            print(repo, rel, "retry", attempt, e)
            time.sleep(5)
print(repo, "downloaded", n, "files")
EOF
done
echo "ALL DONE $(date)" >> $LOG
