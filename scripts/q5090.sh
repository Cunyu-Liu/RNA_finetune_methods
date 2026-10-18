#!/bin/bash
# q5090: run the 22 missing cells sequentially on RTX 5090 (32G).
# bs protocol: 650M lora e3 -> bs8; 650M full e3 -> bs8 (1015f protocol); mega lora/full -> bs16; AIDO full bs2.
# Occupies the single GPU fully; run in background via setsid.
set -x
cd /home/cunyuliu/rna-ft-eval
export PYTHONPATH=/root/rnaft/pypath:/home/cunyuliu/rna-ft-eval:/home/cunyuliu/rna-sc
export HF_HOME=/root/hf_home
export HF_ENDPOINT=https://hf-mirror.com
PY=/root/miniconda3/envs/llr_env/bin/python
LOG=/root/rnaft/logs/q5090.log
echo "=== q5090 start $(date -u +%FT%TZ) ===" >> $LOG

cell() { # model task strat seed split lr n bs
  m=$1; t=$2; s=$3; sd=$4; sp=$5; lr=$6; n=$7; bs=$8
  echo "--- $(date -u +%FT%TZ) $m $t $s s$sd $sp lr=$lr n=$n bs=$bs ---" >> $LOG
  timeout 21600 $PY -m rnafteval.finetune_one --model $m --task $t --strategy $s --seed $sd --split $sp \
    --device 0 ${lr:+--lr $lr} ${n:+--n-train $n} --batch-size $bs --epochs 10 >> $LOG 2>&1
  echo "RC=$? $(date -u +%FT%TZ)" >> $LOG
}

# --- mega e3 tail (8) ---
cell RiNALMo-mega noncoding-rna-family lora 43 family 3e-4 3000 16
cell RiNALMo-mega noncoding-rna-family full 17 family 1e-05 1000 16
cell RiNALMo-mega noncoding-rna-family full 29 family 1e-05 1000 16
cell RiNALMo-mega noncoding-rna-family full 17 family 1e-05 3000 16
cell RiNALMo-mega noncoding-rna-family full 29 family 1e-05 3000 16
cell RiNALMo-mega noncoding-rna-family full 43 family 1e-05 3000 16
cell RiNALMo-mega noncoding-rna-family full 29 family 1e-05 5000 16
cell RiNALMo-mega noncoding-rna-family full 43 family 1e-05 5000 16
# --- 650M e3 tail (13) ---
cell RiNALMo-650M noncoding-rna-family lora 17 family 3e-4 1000 8
cell RiNALMo-650M noncoding-rna-family lora 29 family 3e-4 1000 8
cell RiNALMo-650M noncoding-rna-family lora 43 family 3e-4 1000 8
cell RiNALMo-650M noncoding-rna-family lora 17 family 3e-4 3000 8
cell RiNALMo-650M noncoding-rna-family lora 29 family 3e-4 3000 8
cell RiNALMo-650M noncoding-rna-family lora 43 family 3e-4 3000 8
cell RiNALMo-650M noncoding-rna-family lora 17 family 3e-4 5000 8
cell RiNALMo-650M noncoding-rna-family lora 29 family 3e-4 5000 8
cell RiNALMo-650M noncoding-rna-family lora 43 family 3e-4 5000 8
cell RiNALMo-650M noncoding-rna-family full 43 family 1e-05 1000 8
cell RiNALMo-650M noncoding-rna-family full 43 family 1e-05 3000 8
cell RiNALMo-650M noncoding-rna-family full 17 family 1e-05 5000 8
cell RiNALMo-650M noncoding-rna-family full 29 family 1e-05 5000 8
# --- AIDO mrl full 1 cell (bs2 whole-card, long) ---
cell AIDO.RNA-1.6B mrl full 43 random 1e-05 "" 2
echo "=== q5090 ALL DONE $(date -u +%FT%TZ) ===" >> $LOG
