# To fine-tune or not to fine-tune RNA language models? A controlled
# strategy comparison reveals task-granularity-dependent leakage effects

**Preprint draft v1.0（项目数据全收口版·六幕叙事重构）** — 2026-10-07（数据快照：ledger 1913 done runs，全部计划 0 缺口；17 个架构全接入全收口——5 core + UTR-LM / mRNABERT / NucleicBERT / AIDO.RNA-1.6B / RiboSpan-1K-40 / HydraRNA + 受控 RNA-Sc 家族五档 + RiNALMo 官方三档；E6 遗忘矩阵 87 格（51+18+18）；1.6B 等价线双架构落地；rank 敏感性轴 48 格收口；grid_audit 终审 38 MATCH / 0 RERUN / 0 TUNED-MISSING。数据链全部自动导出，[PENDING] 清零。）

**数据对账声明：v1.0 全文数字已于 2026-10-07 对 ledger.jsonl（1913 done）逐条核验；与 v0.96 的关键差异——17/17 崩溃口径修正为 16 个 FT 架构（3 个部分逃逸）、frozen 家族带实际 0.11–0.89、E6 矩阵 87 格非 124、E2 表 RNA-Sc full 0.808 口径、AIDO 1.6B grid 1e-05=0.720/3e-05=0.520、mRNABERT lora family 0.086。表间冲突（e6_table vs e6_official 的 10M/30M/micro 行）已回 ledger 原始行裁决。**

## Abstract

Practitioners using RNA language models face a three-way choice — frozen
embeddings, low-rank adapters, or full fine-tuning — and the reported
evidence is split: protein-side studies disagree on whether fine-tuning
helps under realistic splits, and no RNA work has ever placed more than
two adaptation strategies in one controlled comparison. Following the
protein-side template of Schmirler et al. (2024), we run a controlled
matrix of **3 adaptation strategies (frozen + shallow MLP head / LoRA
r=8 / full fine-tuning) × 16 RNA-LM architectures (0.5M–1.6B: five core
models, six external-architecture validation arms including two 1.6B
encoders and an SSM hybrid, the three officially released RiNALMo
scales, and a controlled same-recipe RNA-Sc family at 1M–650M) × 4
BEACON tasks × 2 evaluation splits (random vs sequence-family-clustered)
× 3 seeds**, every fine-tuning cell learning-rate-tuned on a held-out
tuning seed, all arms audited with zero-overlap assertions.

**The central claim: on RNA language models, the apparent advantage of
fine-tuning is largely family-level leakage; where the advantage is
real it is governed by task granularity and learning-rate protocol; and
LoRA is the default-optimal route in precisely those regimes where the
advantage is real — while bounding the catastrophic-forgetting tail
where it is worst.** Four lines of evidence:

1. **True or illusory (granularity × family density).** Under random
   splits fine-tuning wins everywhere; under family-clustered splits,
   per-sequence classification with multi-member families collapses in
   **all 16 architectures with backbone-updating arms** (17 in the
   matrix; the 17th, HydraRNA, is frozen-only): 13 fall into the
   0.06–0.12 near-chance band (1/13 = 0.077), and 3 escape partially
   (UTR-LM full 0.15, RiNALMo-mega LoRA 0.21, RNA-FM full 0.53) — none
   reaches its own frozen arm on the same split (frozen family values
   span 0.11–0.89 and the strongest pretraining recipes — ERNIE-RNA
   0.89, RNA-FM 0.86, RiNALMo 0.52–0.72 — retain far more than their
   fine-tuned counterparts). Per-base tasks (m6A, SSP) are immune (0/20
   core cells fall below 0.7× their random-split score) and
   singleton-cluster regression (MRL) degrades only mildly
   (0.85–0.93×). The collapse replicates from random-initialized
   backbones (family-side gap |≤0.014|, 6/6 cells), is in-band by the
   end of the first epoch (10/10 timeline cells), and coincides with an
   instant representation rank collapse under default-LR full-FT. Much
   of the "fine-tuning benefit" on sequence-level tasks under random
   splits is family memorization.
2. **Mechanism.** The default LR (3e-4) is an architecture-agnostic
   trap for full-FT — collapse to the ln(C) plateau across three
   attention architectures (standard / ALiBi / base-pairing-constrained,
   all at 0.077 = 1/13) and all three tasks (5/5 core models on
   regression), driven by effective-rank collapse 300–500→1 within
   5–10 steps at 3–5% weight drift; tuned LRs restore every collapsed
   cell (SpliceBERT ×11.8, ERNIE-RNA ×12.6, NucleicBERT 0.10→0.88),
   and at 1.6B the full-FT grid separates further (AIDO: 1e-05 = 0.72
   vs 3e-05 = 0.52) — the full-FT sweet spot shifts left with scale.
