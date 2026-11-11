from pathlib import Path, PurePosixPath
import hashlib
import json
import posixpath
import shutil
import zipfile

from lxml import etree
from pptx import Presentation

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "交接文档").is_dir() and (p / "ppt").is_dir())
SOURCE = ROOT / "ppt/RNA_LM微调策略评测-导师讨论修订版_20261101_导师反馈修订.pptx"
OUT = ROOT / "ppt/RNA_LM微调策略评测-导师讨论修订版_20261111_导师反馈重测推进.pptx"
BACKUP = ROOT / "ppt/work/review_20261111/before_20261111.pptx"
NEW_FIGURE = ROOT / "ppt/work/review_20261111/peak_memory_by_task.png"
EXPECTED_SHA = "01eb86a913d4b666737d373c1d68650e43de05f124d129e457b13bf56e814209"
NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "pr": "http://schemas.openxmlformats.org/package/2006/relationships",
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def text_of(node):
    return "".join(node.xpath(".//a:t/text()", namespaces=NS))


def slide_parts(zf):
    pres = etree.fromstring(zf.read("ppt/presentation.xml"))
    rels = etree.fromstring(zf.read("ppt/_rels/presentation.xml.rels"))
    targets = {r.get("Id"): r.get("Target") for r in rels}
    parts = []
    for node in pres.xpath("//p:sldIdLst/p:sldId", namespaces=NS):
        rid = node.get("{%s}id" % NS["r"])
        target = targets[rid]
        parts.append(str(PurePosixPath("ppt") / target))
    return parts


def replace_shape_text(xml, old, new):
    matches = []
    for sp in xml.xpath(".//p:sp", namespaces=NS):
        if text_of(sp) == old:
            matches.append(sp)
    assert len(matches) == 1, (old[:80], len(matches))
    texts = matches[0].xpath(".//a:t", namespaces=NS)
    assert texts
    texts[0].text = new
    for node in texts[1:]:
        node.text = ""


def replace_all_text(xml, old, new):
    nodes = xml.xpath(".//a:t[text()=$value]", namespaces=NS, value=old)
    assert nodes, old
    for node in nodes:
        node.text = new


def remove_comment(xml, prefix):
    matches = [sp for sp in xml.xpath(".//p:sp", namespaces=NS) if text_of(sp).startswith(prefix)]
    assert len(matches) == 1, (prefix, len(matches))
    matches[0].getparent().remove(matches[0])


