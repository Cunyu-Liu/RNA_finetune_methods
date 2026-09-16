# To fine-tune or not to fine-tune RNA language models? A controlled
# strategy comparison reveals task-granularity-dependent leakage effects

**Preprint draft v0.1** — 2026-09-15（数据快照：Day 1，~120 formal runs；
矩阵补齐后数值将更新，结构与结论形态已固化）

## Abstract (draft)

Fine-tuning RNA language models (RNA-LMs) is widely assumed to beat frozen
embeddings, yet controlled comparisons across adaptation strategies are
missing. Following the protein-side template of Schmirler et al. (2024), we
run a controlled matrix of **3 adaptation strategies (frozen + shallow MLP
head / LoRA r=8 / full fine-tuning) × 2 RNA-LMs (10M/33M) × 3 BEACON tasks
× 2 evaluation splits (random vs sequence-family-clustered) × 3 seeds**,
each cell with a tuned learning rate chosen on a held-out tuning seed.

Three findings emerge:

1. **Fine-tuning helps, but the size of the help depends on task
   granularity — and on the split.** On ncRNA classification, LoRA/full FT
   improve accuracy by +0.3 to +0.57 under random splits, but **collapse to
   near-chance (0.06–0.10) under family-level splits**, while frozen heads
   degrade mildly. On per-base tasks (m6A modification), fine-tuned models
   **gain under both splits** (AUC 0.94→0.98 LoRA). Structure prediction
   (SSP) shows robust 2–5× gains over k-mer baselines under both splits.
2. **Task granularity determines leakage sensitivity**: the Δ(random−family)
   gap reaches +0.6 to +0.85 for fine-tuning on per-sequence classification
   but is ≈ −0.04 for per-base m6A and +0.003–0.03 for SSP — i.e., much of
   the "fine-tuning benefit" on sequence-level tasks under random splits is
   **family-level leakage**, echoing and quantifying the "simply cheating"
   critique for RNA benchmarks.
3. **Learning rate × strategy × model scale interact**: full FT's sweet
   spot shifts left (3e-5 at 10M → 1e-5 at 33M, with catastrophic collapse
   at 3e-4), while LoRA requires high LR (3e-4) at both scales; LR
   misconfiguration alone can flip apparent strategy rankings by ±0.5
   accuracy — a systematic risk for un-tuned comparisons.

We release the full ledger, family-cluster splits (MMseqs2 0.8/0.8), LR
grids, and a split-leakage audit of the official BEACON modification split
(**27.3% of test windows share a host-transcript-level cluster with
training windows**).

## 1 Introduction
- Gap: no RNA work places ≥2 adaptation strategies in one controlled
  comparison (BEACON full-FT only; Zablocki frozen only; etc. — spec §1
  four-source audit).
- Contribution: (i) C1 controlled matrix; (ii) C4 leakage×strategy
  interaction with task-granularity moderator; (iii) A8 LR-grid protocol
  evidence; (iv) split-leakage audit tooling.

## 2 Results

### 2.1 Fine-tuning is beneficial but task/split dependent (C1, Fig 1)
[fig:fig_c1_matrix] — heatmap; black boxes = beats strongest k-mer baseline.
Cross-model consistency (ncRNA random, LoRA): RNA-Sc 0.75, SpliceBERT 0.90,
RiNALMo 0.93, RNA-FM 0.96, ERNIE 0.97 — gains replicate across corpora.

### 2.2 Family-level splits reveal task-granularity-dependent collapse (C4, Fig 2)
[fig:fig_c4_delta] — Δ bars. Key numbers (3-seed means where marked, tuned LR):
- ncRNA: collapse **replicates across all five models**: LoRA Δ = +0.68
  (RNA-Sc) / +0.85 (RiNALMo) / +0.82 (SpliceBERT) / +0.89 (ERNIE) /
  +0.91 (RNA-FM); frozen Δ = +0.06–0.26 (mild); k-mer LGBM Δ = +0.007.
- m6A (per-base): no collapse, both models — RNA-Sc LoRA 0.94→0.98;
  RiNALMo LoRA 0.97→0.995 (Δ = −0.025).