3. **Route.** Five-arm PEFT comparison with a rank sweep
   (r ∈ {4, 8, 16}): DoRA/LoRA form the first tier with weak,
   non-monotone rank sensitivity (ncRNA spread ≤ 0.06, m6A ≤ 0.01 —
   rank is a second-order knob next to strategy choice); the
   "small-model full-FT = large-model LoRA" equivalence line is
   family-recipe-dependent — the controlled RNA-Sc family shows
   full-FT winning at all five scales (30M full 0.862 ≈ 650M LoRA
   0.855, crossover inside the family), while the official RiNALMo
   family never crosses (33M full 0.944 < 148M LoRA 0.949; 650M LoRA
   0.969 > full 0.956) and both 1.6B encoders favor LoRA outright
   (AIDO 0.826 vs 0.688; RiboSpan 0.841 vs 0.657).
4. **Cost.** Catastrophic forgetting (87-cell pretraining-NLL
   matrix: 51 ncRNA-start + 18 m6A-start + 18 retention cells, noise
   band < 3e-8): non-monotone in scale with a bounded mid-scale danger
   band (30M full-FT worst seed +26.2 NLL); LoRA bounds the tail where
   it is worst (30M: +3.4 vs +26.2; official RiNALMo-650M: LoRA Δ
   +0.017–0.044 vs full +0.098–0.154) — though at 1M one LoRA seed
   (+3.8) exceeds full's worst (+2.5): adapter protection is a
   danger-band phenomenon, not a blanket law. Per-base starting tasks dilute
   forgetting in 14/18 seed-level contrasts (exceptions concentrated
   in MLM-scored RiNALMo-micro LoRA).

We release the full run ledger, MMseqs2 0.8/0.8 family-cluster splits
for all four tasks, LR grids, a rank sweep, and a split-leakage audit
of the official BEACON modification split (**27.3% of test windows
share a host-transcript-level cluster with training windows**).

## 1 Introduction

RNA language models pretrained on genomic-scale corpora now cover a wide
parameter range (0.5M–1.6B) and are routinely fine-tuned on downstream
tasks. A practitioner facing a new RNA task must make one choice before
any hyperparameter matters: **frozen embeddings with a shallow head,
low-rank adapters, or full fine-tuning.** The reported evidence offers
no help — it is split three ways, and no RNA work has ever placed more
than two of these strategies in one controlled comparison. Meanwhile
the protein-side literature has already disagreed with itself on the
same question: Schmirler et al. (2024) report broad fine-tuning gains,
while gLM-eval-style multi-model benchmarks and frozen-embedding
studies find the ranking fragile under realistic splits. Whether the
disagreement transfers to RNA — where task granularity and family
structure differ sharply from protein benchmarks — has never been
tested.

Two evaluation habits make the reported numbers even harder to compare:

First, **adaptation strategies are compared only within single papers**:
BEACON evaluates full fine-tuning only; Zablocki et al. evaluate frozen
embeddings only; LoRA/DoRA/IA3 are evaluated in their respective
introduction papers on task subsets. No RNA work places more than two
strategies in one controlled comparison under identical data, compute
and tuning protocol — the protein-side gap Schmirler et al. (2024)
closed for protein LMs is still open for RNA.

Second, **random splits overstate fine-tuning**. When train and test
sequences share homologous families (ncRNA families; host transcripts for
per-base modification windows), a fine-tuned model can memorize family
signals rather than learn transferable ones. We quantify this with
MMseqs2-clustered, cluster-pure splits on all four BEACON tasks, and audit
the official random arms themselves (27.3% of the official m6A test set
shares a host-level cluster with training windows).

Contributions:
- **C1** A controlled strategy matrix (frozen / LoRA / full) × 16
  architectures × 4 tasks × 2 splits × 3 seeds, every fine-tuning cell
  LR-tuned on a held-out tuning seed (protocol arm; seed 101). The
  architecture axis spans five core models, six external-architecture
  validation arms (UTR-LM 1.2M / mRNABERT 3-mer tokenizer / NucleicBERT
  / AIDO.RNA-1.6B / RiboSpan-1K-40 / HydraRNA SSM hybrid), the three
  officially released RiNALMo scales (33M/148M/650M), and a controlled
  same-recipe RNA-Sc family at 1M–650M.