def main():
    assert sha(SOURCE) == EXPECTED_SHA, sha(SOURCE)
    assert NEW_FIGURE.exists()
    BACKUP.parent.mkdir(parents=True, exist_ok=True)
    if not BACKUP.exists():
        shutil.copy2(SOURCE, BACKUP)
    changes = {}
    with zipfile.ZipFile(SOURCE) as zin:
        parts = slide_parts(zin)
        assert len(parts) == 33
        payloads = {info.filename: zin.read(info.filename) for info in zin.infolist()}
        infos = zin.infolist()

    replacements = {
        5: [("读图：柱高为 ACC，误差线为 SD；斜线=n<3，空白=NA。本页回答修正后 ncRNA 的性能，下一页解释旧 family 崩溃为何被隔离；不把训练顺序伪影当作分布证据。",
             "读图：本页是 corrected 结果：random/family 均保持高 ACC，因此不再显示旧“家族崩溃”。下一页只用严格 A/B 解释旧低值为何不能再作为家族分布证据；两页回答不同问题，并不矛盾。")],
        6: [("读图：shuffle=每轮重排训练样本，不改标签或 split；no-shuffle=保留同类成块顺序。中图红线仅 epoch0–3，是 best0+patience3 的完整停止曲线；结论①用固定 LR 对照，逐任务 validation 选 LR 见结论②。",
             "读图：第5页展示修正后性能，本页只追溯旧结果。shuffle=每轮重排训练样本，不改标签或 split；no-shuffle=保留同类成块顺序。中图红线仅 epoch0–3，是 best0+patience3 的完整停止曲线。严格 A/B 只改变顺序，旧低值不能再称为家族分布崩溃。")],
        7: [("读图：六柱为 frozen/LoRA/full × random/family 的三种子均值，重点看同模型同策略的两柱差。LoRA 多数下降约 0.04–0.06；mega-full 的 family 反而高 0.211。650M frozen 双 split 已三种子闭合，其余未闭合项为 NA。",
             "读图：六柱为 frozen/LoRA/full × random/family 的三种子均值，重点看同模型同策略的两柱差。LoRA 多数下降约 0.04–0.06；mega-full 的 family 反而高 0.211。三策略主矩阵已闭合，差值方向随模型与策略变化，不能称对 split 免疫。")],
        8: [("读图：三档同属 RiNALMo 家族，接近结果只说明当前数据、指标与协议下规模增益有限，不能推广到所有任务。650M frozen 双 split 已三种子闭合，full 等未闭合项为 NA；family 降幅按模型与策略分别比较。",
             "读图：三档同属 RiNALMo 家族，接近结果只说明当前数据、指标与协议下规模增益有限，不能推广到所有任务。三策略主矩阵已闭合；family 降幅按模型与策略分别比较。")],
        19: [("读图：Δ>0 表示 family 表现更低，负值表示 family 更高。本页仅保留 MRL legacy 描述；ncRNA 旧 Δ 与 m6A 旧面板均已隔离，8 任务 corrected Δ 矩阵待补。",
              "读图：Δ>0 表示 family 表现更低，负值表示 family 更高。本页仅保留 MRL legacy 描述；ncRNA 旧 Δ 与 m6A 旧面板均已隔离。corrected 八任务 Δ 可从已闭合主矩阵重算，将作为独立描述性补充，不恢复旧面板。")],
        20: [("读图：3e-4 是 runner 工程缺省，不是普遍最优。seed101 tuning 已闭合76/80组：3e-5三十三组、1e-4十九组、1e-5二十一组、3e-4三组；37个双split均闭合的task×model中，22组选档不同。650M SSI family 1e-5 PCC=0.624，default≈0；SpliceAI仍近基线。其余4组未闭合，test不参与选档，tuned复测待80组。MRL −0.112经CUDA重评为近常数输出，不是评测算错。",
              "读图：80组=8任务×5模型×2 split，不是按 LR 数值聚类。seed101在每组四档LR中仅按 held-out best_val 选档，test不参与；当前76/80组已闭合，tuned待80组。NucleicBERT/AIDO 的 MRL full 共40格重测已登记，按同法选档后用17/29/43复测并保存逐样本预测。MRL −0.112已CUDA复核为近常数输出，不是评测算错。")],
        21: [("读图：新增均值 SpliceAI family rank16=0.450、SSI random/family rank4=0.634/0.597、SSI random/family rank16=0.635/0.597、degradation random rank4/16=0.540/0.536。现有图仍为 legacy，不与 rank8 直接排名；96 格已完成。",
              "读图：新增均值 SpliceAI family rank16=0.450、SSI random/family rank4=0.634/0.597、SSI random/family rank16=0.635/0.597、degradation random rank4/16=0.540/0.536。rank4/16=96/96已闭合，但八任务 DoRA rank8=240格尚待补；本页不与 rank8 混排，也不宣称结论③全部完成。")],
        28: [("数据：最新 best-val 台账 + MRL/modification 聚合 + B20 阶段表（仅补 frozen）；650M 大格在自然空出的独占显存窗口补测，已有 LoRA/frozen 保留，full 等未闭合项为 NA，不补零。",
              "数据：最新 best-val 台账 + MRL/modification 聚合 + B20 阶段表（仅补 frozen）；主矩阵已闭合，650M Full 按实际任务覆盖展示，未闭合扩展格仍为 NA，不补零。")],
        30: [("按当前已完成格统计；650M Full 覆盖6个任务，峰值中位 13.3GB、范围 12.1–17.0GB，不外推全部任务。",
              "按任务分别展示各模型/策略的三种子显存中位数；33M LoRA 的约0.34GB与8.47GB分别对应 CRISPR 与 ncRNA，先查协议再判异常。"),
             ("读图：bar = 8 任务逐任务峰值中位数的中位，whisker = 跨任务 min–max；显存与标签顺序无关，但绝对值随 batch 与序列长度变化，跨任务比较须同看 min–max。",
              "读图：每面板为一个任务，柱为三种子实测峰值中位数，纵轴为 log 刻度。max_len、batch 与输出粒度不同，不能跨任务只比 min–max；两个极值任务的6个独立 CUDA 复测已登记。")],
        31: [("结论 ⑦  遗忘：controlled RNA-Sc 的 30M 峰值", "结论 ⑦  遗忘：RiNALMo official 重测与任务边界"),
             ("A 图纵轴=ΔNLL(post−pre)，正=遗忘、负=反向增益；点=逐 seed，线=均值。30M 最差种子 full=26.2、LoRA=3.4，尾部比约 7.8×。",
              "official 当前任务起点=ncRNA；650M LoRA 余3格待闭合，MRL/modification 的36个新起点已登记。下方 controlled 图仅作方法对照，不代替 RiNALMo 最终结论。"),
             ("证据边界：最新 controlled causal held-out NLL 共 30 格、每组 3 seeds；official MLM 使用独立 fixed-mask 协议，不与本图混合。650M LoRA 余格完成后再更新其覆盖，不影响本 controlled 图。",
              "证据边界：controlled causal held-out NLL 共30格、每组3 seeds；official MLM 使用独立 fixed-mask 协议，不与本图混合。RiNALMo 三档补齐后替换主图，旧泄漏结果不使用。")],
        32: [("证据范围：八任务用于检验结论的任务边界，不是堆数量；SpliceAI random/family 三种子机制均闭合；④/⑤共用同源曲线，当前仅部分面板可判；时间/显存为⑥、遗忘为⑦，未闭合项不作最终结论。",
              "证据范围：八任务用于发现任务边界，不支持任意任务全局成立。新增 LOTO 检验配方迁移，NucleicBERT/AIDO 用于外部架构复核；行文采用“总趋势→例外→适用条件→实践配方”，所有推荐限定模型、任务、split 与协议。")],
        33: [("同数据、同 split、同指标比较策略；任务地图覆盖 4 类任务形式、8 个任务。", "先保证协议可信：统一任务语义，并用 shuffle A/B、best checkpoint 与独立 CUDA 复核排除实现伪影。"),
             ("严格 A/B 证明旧 ncRNA 近随机表现可由未 shuffle 复现；MRL 提示任务结构影响泛化。m6A 已纠正为序列级多标签。", "再用八任务主矩阵识别策略收益的任务与 split 边界，不预设统一赢家。"),
             ("旧 ncRNA 规模谱与等价点已隔离；数据量等价线须在同任务同家族内比较 full(n) 与 LoRA(m)。", "同模型 scaling 与同家族 full(n)↔large-LoRA(m) 回答数据预算；时间、显存与遗忘决定最终成本。"),
             ("训练顺序 A/B 定位 ncRNA 旧伪影；t-SNE 只提供描述性线索，不直接定位分类头或证明因果。", "结论按证据分级：同任务稳健、跨任务稳健、外部架构迁移与 LOTO 新任务外推。"),
             ("主线：先定任务与切分，再调 LR 比较策略，最后按验证表现、资源与遗忘成本选择；8 任务扩展保留阶段性证据边界。", "主线：可信协议→任务边界→优化条件→数据预算→成本决策；只推广到证据覆盖范围。")],
    }
    comments = {5: "从这里也看不出来家族切分是崩溃的呀", 20: "这个把学习率分组是啥意思啊", 21: "还没补全 8 任务？", 30: "33m 这 lora 不对", 32: "你觉得，我就只在这 8 个任务上测评"}
    changed = set()
    for index, edits in replacements.items():
        part = parts[index - 1]
        xml = etree.fromstring(payloads[part])
        for old, new in edits:
            replace_shape_text(xml, old, new)
        if index in comments:
            remove_comment(xml, comments[index])
        payloads[part] = etree.tostring(xml, xml_declaration=True, encoding="UTF-8", standalone=True)
        changed.add(part)

    slide2 = etree.fromstring(payloads[parts[1]])
    table_edits = {
        "ncRNA family 重测": "八任务主矩阵闭合",
        "旧 ncRNA family 与派生结论隔离；其他任务按各自协议复核": "per-base 270/270、complementary 324/324；旧 family 隔离，使用 corrected 结果",
        "corrected 扩展在测": "rank 闭合；DoRA 待补",
        "33M rank8 六格复核完成；rank4/16 共 96 格在跑；8 任务六臂见 ①a 系列": "rank4/16=96/96；DoRA rank8=240格待补；full 主矩阵已完成",
        "扩展在测": "八任务 runtime 更新",
        "时间×性能与显存独立为结论⑥；使用最新 8 任务 runtime；650M full 25GB 实测保留，待自然窗口": "时间×性能与显存独立为结论⑥；650M Full 已覆盖6任务，峰值中位13.3GB",
    }
    for old, new in table_edits.items():
        replace_all_text(slide2, old, new)
    payloads[parts[1]] = etree.tostring(slide2, xml_declaration=True, encoding="UTF-8", standalone=True)
    changed.add(parts[1])

    slide30_part = parts[29]
    slide30 = etree.fromstring(payloads[slide30_part])
    embeds = slide30.xpath(".//p:pic/p:blipFill/a:blip/@r:embed", namespaces=NS)
    assert len(embeds) == 1, embeds
    rel_part = str(PurePosixPath(slide30_part).parent / "_rels" / (PurePosixPath(slide30_part).name + ".rels"))
    rels = etree.fromstring(payloads[rel_part])
    targets = [r.get("Target") for r in rels if r.get("Id") == embeds[0]]
    assert len(targets) == 1
    media_part = posixpath.normpath(posixpath.join("ppt/slides", targets[0]))
    assert media_part.startswith("ppt/media/")
    payloads[media_part] = NEW_FIGURE.read_bytes()
    changed.update([slide30_part, rel_part, media_part])

    with zipfile.ZipFile(OUT, "w") as zout:
        for info in infos:
            zout.writestr(info, payloads[info.filename])
    with zipfile.ZipFile(OUT) as zf:
        assert zf.testzip() is None
    prs = Presentation(str(OUT))
    assert len(prs.slides) == 33
    all_text = "\n".join(getattr(sh, "text", "") for slide in prs.slides for sh in slide.shapes)
    for prefix in comments.values():
        assert prefix not in all_text, prefix
    report = {
        "source": str(SOURCE),
        "source_sha256": EXPECTED_SHA,
        "backup": str(BACKUP),
        "output": str(OUT),
        "output_sha256": sha(OUT),
        "slides": 33,
        "zip_crc": "PASS",
        "changed_parts": sorted(changed),
        "comments_removed": comments,
        "new_figure_sha256": sha(NEW_FIGURE),
    }
    report_path = ROOT / "ppt/work/review_20261111/revision_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
