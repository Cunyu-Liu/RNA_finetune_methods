import copy
from hashlib import sha256
from pathlib import Path

from PIL import Image
from pptx import Presentation
from pptx.util import Inches

WORK = Path(__file__).resolve().parent
ROOT = WORK.parent.parent
SRC = ROOT / "ppt/RNA_LM微调策略评测-导师讨论修订版_20261030_八任务扩展.pptx"
OUT = ROOT / "ppt/RNA_LM微调策略评测-导师讨论修订版_20261101_导师反馈修订.pptx"
SHUFFLE_FIG = ROOT / "交接文档/绘图数据/current/figure_source_data_20261028/figures/ncrna_shuffle_audit.png"
EXPECTED_SHA = "f4277d59af9f1c2436c3e8e0b99feffffaf0af13443b18088fb3b7984c1d7025"


def shape_by_name(slide, name):
    for shape in slide.shapes:
        if shape.name == name:
            return shape
    raise KeyError(name)


def set_text(slide, name, text):
    frame = shape_by_name(slide, name).text_frame
    paragraph = frame.paragraphs[0]
    assert paragraph.runs, name
    paragraph.runs[0].text = text
    for run in paragraph.runs[1:]:
        run._r.getparent().remove(run._r)
    for extra in list(frame.paragraphs[1:]):
        extra._p.getparent().remove(extra._p)
    paragraph.line_spacing = 1.5


def replace_picture(slide, name, path):
    old = shape_by_name(slide, name)
    left, top, width = old.left, old.top, old.width
    old._element.getparent().remove(old._element)
    with Image.open(path) as image:
        w, h = image.size
    picture = slide.shapes.add_picture(str(path), left, top, width=width)
    picture.height = int(width * h / w)
    picture.name = name


def clone_slide(prs, index):
    source = prs.slides[index]
    destination = prs.slides.add_slide(source.slide_layout)
    rid_map = {}
    for rel in source.part.rels.values():
        if "slideLayout" not in rel.reltype and "notesSlide" not in rel.reltype:
            new_rid = destination.part.rels._add_relationship(
                rel.reltype, rel._target, rel.is_external)
            rid_map[rel.rId] = new_rid
    for shape in source.shapes:
        element = copy.deepcopy(shape._element)
        for node in element.iter():
            for attr, value in node.attrib.items():
                if value in rid_map:
                    node.set(attr, rid_map[value])
        destination.shapes._spTree.insert_element_before(element, "p:extLst")
    return destination


def remove_answered_annotations(prs):
    removed = []
    for index, slide in enumerate(prs.slides, 1):
        for shape in list(slide.shapes):
            text = getattr(shape, "text", "").strip()
            if shape.left < 0 and text:
                removed.append((index, shape.name, text))
                shape._element.getparent().remove(shape._element)
    return removed


