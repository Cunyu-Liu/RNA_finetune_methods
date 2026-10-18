#!/bin/bash
# re-run newtask smoke after TokenHead pad_mask fix (1018 v2)
set -x
cd /home/cunyuliu/rna-ft-eval
export PYTHONPATH=/root/rnaft/pypath:/home/cunyuliu/rna-ft-eval:/home/cunyuliu/rna-sc
export HF_HOME=/root/hf_home
export HF_ENDPOINT=https://hf-mirror.com
PY=/root/miniconda3/envs/llr_env/bin/python
LOG=/root/rnaft/logs/newtask_smoke2.log
echo "=== newtask smoke v2 (pad_mask fix) start $(date -u +%FT%TZ) ===" > $LOG

# family splits already generated in v1 run (FAMILY_SPLITS_DONE in old log)
ls -la /root/rna-ft-eval/data/family_splits/degradation.parquet /root/rna-ft-eval/data/family_splits/ssi.parquet >> $LOG 2>&1

timeout 1200 $PY -m rnafteval.finetune_regbase --model RiNALMo-micro --task degradation --strategy frozen --seed 77 --split random --device 0 --epochs 1 --smoke >> $LOG 2>&1
echo "deg_frozen_RC=$?" >> $LOG
timeout 1200 $PY -m rnafteval.finetune_regbase --model RiNALMo-micro --task degradation --strategy lora --seed 77 --split random --device 0 --epochs 1 --smoke >> $LOG 2>&1
echo "deg_lora_RC=$?" >> $LOG
timeout 1200 $PY -m rnafteval.finetune_regbase --model RiNALMo-micro --task ssi --strategy frozen --seed 77 --split random --device 0 --epochs 1 --smoke >> $LOG 2>&1
echo "ssi_frozen_RC=$?" >> $LOG
timeout 1200 $PY -m rnafteval.finetune_regbase --model RiNALMo-micro --task ssi --strategy lora --seed 77 --split random --device 0 --epochs 1 --smoke >> $LOG 2>&1
echo "ssi_lora_RC=$?" >> $LOG
timeout 1200 $PY -m rnafteval.finetune_regbase --model RiNALMo-micro --task degradation --strategy frozen --seed 77 --split family --device 0 --epochs 1 --smoke >> $LOG 2>&1
echo "deg_fam_RC=$?" >> $LOG
echo "=== newtask smoke v2 ALL DONE $(date -u +%FT%TZ) ===" >> $LOG
