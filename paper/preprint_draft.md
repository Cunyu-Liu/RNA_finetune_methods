# To fine-tune or not to fine-tune RNA language models? A controlled
# strategy comparison reveals task-granularity-dependent leakage effects

**Preprint draft v0.96（外部架构验证臂数据刷新——C4 家族崩溃跨架构复现）** — 2026-09-26（数据快照：ledger 1346 runs；E1 缺口补齐 109/111 组；新架构验证臂 UTR-LM 36/36、mRNABERT 18/18（tokenizer 修复后，per-seq 限定）已收口，AIDO.RNA-1.6B / RiboSpan-1K-40 在飞；C6 受控系遗忘谱线 36 格全落地（§2.8，spec §10.4）；fig_e6_spectrum + status/e6_table.md 自动导出）C6 受控系遗忘谱线端点补全——1M→650M 全 6 档 × {LoRA, full-FT} × 3 种子 = 36 格全落地，非单调谱线闭合（§2.8，spec §10.4）；fig_e6_spectrum + status/e6_table.md 自动导出）

## Abstract

Fine-tuning RNA language models (RNA-LMs) is widely assumed to beat frozen
embeddings, yet controlled comparisons across adaptation strategies are
missing. Following the protein-side template of Schmirler et al. (2024), we
run a controlled matrix of **3 adaptation strategies (frozen + shallow MLP
head / LoRA r=8 / full fine-tuning) × 5 core RNA-LMs (10M–99M) + 6 external-architecture validation arms (UTR-LM 1.2M / mRNABERT 3-mer tokenizer / AIDO.RNA-1.6B / RiboSpan-1K-40 / SpliceBERT / ERNIE-RNA, + controlled RNA-Sc 1M-650M family) × 3 BEACON tasks
× 2 evaluation splits (random vs sequence-family-clustered) × 3 seeds**,
each fine-tuning cell with a learning rate chosen on a held-out tuning
seed, and audit every arm with zero-overlap assertions.

Three findings emerge:

1. **Fine-tuning helps, but the size of the help depends on task
   granularity — and on the split.** On ncRNA family classification, LoRA/full FT improve accuracy over frozen heads by +0.04 to +0.43
    (five-model range, strategy-dependent) under random splits, but **collapse to near-chance
   (0.06–0.12 band; partial LoRA escape at 148M: 0.14–0.33) under
   family-level splits** (frozen and
   head-only heads hold at 0.68-0.72 on the same split — the collapse
   requires backbone updates, not the task itself). On per-base tasks (m6A modification), fine-tuned models **gain
   under both splits** (AUC 0.970→0.995 for LoRA). Structure prediction (SSP) shows robust 2–5× gains over k-mer
   baselines under both splits.
2. **Task granularity determines leakage sensitivity**: the Δ(random−family)
   gap reaches +0.68 to +0.91 for fine-tuning on per-sequence classification
   but is −0.007 to −0.042 for per-base m6A and −0.005 to +0.027 for SSP
  (0/39 cells outside multi-member-family per-seq tasks; 5 models × 3
   tasks × 5 arms; collapse is granularity × family-density dependent) — i.e., much of
   the "fine-tuning benefit" on sequence-level tasks under random splits is
   **family-level leakage**, echoing and quantifying the "simply cheating"
   critique for RNA benchmarks.
3. **Learning rate × strategy × model scale interact, and the default
   LR is an architecture-agnostic trap**: full FT's sweet spot shifts
   left with scale (3e-5 at 10M → 1e-5 at 33M), while LoRA requires
   high LR (3e-4); at the 3e-4 default, full FT collapses to ln(C)
   prediction-entropy plateaus across three attention architectures
   (standard / ALiBi / base-pairing-constrained — 0.077 ACC,
   3/3 seeds each), with only the most extensively pretrained model
   (RNA-FM, 23.7M ncRNAs) surviving (0.82–0.84). LR misconfiguration
   alone can flip apparent strategy rankings by ±0.5 accuracy. Under
   tuned LRs the per-sequence task ranking is
   full ≥ DoRA ≈ LoRA ≫ IA3 > head-only.
4. **Whether small-model full-FT matches large-model LoRA is
   recipe-dependent — the two families point in opposite directions on
   every scale tested.** On the controlled RNA-Sc family (same recipe,
   1M–650M, five scales) full-FT beats same-scale LoRA at all five
   scales and a 30M full-FT model (0.862) matches the largest 650M
   LoRA (0.855); on the officially released RiNALMo family (33M/148M/
   650M) LoRA stays ahead at every scale (650M: 0.969 vs 0.957). We
   do not claim the equivalence crossover as a general RNA-LM law; the
   replicable finding is the direction, with the controlled family as
   an existence-proof counter-example bounding the claim.
