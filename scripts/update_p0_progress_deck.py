from pathlib import Path
import argparse
import hashlib
import json
import shutil
import zipfile

from lxml import etree
from pptx import Presentation

from refine_deck_20261111 import replace_text, slide_parts

ROOT = Path(__file__).resolve().parents[3]
DECK = ROOT / "ppt/RNA_LM微调策略评测-导师讨论修订版_20261111_导师反馈重测推进.pptx"
EXPECTED = "8bb8addec60a270461a438e138d86787fe85b9064f3bc2636c9485e5e44520e3"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--p0-complete", type=int, required=True)
    parser.add_argument("--mod-full-random-complete", type=int, required=True)
    parser.add_argument("--mrl-family-complete", type=int, required=True)
    parser.add_argument("--expected-sha", default=EXPECTED)
    parser.add_argument("--previous-p0-complete", type=int, default=8)
    parser.add_argument("--previous-mod-full-random-complete", type=int, default=1)
    parser.add_argument("--previous-mrl-family-complete", type=int, default=1)
    args = parser.parse_args()
    if not 0 <= args.p0_complete <= 18 or not 0 <= args.mod_full_random_complete <= 3 or not 0 <= args.mrl_family_complete <= 3:
        raise ValueError("invalid proof counts")
    assert hashlib.sha256(DECK.read_bytes()).hexdigest() == args.expected_sha
    pending = 18 - args.p0_complete
    mod_pending = 9 - args.mod_full_random_complete
    mrl_pending = 3 - args.mrl_family_complete
    if pending != mod_pending + mrl_pending:
        raise ValueError("proof counts do not decompose into the six P0 cells")
    previous_pending = 18 - args.previous_p0_complete
    previous_mod_pending = 9 - args.previous_mod_full_random_complete
    previous_mrl_pending = 3 - args.previous_mrl_family_complete
    backup = ROOT / "ppt/work/review_20261111/before_p0_progress.pptx"
    if not backup.exists():
        shutil.copy2(DECK, backup)
    with zipfile.ZipFile(DECK) as zin:
        infos = zin.infolist()
        payloads = {info.filename: zin.read(info.filename) for info in infos}
        parts = slide_parts(zin)
    edits = {
        2: [("6任务主矩阵闭合；两任务补尾" if previous_pending == 18 else "6任务主矩阵闭合；P0补尾", "6任务主矩阵闭合；P0补尾"),
            (f"per-base 270/270、complementary 324/324；P0补18格中{args.previous_p0_complete}格已闭合、{previous_pending}格待补" if previous_pending < 18 else "per-base 270/270、complementary 324/324；650M MRL full 6格、modification LoRA/full 12格待补",
             f"per-base 270/270、complementary 324/324；P0补18格中{args.p0_complete}格已闭合、{pending}格待补")],
        7: [(f"读图：六柱为 frozen/LoRA/full × random/family 的三种子均值，重点看同模型同策略的两柱差。LoRA 多数下降约 0.04–0.06；mega-full 的 family 反而高 0.211。非650M三策略已闭合；650M LoRA random=0.984±0.001，full random {args.previous_mod_full_random_complete}/3完成，其余{previous_mod_pending}格待补，不能称对 split 免疫。" if previous_pending < 18 else "读图：六柱为 frozen/LoRA/full × random/family 的三种子均值，重点看同模型同策略的两柱差。LoRA 多数下降约 0.04–0.06；mega-full 的 family 反而高 0.211。非650M三策略已闭合；650M modification LoRA/full 双split共12格待补，不能称对 split 免疫。",
             f"读图：六柱为 frozen/LoRA/full × random/family 的三种子均值，重点看同模型同策略的两柱差。LoRA 多数下降约 0.04–0.06；mega-full 的 family 反而高 0.211。非650M三策略已闭合；650M LoRA random=0.984±0.001，full random {args.mod_full_random_complete}/3完成，其余{mod_pending}格待补，不能称对 split 免疫。")],
        8: [(f"读图：三档同属 RiNALMo 家族，接近结果只说明当前数据、指标与协议下规模增益有限，不能推广到所有任务。650M full random=0.823±0.010；family {args.previous_mrl_family_complete}/3完成，余{previous_mrl_pending}格待补；降幅按模型与策略分别比较。" if previous_pending < 18 else "读图：三档同属 RiNALMo 家族，接近结果只说明当前数据、指标与协议下规模增益有限，不能推广到所有任务。650M MRL full 双split共6格待补；family 降幅按模型与策略分别比较。",
             f"读图：三档同属 RiNALMo 家族，接近结果只说明当前数据、指标与协议下规模增益有限，不能推广到所有任务。650M full random=0.823±0.010；family {args.mrl_family_complete}/3完成，余{mrl_pending}格待补；降幅按模型与策略分别比较。")],
        28: [(f"数据：最新 best-val 台账 + MRL/modification 聚合 + B20 阶段表（仅补 frozen）；6任务主矩阵闭合，P0补18格中{args.previous_p0_complete}格已闭合、{previous_pending}格待补，未闭合格为 NA，不补零。" if previous_pending < 18 else "数据：最新 best-val 台账 + MRL/modification 聚合 + B20 阶段表（仅补 frozen）；6任务主矩阵闭合，MRL/modification 的650M相关臂共18格待补，未闭合格为 NA，不补零。",
              f"数据：最新 best-val 台账 + MRL/modification 聚合 + B20 阶段表（仅补 frozen）；6任务主矩阵闭合，P0补18格中{args.p0_complete}格已闭合、{pending}格待补，未闭合格为 NA，不补零。")],
    }
    changed = []
    for index, replacements in edits.items():
        part = parts[index-1]
        xml = etree.fromstring(payloads[part])
        for old, new in replacements:
            replace_text(xml, old, new)
        payloads[part] = etree.tostring(xml, xml_declaration=True, encoding="UTF-8", standalone=True)
        changed.append(part)
    tmp = DECK.with_suffix(".tmp.pptx")
    with zipfile.ZipFile(tmp, "w") as zout:
        for info in infos:
            zout.writestr(info, payloads[info.filename])
    with zipfile.ZipFile(tmp) as zf:
        assert zf.testzip() is None
    assert len(Presentation(str(tmp)).slides) == 33
    tmp.replace(DECK)
    report = {"sha256": hashlib.sha256(DECK.read_bytes()).hexdigest(), "changed_parts": changed,
              "p0_complete": args.p0_complete, "pending": pending}
    (ROOT / "ppt/work/review_20261111/p0_progress_deck_report.json").write_text(json.dumps(report, indent=2)+"\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
