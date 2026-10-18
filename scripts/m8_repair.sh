#!/bin/bash
# m8 repair: rerun crispr + spliceai cells (claim key bug fixed in finetune_clf/spl)
# waits for m8_phase1 to finish, then reruns the 30 failed cells
set -x
cd /home/cunyuliu/rna-ft-eval
export PYTHONPATH=/root/rnaft/pypath:/home/cunyuliu/rna-ft-eval:/home/cunyuliu/rna-sc
export HF_HOME=/root/hf_home
export HF_ENDPOINT=https://hf-mirror.com
PY=/root/miniconda3/envs/llr_env/bin/python
LOG=/root/rnaft/logs/m8_repair.log
echo "=== m8 repair start $(date -u +%FT%TZ) ===" > $LOG

# wait for m8_phase1 main queue done
while ! grep -q "m8 phase1 ALL DONE" /root/rnaft/logs/m8_phase1.log 2>/dev/null; do sleep 120; done
echo "m8 phase1 done $(date -u +%FT%TZ)" >> $LOG

# smoke re-verify (2 cells)
timeout 1200 $PY -m rnafteval.finetune_clf --model RiNALMo-micro --task crispr-off-target --strategy frozen --seed 77 --split random --device 0 --epochs 1 --smoke >> $LOG 2>&1
echo "crispr_frozen_RC=$?" >> $LOG
timeout 1200 $PY -m rnafteval.finetune_spl --model RiNALMo-micro --task spliceai --strategy frozen --seed 77 --split random --device 0 --epochs 1 --smoke >> $LOG 2>&1
echo "spl_frozen_RC=$?" >> $LOG

# full batch: crispr + spliceai, frozen/lora x random/family x 3 seeds (24 cells)
for TASK in crispr-off-target:clf spliceai:spl; do
  TN="${TASK%%:*}"; RN="${TASK##*:}"
  for STRAT in frozen lora; do
    for SPLIT in random family; do
      for SEED in 17 29 43; do
        echo "--- $(date -u +%FT%TZ) RiNALMo-micro $TN $STRAT s$SEED $SPLIT ---" >> $LOG
        timeout 7200 $PY -m rnafteval.finetune_$RN --model RiNALMo-micro --task $TN --strategy $STRAT --seed $SEED --split $SPLIT --device 0 --epochs 10 >> $LOG 2>&1
        echo "RC=$?" >> $LOG
      done
    done
  done
done
echo "=== m8 repair ALL DONE $(date -u +%FT%TZ) ===" >> $LOG
