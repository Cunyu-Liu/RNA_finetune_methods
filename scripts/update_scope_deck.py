from pathlib import Path
import hashlib
import json
import shutil
import zipfile

from lxml import etree
from pptx import Presentation

from refine_deck_20261111 import replace_text, slide_parts

ROOT = Path(__file__).resolve().parents[3]
DECK = ROOT / "ppt/RNA_LM微调策略评测-导师讨论修订版_20261111_导师反馈重测推进.pptx"
EXPECTED = "3d4306a2fd19b016e51dcaa83e2b45223aa9f052540e60e25ca6a6aa89292719"
OLD20 = "读图：80组=8任务×5模型×2 split；seed101按 held-out best_val 选档，test不参与；80/80组选档完成，tuned 240已生成。NucleicBERT random 7格四档r均约−0.002，default 3e-5三种子mean=−0.00162、SD=2.7e-6；bs16复核7/7，稳定近未学习。Nuc双split 14格已闭合，AIDO待测。"
NEW20 = "读图：80组=8任务×5模型×2 split；seed101按 held-out best_val 选档，test不参与；80/80组选档完成，tuned 240已生成。NucleicBERT random 7格四档r均约−0.002，default 3e-5三种子mean=−0.00162、SD=2.7e-6；bs16复核7/7，稳定近未学习。Nuc双split 14格已闭合；AIDO暂缓，保留NA。"
OLD32 = "证据范围：LOTO 中8/8次统一选择 LoRA，归一化表现均值0.926；但 degradation full 更优、SSP 的 LoRA/frozen 并列，说明 LoRA 是强默认候选而非任意任务定律。650M两任务18格待补；NucleicBERT/AIDO 用于外部架构复核，结论仍限定模型、任务、split 与协议。"
NEW32 = "证据范围：固定LR的LOTO中8/8次选择LoRA、归一化表现0.926，只构成候选假设。须在同模型、任务、split、seed下经validation分别选LR后，LoRA至少不差于full才支持默认推荐；test不选档。主tuned 240与Nuc tuned 6未闭合，AIDO暂缓保留NA。"


def main():
    assert hashlib.sha256(DECK.read_bytes()).hexdigest() == EXPECTED
    backup = ROOT / "ppt/work/review_20261111/before_scope_freeze.pptx"
    if not backup.exists():
        shutil.copy2(DECK, backup)
    with zipfile.ZipFile(DECK) as zin:
        infos = zin.infolist()
        payloads = {info.filename: zin.read(info.filename) for info in infos}
        parts = slide_parts(zin)
    for index, old, new in ((20, OLD20, NEW20), (32, OLD32, NEW32)):
        part = parts[index-1]
        xml = etree.fromstring(payloads[part])
        replace_text(xml, old, new)
        payloads[part] = etree.tostring(xml, xml_declaration=True, encoding="UTF-8", standalone=True)
    tmp = DECK.with_suffix(".tmp.pptx")
    with zipfile.ZipFile(tmp, "w") as zout:
        for info in infos:
            zout.writestr(info, payloads[info.filename])
    with zipfile.ZipFile(tmp) as zf:
        assert zf.testzip() is None
    assert len(Presentation(str(tmp)).slides) == 33
    tmp.replace(DECK)
    report = {"sha256": hashlib.sha256(DECK.read_bytes()).hexdigest(), "changed_parts": [parts[19], parts[31]]}
    (ROOT / "ppt/work/review_20261111/scope_freeze_deck_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
