#!/bin/bash
# A8 机制显微镜: 6 模型 x 100 步诊断（SpliceBERT/RiNALMo/ERNIE 崩, RNA-FM 幸存, RNA-Sc ck1/ck20 剂量两端）
R=/mnt/cunyuliu/rna-ft-eval
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/home/cunyuliu/llr_env/bin/python
GPU=$1
LOG=$R/logs/q_a8_diag_g${GPU}.log
cd /home/cunyuliu/rna-ft-eval

$PY -c "import torch; assert torch.cuda.is_available()" || exit 2
timeout 300 $PY -c "
import torch
free, _ = torch.cuda.mem_get_info($GPU)
assert free > 5e9, "free %.2fG" % (free/1e9)
print("GPU$GPU OK")" >> $LOG 2>&1 || exit 2

for M in SpliceBERT RiNALMo-micro ERNIE-RNA RNA-FM RNA-Sc-10M-ck1 RNA-Sc-10M-ck20; do
  echo "=== DIAG $M GPU$GPU $(date +%T) ===" >> $LOG
  timeout 7200 $PY -m rnafteval.diag_a8 --model $M --device $GPU --steps 100 >> $LOG 2>&1
  echo "--- exit $? $(date +%T) ---" >> $LOG
done
echo "A8-DIAG DONE $(date)" >> $LOG