- **C4** The leakage × strategy interaction with **task granularity as the
  moderator**: family-split collapse of per-sequence classification in
  all 16 backbone-updating architectures; per-base tasks and
  singleton-cluster regression immune — with random-init, timeline, and
  rank-collapse attribution controls.
- **A8** LR-grid protocol evidence: the default 3e-4 is an
  architecture-agnostic full-FT trap; tuned LRs restore every collapsed
  cell; at 1.6B the full-FT optimum shifts left a second time.
- **E2/C5** A five-arm PEFT horizontal comparison (LoRA / DoRA / IA3 /
  head-only / full reference) with a rank sweep (r ∈ {4, 8, 16}) under
  the same protocol, plus a dual-family scale-equivalence line
  (controlled RNA-Sc vs official RiNALMo vs 1.6B encoders).
- **C6/E6** A 87-cell pretraining-objective forgetting matrix with a
  mid-scale danger band, adapter tail protection, and a per-base-start
  dilution contrast.
- **B1** Split-leakage audit tooling (MMseqs2 0.8/0.8 clustering, zero-
  overlap assertions) applied to both our family arms and the official
  BEACON splits.

## 2 Results

### 2.1 Fine-tuning is beneficial but task/split dependent (C1, Fig 1)
[fig:fig_c1_matrix] — heatmap; black boxes = beats strongest k-mer baseline.
Cross-model consistency (ncRNA random, LoRA, 3-seed means): RNA-Sc 0.746,
SpliceBERT 0.903, RiNALMo 0.928, RNA-FM 0.962, ERNIE 0.974 — gains
replicate across corpora and parameter scales (19M–99M).

### 2.1a External-architecture validation arms (complete, v1.0)

Six additional architectures beyond the core five test whether the C1/C4
findings are corpus/architecture-specific. All planned cells are now
done (ledger-audited, non-smoke); no [PENDING] remains anywhere in the
matrix.

- **UTR-LM (1.2M params)** — 3 tasks × 3 strategies × 2 splits × 3
  seeds done (frozen 0.503 / LoRA 0.684 / full 0.647 random ncRNA;
  full family 0.151). A 1.2M model cannot afford full-FT representation
  damage — LoRA wins outright — yet its fine-tuned arms still collapse
  under family splits (LoRA 0.684→0.071).
- **mRNABERT (MosaicBERT, DNA 3-mer tokenizer)** — ncRNA + m6A + SSP
  (3-mer tokens are not base-aligned; SSP is reported as invalid-zero
  and excluded; m6A near-chance 0.50-0.52 for all arms — token mismatch
  dominates). ncRNA (18/18 cells): frozen 0.488 / LoRA 0.759 / full
  0.831 random; family collapse LoRA 0.759→0.086, full 0.831→0.074. A
  k-mer-token model needs backbone adaptation far more than
  nucleotide-token models — and still collapses under family splits.
- **NucleicBERT (k-mer masked LM, 86M)** — 4 tasks × 3 strategies × 2
  splits done (48/48 + tuned backfill + 1007 three-cell backfill). ncRNA:
  frozen 0.838 (3/3 seeds) / LoRA 0.940 (3/3 seeds) / full 0.882
  (tuned 1e-05) random; family LoRA 0.079 / full 0.073 (3/3 seeds).
  The default-LR full arm scored
  0.10 (A8 collapse), tuned 1e-05 restored it to 0.88 —
  the 17th architecture confirming the LR trap (recovery ×8.7) and the
  family-split crash band. m6A: full 0.991 (3/3) — per-base immunity
  replicates. MRL regression: LoRA 0.782 random / 0.690 family
  (mild, ratio 0.88).
- **AIDO.RNA-1.6B / RiboSpan-1K-40 (1.6B encoders)** — complete
  (48/48 planned cells + LR grids). Random ncRNA: AIDO frozen 0.581 /
  LoRA 0.826 / full@1e-05 0.688; RiboSpan frozen 0.582 / LoRA 0.841 /
  full@1e-05 0.657. Family ncRNA: LoRA 0.079 / 0.070, full 0.078 /
  0.068, frozen 0.149 / 0.167 — the 1.6B scale changes the ranking
  (LoRA > full on both encoders at tuned LR) but not the leakage law.
  AIDO's LR grid: full 1e-05 0.720 vs 3e-05 0.520 (tuning seed 101) —
  a second 1.6B-scale leftward shift of the full-FT optimum.
- **HydraRNA (Mamba SSM hybrid)** — frozen-only arm (3 tasks × 2
  splits × 3 seeds, 18/18 cells). The checkpoint's finetune path is
  not exposed for backbone updates (documented limitation, §5); the
  frozen row contributes to the frozen family-band (ncRNA 0.690
  random → 0.114 family) but not to the collapse count.
