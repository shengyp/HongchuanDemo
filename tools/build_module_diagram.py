"""Render the academic module flowchart as a vector PDF."""

from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "长尾营养食谱系统_学术模块图.pdf"
pdfmetrics.registerFont(TTFont("SimHei", r"C:\Windows\Fonts\simhei.ttf"))

W, H = 1200, 700
NAVY = HexColor("#19344A")
TEAL = HexColor("#177C7A")
TEXT = HexColor("#263D4B")
MUTED = HexColor("#647986")
LINE = HexColor("#CEDBE1")
PANEL = HexColor("#F5F8FA")
WHITE = HexColor("#FFFFFF")


def label(c, x, y, value, size=14, color=TEXT, align="left"):
    c.setFillColor(color)
    c.setFont("SimHei", size)
    if align == "center":
        c.drawCentredString(x, y, value)
    else:
        c.drawString(x, y, value)


def rounded(c, x, y, w, h, radius=10, fill=WHITE, stroke=LINE, width=1):
    c.setLineWidth(width)
    c.setStrokeColor(stroke)
    c.setFillColor(fill)
    c.roundRect(x, y, w, h, radius, stroke=1, fill=1)


def card(c, x, y, w, h, title, body):
    rounded(c, x, y, w, h, 10, WHITE, LINE, 1.2)
    label(c, x + 16, y + h - 27, title, 18, NAVY)
    for idx, row in enumerate(body):
        label(c, x + 16, y + h - 51 - idx * 18, row, 12.5, MUTED)


def panel(c, x, w, number, heading):
    rounded(c, x, 91, w, 478, 15, PANEL, HexColor("#DFE8EC"), 0.8)
    label(c, x + 17, 537, number, 17, TEAL)
    label(c, x + 51, 537, heading, 19, NAVY)
    c.setStrokeColor(HexColor("#D8E3E8"))
    c.setLineWidth(1)
    c.line(x + 17, 516, x + w - 17, 516)


def arrow(c, x1, y1, x2, y2, color=TEAL, width=2.2):
    c.setStrokeColor(color)
    c.setFillColor(color)
    c.setLineWidth(width)
    c.line(x1, y1, x2 - 9, y2)
    p = c.beginPath()
    p.moveTo(x2, y2)
    p.lineTo(x2 - 11, y2 + 5.5)
    p.lineTo(x2 - 11, y2 - 5.5)
    p.close()
    c.drawPath(p, stroke=0, fill=1)


def down_arrow(c, x, y1, y2):
    c.setStrokeColor(HexColor("#9EB8C2"))
    c.setFillColor(HexColor("#9EB8C2"))
    c.setLineWidth(1.8)
    c.line(x, y1, x, y2 + 8)
    p = c.beginPath()
    p.moveTo(x, y2)
    p.lineTo(x - 5, y2 + 9)
    p.lineTo(x + 5, y2 + 9)
    p.close()
    c.drawPath(p, stroke=0, fill=1)


OUT.parent.mkdir(parents=True, exist_ok=True)
c = canvas.Canvas(str(OUT), pagesize=(W, H))
c.setTitle("长尾知识补偿驱动的个性化营养食谱系统模块流程图")
c.setAuthor("NutriGraph research prototype")
c.setFillColor(WHITE)
c.rect(0, 0, W, H, fill=1, stroke=0)

label(c, 60, 645, "长尾知识补偿驱动的个性化营养食谱系统", 30, NAVY)
label(c, 60, 612, "系统模块流程图  |  数据构建 · 知识补偿 · 营养约束 · 质量评估", 15, MUTED)
c.setStrokeColor(TEAL)
c.setLineWidth(3)
c.line(60, 593, 1140, 593)

panel(c, 60, 215, "01", "数据输入")
panel(c, 305, 225, "02", "数据构建")
panel(c, 560, 275, "03", "核心模型")
panel(c, 865, 275, "04", "输出与评估")

card(c, 76, 407, 183, 92, "Food.com 食谱", ["食谱与食材清单", "食材搭配记录"])
card(c, 76, 259, 183, 92, "USDA 食材营养", ["食材营养成分", "每 100 g 营养值"])
card(c, 76, 111, 183, 92, "用户需求", ["六项营养目标", "偏好与排除食材"])

card(c, 321, 407, 193, 92, "食材标准化", ["名称与单位统一", "食材营养映射"])
card(c, 321, 259, 193, 92, "食谱结构化", ["食材-食谱关系", "份数与食材克数"])
card(c, 321, 111, 193, 92, "长尾与共现统计", ["食材出现频次", "真实食材搭配关系"])
down_arrow(c, 417, 404, 356)
down_arrow(c, 417, 256, 208)

core_cards = [
    (416, "食材特征表征", ["营养、类别与文本语义"]),
    (314, "长尾知识补偿", ["相似食材检索", "候选关联与证据评分"]),
    (212, "个性化食谱推荐", ["候选检索与偏好匹配", "结合营养目标排序"]),
    (110, "克数优化与营养验算", ["食材用量调整", "六项营养约束检查"]),
]
for y, title_text, body in core_cards:
    card(c, 576, y, 243, 82, title_text, body)
for y1, y2 in [(413, 399), (311, 297), (209, 195)]:
    down_arrow(c, 697, y1, y2)

card(c, 881, 407, 243, 92, "营养问答与解释", ["需求理解与知识检索", "推荐依据说明"])
card(c, 881, 259, 243, 92, "个性化食谱结果", ["候选食谱与食材用量", "营养值与达标状态"])
card(c, 881, 111, 243, 92, "质量评估报告", ["长尾覆盖与推荐质量", "营养达标与对照实验"])

for x1, x2 in [(279, 301), (534, 556), (839, 861)]:
    arrow(c, x1, 330, x2, 330)

c.setStrokeColor(HexColor("#DCE6EA"))
c.setLineWidth(1)
c.line(60, 68, 1140, 68)
label(c, 60, 39, "研究闭环", 15, NAVY)
label(c, 155, 39, "数据输入 → 数据构建 → 模型计算 → 结果输出 → 质量评估", 15, TEAL)

c.showPage()
c.save()
print(OUT)
