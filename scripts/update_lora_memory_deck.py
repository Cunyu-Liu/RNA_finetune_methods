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
BACKUP = ROOT / "ppt/work/review_20261111/before_lora_memory_closure.pptx"
EXPECTED = "0f1ba49654bdcee9fd0888956c7fbeaec9745d7831b67d2e36ffc7edb73c9995"


def main():
    assert hashlib.sha256(DECK.read_bytes()).hexdigest() == EXPECTED
    if not BACKUP.exists():
        shutil.copy2(DECK, BACKUP)
    with zipfile.ZipFile(DECK) as zin:
        infos = zin.infolist()
        payloads = {info.filename: zin.read(info.filename) for info in infos}
        part = slide_parts(zin)[29]
    xml = etree.fromstring(payloads[part])
    edits = [
        ("按任务分别展示各模型/策略的三种子显存中位数；33M LoRA 的约0.34GB与8.47GB分别对应 CRISPR 与 ncRNA，先查协议再判异常。",
         "33M LoRA 两任务×3种子 full-test 均与源一致；训练峰值约0.27GB（CRISPR）与8.48GB（ncRNA），差异来自任务协议，不是训练异常。"),
        ("读图：每面板为一个任务，柱为三种子实测峰值中位数，纵轴为 log 刻度。max_len、batch 与输出粒度不同，不能跨任务只比 min–max；两个极值任务的6个独立 CUDA 复测已登记。",
         "读图：每面板为一个任务，柱为三种子实测训练峰值中位数，纵轴为 log 刻度。max_len=128 vs 512 等协议不同，不能跨任务只比 min–max；ncRNA seed17 独立训练峰值8481.16MB。checkpoint 评测峰值另存，不与训练成本混用。"),
    ]
    for old, new in edits:
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
    report = {"deck": str(DECK), "sha256": hashlib.sha256(DECK.read_bytes()).hexdigest(), "changed_parts": [part], "source_summary": "lora_memory_revalidation_summary.json"}
    (ROOT / "ppt/work/review_20261111/lora_memory_deck_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
