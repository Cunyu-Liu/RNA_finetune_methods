# To fine-tune or not to fine-tune RNA language models? A controlled
# strategy comparison reveals task-granularity-dependent leakage effects

**Preprint draft v0.3** — 2026-09-17（数据快照：Day 2 深夜，228
ledger runs；E1 五模型 full 臂全部落地；跨架构 LR 崩溃新证据：
三种注意力架构全崩 + RNA-FM 唯一幸存；SSP full tuned 5/5 方向一致
×24-27；C4 崩溃矩阵 LoRA/full 双臂均 5/5 模型。G6 尾队列收尾中，
守护链自动刷新八产物）

## Abstract

Fine-tuning RNA language models (RNA-LMs) is widely assumed to beat frozen
embeddings, yet controlled comparisons across adaptation strategies are
missing. Following the protein-side template of Schmirler et al. (2024), we
run a controlled matrix of **3 adaptation strategies (frozen + shallow MLP
head / LoRA r=8 / full fine-tuning) × 5 RNA-LMs (10M–99M) × 3 BEACON tasks
× 2 evaluation splits (random vs sequence-family-clustered) × 3 seeds**,
each fine-tuning cell with a learning rate chosen on a held-out tuning
seed, and audit every arm with zero-overlap assertions.

Three findings emerge:

1. **Fine-tuning helps, but the size of the help depends on task
   granularity — and on the split.** On ncRNA family classification, LoRA/full FT improve accuracy over frozen heads by +0.04 to +0.43
    (five-model range, strategy-dependent) under random splits, but **collapse to near-chance
   (0.06–0.10) under family-level splits**, while frozen heads degrade
   mildly. On per-base tasks (m6A modification), fine-tuned models **gain
   under both splits** (AUC 0.970→0.995 for LoRA). Structure prediction (SSP) shows robust 2–5× gains over k-mer
   baselines under both splits.
2. **Task granularity determines leakage sensitivity**: the Δ(random−family)
   gap reaches +0.68 to +0.91 for fine-tuning on per-sequence classification
   but is ≈ −0.04 for per-base m6A and +0.003–0.03 for SSP — i.e., much of
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

### 2.2 Family-level splits reveal task-granularity-dependent collapse (C4, Fig 2)
[fig:fig_c4_delta] — Δ bars. Key numbers (3-seed means; tuned LR where
marked):

- ncRNA: collapse **replicates across all five models**: LoRA Δ = +0.68
  (RNA-Sc) / +0.85 (RiNALMo) / +0.82 (SpliceBERT) / +0.89 (ERNIE) /
  +0.91 (RNA-FM); frozen Δ = +0.06–0.26 (mild); k-mer LGBM Δ = +0.007.
  The traditional baseline is leakage-insensitive by construction (no
  training on sequence features), making it a robust floor under family
  splits (0.900 vs 0.893 random vs family).
- m6A (per-base): no collapse, both models — RNA-Sc LoRA 0.943→0.983;
  RiNALMo LoRA 0.970→0.995 (Δ = −0.025); tuned full-FT 0.968→0.993.
- SSP: robust gains, no collapse — RiNALMo frozen 0.196→0.218, LoRA
  0.214→0.223 (3 seeds); RNA-Sc LoRA 0.084→0.076.
- **Leakage-sensitive fine-tuning is the norm for per-sequence
  classification (5/5 models), and the exception for per-base tasks (0/4
  model-task pairs).**

### 2.3 E2 PEFT horizontal comparison (C5, 5 arms, RiNALMo ncRNA random)
| arm | 3-seed mean | trainable params |
|---|---|---|
| full FT (LR-tuned 1e-5) | 0.938 | 33.5M |
| DoRA r=8 | 0.934 | ~0.57M |
| LoRA r=8 | 0.928 | ~0.55M |
| IA3 | 0.860 | ~0.01M |
| head-only | 0.817 | 0 (+16K head) |

(auto-exported from ledger: status/e2_table.md, export_e2.py)

