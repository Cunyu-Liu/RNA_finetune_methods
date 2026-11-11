from pathlib import Path
import hashlib
import json
import shutil
import zipfile

from lxml import etree
from pptx import Presentation

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "交接文档").is_dir() and (p / "ppt").is_dir())
DECK = ROOT / "ppt/RNA_LM微调策略评测-导师讨论修订版_20261111_导师反馈重测推进.pptx"
BACKUP = ROOT / "ppt/work/review_20261111/before_loto_refinement.pptx"
EXPECTED = "2c7c3a4249de41b1bc07a28ebde6ea7423c1c0574c818cc037accc39f23ca1c5"
NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def text_of(node):
    return "".join(node.xpath(".//a:t/text()", namespaces=NS))


def replace_text(xml, old, new):
    shapes = [sp for sp in xml.xpath(".//p:sp", namespaces=NS) if text_of(sp) == old]
    if shapes:
        assert len(shapes) == 1, (old[:100], len(shapes))
        nodes = shapes[0].xpath(".//a:t", namespaces=NS)
    else:
        nodes = xml.xpath(".//a:t[text()=$value]", namespaces=NS, value=old)
        assert nodes, old
    nodes[0].text = new
    for node in nodes[1:]:
        node.text = ""


def slide_parts(zf):
    pres = etree.fromstring(zf.read("ppt/presentation.xml"))
    rels = etree.fromstring(zf.read("ppt/_rels/presentation.xml.rels"))
    targets = {r.get("Id"): r.get("Target") for r in rels}
    return [str(Path("ppt") / targets[node.get("{%s}id" % NS["r"])]) for node in pres.xpath("//p:sldIdLst/p:sldId", namespaces=NS)]


def main():
    assert sha(DECK) == EXPECTED, sha(DECK)
    if not BACKUP.exists():
        shutil.copy2(DECK, BACKUP)
    with zipfile.ZipFile(DECK) as zin:
        infos = zin.infolist()
        payloads = {info.filename: zin.read(info.filename) for info in infos}
        parts = slide_parts(zin)
    edits = {
        2: [("八任务主矩阵闭合", "6任务主矩阵闭合；两任务补尾"),
            ("per-base 270/270、complementary 324/324；旧 family 隔离，使用 corrected 结果", "per-base 270/270、complementary 324/324；650M MRL full 6格、modification LoRA/full 12格待补")],
        7: [("读图：六柱为 frozen/LoRA/full × random/family 的三种子均值，重点看同模型同策略的两柱差。LoRA 多数下降约 0.04–0.06；mega-full 的 family 反而高 0.211。三策略主矩阵已闭合，差值方向随模型与策略变化，不能称对 split 免疫。",
             "读图：六柱为 frozen/LoRA/full × random/family 的三种子均值，重点看同模型同策略的两柱差。LoRA 多数下降约 0.04–0.06；mega-full 的 family 反而高 0.211。非650M三策略已闭合；650M modification LoRA/full 双split共12格待补，不能称对 split 免疫。")],
        8: [("读图：三档同属 RiNALMo 家族，接近结果只说明当前数据、指标与协议下规模增益有限，不能推广到所有任务。三策略主矩阵已闭合；family 降幅按模型与策略分别比较。",
             "读图：三档同属 RiNALMo 家族，接近结果只说明当前数据、指标与协议下规模增益有限，不能推广到所有任务。650M MRL full 双split共6格待补；family 降幅按模型与策略分别比较。")],
        28: [("数据：最新 best-val 台账 + MRL/modification 聚合 + B20 阶段表（仅补 frozen）；主矩阵已闭合，650M Full 按实际任务覆盖展示，未闭合扩展格仍为 NA，不补零。",
              "数据：最新 best-val 台账 + MRL/modification 聚合 + B20 阶段表（仅补 frozen）；6任务主矩阵闭合，MRL/modification 的650M相关臂共18格待补，未闭合格为 NA，不补零。")],
        32: [("证据范围：八任务用于发现任务边界，不支持任意任务全局成立。新增 LOTO 检验配方迁移，NucleicBERT/AIDO 用于外部架构复核；行文采用“总趋势→例外→适用条件→实践配方”，所有推荐限定模型、任务、split 与协议。",
              "证据范围：LOTO 中8/8次统一选择 LoRA，归一化表现均值0.926；但 degradation full 更优、SSP 的 LoRA/frozen 并列，说明 LoRA 是强默认候选而非任意任务定律。650M两任务18格待补；NucleicBERT/AIDO 用于外部架构复核，结论仍限定模型、任务、split 与协议。")],
    }
    changed = []
    for index, replacements in edits.items():
        part = parts[index - 1]
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
    report = {"output": str(DECK), "output_sha256": sha(DECK), "slides": 33, "zip_crc": "PASS", "changed_parts": changed}
    (ROOT / "ppt/work/review_20261111/refinement_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
