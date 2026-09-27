#!/bin/bash
# e6_official3: GPU1 目前有 18.7GB 空闲但 e6off2 用 18GB 门在等——其实卡上杂散进程多。
# 策略：用更高的 20GB 门 + 只在夜间窗口跑 + bs 降到 16（e6_forget 的 n-holdout 2000）。
# 且 mega/650M full-FT 的 30M 峰值 +26 是 tuned-LR 3e-5 才出现——e6 里 mega 用 1e-5 已知安全。
R=/mnt/cunyuliu/rna-ft-eval
PY=/home/cunyuliu/llr_env/bin/python
export PYTHONPATH=/mnt/cunyuliu/rna-ft-eval/pypath:/home/cunyuliu/rna-ft-eval
export HF_HOME=/mnt/cunyuliu/hf_home HF_ENDPOINT=https://hf-mirror.com
cd /home/cunyuliu/rna-ft-eval
LOG=$R/logs/q_e6_official2.log
echo "=== e6off3 retry-loop $(date) ===" >> $LOG
for round in 1 2 3 4 5; do
  all_done=1
  for cell in "RiNALMo-mega lora 17" "RiNALMo-mega lora 29" "RiNALMo-mega lora 43" \
              "RiNALMo-mega full 17" "RiNALMo-mega full 29" "RiNALMo-mega full 43" \
              "RiNALMo-650M lora 17" "RiNALMo-650M lora 29" "RiNALMo-650M lora 43" \
              "RiNALMo-650M full 17" "RiNALMo-650M full 29" "RiNALMo-650M full 43"; do
    set -- $cell
    resdir="$R/artifacts/e6/${1}_${2}_s${3}"
    if [ -f "$resdir/result.json" ]; then continue; fi
    all_done=0
    att=0
    while [ $att -lt 3 ]; do
      dev=$(nvidia-smi --query-gpu=index,memory.free --format=csv,noheader,nounits | awk -F", " '{ if ($2+0 >= 20000 && $1 < 6) print $1 }' | head -1)
      if [ -n "$dev" ]; then break; fi
      sleep 900
    done
    $PY -m rnafteval.e6_forget --model "$1" --strategy "$2" \
        --seed "$3" --lr 1e-05 --device "$dev" --batch-size 16 >> $LOG 2>&1
    echo "[e6off3] exit $? $1 $2 s$3 $(date +%H:%M)" >> $LOG
  done
  if [ "$all_done" = "1" ]; then echo "=== e6off3 ALL DONE ===" >> $LOG; break; fi
done
