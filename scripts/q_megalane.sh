#!/bin/bash
# THIRD parallel lane: RiNALMo-mega lora on 4 new tasks (PPT Q2 mechanism-vis needs
# micro/mega/650M trio on new tasks). Runs alongside micro+650M lanes.
set -x
cd /home/cunyuliu/rna-ft-eval
export PYTHONPATH=/root/rnaft/pypath:/home/cunyuliu/rna-ft-eval:/home/cunyuliu/rna-sc
export HF_HOME=/root/hf_home
export HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/root/miniconda3/envs/llr_env/bin/python
LOG=/root/rnaft/logs/q_megalane.log
echo "=== megalane start $(date -u +%FT%TZ) ===" > $LOG

# remove mega cells from q_biglane (they'd duplicate); this lane owns mega
for TASK in degradation:regbase ssi:regbase spliceai:spl crispr-off-target:clf; do
  TN="${TASK%%:*}"; RN="${TASK##*:}"
  for SPLIT in random family; do
    for SEED in 17 29 43; do
      echo "--- $(date -u +%FT%TZ) RiNALMo-mega $TN lora s$SEED $SPLIT ---" >> $LOG
      timeout 14400 $PY -m rnafteval.finetune_$RN --model RiNALMo-mega --task $TN --strategy lora --seed $SEED --split $SPLIT --device 0 --epochs 10 --batch-size 16 >> $LOG 2>&1
      echo "RC=$?" >> $LOG
    done
  done
done
echo "=== megalane ALL DONE $(date -u +%FT%TZ) ===" >> $LOG
