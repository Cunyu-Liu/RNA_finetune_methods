#!/bin/bash
# RNA-Sc-650M full tuned 相位2（前置接管）：s101 网格(1e-5/3e-5) -> BEST -> formal 6 runs
# 背景：主链 q_rnasc650_tests.sh 相位1 无 done-skip 会重跑已完成格子（~10h 浪费），已杀 bash 保孤儿子进程；
#       本队列与 g2(lora) claim 集不相交（队列互斥），full 格全部由本队列覆盖
# 协议：bs8（650M OOM 教训）、lr 后缀口径 _lr%g 与主链/受控系一致、幂等 done-skip、
#       全卡位选择(>=24G)、失败清 pending 重试(<=2)、6h 超时
R=/mnt/cunyuliu/rna-ft-eval
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY=/home/cunyuliu/llr_env/bin/python
LOG=$R/logs/q_rnasc650_full.log
cd /home/cunyuliu/rna-ft-eval

$PY -c "import torch; assert torch.cuda.is_available()" || exit 2

done_chk() {
  $PY - "$1" <<'PYEOF'
import json, sys
rid=sys.argv[1]; n=0
for l in open("/mnt/cunyuliu/rna-ft-eval/ledger.jsonl"):
    r=json.loads(l)
    if r.get("run_id")==rid and r.get("status")=="done": n=1
print(n)
PYEOF
}

pick_gpu() {
  $PY - $1 <<'PYEOF'
import sys, torch
need=int(sys.argv[1])
best=-1; best_free=0
for i in range(torch.cuda.device_count()):
    free,_=torch.cuda.mem_get_info(i)
    if free>best_free: best_free=free; best=i
print(best if best_free>=need*1e9 else -1)
PYEOF
}

run_one() {
  RID=$1; S=$2; SP=$3; LR=$4
  ATT=0
  while [ $ATT -lt 2 ]; do
    D=$(done_chk $RID)
    [ "$D" = "1" ] && { echo "skip $RID (done) $(date +%T)" >> $LOG; return; }
    G=$(pick_gpu 24)
    if [ "$G" != "-1" ]; then
      ATT=$((ATT+1))
      echo "=== attempt $ATT $RID GPU$G lr=$LR bs8 $(date +%T) ===" >> $LOG
      timeout 21600 $PY -m rnafteval.finetune_one --model RNA-Sc-650M \
        --task noncoding-rna-family --strategy full --seed $S --split $SP \
        --device $G --lr $LR --epochs 10 --batch-size 8 >> $LOG 2>&1
      RC=$?
      echo "--- exit $RC $(date +%T) ---" >> $LOG
      [ $RC -eq 0 ] && return
      $PY - <<PYEOF
import fcntl, json
P="/mnt/cunyuliu/rna-ft-eval/ledger.jsonl"
with open(P) as f:
    fcntl.flock(f, fcntl.LOCK_EX)
    rows=[l for l in f]
out=[l for l in rows if not (json.loads(l).get("run_id")=="$RID" and json.loads(l).get("status")=="pending")]
with open(P,"w") as f:
    fcntl.flock(f, fcntl.LOCK_EX)
    f.writelines(out)
PYEOF
    else
      echo "wait all GPU < 24G $(date +%T)" >> $LOG
    fi
    sleep 300
  done
}

echo "=== RNASC650-FULL start $(date) ===" >> $LOG

# 相位2a: s101 LR 网格
run_one ft_rnasc650m_noncodingrnafamily_full_s101_random_lr1e-05 101 random 1e-5
run_one ft_rnasc650m_noncodingrnafamily_full_s101_random_lr3e-05 101 random 3e-5

BEST=$($PY -c "
import json
vals={}
for l in open('$R/ledger.jsonl'):
    r=json.loads(l)
    rid=r.get('run_id','')
    if (r.get('model')=='RNA-Sc-650M' and r.get('task')=='noncoding-rna-family'
        and r.get('strategy')=='full' and r.get('seed')==101 and r.get('split')=='random'
        and r.get('status')=='done' and '_lr' in rid):
        lr=rid.split('_lr')[-1]
        v=r.get('value')
        if v is not None and (lr not in vals or v>vals[lr]): vals[lr]=v
print(max(vals,key=vals.get) if vals else '3e-05')")
echo "BEST LR = $BEST $(date +%T)" >> $LOG

# 相位2b: formal 6 runs（BEST LR）
for SP in random family; do
  for S in 17 29 43; do
    run_one ft_rnasc650m_noncodingrnafamily_full_s${S}_${SP}_lr${BEST} $S $SP $BEST
  done
done
echo "RNASC650-FULL DONE $(date)" >> $LOG