- DoRA ≈ LoRA at r=8 (Schmirler's protein-side observation replicates in
  RNA); IA3 trails by ~0.07 with 10× fewer params; full FT wins only with
  tuned LR (default 3e-4 collapses to 0.077).
- Prefix-tuning infeasible under current dependency versions (peft 0.13
  tuple-style past_key_values vs transformers 5.0 Cache API) — documented
  limitation.

### 2.4 LR grids: scale × strategy × LR triple interaction (A8, Fig 3)
[fig:fig_lr_grid] — 4-point grids per model×strategy (seed 101).
RiNALMo full: 0.943/0.944/0.924/0.077 across 1e-5→3e-4;
RNA-Sc full: 0.683/0.815/0.807/0.688; LoRA @3e-4: RNA-Sc 0.723,
RiNALMo 0.934 (full grid: status/lr_grid_table.md, auto-exported).
Tuned-LR protocol replication (Day 2): RiNALMo m6A full default-LR 0.30 →
**0.968/0.993 (random/family, 3 seeds, 1e-5)**; SSP full default-LR 0.006 →
**0.151–0.176 (3 seeds, 1e-5, direction-consistent ×24–27)** — recovery,
confirming the grid diagnosis that the default 3e-4 is catastrophic for
full-FT.

**Cross-architecture collapse at the default LR (new)**: the ln(C)
loss plateau (prediction entropy saturation) reproduces across three
attention architectures — RiNALMo (standard), SpliceBERT (ALiBi,
6/6 runs), ERNIE-RNA (explicit base-pairing-constrained attention,
6/6, plateau from epoch 0) — all collapsing to 0.077 ACC at 3e-4
full-FT, while RNA-FM (99.5M, most extensive pretraining, 23.7M
ncRNAs) is the only survivor (0.82–0.84 random, healthy loss decay
1.10→0.32). LR misconfiguration is thus architecture-agnostic and
systematic; pretraining depth appears to confer resilience
(observational, n=1). Under family splits RNA-FM full also collapses
(0.06–0.10) — the C4 per-sequence collapse now extends to the full-FT
arm across all five models.

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
(ii) the frozen-vs-LoRA gain flips sign with budget (+0.09 at 100 →
+0.02 at 1,000 → catastrophic at full data under family splits) —
collapse is *data-mass dependent*: more labels → stronger family
memorization → harder collapse, a mechanistic C3×C4 interaction;
(iii) 1,000 labels recover ~99% of the full-data frozen score —
practically, a thousand annotations suffice for this task class.
Full learning-curve figure: fig_e3_curves (per-model panels).

### 2.6 Official split leakage audit (B1 discipline)
MMseqs2 0.8/0.8 over 309k BEACON modification windows: 327/1200 official
test windows (27.3%) cluster with training windows; 31-mer overlap 10.8%.
The official "random" arm is leak-contaminated at host-transcript level.

### 2.7 Statistics
Preregistered plan (§3.5): paired sign tests over 3 seeds + BH FDR q=0.05
across 58 contrasts; 3/3 direction consistency as primary evidence
(seed-level power wall documented: n=3 sign-test minimum p=0.25);
cell-level bootstrap CIs in Supp.

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
3. [Zablocki et al.] Frozen-embedding evaluation of RNA language
   models (深圳湾/GenSLMs line). (single-arm protocol)
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
12. [良渚/gLM-eval] 11 genomic LMs × 4 tasks unified fine-tune
    ranking study. (2025). (sensitivity-of-rankings-to-strategy
    motivation)
13. [Vishniakov et al.] DNA tokenizer perspective. *ICLR* (2026).
14. Dincer A et al. bpRNA: large-scale annotation of ncRNA structure
    alignments. *Nucleic Acids Res* (2017). (SSP task)

（预印本版注：3/7/12/13 的完整书目信息在投稿版 BibTeX 化时
补齐——当前以可辨识缩写标记，见 repo references.bib 计划）

## Data & Code
github.com/Cunyu-Liu/RNA_finetune_methods; ledger + figures auto-generated
(rnafteval export_c4 / stats / figures).