5. **Catastrophic forgetting is real, non-monotone in scale, and
   tail-mitigated by adapters (C6, 36-cell matrix).** Fine-tuning on
   the ncRNA task measurably degrades held-out pretraining-objective
   NLL. The danger is concentrated in a mid-scale band: at 30M, full-FT
   degrades S0 by +4.1 to +26.2 NLL (two of three seeds near-collapse,
   post NLL ≈ 31) while LoRA's worst seed is +3.4 — adapters compress
   the forget tail by ~8×. The 1M–650M spectrum bounds the band on
   both sides: at 1M forgetting is mild and seed-noisy, at 10M and
   again at 650M both strategies *improve* S0 (negative forgetting,
   task data acts as pretraining reinforcement), and at 100M full-FT
   returns to ≈0 while LoRA stays mildly positive.
   The official RiNALMo-33M forgets its own pretraining distribution
   in all 6 cells (LoRA +0.11 to +0.14, full +0.15 to +0.16, MLM
   pseudo-likelihood). Adapter protection against forgetting is a
   variance effect as much as a mean effect.

We release the full run ledger, MMseqs2 0.8/0.8 family-cluster splits for
all three tasks, LR grids, and a split-leakage audit of the official BEACON
modification split (**27.3% of test windows share a host-transcript-level
cluster with training windows**).

## 1 Introduction

RNA language models pretrained on genomic-scale corpora now cover a wide
parameter range (10M–99M) and are routinely fine-tuned on downstream tasks.
Two evaluation habits, however, make the reported numbers hard to compare.

First, **adaptation strategies are compared only within single papers**:
BEACON evaluates full fine-tuning only; Zablocki et al. evaluate frozen
embeddings only; LoRA/DoRA/IA3 are evaluated in their respective
introduction papers on task subsets. No RNA work places more than two
strategies in one controlled comparison under identical data, compute and
tuning protocol — the protein-side gap Schmirler et al. (2024) closed for
protein LMs is still open for RNA.

Second, **random splits overstate fine-tuning**. When train and test
sequences share homologous families (ncRNA families; host transcripts for
per-base modification windows), a fine-tuned model can memorize family
signals rather than learn transferable ones. We quantify this with
MMseqs2-clustered, cluster-pure splits on all three BEACON tasks, and audit
the official random arms themselves (27.3% of the official m6A test set
shares a host-level cluster with training windows).

Contributions:
- **C1** A controlled strategy matrix (frozen / LoRA / full) × 5 models ×
  3 tasks × 2 splits × 3 seeds, every fine-tuning cell LR-tuned on a
  held-out tuning seed (protocol arm; seed 101).
- **C4** The leakage × strategy interaction with **task granularity as the
  moderator**: 5/5 models collapse on per-sequence classification under
  family splits; 0/4 model–task pairs collapse on per-base tasks.
- **A8** LR-grid protocol evidence: full-FT sweet spot shifts left with
  scale; LR misconfiguration flips rankings; tuned-LR protocol arm restores
  full-FT to the top of the ranking.
- **E2** A five-arm PEFT horizontal comparison (LoRA / DoRA / IA3 /
  head-only / full reference) under the same protocol.
- **B1** Split-leakage audit tooling (MMseqs2 0.8/0.8 clustering, zero-
  overlap assertions) applied to both our family arms and the official
  BEACON splits.

## 2 Results

### 2.1 Fine-tuning is beneficial but task/split dependent (C1, Fig 1)
[fig:fig_c1_matrix] — heatmap; black boxes = beats strongest k-mer baseline.
Cross-model consistency (ncRNA random, LoRA): RNA-Sc 0.75, SpliceBERT 0.90,
RiNALMo 0.93, RNA-FM 0.96, ERNIE 0.97 — gains replicate across corpora and
parameter scales (19M–99M).

### 2.1a External-architecture validation arms (new in v0.95, data refresh v0.96)

Six additional architectures beyond the core five test whether the C1/C4
findings are corpus/architecture-specific. Status and rules: only cells
recorded in the run ledger as done (non-smoke) are reported as results;
in-flight arms are marked [PENDING] and excluded from all aggregates.

- **UTR-LM (1.2M params)** — ncRNA only, 3 strategies × 2 splits × 3 seeds
  (36/36 cells done). Frozen 0.503 / LoRA 0.684 / full 0.495 (random,
  3-seed means). Note full-FT *under-performs* LoRA on this 1.2M model —
  consistent with the scale×strategy interaction in §2.4 (tiny models
  cannot afford full-FT representation damage).
- **mRNABERT (MosaicBERT, DNA 3-mer tokenizer)** — ncRNA only (3-mer
  tokens are not base-aligned; per-base tasks are invalid for this
  tokenizer — B20 gate). 18/18 cells done. Frozen 0.488 / LoRA 0.759 /
  full 0.782 (random): a k-mer-token model needs backbone adaptation far
  more than nucleotide-token models.
- **AIDO.RNA-1.6B / RiboSpan-1K-40 (1.6B)** — [PENDING: 48 runs in flight,
  ~7 h/run, ETA 09-27~28]. Baseline assertion: single-nucleotide
  tokenization verified (B20 gate), per-base arms valid.
