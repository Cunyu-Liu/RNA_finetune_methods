#!/bin/bash
# RNA-Sc-650M 预训练完成后的等价线测试链（受控系大端）
# 相位1: frozen+lora x 双切分 x 3 种子（GPU>=14G）
# 相位2: full tuned 链 s101 网格 -> formal（GPU>=28G）
R=/mnt/cunyuliu/rna-ft-eval
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/home/cunyuliu/llr_env/bin/python
LOG=$R/logs/q_rnasc650_tests.log
cd /home/cunyuliu/rna-ft-eval

pick_gpu() {
  $PY -c "
import torch
for i in range(6):
    free, _ = torch.cuda.mem_get_info(i)
    if free > $1:
        print(i); break
else:
    print(-1)" 2>/dev/null
}

echo "=== RNA-Sc-650M tests start $(date) ===" >> $LOG

# 相位1: frozen + lora
while true; do
  G=$(pick_gpu 14e9)
  if [ "$G" != "-1" ]; then break; fi
  sleep 120
done
echo "phase1 GPU$G $(date +%T)" >> $LOG
for strat in frozen lora; do
  for split in random family; do
    for seed in 17 29 43; do
      echo "=== RNA-Sc-650M $strat s$seed $split GPU$G $(date +%T) ===" >> $LOG
      timeout 21600 $PY -m rnafteval.finetune_one --model RNA-Sc-650M \
        --task noncoding-rna-family --strategy $strat --seed $seed --split $split \
        --device $G --epochs 10 --batch-size 8 >> $LOG 2>&1
      echo "--- exit $? $(date +%T) ---" >> $LOG
    done
  done
done

# 相位2: full tuned 链
while true; do
  G2=$(pick_gpu 28e9)
  if [ "$G2" != "-1" ]; then break; fi
  sleep 300
done
echo "phase2 GPU$G2 $(date +%T)" >> $LOG
for lr in 1e-5 3e-5; do
  echo "=== TUNING RNA-Sc-650M full s101 lr=$lr GPU$G2 $(date +%T) ===" >> $LOG
  timeout 21600 $PY -m rnafteval.finetune_one --model RNA-Sc-650M \
    --task noncoding-rna-family --strategy full --seed 101 --split random \
    --device $G2 --lr $lr --epochs 10 --batch-size 8 >> $LOG 2>&1
  echo "--- exit $? $(date +%T) ---" >> $LOG
done
BEST=$($PY -c "
import json
vals = {}
for l in open(\"$R/ledger.jsonl\"):
    r = json.loads(l)
    rid = r.get(\"run_id\",\"\")
    if (r.get(\"model\")==\"RNA-Sc-650M\" and r.get(\"task\")==\"noncoding-rna-family\"
        and r.get(\"strategy\")==\"full\" and r.get(\"seed\")==101
        and r.get(\"split\")==\"random\" and r.get(\"status\")==\"done\" and \"_lr\" in rid):
        lr = rid.split(\"_lr\")[-1]
        v = r.get(\"value\")
        if v is not None and (lr not in vals or v > vals[lr]):
            vals[lr] = v
print(max(vals, key=vals.get) if vals else \"1e-5\")")
echo "BEST LR = $BEST" >> $LOG
for split in random family; do
  for seed in 17 29 43; do
    echo "=== FORMAL RNA-Sc-650M full s$seed $split lr=$BEST GPU$G2 $(date +%T) ===" >> $LOG
    timeout 21600 $PY -m rnafteval.finetune_one --model RNA-Sc-650M \
      --task noncoding-rna-family --strategy full --seed $seed --split $split \
      --device $G2 --lr $BEST --epochs 10 --batch-size 8 >> $LOG 2>&1
    echo "--- exit $? $(date +%T) ---" >> $LOG
  done
done
echo "RNASC-650M TESTS DONE $(date)" >> $LOG
