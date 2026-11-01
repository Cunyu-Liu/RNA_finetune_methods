"""Build the official six-bar MRL or modification figure from the current best-val ledger."""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(OUT.parent.parent / "figure_source_data_20261028" / "scripts"))
import plot_report_20261028 as report


def latest_export():
    candidates = sorted((OUT.parent / "data").glob("bestval_ledger_export_*.csv"),
                        key=lambda p: [int(x) for x in re.split(r"(\d+)", p.name) if x.isdigit()])
    assert candidates, "no bestval export"
    return candidates[-1]


def load_rows(task):
    df = pd.read_csv(latest_export())
    df = df[(df.task == task) & (df.protocol == "bestval_v1") & df.seed.isin([17, 29, 43])]
    df = df[~df.run_id.str.contains("_e3|_smoke|_diag|_noshuffle|_r4_|_r16_|_dense")]
    df = df[~df.run_id.str.endswith("_seqmlfix")]
    df = df[~df.artifact_dir.astype(str).str.contains("/home/cunyuliu/rna-ft-eval/artifacts")]
    df = df.copy()
    df["rid"] = df.run_id
    df["proof_state"] = "complete"
    df["peak_mb"] = df.peak_mem_mb
    return df


def main(task):
    df = load_rows(task)
    report.OUT = OUT
    font_path = Path.home() / "Library/Fonts/msyh.ttc"
    report.font_manager.fontManager.addfont(str(font_path))
    report.YAHEI = report.font_manager.FontProperties(fname=str(font_path)).get_name()
    report.plt.rcParams.update({
        "font.family": [report.YAHEI, "DejaVu Sans"],
        "axes.unicode_minus": False,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.linewidth": 1.2,
        "legend.frameon": False,
        "pdf.fonttype": 42,
        "svg.fonttype": "none",
    })
    if task == "mrl":
        report.sixbar(df, "mrl", "MRL Pearson r (3-seed mean)",
                      "mrl_bestval_official_sixbar",
                      "MRL | official-model best-val comparison", ymax=0.92)
    elif task == "modification":
        report.sixbar(df, "modification", "m6A AUC (sequence-level multi-label)",
                      "modification_bestval_official_sixbar",
                      "Modification | corrected sequence-level 12-label task; m6A index 7",
                      ymax=1.08, chance=0.5)
    else:
        raise ValueError(task)
    print("built", task, "runs", len(df), "source", latest_export().name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task", choices=("mrl", "modification"))
    args = parser.parse_args()
    main(args.task)
