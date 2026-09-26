"""T4.3.4 decision-tree query CLI (reproducibility package component).

Given a task + split scenario (+ optional compute budget hint), print the
strategy recommendation from status/decision_tree.csv (pre-registered rule).

usage:
  python -m rnafteval.recipe_query --task noncoding-rna-family --split family
  python -m rnafteval.recipe_query --list
"""
from __future__ import annotations
import argparse, csv, os

CSV = "/mnt/cunyuliu/rna-ft-eval/status/decision_tree.csv"
ADVICE = {
    "noncoding-rna-family": ("family", "per-sequence family classification collapses under "
                             "accepting LoRA/full fine-tuning when the split is family-level"),
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--task")
    ap.add_argument("--split", default="family", choices=["random", "family"])
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()
    rows = list(csv.DictReader(open(CSV)))
    if args.list or not args.task:
        for r in rows:
            print("%-24s %-7s %-22s med=%+6.1f%%  %s" % (
                r["task"], r["split"], "%s vs %s" % (r["arm_a"], r["arm_b"]),
                float(r["median_gain_pct"]), r["label"]))
        return 0
    sub = [r for r in rows if r["task"] == args.task and r["split"] == args.split]
    if not sub:
        print("no decisions for", args.task, args.split)
        return 1
    print("task=%s  split=%s  granularity=%s" % (args.task, args.split, sub[0]["granularity"]))
    for r in sub:
        print("  %-22s median %+6.1f%% (n=%s, n_pos=%s) -> %s" % (
            "%s vs %s" % (r["arm_a"], r["arm_b"]), float(r["median_gain_pct"]),
            r["n"], r["n_pos"], r["label"]))
    rec = next((r for r in sub if r["arm_a"] == "lora" and r["arm_b"] == "frozen"), None)
    fl = next((r for r in sub if r["arm_a"] == "full" and r["arm_b"] == "lora"), None)
    adv = []
    if rec:
        adv.append("LoRA over frozen: %s" % rec["label"])
    if fl:
        adv.append("full over LoRA: %s" % fl["label"])
    print("RECOMMENDATION:", " | ".join(adv))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
