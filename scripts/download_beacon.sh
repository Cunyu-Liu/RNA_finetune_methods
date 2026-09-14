#!/bin/bash
# BEACON task data download (hf-mirror, SSL-safe via requests)
export HF_ENDPOINT=https://hf-mirror.com
export PYTHONHTTPSVERIFY=0
DEST=/mnt/cunyuliu/rna-ft-eval/data/beacon_raw
LOG=/mnt/cunyuliu/rna-ft-eval/logs/download_beacon.log
mkdir -p $DEST
PY=$( [ -x /home/cunyuliu/miniconda3/envs/rnaft/bin/python ] && echo /home/cunyuliu/miniconda3/envs/rnaft/bin/python || echo python3 )
TASKS="secondary-structure contact-map distance-map structural-score-imputation spliceai isoform noncoding-rna-family modification mean-ribosome-loading degradation programmable-rna-switches crispr-on-target crispr-off-target"
echo "START v2 $(date)" >> $LOG
for t in $TASKS; do
  $PY - "$t" << 'EOF' >> $LOG 2>&1
import sys, os, json, time
import requests
import urllib3
urllib3.disable_warnings()
task = sys.argv[1]
repo = "jiahaozhang2003/beacon-%s" % task
dest = "/mnt/cunyuliu/rna-ft-eval/data/beacon_raw/%s" % task
api = "https://hf-mirror.com/api/datasets/%s/tree/main?recursive=true" % repo
r = requests.get(api, timeout=30, verify=False)
r.raise_for_status()
files = r.json()
n = 0
for f in files:
    if f.get("type") != "file" or f["path"] == ".gitattributes":
        continue
    rel = f["path"]
    out = os.path.join(dest, rel)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    if os.path.exists(out) and os.path.getsize(out) == f["size"]:
        continue
    url = "https://hf-mirror.com/datasets/%s/resolve/main/%s" % (repo, rel)
    for attempt in range(3):
        try:
            with requests.get(url, stream=True, timeout=120, verify=False) as resp:
                resp.raise_for_status()
                with open(out + ".part", "wb") as fh:
                    for chunk in resp.iter_content(1 << 20):
                        fh.write(chunk)
            os.replace(out + ".part", out)
            n += 1
            break
        except Exception as e:
            print(task, rel, "retry", attempt, e)
            time.sleep(5)
print(task, "downloaded", n, "files")
EOF
done
echo "ALL DONE $(date)" >> $LOG
