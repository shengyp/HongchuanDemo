"""Build the project discussion outline in the reference document's writing style."""

from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor


OUT = Path(__file__).resolve().parents[1] / "docs" / "长尾营养食谱系统项目说明.docx"


def line(doc, value, *, lead="", before=0, after=7):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(before)
    p.paragraph_format.space_after = Pt(after)
    p.paragraph_format.line_spacing = 1.35
    if lead and value.startswith(lead):
        r = p.add_run(lead)
        r.bold = True
        if lead in ("注：", "需要补齐：", "下一步："):
            r.font.color.rgb = RGBColor(170, 35, 35)
        p.add_run(value[len(lead):])
    else:
        p.add_run(value)
    return p


def topic(doc, number, question):
    p = line(doc, f"（{number}）{question}", before=13, after=5)
    p.runs[0].bold = True
    p.paragraph_format.keep_with_next = True


doc = Document()
section = doc.sections[0]
section.top_margin = Cm(2.1)
section.bottom_margin = Cm(2.0)
section.left_margin = Cm(2.5)
section.right_margin = Cm(2.5)
normal = doc.styles["Normal"]
normal.font.name = "Microsoft YaHei"
normal._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft YaHei")
normal.font.size = Pt(10.5)
normal.font.color.rgb = RGBColor(20, 24, 25)
title = doc.styles["Title"]
title.font.name = "Microsoft YaHei"
title._element.rPr.rFonts.set(qn("w:eastAsia"), "Microsoft YaHei")
title.font.size = Pt(17)
title.font.bold = True
title.font.color.rgb = RGBColor(0, 0, 0)
title.paragraph_format.space_after = Pt(15)

doc.add_paragraph("长尾知识补偿驱动的个性化营养食谱系统", "Title")
line(doc, "项目说明  讨论稿  2026 年 10 月 22 日", after=14)

topic(doc, 1, "可用性：这个系统是谁用的，完成什么任务？")
line(doc, "主要使用者是研究营养知识图谱与个性化食谱的学生、研究人员，以及检查实验过程的指导教师或评审。使用者需要完成数据接入、长尾诊断、候选关联核查、食谱推荐和质量评估，而不只是查看图表。")
line(doc, "从数据治理的角度来说：Food.com 原始食谱 + USDA 食材营养数据 → 有来源记录的食材与食谱数据 → 长尾知识补偿 → 营养约束下的食谱结果。")
line(doc, "可以：（a）查看食谱和食材统计；（b）搜索真实食谱；（c）查看低频食材、真实共现和补偿候选；（d）输入营养目标、偏好与排除食材；（e）查看推荐排序、克数调整和逐项达标情况；（f）比较补偿前后的实验结果。")

topic(doc, 2, "长尾分布在系统里有什么作用？")
line(doc, "Food.com 中有不少食材只出现在少量食谱里，搭配证据不足，推荐容易偏向常见食材。系统先识别低频食材，保留其真实共现，再参考相似食材提出候选关联，作为检索和排序的弱证据。候选关联须标明来源，不能当作真实搭配，也不能改变营养值。")
line(doc, "当前数据有 14,942 种食材，其中 5,217 种仅出现在不超过 2 道食谱中。补偿是否有效，需在同一测试集上比较补偿前后的长尾覆盖率、推荐质量和营养达标率。")

topic(doc, 3, "数据集与任务怎样衔接？")
line(doc, "建议按用途管理四类数据：（a）食谱与食材出现频次，用于长尾诊断；（b）已观察的食材共现，用于建立真实关系；（c）每 100 g 食材营养值和经核验的食谱克数，用于营养计算；（d）用户目标、偏好和任务结果，用于推荐与评估。")
line(doc, "当前已接入 Food.com 的 231,637 道真实食谱和 USDA 的 180 条六项指标齐全食材记录。但 Food.com 的食材列表没有逐项克数，USDA 食材与食谱也未完成可靠匹配。因此，真实数据目前支持检索和长尾统计；营养推荐及克数生成仍由演示数据驱动。")
line(doc, "需要补齐：一批有原始用量、份数、单位、生熟状态和 FDC ID 的可核验食谱。缺少这些字段的记录应标记待审核，不能进入真实营养验算。", lead="需要补齐：")