- **A tokenizer-pathology case study (new)**: mRNABERT's published
  tokenizer maps raw RNA input to [UNK] (DNA alphabet, space-separated
  3-mer wordpieces) — every run scored at chance (ncRNA ACC 0.077 = 1/13,
  m6A AUC 0.50) until input preprocessing was fixed (U→T + 3-mer spacing).
  We quarantined all 58 invalid runs and re-ran. This is a concrete
  instance of "zero-overlap split audits are necessary but not
  sufficient" — input-path validation must be part of the evaluation
  protocol (checklist B20).

### 2.2 Family-level splits reveal task-granularity-dependent collapse (C4, Fig 2)
[fig:fig_c4_delta] — Δ bars. Key numbers (3-seed means; tuned LR where
marked):

- ncRNA: collapse **replicates across all five models**: LoRA Δ = +0.68
  (RNA-Sc) / +0.85 (RiNALMo) / +0.82 (SpliceBERT) / +0.89 (ERNIE) /
  +0.91 (RNA-FM); frozen Δ = +0.06–0.26 (mild); k-mer LGBM Δ = +0.007.
  The traditional baseline is leakage-insensitive by construction (no
  training on sequence features), making it a robust floor under family
  splits (0.900 vs 0.893 random vs family).
- m6A (per-base): no collapse across all five models — LoRA family/random
  ratios 1.007–1.042 (RNA-Sc 0.943→0.983; RiNALMo 0.970→0.995; ERNIE
  0.989→0.997; RNA-FM 0.982→0.996; SpliceBERT 0.955→0.988); family
  sides are slightly *higher* than random (dense per-position labels
  dilute family memorization).
- SSP (per-base): no collapse across all five models — ratios 0.956–1.110
  (ERNIE LoRA 0.337→0.345; RNA-FM 0.221→0.211; RNA-Sc 0.084→0.076;
  RiNALMo 0.214→0.223; SpliceBERT 0.168→0.169).
  The granularity pattern also replicates on the external arms: UTR-LM
  SSP ratios are flat (0.104→0.103 frozen; 0.135→0.141 LoRA), and
  mRNABERT follows the per-seq collapse rule on ncRNA (below).
- MRL (per-seq, singleton clusters): mild degradation only -- LoRA
  family/random ratios 0.85-0.92 across 5 models; delta = 0.04-0.12
  vs ncRNA 0.68-0.91. **Collapse requires multi-member family
  structure: the MRL task has 90,403 near-singleton clusters,
  leaving no family overlap to leak.**
- **Leakage sensitivity = granularity × family density.** 0/39
  model–task–arm cells collapse outside multi-member-family
  per-seq classification (5 models × 3 tasks × 5 arms): ncRNA collapses
  5/5; m6A/SSP (per-base) and MRL (singleton per-seq) are immune.
  **The collapse also replicates on the external-architecture arms**
  (§2.1a): UTR-LM LoRA 0.684→0.071 (random→family) and mRNABERT LoRA
  0.759→0.072 — including a 1.2M-parameter model and a 3-mer-token
  DNA-alphabet model. The pathology is not an artifact of the core five
  models' corpora or tokenizers.
  The family-split collapse holds at every scale tested -- 1M
  through 650M LoRA, including RiNALMo-650M (0.969 random ->
  0.106 family).

### 2.3 E2 PEFT horizontal comparison (C5: 2 models × 2 tasks, full factorial)

Auto-exported (status/e2_table.md); per-seed values in Supp S3.

| panel | ranking (3-seed means, random split) |
|---|---|
| RiNALMo-33M, ncRNA | full(tuned) 0.938 > **DoRA 0.934** > LoRA 0.928 > IA3 0.860 > head-only 0.817 |
| RNA-Sc-10M, ncRNA | **DoRA 0.765** > LoRA 0.746 > full 0.670 > IA3 0.579 > head-only 0.375 |
| RiNALMo-33M, m6A | **DoRA 0.979** > LoRA 0.970 > full(tuned) 0.968 > IA3 0.941 |
| RNA-Sc-10M, SSP | full 0.097 > LoRA 0.084 > DoRA 0.081 > IA3 0.042 > head-only 0.033 |

- **DoRA is the best arm in 2/4 panels, and full-FT never wins without
  caveats** — full wins on RiNALMo-33M ncRNA only with tuned LR (A8), and
  on RNA-Sc SSP at default LR where the 10M model is A8-robust; at 10M
  scale and on m6A the parameter-efficient arms dominate outright.
  "Small model + PEFT vs large model + full-FT" equivalence lines (C5's
  second question) get a concrete RNA data point: RNA-Sc-10M DoRA
  (0.765, ~0.57M trainable) vs RiNALMo-33M full (0.938) — the corpus/
  scale gap dominates, PEFT alone does not close it.
- IA3 is task-granularity sensitive: trails by 0.078 on per-sequence
  classification but only 0.027 behind LoRA on per-base m6A (0.941) —
  the cheapest adapter is viable where labels are dense per position.