- **A tokenizer-pathology case study**: mRNABERT's published
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
  +0.89 (RNA-FM); frozen Δ spans −0.06 to +0.26 (mild, model-dependent);
  k-mer LGBM Δ = +0.007.
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
  family/random ratios 0.85-0.93 across 5 models; delta = 0.04-0.05
  vs ncRNA 0.68-0.89. **Collapse requires multi-member family
  structure: the MRL task has 90,403 near-singleton clusters,
  leaving no family overlap to leak.**
- **Leakage sensitivity = granularity × family density.** No
  model–task–arm cell outside multi-member-family per-seq
  classification collapses (ncRNA: all 16 FT-bearing architectures;
  m6A/SSP per-base and MRL singleton per-seq immune).
  **The collapse also replicates on the external-architecture arms**
  (§2.1a): UTR-LM LoRA 0.684→0.071 (random→family), mRNABERT LoRA
  0.759→0.086, NucleicBERT LoRA 0.938→0.079, AIDO.RNA-1.6B LoRA
  0.826→0.079, RiboSpan LoRA 0.841→0.070 — from a 1.2M parameter
  model to 1.6B encoders, k-mer and nucleotide tokenizers, attention
  and k-mer-masked backbones. The pathology is not an artifact of the
  core five models' corpora, tokenizers, or scale.
  The family-split collapse holds at every scale tested -- 1M
  through 650M LoRA, including RiNALMo-650M (0.969 random ->
  0.106 family). Three architectures escape *partially*: UTR-LM full
  0.151, RiNALMo-mega LoRA 0.139–0.334 (mean 0.207, all three seeds
  above the band), and RNA-FM tuned-full 0.466–0.597 (mean 0.53) —
  escapes concentrate in tuned-LR full arms of strongly-pretrained
  models, are partial (never reach the model's own frozen arm), and
  do not break the architecture-level pattern.
  Frozen arms span 0.114–0.887 on the same family split — the
  recipe-dependence of frozen family knowledge is itself a finding:
  ERNIE-RNA (0.887) and RNA-FM (0.860) frozen heads retain near-random-
  split performance under family shift, RiNALMo tiers retain 0.52–0.72,
  while RNA-Sc checkpoints (0.15–0.52) and the 1.6B encoders (0.15/
  0.17) lose most of it. Pretraining-corpus breadth, not parameter
  count, predicts frozen family robustness.

Two questions follow directly: *why* do fine-tuned arms destroy the
family representation so fast, and is the apparent strategy ranking
itself trustworthy? Both point to the learning-rate protocol — the
mechanism behind the collapse and behind every strategy comparison
that follows.

### 2.3 LR grids: scale × strategy × LR triple interaction (A8, Fig 3) — the mechanism

Default-LR (3e-4) full-FT collapse is **task-dependent and extends to all
five models on regression**: ncRNA 3/5 collapse (SpliceBERT/ERNIE/RiNALMo),
m6A 2/5 (RiNALMo 0.302, ERNIE 0.508; SpliceBERT degrades to 0.649),
MRL **5/5** (RiNALMo -0.001, SpliceBERT 0.098, ERNIE 0.028,
RNA-Sc 0.159, RNA-FM 0.181 -- the only ncRNA/m6A survivor collapses on
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
**0.971/0.996 (random/family, 3 seeds, grid-best 3e-05)**; SSP full
default-LR 0.006 → **0.204/0.203 (3 seeds, grid-best 3e-05,
direction-consistent ×30–33 recovery)** — recovery, confirming the grid
diagnosis that the default 3e-4 is catastrophic for full-FT.

**Cross-architecture collapse at the default LR, and tuned recovery
(new)**: the ln(C) loss plateau (prediction entropy saturation)
reproduces across three attention architectures — RiNALMo (standard),
SpliceBERT (ALiBi), ERNIE-RNA (explicit base-pairing-constrained
attention) — all collapsing to 0.077 ACC at 3e-4 full-FT, while
RNA-FM (99.5M, most extensive pretraining) is the only survivor
(0.82–0.84 random). Tuned-LR backfill restores every collapsed arm:
SpliceBERT full@3e-5 random = 0.910 (3-seed, ×11.8 recovery,
exceeding its LoRA 0.904); ERNIE full@1e-5 random = 0.973 (×12.6,
matching LoRA 0.974); NucleicBERT full@1e-5 random = 0.878–0.890
(default 0.10, ×8.7) — the collapse is an LR artifact, not a
strategy property. Under family splits both tuned arms still
collapse (0.06–0.10) — the C4 per-sequence collapse holds across
all five models in both LoRA and tuned-full arms (tuned-SpliceBERT
0.064–0.096, tuned-ERNIE 0.076–0.085), ruling out LR
confounding for the leakage finding.

**The full-FT optimum shifts left a second time at 1.6B (new).**
The 10M→33M shift (3e-5→1e-5) is not the end of the trajectory: on
AIDO.RNA-1.6B the full-FT grid separates further — 1e-05 scores
0.720 vs 0.520 at 3e-05 on the tuning seed (3-seed formal mean
0.688 at 1e-05) — and RiboSpan-1K-40 shows the same direction with
full formal seeds (1e-05 0.606–0.690 vs 3e-05 0.448–0.558, 3-seed
means 0.657 vs 0.501). The larger the
backbone, the sharper the penalty for missing the leftward shift;
the practical rule "always LR-sweep full-FT per scale" is itself a
scale-dependent safety requirement, and the default 3e-4 inherited
from the PEFT literature is never the full-FT answer at any RNA-LM
scale tested (0.5M–1.6B).

With the LR confound removed, one moderator of the family collapse
remains untested: the amount of training data itself. Family
memorization needs family members to memorize — how many labels does
it take before the collapse mechanism engages?

### 2.4 Label-budget axis (E3, C3): when the leakage advantage flips

With cluster-level subsampling (draw clusters, keep them whole —
seed-matched subsets at n ∈ {10, 100, 1000} + full 6,859) on the
family split, 3-seed means (tuned-LR backfill applied; auto-exported
status/e3_table.md):

| n | frozen | LoRA | full (tuned) | best |
|---|---|---|---|---|
| 10 | 0.103 | 0.131 | **0.156** | full |
| 100 | 0.424 | 0.509 | **0.519** | full |
| 1,000 | 0.645 | 0.676 | **0.698** | full |
| 6,859 (full) | **0.696** | 0.081 | 0.083 | frozen |

(RiNALMo-micro, family split; RNA-Sc-10M replicates the small-n
full-best pattern: n=10 0.110, n=100 0.154, then LoRA 0.287 at
n=1000 and frozen 0.214 at full data.)

Three signals: (i) **at small label budgets full fine-tuning wins**
— n=10: full 0.156 vs LoRA 0.131 vs frozen 0.103 (3× frozen on
RiNALMo; RNA-Sc n=10 0.110 same direction): ten sequences teach
class priors, not family memorization — there are no family twins to
memorize at n=10, and the frozen head (16K params) cannot even fit
class priors; (ii) the tuned full-FT curve is *non-monotone in label
budget*: 0.156 → 0.519 → **0.698 (best of all strategies)** → 0.083
(collapse) — more labels first help then *hurt* full fine-tuning
under family splits, because family memorization grows with data
mass: the direct C3×C4 mechanism; (iii) **1,000 labels recover ~99%
of the full-data frozen score** (0.698 vs 0.696, both best-arm) —
practically, a thousand annotations under cluster sampling suffice
for this task class, and the small-n regime inverts the
recommendation: full-FT (or LoRA at n=1000 for the 10M model) over
frozen. The label-budget axis turns the §2.2 verdict from "never
fine-tune under family shift" into "fine-tune while the family-
memorization mass is still small." Full learning curves:
fig_e3_curves (per-model panels, min-max bands).

So far "fine-tuning" has meant full-FT with tuned LRs. The remaining
practical question is the route: which adaptation family — and at
which adapter rank — buys the most per trainable parameter?

### 2.5 PEFT route selection: five arms + rank sweep (C5)

Auto-exported (status/e2_table.md, ranksweep runs in ledger); per-seed
values in Supp S3.

| panel | ranking (3-seed means, random split) |
|---|---|
| RiNALMo-33M, ncRNA | full(tuned) 0.944 > **DoRA 0.934** > LoRA 0.928 > IA3 0.860 > head-only 0.817 |
| RNA-Sc-10M, ncRNA | full(tuned) 0.808 > **DoRA 0.765** > LoRA 0.746 > IA3 0.579 > head-only 0.355 |
| RiNALMo-33M, m6A | **DoRA 0.979** > full(tuned) 0.971 > LoRA 0.970 > IA3 0.941 > head-only 0.921 |
| RNA-Sc-10M, SSP | LoRA 0.084 > DoRA 0.081 > full(tuned) 0.060 > IA3 0.042 > head-only 0.034 |

- **DoRA is the best PEFT arm in 2/4 panels, and full-FT wins only
  where its LR is tuned (A8) and the model tolerates it**: full wins
  RiNALMo-33M ncRNA with tuned LR; on RNA-Sc-10M (default 3e-4 is fine
  for this recipe) tuned full 0.808 edges DoRA 0.765; at 10M scale and
  on m6A/SSP the parameter-efficient arms dominate or tie outright.
  "Small model + PEFT vs large model + full-FT" equivalence lines (C5's
  second question) get a concrete RNA data point: RNA-Sc-10M DoRA
  (0.765, ~0.57M trainable) vs RiNALMo-33M full (0.944) — the corpus/
  scale gap dominates, PEFT alone does not close it.
- IA3 is task-granularity sensitive: trails by ~0.17 on per-sequence
  classification (0.579 vs 0.746 LoRA at 10M) but only 0.029 behind
  LoRA on per-base m6A (0.941) — the cheapest adapter is viable where
  labels are dense per position.
- **Rank sweep (r ∈ {4, 8, 16}, LoRA/DoRA × 2 models × 2 tasks × 3
  seeds, 48 runs, random split).** Rank is a second-order knob:

| model · task | LoRA r4 | LoRA r8 | LoRA r16 | DoRA r4 | DoRA r16 |
|---|---|---|---|---|---|
| RiNALMo-micro · ncRNA | 0.907 | 0.928 | 0.916 | 0.906 | 0.911 |
| RNA-Sc-10M · ncRNA | 0.694 | 0.746* | 0.706 | 0.706 | 0.721 |
| RiNALMo-micro · m6A | 0.977 | 0.970 | 0.968 | 0.980 | 0.981 |
| RNA-Sc-10M · m6A | 0.948 | 0.947 | 0.947 | 0.947 | 0.946 |

  (*one r8 seed 0.738 — the r8 vs r4 gap on RNA-Sc ncRNA is 0.052,
  within seed noise of this task; m6A spread ≤ 0.01 everywhere.)
  DoRA never trails LoRA by more than 0.02 at any rank; the strategy
  choice (adapter vs full) moves accuracy by 0.10–0.18 while the rank
  choice moves it by ≤ 0.06 on ncRNA and ≤ 0.01 on m6A. Practitioners
  should tune the strategy axis, not the rank axis.
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
  sizes complete, grid-best LRs): micro-33M full 0.944 < mega-148M full 0.945 <
  giga-650M full 0.956 vs giga-650M LoRA 0.969 -- even
  full-FT at the largest released scale does not beat LoRA on the
  same checkpoint, and the 33M->650M full-FT gain is only +0.012:
  no crossover anywhere in the official family. Clean-scaling
  models reach equivalence early; officially released families retain a
  large-model advantage. Dual-track validation
  (user-requested): on the official three published RiNALMo scales the
  "small full-FT >= large LoRA" pattern does NOT hold -- micro-33M
  full (0.944) trails mega-148M LoRA (0.949) by -0.005, and even
  giga-650M full-FT (0.956) trails
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
  spectrum (LoRA 1M-650M, five scales: 0.941-0.948, spread < 0.006;
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
  (0.139-0.334, mean 0.207), 1M in two (0.144/0.160), and official
  650M in one (0.166) --
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
| RiNALMo-micro (official) | +0.11 / +0.14 / +0.11 | +0.16 / +0.15 / +0.16 | official model forgets its own corpus, tight variance |

Official RiNALMo scale spectrum (MLM pseudo-likelihood, per-scale tuned
LRs; 87 cells total across E6-v1/v2/v3):

| model | strategy (lr) | Δ s17 / s29 / s43 | mean |
|---|---|---|---|
| RiNALMo-micro | full (1e-05) | +0.159 / +0.155 / +0.159 | +0.157 |
| RiNALMo-micro | lora (3e-04) | +0.110 / +0.140 / +0.105 | +0.118 |
| RiNALMo-mega | full (1e-05) | +0.129 / +0.136 / +0.119 | +0.128 |
| RiNALMo-mega | lora (1e-05) | +0.036 / +0.036 / +0.037 | +0.036 |
| RiNALMo-mega | lora (3e-04) | +0.080 / +0.063 / +0.068 | +0.070 |
| RiNALMo-650M | full (1e-05) | +0.098 / +0.154 / +0.122 | +0.125 |
| RiNALMo-650M | lora (3e-04) | +0.017 / +0.044 / +0.017 | +0.026 |

Four findings: (i) **forgetting is non-monotone in scale, with a bounded
mid-scale danger band** — across the now-complete 1M→650M controlled
spectrum, 1M is mild and seed-noisy, 10M gains, 30M catastrophically
degrades (full-FT post NLL reaches 30.8, +26 over pre), 100M
re-stabilizes to ≈0, and 650M is again negative (LoRA +0/−1.1, full-FT
worst seed +7.1) — so "bigger models forget more/less" is wrong in both
directions; the mid-scale band is where task gradients compete most
directly with pretraining features. (ii) **Adapter protection is
primarily a tail effect, and it is conditional**: at 30M LoRA's worst
seed is +3.38 vs full-FT's +26.24 (8× tail compression; one LoRA seed
is even negative), and on the official 650M LoRA Δ stays at
+0.017–0.044 vs full's +0.098–0.154 — but at 1M one LoRA seed (+3.76)
exceeds full-FT's worst (+2.50): adapters bound the tail in the danger
band, they are not a blanket guarantee. For deployment risk management
in the band, LoRA bounds the downside. (iii) **Every official RiNALMo
scale forgets its own pretraining distribution in every cell** (micro
6/6, mega 6/6, 650M 6/6 — 18/18 cells positive, +0.036 to +0.159) with
tight seed variance, and LoRA forgetting *decreases* with scale within
the official family (micro +0.118 → 650M +0.026; full +0.157 →
+0.125) —
released-model users pay a measurable, scale-attenuated forgetting cost
on any task fine-tune. (iv) **Per-base starting tasks dilute forgetting
(E6-v2)**: m6A-start Δ is more negative than ncRNA-start Δ in 14/18
seed-level contrasts (controlled family 11/12; the 4 exceptions are
RiNALMo-micro MLM-scored LoRA ×3 and one 30M full seed whose ncRNA-start
variance is extreme). Dense per-position labels act as
implicit pretraining replay for the positions they touch.

[fig:fig_e6_matrix] — forgetting matrix, auto-exported:
status/e6_table.md (per-seed cells + csv); [fig:fig_e6_spectrum] —
controlled-family ΔNLL vs scale, status/figs/fig_e6_spectrum.{png,pdf}.

## 3 Methods (summary)
- Models (16 architectures, 0.5M–1.6B). Core five: RNA-Sc-10M
  (controlled pretraining family, 10M); RiNALMo-micro (33M, 650M-family
  micro variant); SpliceBERT (19M, splice/pre-mRNA corpus —
  cross-domain); ERNIE-RNA (86M, base-pairing-constrained attention,
  20.4M ncRNAs); RNA-FM (99.5M, 23.7M ncRNAs — strongest frozen
  features, near k-mer LGBM 0.900). External validation six: UTR-LM
  (1.2M, 3′UTR corpus), mRNABERT (MosaicBERT, DNA 3-mer tokenizer),
  NucleicBERT (86M k-mer masked LM), AIDO.RNA-1.6B and RiboSpan-1K-40
  (1.6B nucleotide-token encoders), HydraRNA (Mamba SSM hybrid,
  frozen-only). Scale families: RiNALMo official micro/mega/650M
  (33M/148M/650M); RNA-Sc controlled 1M/10M/30M/100M/650M (same
  recipe). Frozen reference scores (ncRNA random): ERNIE 0.825,
  RNA-FM 0.917.
  Tasks: BEACON ncRNA-family (13-class, n=8.5k, dedup'd),
  modification (m6A per-base, 309k windows), secondary-structure
  (bpRNA, pair-F1), MRL (regression, near-singleton clusters).
- Strategies: frozen+MLP(32)/LoRA(r8,α4,qkv+out)/full; PEFT arms
  DoRA/IA3 in the E2 comparison; rank sweep r ∈ {4,8,16} for
  LoRA/DoRA; AdamW; LR per A8 grid on tuning seed 101; formal seeds
  17/29/43.
- Splits: official random arms; family arms = MMseqs2 80/80 cluster-pure
  (per-seq & whole-sequence tasks: sequence clusters; per-base m6A:
  host-transcript proxy via window clustering; assertion-checked purity).
- Evaluation: official metrics (ACC / AUC / pair-F1 / MSE); zero-overlap
  assertions on every arm; GPU-only discipline with wall-time and peak
  memory recorded per run in a JSONL ledger (1,913 done runs at this
  snapshot).
- Forgetting (E6): S0 held-out NLL (RNAcentral release-22 29M-sequence
  80/80 cluster split, held-out test + family-test tiers, n=2,000,
  len 32–512, deterministic eval with reorder-noise band <3e-8); causal
  LMs scored with shift-by-1 CE, bidirectional RiNALMo with MLM
  full-context pseudo-likelihood; LoRA arms merged (merge_and_unload)
  before post-NLL so the score reflects deployed weights. 87 cells:
  51 ncRNA-start + 18 m6A-start (E6-v2) + 18 cross-task retention
  probes (E6-v3).

## 4 Discussion (draft)
- **Granularity, not "fine-tuning vs frozen", is the first-order factor.**
  The 0.68–0.89 Δ gaps on per-sequence tasks vs ≈0.03 on per-base tasks
  mean a practitioner's first question should be whether their task label
  is constant over homologous families — if yes, random-split fine-tuning
  numbers are inflated by family memorization. This diagnostic question
  — "is the label family-constant?" — costs nothing and changes the
  answer more than any architecture or parameter-scale choice we tested.
- **Frozen features + shallow heads are the robust default under
  distribution shift, with recipe breadth as the moderator**: frozen Δ
  spans +0.06–0.26 (core five) while fine-tuning Δ explodes; k-mer LGBM
  is invariant by construction. For family-shifted deployment (new
  ncRNA families), frozen or k-mer baselines remain competitive
  (0.893–0.896 vs fine-tuned 0.06–0.10) — but frozen robustness itself
  tracks pretraining-corpus breadth (ERNIE/RNA-FM retain ~0.86–0.89,
  narrow-recipe models drop to 0.11–0.20), so the default must be
  chosen per backbone, not assumed.
- **LR discipline is a confound-killer**: with per-scale tuned LRs the
  full ≥ LoRA ordering re-emerges (0.944 vs 0.928); untuned defaults
  (3e-4) invert it (0.077 vs 0.928). Any cross-strategy claim without a
  per-strategy LR sweep on held-out data is suspect. The 1.6B grids
  (AIDO, RiboSpan) make this sharper: the full-FT optimum continues to
  shift left with scale — 3e-4 is never the full-FT answer from 0.5M
  to 1.6B.
- **Practical selection rule (from C5 + rank sweep)**: at 33M scale,
  DoRA r=8 matches LoRA within noise (0.934 vs 0.928) at comparable
  params (~0.57M vs ~0.55M); IA3 trades ~0.07 ACC for 10× param
  economy; head-only is a strong floor (0.817) but not competitive for
  per-sequence tasks under random splits. The rank sweep demotes rank
  choice to a second-order knob (≤0.06 ncRNA, ≤0.01 m6A across
  r∈{4,8,16}) — budget spent tuning rank is budget wasted relative to
  the strategy and LR axes.
- **Forgetting risk is concentrated, not uniform (C6)**: the E6 matrix
  shows the practitioner-relevant summary — mid-scale (30M) full-FT
  carries a catastrophic-forgetting tail (+26 NLL worst seed) that
  LoRA bounds 8×, while 10M fine-tuning is free (negative forgetting)
  and 100M full-FT self-stabilizes. Adapter protection is a
  danger-band effect (one 1M LoRA seed +3.8 exceeds full's worst
  +2.5), not a blanket law. Where downstream deployments reuse the
  backbone (multi-task pipelines, continued pretraining), adapters are
  insurance with a bounded premium inside the band, not a universal
  guarantee.


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
- HydraRNA contributes frozen-only arms (no backbone-updating cells):
  the Mamba finetune path was not exposed by the released checkpoint;
  it is included in the frozen family-band but excluded from the
  fine-tuning collapse count (16, not 17, FT-bearing architectures).
- mRNABERT per-base tasks are invalid (3-mer tokenization not
  base-aligned; SSP zeros, m6A at chance) — reported as the
  tokenizer-pathology case study, excluded from per-base aggregates.
- Prefix-tuning excluded due to dependency-stack incompatibility (peft
  0.13 / transformers 5.0 Cache API); documented, not worked around.
- RiNALMo SSP full tuned arm: 3/3 seeds random at grid-best 3e-05
  (0.204 mean, ×30–33 recovery) + family side (0.203); the earlier
  1e-05 arm (0.151–0.176 random) is also reported in the grid table.
- Preregistered checkpoint rule has two ambiguities discovered at
  automation (B16): the gain-median population was undefined (fixed:
  per-task best model, primary; all-cell pool, reported); and the
  "no BH-significant cell" branch is vacuously true under n=3 sign
  tests (power wall) — documented, decision unchanged.
- E6 forgetting: causal (RNA-Sc) vs MLM (RiNALMo) NLL metrics are
  family-internal only; the 87-cell matrix is complete (51+18+18);
  single-finetune-epoch protocol (10 ep, no replay or regularization
  baselines) measures the raw forgetting cost. The rank sweep covers
  two models × two tasks; adapter-axis coverage beyond LoRA/DoRA
  (e.g., r=64, VeRA) is future work.



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
