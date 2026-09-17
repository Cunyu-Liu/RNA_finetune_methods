#!/bin/bash
# GPU3 整卡 (free 18.6G): E2 受控重复 — RNA-Sc-10M DoRA/IA3 补臂
# spec v1.4: E2 = RiNALMo micro + RNA-Sc 受控重复; 现缺 dora/ia3
# 6 runs: {dora,ia3} × s{17,29,43} × random（对齐 RiNALMo E2 口径:
# epochs 10 / bs 8 / 默认 LR 3e-4; head-only 不跑——与 frozen
# 代码路径相同数值逐位一致, 项目规则）
R=/mnt/cunyuliu/rna-ft-eval
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/home/cunyuliu/llr_env/bin/python
LOG=$R/logs/q_e2_rnasc_g3.log
cd /home/cunyuliu/rna-ft-eval
GPU=3

$PY -c "import torch; assert torch.cuda.is_available()" || exit 2
timeout 300 $PY -c "
import torch
free, _ = torch.cuda.mem_get_info($GPU)
assert free > 4e9, 'GPU$GPU free %.2fG < 4G' % (free/1e9)
print('GPU$GPU free %.2fG OK' % (free/1e9))" >> $LOG 2>&1 || exit 2

for strat in dora ia3; do
  for seed in 17 29 43; do
    echo "=== E2-RNASC $strat s$seed random GPU$GPU $(date +%T) ===" >> $LOG
    timeout 14400 $PY -m rnafteval.finetune_one --model RNA-Sc-10M \
      --task noncoding-rna-family --strategy $strat --seed $seed \
      --split random --device $GPU --epochs 10 --batch-size 8 >> $LOG 2>&1
    echo "--- exit $? $(date +%T) ---" >> $LOG
  done
done
echo "E2 RNASC REPEAT GPU$GPU DONE $(date)" >> $LOG