def main():
    assert sha256(SRC.read_bytes()).hexdigest() == EXPECTED_SHA
    prs = Presentation(str(SRC))
    assert len(prs.slides) == 30

    set_text(prs.slides[1], "PurposeNote",
             "八任务的目的：检验结论是否随任务粒度、分类/回归、类别不平衡和 split 改变，区分普遍规律与任务边界；不是堆实验数量。最终输出“何时用何种策略”的条件化配方。")
    table = next(shape.table for shape in prs.slides[1].shapes if shape.has_table)
    updates = {
        (0, 2): "关键实测结果（2026-11-01 · 导师反馈修订）",
        (3, 1): "random 6/8；family 5/8",
        (3, 2): "degradation/SSI 三臂均五档，④/⑤均6/8。SSI ④保留 full2000≈148M-LoRA1500、full2500/3000≈148M-LoRA2000 三组候选，非唯一；Frozen待阶段门",
        (5, 2): "时间×性能与显存独立为结论⑥；使用最新 8 任务 runtime；650M full 25GB 实测保留，待自然窗口",
        (6, 2): "controlled 30 格已重绘均值线与逐 seed 点；official 27/30 complete，650M LoRA 3 格按 corrected 队列补测",
        (8, 1): "5 个分类组合任务；SpliceAI 双 split 三种子",
        (8, 2): "ncRNA/modification/CRISPR/SSP 组合图完成；SpliceAI random/family 三种子均闭合，其余矩阵按最新 accepted 台账滚动更新",
    }
    for (row, col), text in updates.items():
        frame = table.rows[row].cells[col].text_frame
        paragraph = frame.paragraphs[0]
        assert paragraph.runs
        paragraph.runs[0].text = text
        for run in paragraph.runs[1:]:
            run._r.getparent().remove(run._r)
        for extra in list(frame.paragraphs[1:]):
            extra._p.getparent().remove(extra._p)
        paragraph.line_spacing = 1.15

    slide = prs.slides[4]
    set_text(slide, "TextBox 2", "结论 ①  ncRNA 旧“家族崩溃”可由样本顺序伪影解释")
    set_text(slide, "TextBox 3",
             "只改变每 epoch 是否重排训练样本：shuffle ACC=0.895，no-shuffle=0.096；旧 family 结果无法区分分布偏移与优化伪影，故隔离。")
    set_text(slide, "TextBox 5",
             "读图：shuffle=每轮重排训练样本，不改标签或 split；no-shuffle=保留同类成块顺序。中图红线仅 epoch0–3，是 best0+patience3 的完整停止曲线；结论①用固定 LR 对照，逐任务 validation 选 LR 见结论②。")
    replace_picture(slide, "Picture 6", SHUFFLE_FIG)

    slide = prs.slides[5]
    set_text(slide, "TextBox 2", "结论 ①a-2  modification：family 仍高 AUC，但非“免疫”")
    set_text(slide, "TextBox 3",
             "这是序列级 12 标签任务。已测非 650M 模型的 random−family 差值为 −0.211~+0.058，方向与幅度随模型/策略变化，不能称对切分免疫。")
    set_text(slide, "TextBox 5",
             "读图：六柱为 frozen/LoRA/full × random/family 的三种子均值，重点看同模型同策略的两柱差。LoRA 多数下降约 0.04–0.06；mega-full 的 family 反而高 0.211。650M frozen 双 split 已三种子闭合，其余未闭合项为 NA。")
    replace_picture(slide, "Picture 6",
                    ROOT / "交接文档/绘图数据/current/figure_source_data_20261030_eight_task_v14/scripts/modification_bestval_official_sixbar.png")

    slide = prs.slides[6]
    set_text(slide, "TextBox 2", "结论 ①a-3  MRL：family 普遍下降，RiNALMo 三档性能接近")
    set_text(slide, "TextBox 3",
             "micro/mega/650M 的 LoRA random=0.804/0.804/0.793，family=0.711/0.725/0.710；规模差异小，符合当前 MRL 任务的规模收益饱和，并非异常。")
    set_text(slide, "TextBox 5",
             "读图：三档同属 RiNALMo 家族，接近结果只说明当前数据、指标与协议下规模增益有限，不能推广到所有任务。650M frozen 双 split 已三种子闭合，full 等未闭合项为 NA；family 降幅按模型与策略分别比较。")
    replace_picture(slide, "Picture 6",
                    ROOT / "交接文档/绘图数据/current/figure_source_data_20261030_eight_task_v14/scripts/mrl_bestval_official_sixbar.png")

    composite = ROOT / "交接文档/绘图数据/current/figure_source_data_20261101_classification_composite/figures"
    slide = prs.slides[8]
    set_text(slide, "TextBox 2", "分类机制：ncRNA 表示与 full-test 性能同图对照")
    set_text(slide, "TextBox 3",
             "左：pre/LoRA/full 的 CLS 联合 t-SNE；右：同 seed17 checkpoint 的 Frozen/LoRA/Full ACC。聚类增强与泛化提升相关但不等同。")
    set_text(slide, "TextBox 5",
             "读图：上 random、下 family；性能来自 full-test，投影只用于显示。corrected seed17 下 LoRA/full 均保持高 ACC，旧“分类头坍缩”不作因果结论。其余分类任务沿用同版式，回归机制页保留。")
    picture = shape_by_name(slide, "图片 7")
    picture.left, picture.top, picture.width = Inches(0.95), Inches(1.42), Inches(11.4)
    replace_picture(slide, "图片 7", composite / "ncrna_classification_composite.png")

    slide = prs.slides[10]
    set_text(slide, "TextBox 2", "分类机制：modification 的多标签表示与性能")
    set_text(slide, "TextBox 3",
             "这是序列级 12 标签分类，m6A 为索引 7。左看表示，右看同 seed17 的 full-test m6A AUC；family 高 AUC 不等于对 split 免疫。")
    set_text(slide, "TextBox 5",
             "读图：上 random、下 family；红色为 m6A 阳性，灰色为阴性。性能与投影使用同一 checkpoint，但不以聚类形态推断因果；多标签不转成 softmax 单分类。")
    picture = shape_by_name(slide, "图片 7")
    picture.left, picture.top, picture.width = Inches(0.95), Inches(1.42), Inches(11.4)
    replace_picture(slide, "图片 7", composite / "modification_classification_composite.png")

    slide = prs.slides[11]
    set_text(slide, "TextBox 2", "分类机制：CRISPR 的表示与 PR-AUC 对照")
    set_text(slide, "TextBox 3",
             "极不平衡分类任务。左为 pre/LoRA/full 表示，右为同 seed17 的 full-test PR-AUC；当前 full 低于 LoRA，需结合 LR 与优化分析。")
    set_text(slide, "TextBox 5",
             "读图：上 random、下 family；红色为阳性。正例富集只用于投影，性能始终在完整 test 上计算；family 是 pair-sequence cluster，不宣称 guide-disjoint。")
    picture = shape_by_name(slide, "图片 7")
    picture.left, picture.top, picture.width = Inches(0.9), Inches(1.42), Inches(11.5)
    replace_picture(slide, "图片 7", composite / "crispr_classification_composite.png")

    slide = prs.slides[12]
    set_text(slide, "TextBox 2", "分类机制：SSP 的碱基对表示与 pair-F1")
    set_text(slide, "TextBox 3",
             "pair-level 分类。左为 PairHead 输入表示，右为同 seed17 的 full-test pair-F1；random 上 LoRA 略高，family 上 full 更高，仅限该种子。")
    set_text(slide, "TextBox 5",
             "读图：上 random、下 family；红色为 paired，灰色为 unpaired。正负各半只用于投影，性能使用完整 pair 集合与各状态 validation threshold，不用 sampled F1。")
    picture = shape_by_name(slide, "图片 7")
    picture.left, picture.top, picture.width = Inches(0.95), Inches(1.42), Inches(11.4)
    replace_picture(slide, "图片 7", composite / "ssp_classification_composite.png")

    slide = prs.slides[7]
    set_text(slide, "TextBox 5",
             "读图：5 个面板各用自己的主指标，纵轴独立。CRISPR/SSP/SpliceAI/degradation/SSI 分别有 28/28/26/25/25 个三种子单元（共30）；按正式best-val计数，不用阶段表补齐；斜线=n<3，空白=未完成。")
    replace_picture(slide, "Picture 4",
                    ROOT / "交接文档/绘图数据/current/figure_source_data_20261030_eight_task_v14/scripts/eight_task_sixbar.png")

    slide = prs.slides[17]
    set_text(slide, "TextBox 5",
             "读图：3e-4 是 runner 工程缺省，不是普遍最优。全参 tuning 已闭合 52/80 组：3e-5 二十三组、1e-4 十六组、1e-5 十一组、3e-4 两组。RNA-FM modification family 与 SSP random 默认档最优，说明必须逐组 validation；其余格继续补齐。MRL −0.112 经 CUDA 重评为近常数输出，不是评测算错。")

    slide = prs.slides[18]
    set_text(slide, "TextBox 3",
             "rank4/16 已 96/96，32/32 组三种子闭合。degradation 双 split、SpliceAI family rank16、SSI random/family rank4 与 random rank16 新增闭合；ncRNA rank8 复核不变。")
    set_text(slide, "TextBox 5",
             "读图：新增均值 SpliceAI family rank16=0.450、SSI random/family rank4=0.634/0.597、SSI random/family rank16=0.635/0.597、degradation random rank4/16=0.540/0.536。现有图仍为 legacy，不与 rank8 直接排名；96 格已完成。")

    slide = prs.slides[19]
    set_text(slide, "TextBox 2", "结论 ④  数据量等价：small-full(n) vs large-LoRA(m)")
    set_text(slide, "TextBox 3",
             "同家族 33M-full@1e-5 vs 148M-LoRA@3e-4；6/8 任务可判。SSI 三臂五档，三组候选非唯一；degradation cap 不变。")
    set_text(slide, "TextBox 5",
             "读图：SSI 现有 full2000≈LoRA1500、full2500/3000≈LoRA2000 三组候选，均满足逐 seed |Δ|≤0.02 且 CI 覆盖 0；其他近值不写等价。degradation 候选保留；2000/2500 同 cap，不重复计为新增数据证据。")
    picture = shape_by_name(slide, "Picture 6")
    picture.left, picture.top, picture.width = Inches(1.75), Inches(1.52), Inches(9.8)
    replace_picture(slide, "Picture 6",
                    ROOT / "交接文档/绘图数据/current/figure_source_data_20261030_eight_task_v14/scripts/equivalence_8task.png")

    slide = prs.slides[21]
    set_text(slide, "TextBox 2", "结论 ⑤  数据量 scaling：标注量如何改变策略收益")
    set_text(slide, "TextBox 3",
             "同模型内比较策略；④/⑤均 6/8 可判。degradation 与 SSI 的三臂均已五档闭合。")
    set_text(slide, "TextBox 5",
             "读图：SSI 三臂五档的 PCC 整体上升；④现有三组等价候选，非唯一交点。degradation 的 requested≥2000 仍是 cap=1552，不能解释为新增数据。")
    replace_picture(slide, "Picture 6",
                    ROOT / "交接文档/绘图数据/current/figure_source_data_20261030_eight_task_v14/scripts/data_volume_8task.png")

    slide = prs.slides[22]
    set_text(slide, "TextBox 2", "结论⑤补充  大模型覆盖与证据边界")
    set_text(slide, "TextBox 4",
             "数据：最新 best-val 台账 + MRL/modification 聚合 + B20 阶段表（仅补 frozen）；650M 大格在自然空出的独占显存窗口补测，已有 LoRA/frozen 保留，full 等未闭合项为 NA，不补零。")
    set_text(slide, "ReadNote",
             "读图：格内数字为已完成种子数，0 表示未闭合而非 0 分。148M 八任务六臂均已三种子闭合；650M 只展示已有格，不提前写规模律。")
    replace_picture(slide, "Picture 3",
                    ROOT / "交接文档/绘图数据/current/figure_source_data_20261030_eight_task_v14/scripts/bigmodel_coverage.png")
    shape_by_name(slide, "ReadNote").top = Inches(5.42)

    slide = prs.slides[23]
    set_text(slide, "TextBox 2", "结论④补充  MRL 高预算：legacy 局部对照")
    set_text(slide, "TextBox 5",
             "读图：full@3000=0.621、LoRA@10000=0.687，并非等价点。本页是 legacy 历史对照，只用于说明④的预算匹配问题，不与当前 best-val 图混算。")

    slide = prs.slides[24]
    set_text(slide, "TextBox 2", "结论④补充  MRL 低预算：legacy 数据收益对照")
    set_text(slide, "TextBox 5",
             "读图：full@1000=0.345、LoRA@3000=0.646，差距明显，不能称等价。保留 frozen 轨迹作历史参照；当前等价候选统一由同协议逐 seed 配对与 CI 判定。")

    slide = prs.slides[25]
    set_text(slide, "TextBox 2", "结论 ⑥  成本：时间×性能的逐任务比较")
    replace_picture(slide, "Picture 6",
                    ROOT / "交接文档/绘图数据/current/figure_source_data_20261030_eight_task_v14/scripts/eight_task_time_perf.png")

    slide = prs.slides[26]
    set_text(slide, "TextBox 2", "结论⑥补充  成本：显存峰值与规模边界")
    replace_picture(slide, "Picture 6",
                    ROOT / "交接文档/绘图数据/current/figure_source_data_20261030_eight_task_v14/scripts/peak_memory.png")

    slide = prs.slides[27]
    set_text(slide, "TextBox 2", "结论 ⑦  遗忘：controlled RNA-Sc 的 30M 峰值")
    set_text(slide, "TextBox 3",
             "A 图纵轴=ΔNLL(post−pre)，正=遗忘、负=反向增益；点=逐 seed，线=均值。30M 最差种子 full=26.2、LoRA=3.4，尾部比约 7.8×。")
    set_text(slide, "TextBox 5",
             "证据边界：最新 controlled causal held-out NLL 共 30 格、每组 3 seeds；official MLM 使用独立 fixed-mask 协议，不与本图混合。650M LoRA 余格完成后再更新其覆盖，不影响本 controlled 图。")
    replace_picture(slide, "Picture 6",
                    ROOT / "交接文档/绘图数据/current/figure_source_data_20261101_e6/e6_controlled_valid_20261101.png")

    set_text(prs.slides[28], "TextBox 10",
             "证据范围：八任务用于检验结论的任务边界，不是堆数量；SpliceAI random 三种子机制已闭合，family 待最后源格；④/⑤共用同源曲线，当前仅部分面板可判；时间/显存为⑥、遗忘为⑦，未闭合项不作最终结论。")
    set_text(prs.slides[29], "TextBox 21", "对应结论④/⑤")
    set_text(prs.slides[29], "TextBox 26", "对应结论①/机制")
    for index, tag in ((19, "04"), (21, "05"), (22, "05a"), (23, "04b"),
                       (24, "04c"), (25, "06a"), (26, "06b"), (27, "07")):
        set_text(prs.slides[index], "TextBox 1", tag)

    random_multiseed = composite / "spliceai_random_multiseed_composite.png"
    family_multiseed = composite / "spliceai_family_multiseed_composite.png"
    multiseed_ready = random_multiseed.is_file() and family_multiseed.is_file()
    if multiseed_ready:
        family_slide = clone_slide(prs, 13)
        slide = prs.slides[13]
        set_text(slide, "TextBox 2", "分类机制：SpliceAI random 的三种子对照")
        set_text(slide, "TextBox 3",
                 "三行依次为 seed17/29/43；每行左侧为三状态投影，右侧为对应 checkpoint 的 full-test macro-F1。")
        set_text(slide, "TextBox 5",
                 "读图：random split 下三种子均已完成。灰/红/蓝=negative/acceptor/donor；类别均衡只用于显示，性能用完整 test。family 的三种子见下一页。")
        picture = shape_by_name(slide, "图片 7")
        picture.left, picture.top, picture.width = Inches(1.45), Inches(1.42), Inches(10.4)
        replace_picture(slide, "图片 7", random_multiseed)

        set_text(family_slide, "TextBox 2", "分类机制：SpliceAI family 的三种子对照")
        set_text(family_slide, "TextBox 3",
                 "三行依次为 seed17/29/43；表示与 full-test 性能使用同一 checkpoint，避免把 split 差异误读为投影差异。")
        set_text(family_slide, "TextBox 5",
                 "读图：family split 下三种子均已完成。投影只用于描述，full-test macro-F1 用于性能判断；两页合读才可比较 random 与 family，不以 t-SNE 推断因果。")
        picture = shape_by_name(family_slide, "图片 7")
        picture.left, picture.top, picture.width = Inches(1.45), Inches(1.42), Inches(10.4)
        replace_picture(family_slide, "图片 7", family_multiseed)
        family_id = prs.slides._sldIdLst[-1]
        prs.slides._sldIdLst.remove(family_id)
        prs.slides._sldIdLst.insert(14, family_id)
        set_text(prs.slides[29], "TextBox 10",
                 "证据范围：八任务用于检验结论的任务边界，不是堆数量；SpliceAI random/family 三种子机制均闭合；④/⑤共用同源曲线，当前仅部分面板可判；时间/显存为⑥、遗忘为⑦，未闭合项不作最终结论。")

    tier_dir = ROOT / "交接文档/绘图数据/current/figure_source_data_20261030_eight_task_v14/scripts"
    family_ready = (tier_dir / "equivalence_8task_family.png").is_file() and \
        (tier_dir / "data_volume_8task_family.png").is_file()
    if family_ready:
        family_equiv = clone_slide(prs, 20)
        set_text(family_equiv, "TextBox 1", "04F")
        set_text(family_equiv, "TextBox 2", "结论④补充  family：数据量等价的切分边界")
        set_text(family_equiv, "TextBox 3",
                 "family split；5/8 任务可判。MRL/degradation/SSI 有候选，modification/SSP 当前未观测到；不套用 random 配对。")
        set_text(family_equiv, "TextBox 5",
                 "读图：MRL full2000≈LoRA1000；degradation full1500及 cap 后2000–3000均≈LoRA1000；SSI full1500≈LoRA1500、full3000≈LoRA2000。均满足逐 seed |Δ|≤0.02 且 CI 覆盖 0；degradation requested 2000–3000 同为 actual=1680，不重复计数据收益。")
        replace_picture(family_equiv, "Picture 6", tier_dir / "equivalence_8task_family.png")

        family_scaling = clone_slide(prs, 22)
        set_text(family_scaling, "TextBox 1", "05F")
        set_text(family_scaling, "TextBox 2", "结论⑤补充  family：三臂数据量曲线")
        set_text(family_scaling, "TextBox 3",
                 "family split；5/8 任务可判。modification/MRL/SSP/degradation/SSI 三臂均五档；ncRNA 待补。")
        set_text(family_scaling, "TextBox 5",
                 "读图：family 只用于检验 split 边界，不与 random 合并均值。CRISPR/SpliceAI 低信号不判趋势；degradation requested 2000–3000 同为 cap=1680，SSI 148M-LoRA 五档。等价配对见④ family 页。")
        replace_picture(family_scaling, "Picture 6", tier_dir / "data_volume_8task_family.png")

    ncrna_overview = clone_slide(prs, 4)
    set_text(ncrna_overview, "TextBox 1", "01a")
    set_text(ncrna_overview, "TextBox 2", "结论①a-1  ncRNA 性能总览：修正后的六柱对照")
    set_text(ncrna_overview, "TextBox 3",
             "Frozen/LoRA/Full × random/family 的三种子均值±SD；28/30 单元闭合，固定 LR 对照，NA=未闭合。")
    set_text(ncrna_overview, "TextBox 5",
             "读图：柱高为 ACC，误差线为 SD；斜线=n<3，空白=NA。本页回答修正后 ncRNA 的性能，下一页解释旧 family 崩溃为何被隔离；不把训练顺序伪影当作分布证据。")
    replace_picture(ncrna_overview, "Picture 6",
                    ROOT / "交接文档/绘图数据/current/figure_source_data_20261030_eight_task_v14/scripts/ncrna_bestval_official_sixbar.png")
    ncrna_overview_id = prs.slides._sldIdLst[-1]
    prs.slides._sldIdLst.remove(ncrna_overview_id)

    slide_ids = prs.slides._sldIdLst
    obsolete = slide_ids[20 + int(multiseed_ready)]
    prs.part.drop_rel(obsolete.rId)
    slide_ids.remove(obsolete)
    moving = [slide_ids[22 + int(multiseed_ready)], slide_ids[23 + int(multiseed_ready)]]
    for element in moving:
        slide_ids.remove(element)
    slide_ids.insert(20 + int(multiseed_ready), moving[0])
    slide_ids.insert(21 + int(multiseed_ready), moving[1])
    assert len(prs.slides) == 29 + int(multiseed_ready) + 2 * int(family_ready)

    if family_ready:
        family_equiv_id, family_scaling_id = slide_ids[-2], slide_ids[-1]
        slide_ids.remove(family_equiv_id)
        slide_ids.remove(family_scaling_id)
        slide_ids.insert(21, family_equiv_id)
        slide_ids.insert(25, family_scaling_id)
    assert len(prs.slides) == 29 + int(multiseed_ready) + 2 * int(family_ready)

    slide_ids.insert(4, ncrna_overview_id)
    assert len(prs.slides) == 30 + int(multiseed_ready) + 2 * int(family_ready)

    removed = remove_answered_annotations(prs)
    prs.save(str(OUT))
    print("saved", OUT)
    print("slides", len(prs.slides), "annotations_removed", len(removed))
    for item in removed:
        print("removed", item[0], item[1])


if __name__ == "__main__":
    main()
