#!/bin/bash
# Single owner for B20-corrected cells; completion is decided by the dispatcher.
set -e
cd /home/cunyuliu/rna-ft-eval
export PYTHONPATH=/root/rnaft/pypath:/home/cunyuliu/rna-ft-eval:/home/cunyuliu/rna-sc
export HF_HOME=/root/hf_home
export HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/root/miniconda3/envs/llr_env/bin/python
ARGS=(--workers "${WORKERS:-1}")
if [ -n "${MODELS:-}" ]; then ARGS+=(--models $MODELS); fi
if [ -n "${TASKS:-}" ]; then ARGS+=(--tasks $TASKS); fi
exec "$PY" scripts/q_corrected_8task.py "${ARGS[@]}"
