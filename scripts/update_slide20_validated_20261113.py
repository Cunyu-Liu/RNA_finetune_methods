#!/usr/bin/env python3
import argparse
import hashlib
import json
import shutil
import zipfile
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np
import pandas as pd
from pptx import Presentation


def validated_rows(source, summary):
    if summary["prediction_revalidation_passed"] != 7 or summary["n_complete"] != 7:
        raise ValueError("NucleicBERT random summary lacks complete prediction proof")
    if summary["default_lr"] != "3e-5" or summary["tuned_selection_lr"] != "3e-5":
        raise ValueError("unexpected NucleicBERT default or selected LR")
    if {row["seed"] for row in summary["formal"]} != {17, 29, 43}:
        raise ValueError("formal seed coverage is incomplete")
    frame = pd.read_csv(source, dtype={"lr": str, "rids": str})
    original = frame.copy(deep=True)
    rids = ";".join(row["rid"] for row in summary["formal"])
    for arm in ("default", "tuned"):
        mask = ((frame.task == "mrl") & (frame.model == "NucleicBERT")
                & (frame.arm == arm))
        if mask.sum() != 1:
            raise ValueError("NucleicBERT MRL source row is missing or duplicated")
        frame.loc[mask, ["lr", "n", "mean", "sd", "rids"]] = [
            "3e-5", 3, summary["formal_mean"], summary["formal_sample_sd"], rids]
    for task in ("noncoding-rna-family", "mrl"):
        mask = ((frame.task == task) & (frame.model == "AIDO.RNA-1.6B")
                & (frame.arm == "tuned"))
        if mask.sum() != 1:
            raise ValueError("AIDO tuned source row is missing or duplicated")
        frame.loc[mask, ["lr", "n", "mean", "sd", "rids"]] = ["", 0, np.nan, 0.0, ""]
    changed = (frame.ne(original) & ~(frame.isna() & original.isna())).any(axis=1)
    if changed.sum() != 4:
        raise ValueError(f"expected exactly four corrected rows, got {changed.sum()}")
    return frame


def draw(frame, output_dir, font):
    font_manager.fontManager.addfont(str(font))
    family = font_manager.FontProperties(fname=str(font)).get_name()
    plt.rcParams.update({"font.family": [family, "DejaVu Sans"],
                         "axes.unicode_minus": False,
                         "axes.spines.top": False, "axes.spines.right": False,
                         "pdf.fonttype": 42})
    models = ["RNA-Sc-10M", "RiNALMo-micro", "SpliceBERT", "ERNIE-RNA", "RNA-FM",
              "NucleicBERT", "AIDO.RNA-1.6B"]
    short = ["RNA-Sc\n10M", "RiNALMo\n33M", "SpliceBERT\n19M", "ERNIE\n86M",
             "RNA-FM\n99M", "NucleicBERT\n404M", "AIDO\n1.6B"]
    fig, axes = plt.subplots(1, 2, figsize=(15.2, 4.5), constrained_layout=True)
    for ax, (task, metric) in zip(axes, [("noncoding-rna-family", "ncRNA ACC"),
                                         ("mrl", "MRL Pearson r")]):
        x = np.arange(len(models))
        for j, arm in enumerate(("default", "tuned")):
            for i, model in enumerate(models):
                rows = frame[(frame.task == task) & (frame.model == model) & (frame.arm == arm)]
                if len(rows) != 1:
                    raise ValueError(f"invalid source coverage: {task}/{model}/{arm}")
                row = rows.iloc[0]
                pos = x[i] + (-0.17 if j == 0 else 0.17)
                if row.n == 0 or pd.isna(row["mean"]):
                    ax.text(pos, 0.025, "NA", ha="center", va="bottom", fontsize=7.5,
                            color="#8A8A8A", rotation=90)
                    continue
                value = float(row["mean"])
                color = "#C94C4C" if arm == "default" else "#27AE60"
                ax.bar(pos, value, width=0.30, color=color, yerr=float(row.sd), capsize=2,
                       hatch="///" if row.n < 3 else None, edgecolor="white", linewidth=0.5,
                       label=("Default LR" if arm == "default" else "Validation-tuned LR") if i == 0 else None)
                label = f"{value:.3f}" if abs(value) < 0.005 else f"{value:.2f}"
                if arm == "tuned":
                    label += "\n" + str(row.lr)
                ax.text(pos, value + 0.025, label, ha="center", va="bottom", fontsize=7.2,
                        color="#333333")
                if row.n < 3:
                    ax.text(pos, max(0.035, value * 0.45), f"n={row.n}", ha="center",
                            va="center", fontsize=7, rotation=90, color="#333333")
        ax.axhline(0, color="#777777", lw=0.7)
        ax.set_title(metric, fontsize=12, fontweight="bold", color="#1F3A5F")
        ax.set_xticks(x)
        ax.set_xticklabels(short, fontsize=8, rotation=25, ha="right", rotation_mode="anchor")
        ax.set_ylim(-0.12, 1.12)
        ax.grid(axis="y", color="#E8E8E8", lw=0.7)
        ax.set_axisbelow(True)
    axes[0].legend(ncol=2, loc="upper left", fontsize=9)
    fig.suptitle("Default vs validation-tuned LR | full-FT | Nuc MRL revalidated",
                 fontsize=13, fontweight="bold", color="#1F3A5F")
    fig.text(0.5, -0.03,
             "Default=3e-4 except Nuc MRL=3e-5; Nuc tuned reuses its default; AIDO deferred=NA; hatched=n<3",
             ha="center", va="top", fontsize=8.5, color="#666666")
    fig.savefig(output_dir / "a8_ncrna_mrl_only_validated_20261113.png", dpi=300,
                bbox_inches="tight", facecolor="white")
    fig.savefig(output_dir / "a8_ncrna_mrl_only_validated_20261113.pdf", bbox_inches="tight")
    plt.close(fig)