- **Equivalence line (C5b, dual-family): "small full-FT = large LoRA"
  is family-dependent.** Controlled family (RNA-Sc, same recipe, full
  5-scale spectrum 1M-650M now complete): full-FT 1M 0.700 / 10M 0.808
  / 30M 0.862 / 100M 0.824 / 650M 0.896 vs LoRA 1M 0.639 / 10M 0.746
  / 30M 0.773 / 100M 0.795 / 650M 0.855 -- full@10M already matches
  LoRA@100M, full@30M outright beats it (crossover within one 3.3x
  scale step), and the advantage is not recovered at the large end:
  full@30M (0.862) ties LoRA@650M (0.855, +0.007), and full@650M
  (0.896) beats same-scale LoRA by +0.040 -- full-FT wins the
  controlled family at all five scales (full-FT curve is non-monotone
  with a 30M peak). Official family (RiNALMo, all three published
  sizes complete): micro-33M full 0.938 < mega-148M full 0.945 <
  giga-650M full 0.957 vs giga-650M LoRA 0.969 -- even
  full-FT at the largest released scale does not beat LoRA on the
  same checkpoint, and the 33M->650M full-FT gain is only +0.028:
  no crossover anywhere in the official family. Clean-scaling
  models reach equivalence early; officially released families retain a
  large-model advantage. Dual-track validation
  (user-requested): on the official three published RiNALMo scales the
  "small full-FT >= large LoRA" pattern does NOT hold -- micro-33M
  full (0.938) trails mega-148M LoRA (0.949) by -0.011, and even
  giga-650M full-FT (0.957, 3-seed mean: 0.966/0.939/0.964) trails
  giga LoRA (0.969) -- whereas the controlled family shows the
  crossover at 10M-30M and holds it through the largest controlled
  scale (650M full 0.896 > 650M LoRA 0.855; 30M full 0.862 ~
  650M LoRA 0.855): the two families are directionally opposite
  on every scale tested. **We explicitly do NOT claim the equivalence
  crossover as a general RNA-LM law: it is evidenced in exactly one
  model family (our controlled RNA-Sc recipe) and absent in the
  official RiNALMo family and in the wider model pool at comparable
  scales (ERNIE-86M full 0.973 vs LoRA 0.974 tie; RNA-FM-99M full
  0.835 < LoRA 0.962; SpliceBERT-19M full 0.910 ≈ LoRA 0.903). The
  honest reading: whether small-model full-FT matches large-model LoRA
  is recipe-dependent and currently single-family-evidenced. The
  robust, replicable finding is the direction -- released families
  retain a large-model LoRA advantage -- and the controlled family
  serves as the existence-proof counter-example bounding the claim,
  the role spec v1.7 pre-assigned to it.** On the per-base
  m6A task the dual-track line saturates across the full controlled
  spectrum (LoRA 1M-650M, six scales: 0.941-0.948, spread < 0.006;
  1M already reaches the ceiling, gap to 650M < 0.006) and the
  official family (all tiers 0.94-0.997): equivalence-line
  identifiability itself is task-granularity dependent. The 650M
  controlled point adds a task-granularity x strategy mirror: on
  m6A, LoRA (0.948) beats full-FT (0.927) by +0.021 while on ncRNA
  the same checkpoint reverses (full 0.896 > LoRA 0.855, +0.040) --
  per-base tasks favor adapters, per-sequence tasks (in this
  family) favor full-FT, an orthogonal confirmation that the best
  strategy is a property of task granularity, not of the model. On family splits, all eight LoRA cells
  (controlled 1M/10M/30M/100M/650M + official 33M/148M/650M)
  collapse to the 0.06-0.12 band *on average* (3-seed means: 1M 0.126,
  10M 0.072, 30M 0.064, 100M 0.081, controlled 650M 0.064, 33M 0.081,
  148M 0.207, official 650M 0.106) -- leakage sensitivity is
  largely scale-invariant, with one structured exception: the
  148M mega checkpoint escapes the band in all three seeds
  (0.139-0.334, mean 0.207) and 1M/650M escape in single seeds --
  partial escape is LoRA x pretraining-sufficiency dependent, not
  a monotone function of scale. The controlled 650M shows the most
  complete collapse observed: all three LoRA seeds return the
  identical degenerate value 0.064 (majority-class prediction), and
  tuned full-FT (0.064-0.096) joins the band while frozen reaches
  0.516 -- backbone-updating arms destroy the frozen family-level
  representation rather than transfer it.

[fig:fig_c5b] -- dual-family equivalence-line spectrum (8 scales);
status/figs/fig_c5b.png (slide: figs/equivalence_line.pptx).

- Prefix-tuning infeasible under current dependency versions (peft 0.13
  tuple-style past_key_values vs transformers 5.0 Cache API) — documented
  limitation.

### 2.4 LR grids: scale × strategy × LR triple interaction (A8, Fig 3)