topic(doc, 4, "任务管理是否应当单独成为一个模块？")
line(doc, "建议单独设置任务管理。创建任务时，先选择数据集及其版本，再选择任务类型和算法，最后设置营养目标或长尾阈值。任务执行后保存输入条件、结果、耗时和来源，便于复现。")
line(doc, "任务类型可以是：长尾识别、候选关系补偿、食谱检索推荐、食材克数生成、营养问答和效果评估。任务 → 数据 → 算法 → 结果，这条链应在页面上能够回看。当前各页面可分别操作，统一的任务记录与跨模块联动尚需建设。")

topic(doc, 5, "前面两个研究点在哪里接入？")
line(doc, "UnKGE-BCKC 提供长尾实体和关系表征不足、知识补偿的研究思路。系统在长尾诊断和候选关系模块承接这个问题：输入食材与关系数据，输出真实边、推断边及证据。当前实现是营养、类别和名称相似度的规则基线；BERT 编码、聚类残差补偿和对比学习模型尚未接入。")
line(doc, "Nutri20K 提供营养约束问答与个性化食谱任务的研究思路。系统在问答、食谱推荐和克数生成模块接收六项营养目标、食材偏好及排除条件，输出候选食谱、每份营养值和目标偏差。当前系统是独立实现，未复现论文原模型及其指标。")
line(doc, "两者的接点是推荐阶段：长尾补偿提供有来源的候选关系，营养约束模块判断候选食谱能否满足用户目标。补偿只影响候选覆盖和排序解释；最终营养数值仍须由真实食材营养值与核验后的克数计算。")

topic(doc, 6, "大模型在什么位置使用？")
line(doc, "可以设置一个问答与解释中心。大模型读取检索到的食谱、食材关系和程序计算的营养结果，帮助用户理解“为什么推荐”和“哪项目标未达标”。数值约束由后端计算和复核；大模型不负责臆造食材克数、营养值或候选边。")
line(doc, "当前系统默认知识检索回答，可选连接本地 Ollama。没有配置模型时，系统仍能运行；模型未接入不影响数据分析与营养计算。")

topic(doc, 7, "如何评价系统和模型的质量？")
line(doc, "任务 → 数据 → 评测标准 → 质量报告。报告建议分三部分：数据质量看来源、完整性、单位和食材匹配；补偿质量看长尾覆盖、候选关联核验与有无补偿对照；应用质量看推荐排序、六项营养达标和错误案例。")
line(doc, "执行一次任务后，应能追溯所用数据版本、阈值、算法、输入目标、输出结果和失败原因。若学校要求体现研究与系统的衔接，这份报告比单纯的图谱展示更能说明模型在系统中产生了什么作用。")

topic(doc, 8, "可行性现在体现在哪里？")
line(doc, "已具备：Vue 3 + TypeScript + Vite 前端、Python 后端、SQLite 食谱索引；真实食谱搜索、长尾频次和共现统计；USDA 食材来源目录；基于演示数据的推荐和克数生成。")
line(doc, "下一步：先核验一批带克数的真实食谱并匹配 USDA FDC ID，再打通真实营养计算；随后建立任务管理和质量报告，比较规则基线与后续研究模型。满足这些条件后，系统才能对“长尾补偿提高推荐效果”给出可重复的证据。", lead="下一步：")

footer = section.footer.paragraphs[0]
footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = footer.add_run("长尾营养食谱系统项目说明  ·  讨论稿")
run.font.size = Pt(8)
run.font.color.rgb = RGBColor(100, 100, 100)
OUT.parent.mkdir(parents=True, exist_ok=True)
doc.save(OUT)
print(OUT)
