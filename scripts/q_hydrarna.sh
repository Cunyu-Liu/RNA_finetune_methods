#!/bin/bash
# HydraRNA frozen 观察臂队列（0930，P2.8；B11 SSM 架构观察——不入等价线）
# 协议：{ncRNA, m6A, SSP} × frozen × {random, family} × 3 种子 = 54 runs（UTR-LM 同款）
# 工程：worker = finetune runner（llr_env）持 RPC 子进程（hydrarna env）；
#       共享卡锁（slot 独占——RPC 子进程显存 ~2-3GB 但模型加载慢，串行最稳）；
#       done-skip（ledger run_id：ft_hydrarna_<task>_frozen_s<seed>_<split>）；
#       真 CUDA 断言（llr_env + worker ready 即证）；3 轮重试。
R=/mnt/cunyuliu/rna-ft-eval
PY=/home/cunyuliu/llr_env/bin/python
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
cd /home/cunyuliu/rna-ft-eval
LOG=$R/logs/q_hydrarna.log
CARD="$PY /home/cunyuliu/rna-ft-eval/scripts/rnaft_card.py"
NEED=8

is_done () {  # $1=task $2=seed $3=split
  $PY - "$1" "$2" "$3" <<'PYEOF'
import json,sys
task,seed,split=sys.argv[1:4]
rid="ft_hydrarna_%s_frozen_s%s_%s"%(task,seed,split)
for l in open("/mnt/cunyuliu/rna-ft-eval/ledger.jsonl"):
    l=l.strip()
    if not l: continue
    try: r=json.loads(l)
    except Exception: continue
    if r.get("run_id")==rid and r.get("status")=="done": sys.exit(0)
sys.exit(1)
PYEOF
}

run_task () {  # $1=task $2=mod $3=extra...
  local task=$1; shift
  local mod=$1; shift
  $PY -m "$mod" --model HydraRNA --strategy frozen --seed "$SEED" --split "$SPLIT" \
      --device "$G" "$@" >> $LOG 2>&1
}

$PY -c "import torch; assert torch.cuda.is_available(), 'CUDA NOT AVAILABLE'" || { echo "FATAL: CUDA unavailable (hydrarna)" >> $LOG; exit 1; }
echo "=== hydrarna queue start $(date) ===" >> $LOG

# ncRNA-family（per-seq；ncTask 用 finetune_one）
for cell in "17 random" "29 random" "43 random" "17 family" "29 family" "43 family"; do
  set -- $cell; SEED=$1; SPLIT=$2
  is_done noncoding-rna-family $SEED $SPLIT && continue
  ok=0
  for round in 1 2 3; do
    GS=$($CARD pick $NEED)
    if [ -z "$GS" ]; then
      echo "[hy] wait card ncRNA s$SEED $SPLIT r$round $(date +%H:%M)" >> $LOG; sleep 300; continue
    fi
    G=${GS%% *}; SL=${GS##* }
    if is_done noncoding-rna-family $SEED $SPLIT; then $CARD release "$G" "$SL"; ok=1; break; fi
    export HYDRA_CUDA_DEV=$G
    echo "[hy] RUN ncRNA s$SEED $SPLIT GPU$G.$SL r$round $(date +%H:%M)" >> $LOG
    $PY -m rnafteval.finetune_one --model HydraRNA --task noncoding-rna-family \
        --strategy frozen --seed $SEED --split $SPLIT --device $G >> $LOG 2>&1
    rc=$?; $CARD release "$G" "$SL"
    echo "[hy] exit $rc ncRNA s$SEED $SPLIT $(date +%H:%M)" >> $LOG
    [ $rc -eq 0 ] && { ok=1; break; }
  done
  [ $ok -eq 0 ] && echo "[hy] GAVEUP ncRNA s$SEED $SPLIT" >> $LOG
done

# modification (m6A per-base)
for cell in "17 random" "29 random" "43 random" "17 family" "29 family" "43 family"; do
  set -- $cell; SEED=$1; SPLIT=$2
  is_done modification $SEED $SPLIT && continue
  ok=0
  for round in 1 2 3; do
    GS=$($CARD pick $NEED)
    if [ -z "$GS" ]; then
      echo "[hy] wait card m6A s$SEED $SPLIT r$round $(date +%H:%M)" >> $LOG; sleep 300; continue
    fi
    G=${GS%% *}; SL=${GS##* }
    if is_done modification $SEED $SPLIT; then $CARD release "$G" "$SL"; ok=1; break; fi
    export HYDRA_CUDA_DEV=$G
    echo "[hy] RUN m6A s$SEED $SPLIT GPU$G.$SL r$round $(date +%H:%M)" >> $LOG
    $PY -m rnafteval.finetune_base --model HydraRNA --task modification \
        --strategy frozen --seed $SEED --split $SPLIT --device $G \
        --epochs 3 --n-train 20000 --batch-size 32 >> $LOG 2>&1
    rc=$?; $CARD release "$G" "$SL"
    echo "[hy] exit $rc m6A s$SEED $SPLIT $(date +%H:%M)" >> $LOG
    [ $rc -eq 0 ] && { ok=1; break; }
  done
  [ $ok -eq 0 ] && echo "[hy] GAVEUP m6A s$SEED $SPLIT" >> $LOG
done

# secondary-structure (SSP per-base)
for cell in "17 random" "29 random" "43 random" "17 family" "29 family" "43 family"; do
  set -- $cell; SEED=$1; SPLIT=$2
  is_done secondary-structure $SEED $SPLIT && continue
  ok=0
  for round in 1 2 3; do
    GS=$($CARD pick $NEED)
    if [ -z "$GS" ]; then
      echo "[hy] wait card SSP s$SEED $SPLIT r$round $(date +%H:%M)" >> $LOG; sleep 300; continue
    fi
    G=${GS%% *}; SL=${GS##* }
    if is_done secondary-structure $SEED $SPLIT; then $CARD release "$G" "$SL"; ok=1; break; fi
    export HYDRA_CUDA_DEV=$G
    echo "[hy] RUN SSP s$SEED $SPLIT GPU$G.$SL r$round $(date +%H:%M)" >> $LOG
    $PY -m rnafteval.finetune_ssp --model HydraRNA --task secondary-structure \
        --strategy frozen --seed $SEED --split $SPLIT --device $G \
        --epochs 3 --n-train 3000 --n-test 500 --batch-size 4 >> $LOG 2>&1
    rc=$?; $CARD release "$G" "$SL"
    echo "[hy] exit $rc SSP s$SEED $SPLIT $(date +%H:%M)" >> $LOG
    [ $rc -eq 0 ] && { ok=1; break; }
  done
  [ $ok -eq 0 ] && echo "[hy] GAVEUP SSP s$SEED $SPLIT" >> $LOG
done
echo "=== hydrarna queue DONE $(date) ===" >> $LOG