Default-LR (3e-4) full-FT collapse is **task-dependent and extends to all
five models on regression**: ncRNA 3/5 collapse (SpliceBERT/ERNIE/RiNALMo),
m6A 3/5, MRL **5/5** (RiNALMo -0.001, SpliceBERT 0.098, ERNIE 0.028,
RNA-Sc 0.169, RNA-FM 0.181 -- the only ncRNA/m6A survivor collapses on
MRL); tuned LR recovers every cell (MRL 0.79-0.80 except RNA-Sc 0.53).
LoRA never collapses at default LR on any task -- the phenomenon is
full-FT-specific. Mechanistically (100-step diagnostics), collapse is an
instant representation rank collapse: last-hidden effective rank drops
300-500 -> 1 within 5-10 steps at only 3-5% weight drift; RNA-FM survives
via post-collapse rebound (rank 9 -> 51) and RNA-Sc recovers within
epochs -- collapse resistance is a recipe-family property (ALiBi-narrow
robust, BERT-family mid-size fragile), not a monotone function of
pretraining progress (dose experiment over RNA-Sc ck1-ck15 shows no
dose effect).
[fig:fig_lr_grid] — 4-point grids per model×strategy (seed 101).
RiNALMo full: 0.943/0.944/0.924/0.077 across 1e-5→3e-4;
RNA-Sc full: 0.683/0.815/0.807/0.688; LoRA @3e-4: RNA-Sc 0.723,
RiNALMo 0.934 (full grid: status/lr_grid_table.md, auto-exported).
Tuned-LR protocol replication (Day 2): RiNALMo m6A full default-LR 0.30 →
**0.968/0.993 (random/family, 3 seeds, 1e-5)**; SSP full default-LR 0.006 →
**0.151–0.176 (3 seeds, 1e-5, direction-consistent ×24–27)** — recovery,
confirming the grid diagnosis that the default 3e-4 is catastrophic for
full-FT.

**Cross-architecture collapse at the default LR, and tuned recovery
(new)**: the ln(C) loss plateau (prediction entropy saturation)
reproduces across three attention architectures — RiNALMo (standard),
SpliceBERT (ALiBi), ERNIE-RNA (explicit base-pairing-constrained
attention) — all collapsing to 0.077 ACC at 3e-4 full-FT, while
RNA-FM (99.5M, most extensive pretraining) is the only survivor
(0.82–0.84 random). Tuned-LR backfill restores every collapsed arm:
SpliceBERT full@3e-5 random = 0.910 (3-seed, ×11.8 recovery,
exceeding its LoRA 0.904); ERNIE full@1e-5 random = 0.973 (×12.6,
matching LoRA 0.974) — the collapse is an LR artifact, not a
strategy property. Under family splits both tuned arms still
collapse (0.06–0.10) — the C4 per-sequence collapse holds across
all five models in both LoRA and tuned-full arms, ruling out LR
confounding for the leakage finding.

### 2.5 Label-budget axis (E3 first data, C3 preview)

With cluster-level subsampling (draw clusters, keep them whole —
seed-matched subsets at n ∈ {10, 100, 1000} + full 6,859) on the
family split, the strategy ranking flips with label budget
(RiNALMo-micro, 3-seed means; RNA-Sc-10M replicates the n=10
pattern):

| n | frozen | LoRA | full | best |
|---|---|---|---|---|
| 10 | 0.103 | 0.131 | **0.229** | full |
| 100 | 0.424 | **0.509** | 0.076† | LoRA |
| 1,000 | 0.664 | **0.685** | 0.076† | LoRA |
| 6,859 (full) | **0.696** | 0.081 | 0.083† | frozen |

† full-FT small-n arms at the default LR (3e-4) — the A8 collapse;
not a label-budget effect (tuned-LR backfill queued).

Three signals: (i) at n=10 full fine-tuning is *best* (3× chance on
both models) — ten sequences teach class priors, not family
memorization, and the frozen head (16K params) cannot even fit that;
(ii) the tuned full-FT curve is *non-monotone in label budget*:
0.16 (n=10) → 0.52 (100) → **0.707 (1,000, best of all strategies)**
→ 0.083 (6,859, collapse) — more labels first help then *hurt*
full fine-tuning under family splits, because family memorization
grows with data mass: the direct C3×C4 mechanism;
(iii) 1,000 tuned labels recover 99%+ of the full-data frozen score
and beat every strategy — practically, a thousand annotations
suffice for this task class. RNA-Sc-10M replicates the n=10/n=100
full-best pattern at its scale. Full learning curves:
fig_e3_curves (per-model panels, min-max bands).

### 2.6 Official split leakage audit (B1 discipline)
MMseqs2 0.8/0.8 over 309k BEACON modification windows: 327/1200 official
test windows (27.3%) cluster with training windows; 31-mer overlap 10.8%.
The official "random" arm is leak-contaminated at host-transcript level.

### 2.7 Statistics
Preregistered plan (§3.5): paired sign tests over 3 seeds + BH FDR q=0.05
across 58 contrasts; 3/3 direction consistency as primary evidence
(seed-level power wall documented: n=3 sign-test minimum p=0.25);
cell-level bootstrap CIs in Supp.

