#!/bin/bash
# Single-owner AIDO MRL s43 lane; exclusive_aido.py owns the /tmp lifecycle flock.
set -e
cd /home/cunyuliu/rna-ft-eval
export PYTHONPATH=/root/rnaft/pypath:/home/cunyuliu/rna-ft-eval:/home/cunyuliu/rna-sc
export HF_HOME=/root/hf_home
export HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/root/miniconda3/envs/llr_env/bin/python
LOG=/root/rnaft/logs/q_aido_exclusive.log
mkdir -p "$(dirname "$LOG")"
exec >> "$LOG" 2>&1
echo "=== q_aido_exclusive start $(date -u +%FT%TZ) ==="
exec "$PY" scripts/exclusive_aido.py
