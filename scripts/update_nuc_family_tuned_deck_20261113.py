#!/usr/bin/env python3
import argparse
import hashlib
import json
import shutil
import zipfile
from pathlib import Path

from pptx import Presentation


def validated_family(document):
    if document["revision"] != "20261113_nucleicbert_mrl_default_vs_tuned_v1":
        raise ValueError("unexpected paired summary revision")
    if document["prediction_checks"] != 12 or document["unique_prediction_rids"] != 9:
        raise ValueError("paired summary lacks complete independent prediction proof")
    rows = {row["split"]: row for row in document["splits"]}
    if set(rows) != {"random", "family"}:
        raise ValueError("paired summary must cover random and family")
    family = rows["family"]
    if family["n_pairs"] != 3 or len(family["pairs"]) != 3:
        raise ValueError("family tuned must contain three formal seeds")
    if {pair["seed"] for pair in family["pairs"]} != {17, 29, 43}:
        raise ValueError("family tuned seed coverage mismatch")
    if family["default_lr"] != "3e-5" or family["tuned_lr"] != "3e-4":
        raise ValueError("unexpected family default or tuned LR")
    if family["test_metric_used_for_selection"] is not False:
        raise ValueError("test metric must not be used for LR selection")
    if family["unique_prediction_rids"] != 6:
        raise ValueError("family requires six distinct default/tuned prediction proofs")
    return family


def update_deck(deck, backup, family, report_path):
    if not backup.exists():
        shutil.copy2(deck, backup)
    presentation = Presentation(deck)
    slide20 = presentation.slides[19]
    footer = slide20.shapes[3].text_frame.paragraphs[0].runs[0]
    if "family tuned在训" not in footer.text:
        raise ValueError("slide 20 is not in the expected pending state")
    tuned_sd = (f"{family['tuned_sample_sd']:.5f}" if family["tuned_sample_sd"] >= 5e-6
                else f"{family['tuned_sample_sd']:.1e}")
    footer.text = (
        "读图：80组=8任务×5模型×2 split；seed101按held-out best_val选档，test不选档；主tuned 240按队列推进。"
        "Nuc random default=tuned=3e-5，复用三格r=−0.00162±2.7e-6；"
        f"family default(3e-5) r={family['default_mean']:.5f}±{family['default_sample_sd']:.5f}，"
        f"tuned(3e-4) r={family['tuned_mean']:.5f}±{tuned_sd}，"
        f"配对Δ={family['tuned_minus_default_mean']:+.5f}，6/6复核；AIDO暂缓NA。"
    )
    scope = presentation.slides[31].shapes[9].text_frame.paragraphs[0].runs[0]
    old = "full/LoRA tuned与Nuc family 3未闭合"
    if old not in scope.text:
        raise ValueError("slide 32 is not in the expected pending state")
    scope.text = scope.text.replace(old, "full/LoRA tuned未闭合；Nuc family tuned 3已闭合")
    temporary = deck.with_suffix(".nuc-family.tmp.pptx")
    presentation.save(temporary)
    with zipfile.ZipFile(temporary) as archive:
        if archive.testzip() is not None:
            raise ValueError("PPTX ZIP validation failed")
    temporary.replace(deck)
    report = {
        "deck": str(deck), "deck_sha256": hashlib.sha256(deck.read_bytes()).hexdigest(),
        "family_default_mean": family["default_mean"],
        "family_tuned_mean": family["tuned_mean"],
        "family_tuned_sample_sd": family["tuned_sample_sd"],
        "family_paired_delta_mean": family["tuned_minus_default_mean"],
        "family_paired_delta_sample_sd": family["tuned_minus_default_sample_sd"],
        "prediction_checks": 12, "unique_prediction_rids": 9,
        "interpretation": "Descriptive paired result for NucleicBERT MRL family only; not a global LR conclusion",
        "aido_status": "deferred_na",
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--paired-summary", type=Path, required=True)
    parser.add_argument("--deck", type=Path, required=True)
    parser.add_argument("--backup", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    document = json.loads(args.paired_summary.read_text())
    family = validated_family(document)
    report = update_deck(args.deck, args.backup, family, args.report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
