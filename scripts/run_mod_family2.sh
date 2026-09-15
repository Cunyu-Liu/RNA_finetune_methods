#!/bin/bash
# mod family retry on GPU2 (after fill queue): lora s29/s43 + full 3 seeds
R=/mnt/cunyuliu/rna-ft-eval
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/home/cunyuliu/llr_env/bin/python
LOG=$R/logs/q_mod_family2.log
cd /home/cunyuliu/rna-ft-eval
# 清掉 GPU7 上 OOM 失败的 pending 行（lora s29/s43 family）
python3 - << "PYEOF"
import json
p = "/mnt/cunyuliu/rna-ft-eval/ledger.jsonl"
rows = [json.loads(l) for l in open(p) if l.strip()]
out = []
for r in rows:
    if r["run_id"] in ("ft_rnasc10m_modification_lora_s29_family",
                       "ft_rnasc10m_modification_lora_s43_family",
                       "ft_rnasc10m_modification_full_s17_family",
                       "ft_rnasc10m_modification_full_s29_family",
                       "ft_rnasc10m_modification_full_s43_family"):
        continue
    out.append(r)
with open(p, "w") as f:
    for r in out:
        f.write(json.dumps(r, default=str) + "\n")
print("cleaned", len(out))
PYEOF
for job in "lora 29" "lora 43" "full 17" "full 29" "full 43"; do
  set -- $job; strat=$1; seed=$2
  echo "=== modification-family $strat s$seed GPU2 $(date +%T) ===" >> $LOG
  timeout 14400 $PY -m rnafteval.finetune_base --model RNA-Sc-10M \
    --task modification --strategy $strat --seed $seed --split family \
    --device 2 --epochs 3 --n-train 20000 --batch-size 32 >> $LOG 2>&1
done
echo "MOD FAMILY2 QUEUE DONE $(date)" >> $LOG
