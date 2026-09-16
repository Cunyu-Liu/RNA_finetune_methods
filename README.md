# RNA_finetune_methods

**Controlled comparison of adaptation strategies for RNA language
models** — the RNA-side counterpart of Schmirler et al. (Nat Commun
2024) for protein LMs.

> Preprint: `paper/preprint_draft.md` (v0.2.1) · Chinese mirror:
> `paper/preprint_zh_summary.md` · Supplementary: `paper/supplementary.md`

## What this repo answers

Given an RNA task with limited labels and a single GPU, should you
fine-tune, and how? Three findings from a controlled matrix
(3 strategies × 5 RNA-LMs × 3 BEACON tasks × 2 splits × 3 seeds):

1. **Task granularity decides whether fine-tuning gains survive
   family-level splits**: per-sequence classification collapses
   (5/5 models, to 0.06–0.10) under MMseqs2 family-clustered splits;
   per-base tasks (m6A) keep gaining (0/4 collapse).
2. **LR × scale × strategy interact**: full-FT sweet spot shifts left
   with model scale; the 3e-4 default collapses full-FT (ln-C entropy
   plateau) while LoRA stays stable at the same LR.
3. **The official BEACON m6A "random" split is leak-contaminated**:
   27.2% of test windows share a host-transcript-level MMseqs2 cluster
   with training windows.

## Repository layout

| Path | Content |
|---|---|
| `rnafteval/` | pipeline: `finetune_one` / `finetune_base` / `finetune_ssp` (runners), `strategies` (frozen/LoRA/DoRA/IA3/head-only/full), `models` (5 RNA-LMs loaders), exporters (`export_c4/e2/resources/lr_grid/splits/leakage`), `stats`, `figures`, `checkpoint_report` |
| `paper/` | preprint draft + zh summary + supplementary |
| `scripts/` | queue chains (setsid nohup, kill -0 PID monitoring), family-split construction |
| `docs/` | checklist audit, checkpoint decisions (B15/B16) |
| `TRAINING_LOG.md` | full run-level training log (server-authoritative) |

## Reproducing

```bash
export PYTHONPATH=/mnt/<path>/pypath:/home/<user>/rna-ft-eval
python -m rnafteval.finetune_one --model RiNALMo-micro \
  --task noncoding-rna-family --strategy lora --seed 17 \
  --split family --device 0 --epochs 10 --batch-size 8
```

All results regenerate from the run ledger (JSONL, one row per run
with wall-time / peak memory / checkpoint size):

```bash
python -m rnafteval.export_c4        # C4 table (leakage × strategy)
python -m rnafteval.export_e2        # E2 five-arm PEFT table
python -m rnafteval.export_lr_grid   # A8 LR grids (seed 101)
python -m rnafteval.export_splits    # family-split stats + purity re-check
python -m rnafteval.export_leakage   # official-split leakage audit
python -m rnafteval.export_resources # E5 per-strategy cost
python -m rnafteval.stats            # sign tests + BH FDR + bootstrap CI
python -m rnafteval.figures --out status/figs
```

`scripts/chain_final_refresh.sh` re-runs all eight exporters after
the training queues drain — the ledger and family-split parquets are
the single sources of truth; no number is hand-transcribed.

## Protocols (frozen spec)

- Seeds: formal 17/29/43; tuning 101 (LR grids, excluded from formal
  matrices; tuned-LR rows tagged `_lr<value>`).
- Splits: official random arms + MMseqs2 0.8/0.8 cluster-pure family
  arms (per-base m6A via host-transcript proxy, assertion-checked).
- Statistics: preregistered plan (sign tests, BH q=0.05, direction
  consistency B14, checkpoint rules B15/B16 — see `docs/`).

## Data & weights

Run ledger, family splits, artifacts and logs live outside the repo
(`/mnt` runtime area per project layout); BEACON task data from the
official repository; RNA-LM weights from their respective releases
(see References in the preprint).
