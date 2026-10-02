#!/bin/bash
# 补死格：e6off4/ fb5 GAVEUP 的格子收编重跑（2026-10-02）
# 1) RiNALMo-650M e6 lora s17 lr3e-4 bs16 need11（5 次中途 OOM 后 GAVEUP）
# 2) AIDO 1.6B ncRNA full s101 random lr1e-05 bs1 need34（等卡超限 GAVEUP）
R=/mnt/cunyuliu/rna-ft-eval
PY=/home/cunyuliu/llr_env/bin/python
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
cd /home/cunyuliu/rna-ft-eval
LOG=$R/logs/q_patch_dead_cells.log
CARD="$PY /home/cunyuliu/rna-ft-eval/scripts/rnaft_card.py"

$PY -c "import torch; assert torch.cuda.is_available()" || { echo "FATAL CUDA" >> $LOG; exit 1; }
echo "=== patch start $(date) ===" >> $LOG

# cell 1: e6 650M lora s17
res1=$R/artifacts/e6/RiNALMo-650M_lora_s17/result.json
ok1=0
[ -f "$res1" ] && ok1=1
for round in 1 2 3; do
  [ $ok1 -eq 1 ] && break
  for att in $(seq 1 200); do
    GS=$($CARD pick 11)
    if [ -z "$GS" ]; then echo "[patch] wait e6-650M-lora-s17 r$round $(date +%H:%M)" >> $LOG; sleep 300; continue; fi
    G=${GS%% *}; SL=${GS##* }
    [ -f "$res1" ] && { $CARD release $G $SL; ok1=1; break; }
    echo "[patch] RUN e6 650M lora s17 GPU$G.$SL r$round $(date +%H:%M)" >> $LOG
    $PY -m rnafteval.e6_forget --model RiNALMo-650M --strategy lora --seed 17 \
        --lr 3e-4 --device $G --batch-size 16 >> $LOG 2>&1
    rc=$?; $CARD release $G $SL
    echo "[patch] exit $rc e6 650M lora s17 $(date +%H:%M)" >> $LOG
    [ $rc -eq 0 ] && { ok1=1; break; }
  done
done
[ $ok1 -eq 0 ] && echo "[patch] GAVEUP e6 650M lora s17" >> $LOG

# cell 2: AIDO 1.6B full s101 lr1e-05（网格缺档）
res2=$R/artifacts/ft_aidorna16b_noncodingrnafamily_full_s101_random_lr1e-05/result.json
ok2=0
[ -f "$res2" ] && ok2=1
for round in 1 2 3; do
  [ $ok2 -eq 1 ] && break
  for att in $(seq 1 300); do
    GS=$($CARD pick 34)
    if [ -z "$GS" ]; then echo "[patch] wait aido-full-s101-1e5 r$round $(date +%H:%M)" >> $LOG; sleep 300; continue; fi
    G=${GS%% *}; SL=${GS##* }
    [ -f "$res2" ] && { $CARD release $G $SL; ok2=1; break; }
    echo "[patch] RUN AIDO full s101 lr1e-05 bs1 GPU$G.$SL r$round $(date +%H:%M)" >> $LOG
    $PY -m rnafteval.finetune_one --model AIDO.RNA-1.6B --task noncoding-rna-family \
        --strategy full --seed 101 --split random --device $G --lr 1e-05 \
        --batch-size 1 --epochs 10 >> $LOG 2>&1
    rc=$?; $CARD release $G $SL
    echo "[patch] exit $rc AIDO full s101 lr1e-05 $(date +%H:%M)" >> $LOG
    [ $rc -eq 0 ] && { ok2=1; break; }
  done
done
[ $ok2 -eq 0 ] && echo "[patch] GAVEUP AIDO full s101 lr1e-05" >> $LOG
echo "=== patch DONE $(date) ===" >> $LOG
