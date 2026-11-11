#!/bin/bash
set -euo pipefail
export PYTHONPATH=/root/rna-ft-eval/pypath:.
export RNAFT_ARTIFACT_ROOT=/teams/HoulabData_1788502323/liucunyu/rna-ft-eval/artifacts
export RNAFT_TEAMS_ROOT=/teams/HoulabData_1788502323/liucunyu/rna-ft-eval
cd /home/cunyuliu/rna-ft-eval-delivery-20261111
out=/teams/HoulabData_1788502323/liucunyu/rna-ft-eval/status/revalidation/lora_memory_20261111
mkdir -p "$out/checkpoint"
for seed in 29 43; do
    /home/cunyuliu/llr_env/bin/python scripts/revalidate_lora_checkpoint.py \
        --seed "$seed" --device 0 --batch-size 32 --output-dir "$out/checkpoint" \
        > "$out/checkpoint_seed${seed}.log" 2>&1
done
export RNAFT_MECHANISM_CRISPR_ROOT="$RNAFT_ARTIFACT_ROOT/revalidation/lora_memory_20261111/crispr"
for seed in 29 43; do
    REVALIDATION_RID="crispr_lora_s${seed}_random" \
    REVALIDATION_OUT="$out/crispr_lora_s${seed}_random.json" \
        /home/cunyuliu/llr_env/bin/python scripts/revalidate_lora_memory.py \
        scripts.mechanism_crispr --split random --strategy lora --device 0 \
        --seed "$seed" --batch-size 64 > "$out/crispr_lora_s${seed}_random.log" 2>&1
done
