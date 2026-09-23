"""C5b 等价线图：双家族 full-FT vs LoRA（random 切分 acc）+ family 侧崩溃注记。

用法: python -m rnafteval.fig_c5b
产物: status/figs/fig_c5b.png

v2 (2026-09-23): 谱线扩展到双系 8 尺度（受控 1M/10M/30M/100M/650M + 官方 33/148/650M）；
full-FT 曲线统一取「tuned LR」口径（官方系 _lr1e-05、受控系 _lr3e-05 的 3 种子均值），
无 tuning 行的模型回退到 default-LR 3 种子均值（并注 * 标记）。
"""
from __future__ import annotations

import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = "/mnt/cunyuliu/rna-ft-eval"
OUT = os.path.join(ROOT, "status", "figs")

FAMILY = {
    "RiNALMo (official)": {
        "full": [("RiNALMo-micro", 33), ("RiNALMo-mega", 148), ("RiNALMo-650M", 650)],
        "lora": [("RiNALMo-micro", 33), ("RiNALMo-mega", 148), ("RiNALMo-650M", 650)],
    },
    "RNA-Sc (controlled)": {
        "full": [("RNA-Sc-1M", 1), ("RNA-Sc-10M", 10), ("RNA-Sc-30M", 30),
                 ("RNA-Sc-100M", 100), ("RNA-Sc-650M", 650)],
        "lora": [("RNA-Sc-1M", 1), ("RNA-Sc-10M", 10), ("RNA-Sc-30M", 30),
                 ("RNA-Sc-100M", 100), ("RNA-Sc-650M", 650)],
    },
}

TUNED_LR = {
    "RiNALMo-micro": "1e-05", "RiNALMo-mega": "1e-05", "RiNALMo-650M": "1e-05",
    "RNA-Sc-1M": "3e-05", "RNA-Sc-10M": "3e-05", "RNA-Sc-30M": "3e-05",
    "RNA-Sc-100M": "3e-05", "RNA-Sc-650M": "3e-05",
}


def collect():
    """ledger -> {(model, strategy): (mean, n, is_tuned)} for random split, seeds 17/29/43.

    去重：同一 run_id 的多行 done（历史双写事故）只取最后一条。
    """
    latest = {}
    with open(os.path.join(ROOT, "ledger.jsonl")) as f:
        for line in f:
            r = json.loads(line)
            if (r.get("task") != "noncoding-rna-family" or r.get("status") != "done"
                    or r.get("split") != "random" or r.get("seed") not in (17, 29, 43)):
                continue
            rid = r.get("run_id", "")
            if "_smoke" in rid or r.get("value") is None:
                continue
            latest[rid] = r
    tuned, plain = {}, {}
    for r in latest.values():
        key = (r.get("model"), r.get("strategy"))
        v = r["value"]
        rid = r.get("run_id", "")
        if "_lr" in rid:
            lr_tag = rid.split("_lr")[-1]
            if lr_tag == TUNED_LR.get(r.get("model")):
                tuned.setdefault(key, []).append(v)
        else:
            plain.setdefault(key, []).append(v)
    out = {}
    for key in set(list(tuned.keys()) + list(plain.keys())):
        if key in tuned:
            vs = tuned[key]
            out[key] = (sum(vs) / len(vs), len(vs), True)
        elif key in plain:
            vs = plain[key]
            out[key] = (sum(vs) / len(vs), len(vs), False)
    return out


def main():
    vals = collect()
    os.makedirs(OUT, exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), sharey=True)
    for ax, (fam, arms) in zip(axes, FAMILY.items()):
        for arm, style in (("full", "o-"), ("lora", "s--")):
            pts, labels = [], []
            for m, scale in arms[arm]:
                d = vals.get((m, arm))
                if d is None:
                    continue
                mean, n, is_tuned = d
                pts.append((scale, mean))
                star = "" if is_tuned or arm != "full" else "*"
                labels.append("%s\n%.3f (n=%d)%s" % (scale, mean, n, star))
            if len(pts) >= 2:
                xs, ys = zip(*pts)
                ax.plot(xs, ys, style, label={"full": "full FT (tuned)",
                                              "lora": "LoRA (r=8)"}[arm])
                for (x, y), lab in zip(pts, labels):
                    ax.annotate(lab, (x, y), textcoords="offset points",
                                xytext=(0, 6 if arm == "full" else -16),
                                ha="center", fontsize=7)
        ax.set_xscale("log")
        ax.set_xlabel("params (M, log)")
        ax.set_title(fam, fontsize=11)
        ax.grid(alpha=0.3)
        ax.legend(fontsize=9, loc="lower right")
    axes[0].set_ylabel("ncRNA accuracy (random split)")
    axes[0].set_ylim(0.55, 1.02)
    fig.suptitle("C5b: small full-FT vs large LoRA — equivalence is family-dependent",
                 fontsize=12)
    fig.text(0.5, 0.01,
             "family splits: 8 scales in 0.06-0.12 band on average (controlled 1M-650M + official 33/148/650M); "
             "148M LoRA escapes (0.14-0.33) — largely scale-invariant; * = default-LR arm",
             ha="center", fontsize=9, style="italic")
    fig.tight_layout(rect=(0, 0.05, 1, 0.94))
    out = os.path.join(OUT, "fig_c5b.png")
    fig.savefig(out, dpi=200)
    print("saved", out)
    for fam, arms in FAMILY.items():
        for arm in arms:
            for m, scale in arms[arm]:
                d = vals.get((m, arm))
                print("%-9s %-5s %-13s %s" % (fam.split(" ")[0], arm, m,
                                               ("%.4f (n=%d,%s)" % d) if d else "MISSING"))


if __name__ == "__main__":
    main()