def replace_slide_image(deck, backup, png):
    if not backup.exists():
        shutil.copy2(deck, backup)
    presentation = Presentation(deck)
    slide = presentation.slides[19]
    pictures = [shape for shape in slide.shapes if shape.shape_type == 13]
    if len(pictures) != 1:
        raise ValueError("slide 20 must contain exactly one picture")
    picture = pictures[0]
    part = slide.part.related_part(picture._pic.blipFill.blip.rEmbed)
    references = [candidate for candidate in presentation.slides
                  for relationship in candidate.part.rels.values()
                  if relationship.reltype.endswith("/image")
                  and relationship.target_part == part]
    if references != [slide]:
        raise ValueError("slide 20 image is shared with another slide")
    part._blob = png.read_bytes()
    footer = slide.shapes[3].text_frame.paragraphs[0].runs[0]
    footer.text = ("读图：80组=8任务×5模型×2 split；seed101按held-out best_val选档，test不选档；tuned 240待跑。"
                   "Nuc random default=tuned=3e-5，复用三格r=−0.00162±2.7e-6；family default r=0.08714±0.00037，均7/7复核。family tuned在训；AIDO暂缓NA。")
    temporary = deck.with_suffix(".slide20.tmp.pptx")
    presentation.save(temporary)
    with zipfile.ZipFile(temporary) as archive:
        if archive.testzip() is not None:
            raise ValueError("PPTX ZIP validation failed")
    temporary.replace(deck)
    return str(part.partname)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-csv", type=Path, required=True)
    parser.add_argument("--random-summary", type=Path, required=True)
    parser.add_argument("--corrected-csv", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--font", type=Path, required=True)
    parser.add_argument("--deck", type=Path, required=True)
    parser.add_argument("--backup", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    summary = json.loads(args.random_summary.read_text())
    frame = validated_rows(args.source_csv, summary)
    frame.to_csv(args.corrected_csv, index=False)
    draw(frame, args.output_dir, args.font)
    png = args.output_dir / "a8_ncrna_mrl_only_validated_20261113.png"
    image_part = replace_slide_image(args.deck, args.backup, png)
    report = {
        "source_csv": str(args.source_csv),
        "source_csv_sha256": hashlib.sha256(args.source_csv.read_bytes()).hexdigest(),
        "corrected_csv": str(args.corrected_csv),
        "corrected_csv_sha256": hashlib.sha256(args.corrected_csv.read_bytes()).hexdigest(),
        "random_summary_sha256": hashlib.sha256(args.random_summary.read_bytes()).hexdigest(),
        "changed_rows": [["mrl", "NucleicBERT", "default"], ["mrl", "NucleicBERT", "tuned"],
                         ["noncoding-rna-family", "AIDO.RNA-1.6B", "tuned"],
                         ["mrl", "AIDO.RNA-1.6B", "tuned"]],
        "changed_row_count": 4,
        "image_part": image_part,
        "png_sha256": hashlib.sha256(png.read_bytes()).hexdigest(),
        "deck_sha256": hashlib.sha256(args.deck.read_bytes()).hexdigest(),
        "interpretation": "Nuc random default and tuned share LR=3e-5 and the same three formal runs; AIDO is deferred NA, never zero",
    }
    (args.output_dir / "slide20_validation_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
