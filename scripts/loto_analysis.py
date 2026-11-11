from pathlib import Path
import hashlib
import json
import re

import pandas as pd

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "交接文档").is_dir() and (p / "ppt").is_dir())
SOURCE = ROOT / "交接文档/绘图数据/current/figure_source_data_20261030_eight_task_v14/data/bestval_ledger_export_20261101_v209.csv"
OUT = ROOT / "ppt/work/review_20261111"
STRATEGIES = ["frozen", "lora", "full"]
TASK_LABELS = {
    "noncoding-rna-family": "ncRNA",
    "crispr-off-target": "CRISPR",
    "modification": "modification",
    "mrl": "MRL",
    "spliceai": "SpliceAI",
    "secondary-structure": "SSP",
    "degradation": "degradation",
    "ssi": "SSI",
}


def keep_row(row):
    rid = row["run_id"]
    if any(tag in rid for tag in ("_noshuffle", "_smoke", "_diag", "_seqmlfix")):
        return False
    if re.search(r"_r(?:4|16)_", rid) or int(row["seed"]) not in (17, 29, 43):
        return False
    if re.search(r"_e3\d+_", rid):
        return False
    for key in ("artifact_dir", "resolved_artifact_dir"):
        if "/home/cunyuliu/rna-ft-eval/artifacts" in str(row.get(key, "")):
            return False
    return True


def main():
    raw = list(__import__("csv").DictReader(SOURCE.open()))
    rows = [r for r in raw if keep_row(r)]
    assert len(rows) == 702, len(rows)
    frame = pd.DataFrame(rows)
    frame["value"] = pd.to_numeric(frame["value"])
    cells = frame.groupby(["task", "model", "split", "strategy"], as_index=False).agg(value=("value", "mean"), n=("seed", "nunique"))
    assert cells.n.eq(3).all(), cells[cells.n != 3]
    cells["rank"] = cells.groupby(["task", "model", "split"])["value"].rank(ascending=False, method="average")
    cells["best"] = cells.groupby(["task", "model", "split"])["value"].transform("max")
    cells["worst"] = cells.groupby(["task", "model", "split"])["value"].transform("min")
    cells["span"] = cells["best"] - cells["worst"]
    output = []
    for task in TASK_LABELS:
        train = cells[cells.task != task]
        test = cells[cells.task == task]
        global_ranks = train.groupby("strategy")["rank"].mean().sort_values()
        chosen = global_ranks.index[0]
        selected = test[test.strategy == chosen].copy()
        score = ((selected.value - selected.worst) / selected.span.replace(0, pd.NA)).dropna()
        oracle = test[test["rank"] == 1]
        output.append({
            "held_out_task": task,
            "selected_strategy": chosen,
            "train_mean_rank": float(global_ranks.iloc[0]),
            "held_out_mean_rank": float(selected["rank"].mean()),
            "normalized_performance": float(score.mean()),
            "best_possible_rank": float(oracle["rank"].mean()),
            "lora_mean_rank": float(test[test.strategy == "lora"]["rank"].mean()),
            "full_mean_rank": float(test[test.strategy == "full"]["rank"].mean()),
            "frozen_mean_rank": float(test[test.strategy == "frozen"]["rank"].mean()),
            "n_cells": int(len(selected)),
        })
    result = pd.DataFrame(output)
    result.to_csv(OUT / "loto_strategy_generalization.csv", index=False)
    cells.to_csv(OUT / "loto_strategy_cells.csv", index=False)
    summary = {
        "method": "For each held-out task, select one strategy with the lowest mean within-task rank across the other seven tasks. Test only on the held-out task.",
        "source": str(SOURCE.relative_to(ROOT)),
        "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "n_runs": len(rows),
        "n_cells": len(cells),
        "tasks": output,
        "mean_normalized_performance": float(result.normalized_performance.mean()),
        "selected_counts": result.selected_strategy.value_counts().to_dict(),
        "boundary": "Eight tasks are not eight independent statistical replicates. LOTO is a descriptive stress test, not proof of universal generalization.",
    }
    (OUT / "loto_strategy_generalization.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
