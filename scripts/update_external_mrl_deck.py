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
SOURCE = ROOT / "ppt/work/review_20261111/mrl_nucleicbert_random_summary_20261112.json"
EXPECTED = "d80b3d95742c9194e1f23edf8900f185d272ea970033e86c3f3046714854640e"
OLD = "读图：80组=8任务×5模型×2 split，不是按 LR 数值聚类。seed101仅按 held-out best_val 选档，test不参与；已闭合80/80组：3e-5三十三组、1e-4十九组、1e-5二十五组、3e-4三组，tuned 240格已生成。3组 default 近常数经CUDA证明不可选。NucleicBERT/AIDO 的 MRL full 共40格重测已登记，按同法选档后用17/29/43复测并保存逐样本预测。"
NEW = "读图：80组=8任务×5模型×2 split；seed101按 held-out best_val 选档，test不参与；80/80组选档完成，tuned 240已生成。NucleicBERT random 7格四档r均约−0.002，default 3e-5三种子mean=−0.00162、SD=2.7e-6；bs16复核7/7，稳定近未学习。Nuc双split 14格已闭合，AIDO待测。"


def main():
    assert hashlib.sha256(DECK.read_bytes()).hexdigest() == EXPECTED
    source = json.loads(SOURCE.read_text())
    assert source["n_complete"] == 7 and source["prediction_revalidation_passed"] == 7
    assert abs(source["formal_mean"] + 0.001618557195390723) < 1e-12
    assert abs(source["formal_sample_sd"] - 2.6756804629179136e-06) < 1e-12
    backup = ROOT / "ppt/work/review_20261111/before_external_mrl.pptx"
    if not backup.exists():
        shutil.copy2(DECK, backup)
    with zipfile.ZipFile(DECK) as zin:
        infos = zin.infolist()
        payloads = {info.filename: zin.read(info.filename) for info in infos}
        part = slide_parts(zin)[19]
    xml = etree.fromstring(payloads[part])
    replace_text(xml, OLD, NEW)
    payloads[part] = etree.tostring(xml, xml_declaration=True, encoding="UTF-8", standalone=True)
    tmp = DECK.with_suffix(".tmp.pptx")
    with zipfile.ZipFile(tmp, "w") as zout:
        for info in infos:
            zout.writestr(info, payloads[info.filename])
    with zipfile.ZipFile(tmp) as zf:
        assert zf.testzip() is None
    assert len(Presentation(str(tmp)).slides) == 33
    tmp.replace(DECK)
    report = {"sha256": hashlib.sha256(DECK.read_bytes()).hexdigest(), "changed_parts": [part],
              "source": str(SOURCE), "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest()}
    (ROOT / "ppt/work/review_20261111/external_mrl_deck_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
