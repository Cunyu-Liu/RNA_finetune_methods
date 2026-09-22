#!/bin/bash
# 第七波：SSP micro dora/ia3 family 侧（E2 SSP 面板对称，6 runs）
# <gpu>；带 done 跳过 + 失败清行重试 x2
R=/mnt/cunyuliu/rna-ft-eval
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/home/cunyuliu/llr_env/bin/python
GPU=$1
LOG=$R/logs/q_ssp_micro_fam_g${GPU}.log
cd /home/cunyuliu/rna-ft-eval

$PY -c "import torch; assert torch.cuda.is_available()" || exit 2

for strat in dora ia3; do
  for S in 17 29 43; do
    RID=ft_rinalmomicro_secondarystructure_${strat}_s${S}_family
    ATT=0
    while [ $ATT -lt 2 ]; do
      D=$($PY -c "
import json
n=0
for l in open(\"$R/ledger.jsonl\"):
    r=json.loads(l)
    if r.get(\"run_id\")==\"$RID\" and r.get(\"status\")==\"done\": n=1
print(n)")
      [ "$D" = "1" ] && { echo "skip $RID (done)" >> $LOG; break; }
      F=$($PY -c "
import torch
free,_=torch.cuda.mem_get_info($GPU)
print(int(free/1e9))")
      if [ "$F" -ge 4 ]; then
        ATT=$((ATT+1))
        echo "=== attempt $ATT micro SSP $strat family s$S GPU$GPU (free ${F}G) $(date +%T) ===" >> $LOG
        timeout 21600 $PY -m rnafteval.finetune_ssp --model RiNALMo-micro \
          --strategy $strat --seed $S --split family --device $GPU \
          --epochs 3 --n-train 3000 --n-test 500 --batch-size 4 >> $LOG 2>&1
        RC=$?
        echo "--- exit $RC $(date +%T) ---" >> $LOG
        [ $RC -eq 0 ] && break
        $PY -c "
import fcntl,json
P=\"$R/ledger.jsonl\"
with open(P) as f: fcntl.flock(f,fcntl.LOCK_EX); rows=[l for l in f]
out=[l for l in rows if not (json.loads(l).get(\"run_id\")==\"$RID\" and json.loads(l).get(\"status\")==\"pending\")]
with open(P,\"w\") as f: fcntl.flock(f,fcntl.LOCK_EX); f.writelines(out)
print(\"cleaned\")" >> $LOG 2>&1
      fi
      sleep 300
    done
  done
done
echo "SSP-MICRO-FAM DONE $(date)" >> $LOG