- SSP: robust gains, no collapse — RiNALMo frozen 0.196→0.218, LoRA
  0.214→0.223 (3 seeds); RNA-Sc LoRA 0.084→0.076.
- **Leakage-sensitive fine-tuning is the norm for per-sequence
  classification (5/5 models), and the exception for per-base tasks (0/4
  model-task pairs).**

### 2.3 E2 PEFT horizontal comparison (C5, 5 arms, RiNALMo ncRNA random)
| arm | 3-seed mean | trainable params |
|---|---|---|
| full FT (LR-tuned 1e-5) | 0.938 | 33M |
| DoRA r=8 | 0.934 | ~0.35M |
| LoRA r=8 | 0.927 | ~0.18M |
| IA3 | 0.860 | ~0.02M |
| head-only | 0.817 | 16K |

- DoRA ≈ LoRA at r=8 (Schmirler's protein-side observation replicates in
  RNA); IA3 trails by ~0.07 with 10× fewer params; full FT wins only with
  tuned LR (default 3e-4 collapses to 0.077).
- Prefix-tuning infeasible under current dependency versions (peft 0.13
  tuple-style past_key_values vs transformers 5.0 Cache API) — documented
  limitation.

### 2.4 LR grids: scale × strategy × LR triple interaction (A8, Fig 3)
[fig:fig_lr_grid] — 4-point grids per model×strategy (seed 101).
RiNALMo full: 0.943/0.944/0.924/0.077 across 1e-5→3e-4;
RNA-Sc full: 0.683/0.815/0.807/0.688; LoRA: 0.723/0.923 (RNA-Sc/RiNALMo @3e-4).
m6A replication: RiNALMo full default-LR 0.30 → tuned 1e-5 (runs queued);
SSP full default-LR 0.006 → re-run at 1e-5 (queued).

### 2.5 Official split leakage audit (B1 discipline, new)
MMseqs2 0.8/0.8 over 309k BEACON modification windows: 327/1200 official
test windows (27.3%) cluster with training windows; 31-mer overlap 10.8%.
The official "random" arm is leak-contaminated at host-transcript level.

### 2.5 Statistics
Preregistered plan (§3.5): paired sign tests over 3 seeds + BH FDR q=0.05
across 30 contrasts; 3/3 direction consistency as primary evidence
(seed-level power wall documented); cell-level bootstrap CIs in Supp.

## 3 Methods (summary)
- Models: RNA-Sc-10M (controlled pretraining family), RiNALMo-micro (33M);
  first-look additions: ERNIE-RNA (frozen 0.825) and RNA-FM
  (frozen 0.917 — strongest frozen features, near k-mer LGBM 0.900).
  Tasks: BEACON ncRNA-family (13-class, n=8.5k, dedup'd), modification
  (m6A per-base, 309k windows), secondary-structure (bpRNA, pair-F1).
- Strategies: frozen+MLP(32)/LoRA(r8,α4,qkv+out)/full; AdamW; LR per
  A8 grid on tuning seed 101; formal seeds 17/29/43.
- Splits: official random arms; family arms = MMseqs2 80/80 cluster-pure
  (per-seq & whole-sequence tasks: sequence clusters; per-base m6A:
  host-transcript proxy via window clustering; assertion-checked purity).
- Evaluation: official metrics (ACC / AUC / pair-F1); zero-overlap
  assertions on every arm; GPU-only discipline with wall-time and peak
  memory recorded per run in a JSONL ledger.

## 4 Limitations
- n=3 seeds: sign-test power floor (min p=0.25); direction consistency +
  effect sizes are primary evidence, BH-significance aspirational.
- Family split for m6A is a host-proxy (window-clustering), not exact
  transcript IDs.
- Model pool currently 2 core + 3 first-look models; Tier-A expansion
  (8 models) in progress per spec E1.

## Data & Code
github.com/Cunyu-Liu/RNA_finetune_methods; ledger + figures auto-generated
(rnafteval export_c4 / stats / figures).