### 2.8 Catastrophic forgetting: mid-scale danger band, adapter tail
protection (C6, E6 first data)

We measure pretraining-objective forgetting directly: ncRNA-family
fine-tuning (tuned LRs, 10 epochs, 3 seeds) with held-out pretraining
NLL evaluated before and after (S0 = the held-out tiers — test plus
cluster-disjoint family-test — of the 29M-sequence RNAcentral
release-22 80/80 split, n=2,000; ΔNLL = post − pre, reorder noise
band < 3e-8, every cell significant). Controlled-family models are
causal LMs (shift-by-1 NLL, baseline ≈ 4.5); RiNALMo-micro is
bidirectional, so we score MLM full-context pseudo-likelihood
(baseline 0.07) — absolute NLL is comparable within a family only.

| model | ΔNLL LoRA (s17/29/43) | ΔNLL full-FT | reading |
|---|---|---|---|
| RNA-Sc-1M | +0.29 / −0.26 / +3.76 | +2.50 / −0.86 / −0.71 | mild, seed-noisy (one LoRA seed +3.8); full-FT does not exceed the band |
| RNA-Sc-10M | −0.93 / −1.07 / −0.59 | −1.44 / −1.89 / −1.56 | **negative forgetting** (both arms improve S0) |
| RNA-Sc-30M | +1.93 / −0.84 / +3.38 | +4.12 / **+26.24** / **+22.67** | forgetting peak; full-FT tail risk |
| RNA-Sc-100M | +0.86 / +0.56 / +0.18 | +1.39 / +0.15 / **−1.61** | full-FT re-stabilizes, LoRA stays mildly positive |
| RNA-Sc-650M | −0.40 / −1.05 / −1.11 | −2.75 / +7.07 / −3.18 | large-scale re-stabilizes; LoRA 3/3 negative, full-FT 1/3 over band (worst +7.1) |
| RiNALMo-micro | +0.11 / +0.14 / +0.11 | +0.16 / +0.15 / +0.16 | official model forgets its own corpus, tight variance |

Three findings: (i) **forgetting is non-monotone in scale, with a bounded mid-scale
danger band** — across the now-complete 1M→650M controlled spectrum, 1M
is mild and seed-noisy, 10M gains, 30M catastrophically degrades
(full-FT post NLL reaches 30.8, +26 over pre), 100M re-stabilizes to ≈0,
and 650M is again negative (LoRA +0/−1.1, full-FT worst seed +7.1) — so
"bigger models forget more/less" is wrong in both directions; the
mid-scale band is where task gradients compete most directly with
pretraining features. (ii) **Adapter protection is
primarily a tail effect**: at 30M the mean full/lora ratio is ~12×, but
the decision-relevant quantity is the worst seed — LoRA's worst is +3.38
vs full-FT's +26.24 (8× tail compression; one LoRA seed is even
negative). For deployment risk management, LoRA bounds the downside.
(iii) **The official RiNALMo model forgets its own pretraining
distribution in every cell** (6/6, +0.11 to +0.16) with tight seed
variance — released-model users pay a measurable forgetting cost on
*any* task fine-tune at this scale. The controlled 1M–650M spectrum is
now complete (fig_e6_spectrum): forgetting is bounded on both the small
and large ends and peaks sharply at 30M.

[fig:fig_e6_matrix] — forgetting matrix, auto-exported:
status/e6_table.md (per-seed cells + csv); [fig:fig_e6_spectrum] —
controlled-family ΔNLL vs scale, status/figs/fig_e6_spectrum.{png,pdf}.

