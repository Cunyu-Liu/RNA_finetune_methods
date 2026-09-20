#!/bin/bash
# E3-MRL: RiNALMo {full@1e-5, lora, frozen} x n{100,1000,10000} x {random,family} x s{17,29,43} = 54 runs
R=/mnt/cunyuliu/rna-ft-eval
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/home/cunyuliu/llr_env/bin/python
GPU=$1
LOG=$R/logs/q_e3_mrl_g${GPU}.log
cd /home/cunyuliu/rna-ft-eval

$PY -c "import torch; assert torch.cuda.is_available()" || exit 2
timeout 300 $PY -c "
import torch
free, _ = torch.cuda.mem_get_info($GPU)
assert free > 4e9, "free %.2fG" % (free/1e9)
print("GPU$GPU OK")" >> $LOG 2>&1 || exit 2

for seed in 17 29 43; do
  for split in random family; do
    for n in 100 1000 10000; do
      for arm in full:1e-5 lora:- frozen:-; do
        STRAT=${arm%%:*}
        LRVAL=${arm##*:}
        echo "=== E3-MRL RiNALMo $STRAT s$seed $split n=$n GPU$GPU $(date +%T) ===" >> $LOG
        if [ "$LRVAL" = "-" ]; then
          timeout 7200 $PY -m rnafteval.finetune_mrl --model RiNALMo-micro \
            --strategy $STRAT --seed $seed --split $split \
            --device $GPU --epochs 3 --n-train $n --batch-size 32 >> $LOG 2>&1
        else
          timeout 7200 $PY -m rnafteval.finetune_mrl --model RiNALMo-micro \
            --strategy $STRAT --seed $seed --split $split \
            --device $GPU --lr $LRVAL --epochs 3 --n-train $n --batch-size 32 >> $LOG 2>&1
        fi
        echo "--- exit $? $(date +%T) ---" >> $LOG
      done
    done
  done
done
echo "E3-MRL DONE $(date)" >> $LOG
