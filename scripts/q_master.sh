#!/bin/bash
# q_master v2: stricter drain gate — requires (a) 3 consecutive checks <8G 60s apart,
# (b) zero finetune processes running. Fixes cold-start race where lanes load
# their next cell right after a momentary <8G reading.
set -x
export CELLTM=14400
cd /home/cunyuliu/rna-ft-eval
export PYTHONPATH=/root/rnaft/pypath:/home/cunyuliu/rna-ft-eval:/home/cunyuliu/rna-sc
export HF_HOME=/root/hf_home
export HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/root/miniconda3/envs/llr_env/bin/python
LOG=/root/rnaft/logs/q_master.log
echo "=== q_master v2 start $(date -u +%FT%TZ) ===" >> $LOG

wait_drain() {
  while true; do
    ok=0
    for i in 1 2 3; do
      used=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1)
      procs=$(ps aux | grep -cE '[f]inetune|[e]6_forget')
      if [ "$used" -lt 8000 ] && [ "$procs" -eq 0 ]; then ok=$((ok+1)); fi
      sleep 60
    done
    if [ "$ok" -eq 3 ]; then break; fi
    sleep 300
  done
}

run_cell() {
  desc=$1; shift
  wait_drain
  echo "=== $(date -u +%FT%TZ) $desc ===" >> $LOG
  timeout $CELLTM "$@" >> $LOG 2>&1
  echo "RC=$? $(date -u +%FT%TZ)" >> $LOG
}

# ---- Phase 1: E6 forgetting, 15 remaining cells ----
for s in 17 29 43; do
  run_cell "E6 ERNIE lora s$s" $PY -m rnafteval.e6_forget --model ERNIE-RNA --strategy lora --seed $s --lr 3e-4 --device 0 --epochs 10 --batch-size 32
done
for s in 17 29 43; do
  run_cell "E6 ERNIE full s$s" $PY -m rnafteval.e6_forget --model ERNIE-RNA --strategy full --seed $s --lr 1e-5 --device 0 --epochs 10 --batch-size 32
done
for s in 17 29 43; do
  run_cell "E6 RNAFM lora s$s" $PY -m rnafteval.e6_forget --model RNA-FM --strategy lora --seed $s --lr 3e-4 --device 0 --epochs 10 --batch-size 32
done
for s in 17 29 43; do
  run_cell "E6 RNAFM full s$s" $PY -m rnafteval.e6_forget --model RNA-FM --strategy full --seed $s --lr 1e-5 --device 0 --epochs 10 --batch-size 32
done
for s in 17 29 43; do
  run_cell "E6 NB full s$s" $PY -m rnafteval.e6_forget --model NucleicBERT --strategy full --seed $s --lr 1e-5 --device 0 --epochs 10 --batch-size 8
done
echo "PHASE1_E6_DONE $(date -u +%FT%TZ)" >> $LOG

# ---- Phase 2: spliceai family timeout reruns (mega/650M) ----
for M in RiNALMo-mega RiNALMo-650M; do
  for s in 17 29 43; do
    run_cell "spl-rerun $M lora family s$s" $PY -m rnafteval.finetune_spl --model $M --task spliceai --strategy lora --seed $s --split family --device 0 --epochs 10 --batch-size 16
  done
done
for M in RiNALMo-mega RiNALMo-650M; do
  for s in 17 29 43; do
    run_cell "spl-rerun $M full family s$s" $PY -m rnafteval.finetune_spl --model $M --task spliceai --strategy full --seed $s --split family --device 0 --epochs 10 --batch-size 8 --lr 1e-05
  done
done
echo "PHASE2_SPL_DONE $(date -u +%FT%TZ)" >> $LOG

# ---- Phase 3: AIDO 1.6B mrl full s43 (12h, bs1) ----
export CELLTM=43200
run_cell "AIDO mrl full s43 v5" $PY -m rnafteval.finetune_mrl --model AIDO.RNA-1.6B --task mrl --strategy full --seed 43 --split random --device 0 --epochs 3 --batch-size 1 --lr 1e-05
echo "=== q_master ALL DONE $(date -u +%FT%TZ) ===" >> $LOG