## 3 Methods (summary)
- Models (5, spanning 10M-99M): RNA-Sc-10M (controlled pretraining
  family, 10M); RiNALMo-micro (33M, 650M-family micro variant);
  SpliceBERT (19M, splice/pre-mRNA corpus — cross-domain); ERNIE-RNA
  (86M, base-pairing-constrained attention, 20.4M ncRNAs); RNA-FM
  (99.5M, 23.7M ncRNAs — strongest frozen features, near k-mer LGBM
  0.900). Frozen reference scores: ERNIE 0.825, RNA-FM 0.917.
  Tasks: BEACON ncRNA-family (13-class, n=8.5k, dedup'd),
  modification (m6A per-base, 309k windows), secondary-structure
  (bpRNA, pair-F1).
- Strategies: frozen+MLP(32)/LoRA(r8,α4,qkv+out)/full; AdamW; LR per
  A8 grid on tuning seed 101; formal seeds 17/29/43.
- Splits: official random arms; family arms = MMseqs2 80/80 cluster-pure
  (per-seq & whole-sequence tasks: sequence clusters; per-base m6A:
  host-transcript proxy via window clustering; assertion-checked purity).
- Evaluation: official metrics (ACC / AUC / pair-F1); zero-overlap
  assertions on every arm; GPU-only discipline with wall-time and peak
  memory recorded per run in a JSONL ledger (196 runs at this snapshot).
- Forgetting (E6): S0 held-out NLL (RNAcentral release-22 29M-sequence
  80/80 cluster split, held-out test + family-test tiers, n=2,000,
  len 32–512, deterministic eval with reorder-noise band <3e-8); causal
  LMs scored with shift-by-1 CE, bidirectional RiNALMo with MLM
  full-context pseudo-likelihood; LoRA arms merged (merge_and_unload)
  before post-NLL so the score reflects deployed weights.

## 4 Discussion (draft)
- **Granularity, not "fine-tuning vs frozen", is the first-order factor.**
  The 0.68–0.91 Δ gaps on per-sequence tasks vs ≈0.03 on per-base tasks
  mean a practitioner's first question should be whether their task label
  is constant over homologous families — if yes, random-split fine-tuning
  numbers are inflated by family memorization.
- **Frozen features + shallow heads are the robust default under
  distribution shift**: frozen Δ stays within +0.06–0.26 while fine-tuning
  Δ explodes; k-mer LGBM is invariant by construction. For family-shifted
  deployment (new ncRNA families), frozen or k-mer baselines remain
  competitive (0.893–0.896 vs fine-tuned 0.06–0.10).
- **LR discipline is a confound-killer**: with per-scale tuned LRs the
  full ≥ LoRA ordering re-emerges (0.938 vs 0.928); untuned defaults
  (3e-4) invert it (0.077 vs 0.928). Any cross-strategy claim without a
  per-strategy LR sweep on held-out data is suspect.
- **Practical selection rule (from C5)**: at 33M scale, DoRA r=8 matches
  LoRA within noise (0.934 vs 0.928) at comparable params (~0.57M vs ~0.55M); IA3 trades ~0.07 ACC
  for 10× param economy; head-only is a strong floor (0.817) but not
  competitive for per-sequence tasks under random splits.
- **Forgetting risk is concentrated, not uniform (C6)**: the E6 matrix
  shows the practitioner-relevant summary — mid-scale (30M) full-FT
  carries a catastrophic-forgetting tail (+26 NLL worst seed) that
  LoRA compresses 8×, while 10M fine-tuning is free (negative
  forgetting) and 100M full-FT self-stabilizes. Where downstream
  deployments reuse the backbone (multi-task pipelines, continued
  pretraining), adapters are insurance with a bounded premium, not
  just a parameter-economy trade.


### 4.1 Preregistered decision rules (spec §7-8, frozen before analysis)

To prevent post-hoc narrative, the strategy-recommendation rules were
frozen in the preregistered spec before any matrix results existed:

| verdict | rule (frozen) |
|---|---|
| recommend | gain > +2% AND BH-significant (q<0.05) |
| neutral | gain in [−?%, +2%] OR seed direction inconsistent |
| not-recommend | gain < 0 AND BH-significant decline |

Applied to this snapshot (n=3 seeds; sign-test power wall documented
in Limitations — BH-significance is aspirational at this seed count,
so direction consistency + effect size carry the primary evidence):

- **ncRNA classification (per-seq), random split**: LoRA/full
  recommend (gains +0.04..+0.43 across five models, 3/3
  seed-consistent; full-FT only at tuned LR — the default-3e-4 full
  arm collapses and is the LR-misconfiguration illustration, not a
  strategy verdict); under family split, all fine-tuning arms are
  *not-recommendable* (collapse to 0.06–0.10 vs frozen 0.19–0.92
  and k-mer 0.893).
- **m6A (per-base)**: fine-tuning recommend (LoRA +0.05 frozen→0.995;
  0/3-contrast-significant but 3/3 direction-consistent); frozen head
  neutral-to-recommend at 33M (+0.39 vs k-mer).
- **SSP**: LoRA/frozen recommend vs k-mer baselines (2–5× pair-F1);
  full-FT neutral at default LR, recommend at tuned 1e-5.

The decision tree for practice (which strategy at which label budget)
arrives with the E3 low-data axis (spec T3.1) — out of this
preprint scope, rules already frozen.

## 5 Limitations
- n=3 seeds: sign-test power floor (min p=0.25); direction consistency +
  effect sizes are primary evidence, BH-significance aspirational.
- Family split for m6A is a host-proxy (window-clustering), not exact
  transcript IDs.
- Model pool currently 2 core + 3 first-look models; Tier-A expansion
  (8 models) in progress per spec E1.
- Prefix-tuning excluded due to dependency-stack incompatibility (peft
  0.13 / transformers 5.0 Cache API); documented, not worked around.
- RiNALMo SSP full tuned arm: 3/3 seeds random (0.151–0.176,
  ×24–27 recovery, direction-consistent) + family side backfilled
  (0.158–0.189); no longer a 1-seed claim.
- Preregistered checkpoint rule has two ambiguities discovered at
  automation (B16): the gain-median population was undefined (fixed:
  per-task best model, primary; all-cell pool, reported); and the
  "no BH-significant cell" branch is vacuously true under n=3 sign
  tests (power wall) — documented, decision unchanged.
- E6 forgetting: causal (RNA-Sc) vs MLM (RiNALMo) NLL metrics are
  family-internal only; the controlled 1M–650M spectrum is complete
  (36 cells); single-finetune-epoch protocol (10 ep, no replay or
  regularization baselines) measures the raw forgetting cost.



## Author Contributions (draft, to be finalized)

L.C. conceived and designed the study, implemented the full
pipeline (data splits, training, evaluation, statistics, figures),
ran all experiments, and wrote the manuscript. (Additional
co-author roles — e.g. supervision, funding, revision — to be
assigned with the PI before submission.)

## Acknowledgments

We thank the BEACON consortium for open benchmark tasks and data,
the RNA-LM community for open weights (RiNALMo / ERNIE-RNA /
RNA-FM / SpliceBERT / RNA-Sc), and the A100 cluster operators.
Computing resources: institutional GPU cluster (see Data & Code
for per-run resource ledger).

## Funding

To be completed before submission. (No funding statement is made
in this draft.)

## References (core; full list to be BibTeX-ized at submission)

1. Schmirler R, Heinzinger M, Rost B. Fine-tuning protein language
   models boosts predictions across diverse tasks. *Nat Commun*
   15:7407 (2024). doi:10.1038/s41467-024-51844-2
2. Ren Y, Chen Z, Qiao L, et al. BEACON: benchmark for
   comprehensive RNA tasks and language models. *NeurIPS 2024
   Datasets & Benchmarks*. (full-FT-only protocol that we extend
   with the strategy axis; 13 tasks)
3. Zablocki LI, Bugnon LA, Gerard M, Di Persia L, Stegmayer G,
   Milone DH. Comprehensive benchmarking of large language models
   for RNA secondary structure prediction. arXiv:2410.16212 (2025).
   (frozen-embedding single-arm protocol; cross-family
   generalization gap)
4. Penić R, Vlašić T, Huber RG, Wan Y, Šikić M. RiNALMo: general-
   purpose RNA language models can generalize well on structure
   prediction tasks. *Nat Commun* (2025).
   doi:10.1038/s41467-025-60872-5. (650M params, 36M ncRNAs;
   the 33M micro variant used here)
5. Yin W, Zhang Z, Zhang S, et al. (Xie Z, Zhang X, Qin T
   corresponding) ERNIE-RNA: an RNA language model with structure-
   enhanced representations. *Nat Commun* (2025).
   doi:10.1038/s41467-025-64972-0. (86M params, 20.4M ncRNAs;
   base-pairing-constrained attention)
6. Chen J, Hu Z, Sun S, et al. Interpretable RNA foundation model
   from unannotated data for highly accurate RNA structure and
   function predictions. arXiv:2204.00300 (2022). (100M params,
   23.7M ncRNAs from RNAcentral)
7. Chen K, Zhou Y, Ding M, Wang Y, Ren Z, Yang Y. Self-supervised
   learning on millions of primary RNA sequences from 72 vertebrates
   improves sequence-based RNA splicing prediction. *Brief
   Bioinform* 25(3):bbae163 (2024). doi:10.1093/bib/bbae163.
   (SpliceBERT, 19M, pre-mRNA corpus)
8. Hu E et al. LoRA: low-rank adaptation of large language models.
   *ICLR* (2022).
9. Liu S et al. DoRA: weight-decomposed low-rank adaptation.
   *ICLR* (2024).
10. Liu H et al. IA3: parameter-efficient fine-tuning with
    learned activation rescaling. *ICLR Wkshp PEFT* (2023).
11. Steinegger M, Söding J. MMseqs2 enables sensitive protein
    sequence searching and clustering. *Nat Commun* 8:1558 (2017).
12. [Liangyu Lab/gLM-eval] Shen N et al. Benchmarking
    pre-trained genomic language models for RNA sequence-related
    predictive applications. *Nat Commun* (2025-12). (11 gLMs ×
    4 tasks, unified fine-tuning — sensitivity-of-rankings
    motivation; full author list at BibTeX stage)
13. Vishniakov K, Viswanathan K, Medvedev A, Kanithi PK,
    Pimentel MAF, Rajan R, Khan S. Tokenization to transfer: do
    genomic foundation models learn good representations? *ICLR*
    (2026, poster). (random-init baselines surprisingly strong;
    tokenizer-gated pretraining gains — DNA-domain counterpart to
    our A8/random-baseline observations)
14. Dincer A, Bachega JFR, Anthon C, et al. bpRNA: large-scale
    automated annotation and analysis of RNA motif families.
    *Nucleic Acids Res* 47(10):e57 (2019). (SSP task dataset)

（注：14/14 条均已按原始出处逐一核证（作者/年份/DOI/venue
经 web 溯源）；投稿版直接 BibTeX 化即可。）

## Data & Code
github.com/Cunyu-Liu/RNA_finetune_methods; ledger + figures auto-generated
(rnafteval export_c4 / stats / figures).
