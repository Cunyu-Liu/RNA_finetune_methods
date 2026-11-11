from pathlib import Path
import argparse
import csv
import hashlib
import importlib.util
import json
import posixpath
import shutil
import zipfile

from lxml import etree
from pptx import Presentation

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "ppt/work/review_20261111"
DECK = ROOT / "ppt/RNA_LM微调策略评测-导师讨论修订版_20261111_导师反馈重测推进.pptx"
EXPECTED = "8bb8addec60a270461a438e138d86787fe85b9064f3bc2636c9485e5e44520e3"
NS = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main",
      "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
      "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--embed", action="store_true")
    parser.add_argument("--deck-sha", default=EXPECTED)
    args = parser.parse_args()
    base = ROOT / "交接文档/绘图数据/current/figure_source_data_20261030_eight_task_v14/data/bestval_ledger_export_20261101_v209.csv"
    increment = OUT / "p0_accepted_ledger_extension_20261112.csv"
    original = list(csv.DictReader(base.open()))
    added = list(csv.DictReader(increment.open()))
    assert len(original) == 2137 and added
    ids = {row["run_id"] for row in original}
    assert not ids & {row["run_id"] for row in added}
    source = OUT / "coverage_source"
    (source / "current_results").mkdir(parents=True, exist_ok=True)
    (source / "figures").mkdir(parents=True, exist_ok=True)
    merged = source / f"current_results/bestval_ledger_export_20261101_v210_p0_{len(added)}.csv"
    with merged.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(original[0]))
        writer.writeheader()
        writer.writerows(original + added)
    shutil.copy2(ROOT / "交接文档/绘图数据/current/figure_source_data_20261028/figures/extension_three_task_sixbar_data.csv",
                 source / "figures/extension_three_task_sixbar_data.csv")
    spec = importlib.util.spec_from_file_location(
        "coverage_builder", ROOT / "ppt/work/fig_20261030/build_time_perf_coverage.py")
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    builder.WORK = source
    builder.OUT = OUT
    builder.latest_export = lambda: merged
    frame = builder.load_ledger()
    coverage = builder.coverage_matrix(frame)
    coverage.to_csv(OUT / "bigmodel_coverage_data.csv", index=False)
    builder.draw_coverage(coverage, OUT / "bigmodel_coverage.png", OUT / "bigmodel_coverage.pdf")
    selected = coverage[coverage.model == "RiNALMo-650M"].set_index("task")
    expected = {}
    for task, strategy, split in (("mrl", "full", "random"), ("mrl", "full", "family"),
                                  ("modification", "lora", "random"), ("modification", "full", "random")):
        expected[(task, f"{strategy}_{split}")] = len({row["seed"] for row in added
            if row["task"] == task and row["strategy"] == strategy and row["split"] == split})
    for (task, key), value in expected.items():
        assert int(selected.loc[task, key]) == value, (task, key, selected.loc[task, key])
    manifest = {"revision": "20261112_p0_coverage_v210", "p0_complete": len(added),
                "inputs": {str(base.relative_to(ROOT)): sha(base), increment.name: sha(increment)},
                "merged": str(merged.relative_to(ROOT)), "merged_sha256": sha(merged),
                "expected_cells": {f"{task}:{key}": value for (task, key), value in expected.items()},
                "outputs": {name: sha(OUT / name) for name in
                            ("bigmodel_coverage_data.csv", "bigmodel_coverage.png", "bigmodel_coverage.pdf")}}
    (OUT / "p0_coverage_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+"\n")
    if args.embed:
        assert sha(DECK) == args.deck_sha, sha(DECK)
        backup = OUT / f"before_p0_coverage_image_{len(added)}.pptx"
        if not backup.exists():
            shutil.copy2(DECK, backup)
        with zipfile.ZipFile(DECK) as zin:
            infos = zin.infolist()
            payloads = {info.filename: zin.read(info.filename) for info in infos}
            part = "ppt/slides/slide28.xml"
            xml = etree.fromstring(payloads[part])
            embeds = xml.xpath(".//p:pic/p:blipFill/a:blip/@r:embed", namespaces=NS)
            assert len(embeds) == 1
            rels = etree.fromstring(payloads["ppt/slides/_rels/slide28.xml.rels"])
            targets = [r.get("Target") for r in rels if r.get("Id") == embeds[0]]
            assert len(targets) == 1
            media = posixpath.normpath(posixpath.join("ppt/slides", targets[0]))
            assert media.startswith("ppt/media/")
            payloads[media] = (OUT / "bigmodel_coverage.png").read_bytes()
        temporary = DECK.with_suffix(".tmp.pptx")
        with zipfile.ZipFile(temporary, "w") as zout:
            for info in infos:
                zout.writestr(info, payloads[info.filename])
        with zipfile.ZipFile(temporary) as zf:
            assert zf.testzip() is None
        assert len(Presentation(str(temporary)).slides) == 33
        temporary.replace(DECK)
        manifest["deck_sha256"] = sha(DECK)
        manifest["changed_parts"] = [media]
        (OUT / "p0_coverage_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+"\n")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
