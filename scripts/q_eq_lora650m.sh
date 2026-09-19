#!/bin/bash
# 等价线 RiNALMo-650M LoRA 臂（GPU3）: 等下载完成 -> lora x {random,family} x 3 seeds
R=/mnt/cunyuliu/rna-ft-eval
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/home/cunyuliu/llr_env/bin/python
GPU=$1
LOG=$R/logs/q_eq_lora_rinalmo650m_g$GPU.log
cd /home/cunyuliu/rna-ft-eval
MODEL=RiNALMo-650M

CKPT=$HF_HOME/models/multimolecule--rinalmo-giga/snapshots/main/model.safetensors
echo "waiting for 650M download $(date +%T)" >> $LOG
while true; do
  if [ -f "$CKPT" ]; then
    S1=$(stat -c%s "$CKPT")
    sleep 30
    S2=$(stat -c%s "$CKPT" 2>/dev/null || echo 0)
    if [ "$S1" = "$S2" ] && [ "$S1" -gt 2000000000 ]; then
      echo "download complete size=$S1 $(date +%T)" >> $LOG
      break
    fi
  fi
  sleep 60
done

$PY -c "import torch; assert torch.cuda.is_available()" || exit 2
timeout 300 $PY -c "
import torch
free, _ = torch.cuda.mem_get_info($GPU)
assert free > 8e9, "free %.2fG" % (free/1e9)
print("GPU$GPU OK")" >> $LOG 2>&1 || { echo "GPU gate failed" >> $LOG; exit 2; }

for split in random family; do
  for seed in 17 29 43; do
    echo "=== $MODEL ncRNA lora s$seed $split GPU$GPU $(date +%T) ===" >> $LOG
    timeout 21600 $PY -m rnafteval.finetune_one --model $MODEL \
      --task noncoding-rna-family --strategy lora --seed $seed --split $split \
      --device $GPU --epochs 10 --batch-size 8 >> $LOG 2>&1
    echo "--- exit $? $(date +%T) ---" >> $LOG
  done
done
echo "EQ-LORA $MODEL DONE $(date)" >> $LOG
