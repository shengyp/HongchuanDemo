from pathlib import Path
from docx import Document
from docx.shared import Cm,Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from PIL import Image

root=Path(__file__).resolve().parents[1]
docs=root/'docs'
shots=docs/'功能模块截图_2026-11-02'
tmp=docs/'_soft_copyright_render'
tmp.mkdir(exist_ok=True)
out=docs/'长尾知识补偿驱动的个性化营养食谱系统V1.0_软著使用说明书.docx'
name='长尾知识补偿驱动的个性化营养食谱系统 V1.0'
d=Document()
sec=d.sections[0]
sec.page_width,sec.page_height=Cm(21),Cm(29.7)
sec.top_margin,sec.bottom_margin=Cm(2.4),Cm(2.2)
sec.left_margin,sec.right_margin=Cm(2.7),Cm(2.7)
sec.header_distance=Cm(1.1)
normal=d.styles['Normal']
normal.font.name='宋体';normal._element.rPr.rFonts.set(qn('w:eastAsia'),'宋体');normal.font.size=Pt(10.5)
normal.paragraph_format.line_spacing=1.35
for sty in ('Heading 1','Heading 2'):
 s=d.styles[sty];s.font.name='黑体';s._element.rPr.rFonts.set(qn('w:eastAsia'),'黑体');s.font.color.rgb=None
hp=sec.header.paragraphs[0];hp.alignment=WD_ALIGN_PARAGRAPH.RIGHT
r=hp.add_run(name+'    ');r.font.name='宋体';r.font.size=Pt(8)
fld=OxmlElement('w:fldSimple');fld.set(qn('w:instr'),'PAGE');hp._p.append(fld)
def p(t='',indent=True):
 x=d.add_paragraph(t);x.paragraph_format.space_after=Pt(7);x.paragraph_format.line_spacing=1.35
 if indent:x.paragraph_format.first_line_indent=Pt(21)
 return x
def h(t,l=1):
 x=d.add_paragraph(t,style='Heading '+str(l));x.paragraph_format.space_before=Pt(12 if l==1 else 7);x.paragraph_format.space_after=Pt(7);x.paragraph_format.keep_with_next=True
 return x
def br():d.add_page_break()
def steps(items):
 for i,t in enumerate(items,1):
  x=p(str(i)+'．'+t,False);x.paragraph_format.left_indent=Cm(.55);x.paragraph_format.first_line_indent=Cm(-.55)
def pic(file,caption,height=850):
 source=shots/file
 with Image.open(source) as im:
  im=im.convert('RGB');im=im.crop((0,0,im.width,min(max(height,1100),im.height)))
  target=tmp/('crop_'+file);im.save(target,quality=92)
 x=d.add_paragraph();x.alignment=WD_ALIGN_PARAGRAPH.CENTER;x.paragraph_format.space_before=Pt(7)
 x.add_run().add_picture(str(target),width=Cm(15.5))
 x=p(caption,False);x.alignment=WD_ALIGN_PARAGRAPH.CENTER
 for r in x.runs:r.font.size=Pt(9)
def note(t):p('说明：'+t)
for _ in range(4):p('',False)
x=d.add_paragraph();x.alignment=WD_ALIGN_PARAGRAPH.CENTER
r=x.add_run('长尾知识补偿驱动的\n个性化营养食谱系统');r.font.name='黑体';r.font.size=Pt(23)
x=d.add_paragraph();x.alignment=WD_ALIGN_PARAGRAPH.CENTER;r=x.add_run('V1.0 使用说明书');r.font.name='黑体';r.font.size=Pt(20)
for _ in range(4):p('',False)
x=p('文档类型：软件使用说明书',False);x.alignment=WD_ALIGN_PARAGRAPH.CENTER
x=p('编写日期：2026 年 11 月',False);x.alignment=WD_ALIGN_PARAGRAPH.CENTER
br();h('目 录')
for t in ['第1章  概述','第2章  软件主要功能与技术特点','第3章  软件安装与配置','第4章  软件架构与核心业务流程','第5章  软件功能界面与操作','    5.1  数据管理','    5.2  知识图谱可视化','    5.3  食材关联发现','    5.4  DIY 食谱与评估','    5.5  营养食谱问答','第6章  数据说明与使用边界']:
 p(t,False)
p('本说明书依据 V1.0 项目代码与 2026 年 11 月 2 日的界面截图编写。图片展示页面入口，内容以软件实际运行状态为准。')
br();h('第1章  概述');h('1.1  软件简介',2)
p(name+'是一套在本地浏览器使用的营养食谱研究与功能演示软件。系统围绕食材、食谱和知识关系组织数据，提供数据导入、图谱浏览、搭配发现、营养计算、自制食谱评估及对话问答功能。')
p('软件将食材营养数据、真实食谱记录与用户上传的知识三元组分开管理。用户按用途选择数据集，页面分别展示计算结果、原始记录和待核查候选，避免混淆营养数值与食谱证据。')
h('1.2  适用对象',2)
p('本软件适用于营养食谱数据整理、食材关系展示、教学演示及方法原型验证。默认营养数据和部分模型选项具有演示性质。')
h('1.3  软件组成',2)
for t in ['数据管理：上传知识三元组与营养数据，查看来源和 Food.com 真实食谱索引。','知识图谱可视化：按数据集、实体及关系检索局部图谱。','食材关联发现：查看搭配候选，推荐食谱并调整食材用量。','DIY 食谱与评估：输入自制食谱，查看证据与营养评分。','营养食谱问答：管理对话、选择模型并查看回答依据。']:p('• '+t,False)
h('第2章  软件主要功能与技术特点');h('2.1  软件主要功能',2)
p('数据管理支持导入 CSV 或 JSON 格式的知识三元组，为数据集命名、选择、重命名和删除；默认 Food.com 数据集保留。营养数据管理支持导入食材每 100 g 营养值及食谱组成。')
p('知识图谱可视化可搜索实体并按类型、关系及邻居层数筛选。食材关联发现可创建搭配发现任务、按营养目标与偏好推荐食谱、对已有食谱调整食材克数。')
p('DIY 食谱与评估结合当前营养表和 Food.com 已观察食材共现，分别给出营养匹配和搭配证据分。问答页提供左侧对话记录、模型选择、消息区及回答依据区。')
h('2.2  软件技术特点',2)
for t in ['前端通过 HTTP 接口与 Python 本地服务通信。','真实食谱关系、上传三元组和推断候选分别展示，并保留来源。','每份营养值根据食材每 100 g 数值、用量和食谱份数计算。','知识三元组、Food.com 索引和对话记录保存在本机。','未接入的模型选项明确标为界面演示，不宣称参与计算。']:p('• '+t,False)
h('第3章  软件安装与配置');h('3.1  软硬件环境',2)
p('客户端使用支持现代网页标准的桌面浏览器。构建前端需要 Node.js 20 及以上版本和 pnpm；运行本地服务需要 Python 3.10 及以上版本。前端主要使用 Vue 3、TypeScript、Vite 和 Vuetify；后端使用 Python 与 SQLite。')
p('软件可在普通个人计算机上运行。实际存储空间取决于导入的数据规模；外部大模型需要相应服务另行提供接口与计算资源。')
h('3.2  运行步骤',2)
steps(['进入 frontend 目录，运行 pnpm install 安装依赖。','运行 pnpm run build，生成前端静态文件。','返回项目根目录，运行 python app.py 启动本地服务。','在本机浏览器打开 http://127.0.0.1:8765；如已设置 NUTRI_PORT，则使用对应端口。'])
note('页面直接进入体验工作台。当前开发环境可能使用其他端口，以实际启动地址为准。')
h('3.3  数据与模型准备',2)
p('首次打开时可使用内置演示营养数据和默认 Food.com 索引。用户可上传自己的营养数据及知识三元组。知识检索问答无需配置外部大模型；第三方模型需接入相应服务后才能生成回答。')
h('第4章  软件架构与核心业务流程');h('4.1  软件架构',2)
p('前端 Vue 组件实现五个主模块和各功能页面。Python 服务负责数据验证、关系查询、营养计算、候选排序与问答接口。SQLite 保存三元组、食谱索引和部分会话数据，JSON 文件提供演示及导入营养数据。')
table=d.add_table(rows=1,cols=3);table.style='Table Grid'
for c,t in zip(table.rows[0].cells,['层次','组成','作用']):c.text=t
for row in [('界面层','Vue 3、Vuetify、TypeScript','模块导航、表单与结果展示'),('服务层','Python HTTP 接口','校验、检索、计算与任务处理'),('数据层','SQLite、JSON、CSV','保存索引、关系、会话与导入数据')]:
 for c,t in zip(table.add_row().cells,row):c.text=t
h('4.2  核心业务流程',2)
steps(['选择相应数据集，并输入食材、关系、食谱或营养目标。','服务按数据类型读取营养值、食谱组成或知识三元组，执行检索和校验。','页面展示已观察记录、候选排序、营养计算或问答依据，并标注来源。','按结果调整条件；可在相应页面保存任务或对话。'])
h('4.3  数据集与证据流向',2)
p('知识三元组上传后按数据集保存，图谱可视化与搭配发现任务读取同一数据集中的实体和关系。Food.com 作为默认食谱证据索引，记录原始食谱与食材共现，不给关系补充虚构置信度。营养计算读取另行选择的食材营养表，因此从 Food.com 检索到的搭配不会自动成为营养数值。')
p('在 DIY 食谱评分中，系统按食材名称或已列明的映射查找真实食谱中的共现，再按所选营养表计算六项指标。两类结果分别展示，用户可追溯食谱依据，也可检查克数和目标偏差。关联发现生成的候选关系保留在任务结果中，不会覆盖已观察的原始数据。')
h('4.4  异常处理与结果标识',2)
p('输入文件缺少必填字段、数值越界或引用了不存在的食材时，系统拒绝导入并给出错误提示。创建任务时如目标实体或关系不符合当前数据集，也应按页面提示重新选择。营养目标无法全部满足时，页面显示最接近的方案并标记未全部达标，不把近似结果显示为达标。')
p('展示型模型选项与真实计算功能使用不同提示。关联发现的模型下拉项目前仅记录用户的演示选择；营养问答的未接入模型仅保存提问。用户应根据界面标识判断结果是否由知识检索、本地规则或已配置的外部模型实际生成。')
# Chapter 5 begins with the first function page
pages=[
('5.1  数据管理','5.1.1  不确定知识管理','上传和查看带置信度的知识三元组。页面提供上传区、数据集列表、图谱概览、统计与三元组明细。默认 Food.com 数据集展示真实食谱和食材关系。',['选择 CSV 或 JSON 文件，输入数据集名称与来源。','点击“上传并构建图谱”，在列表中选择该数据集。','查看关系明细，按需重命名或删除用户上传的数据集。'],'CSV 至少包含 head、relation、tail、confidence。默认 Food.com 不可删除，也不提供关系置信度。','01-01_数据管理_知识数据集.jpg','图 5-1  不确定知识管理页面',900),
(None,'5.1.2  营养数据管理','营养数据管理用于导入食材营养表与食谱组成。支持 JSON 或两张 CSV 表，并可在演示数据与已导入数据之间选择。',['按页面示例准备食材营养表和食谱组成文件。','选择文件并导入，按错误提示修正不合法字段。','切换到导入的数据集，查看食材、食谱和汇总信息。'],'营养值按每 100 g 记录；克数按整道食谱填写，系统按份数换算。','01-02_数据管理_营养数据.jpg','图 5-2  营养数据管理页面',850),
(None,'5.1.3  数据来源说明','数据来源说明页解释默认数据、用户导入数据以及不同数据类型的用途。用户可区分 Food.com 真实食谱索引和用于数值计算的营养表。',['在“数据管理”下选择“数据来源说明”。','阅读数据源名称、内容与适用功能。','正式计算前，导入并核验食材营养数据。'],None,'01-03_数据管理_数据来源.jpg','图 5-3  数据来源说明页面',850),
(None,'5.1.4  真实食谱数据','真实食谱数据页展示 Food.com 食谱索引及统计。可搜索食谱或食材，查看原始食谱中的食材组成和出现情况。',['打开“真实食谱数据”，查看统计摘要。','输入食谱名或食材名检索并选择结果。','查看食谱食材与来源记录。'],'Food.com 原始记录不等同于完整的食材克数和营养表。','01-04_数据管理_真实食谱.jpg','图 5-4  真实食谱数据页面',850),
('5.2  知识图谱可视化',None,'该模块把食材、食谱或上传实体及其关系列为可交互局部图谱。搜索与筛选条件作用于当前选择的数据集。',['选择 Food.com 或上传数据集，输入实体名称并设置筛选条件。','点击探索按钮生成局部图谱，可切换布局、缩放或重置。','点击节点或关系查看邻接信息、来源和证据。'],'Food.com 关系来自原始食谱组成；上传三元组保留用户提供的置信度。','02_知识图谱可视化.jpg','图 5-5  知识图谱可视化页面',850),
('5.3  食材关联发现','5.3.1  发现食材搭配','选择数据集和目标实体，查看已有搭配及待核查候选。对上传的知识三元组，可创建发现任务并选择待预测关系。',['选择 Food.com 或已上传数据集。','创建任务时填写任务名、目标实体、待预测关系和模型选项。','查看候选排序与支持它的已观察关系和原文证据。'],'GTransE、UKGE 等模型选项仅作前端演示；当前候选仍按共享邻居和已观察关系置信度排序。','03-01_食材关联发现_搭配发现.jpg','图 5-6  食材搭配发现页面',850),
(None,'5.3.2  个性化食谱推荐','根据单餐营养目标、偏好与排除食材，对所选营养数据集中的食谱排序。结果展示每份营养值和匹配依据。',['选择营养计算数据集。','填写六项营养目标，设置偏好与排除食材。','点击“生成推荐”，查看食谱组成、分数与营养结果。'],'推荐分数只表示当前条件下的排序，不代表医学适用性。','03-02_食材关联发现_食谱推荐.jpg','图 5-7  个性化食谱推荐页面',800),
(None,'5.3.3  调整食材用量','以已有食谱为基础调整食材克数，使每份营养值尽量接近用户输入的目标，逐项显示数值与偏差。',['选择营养数据集和基础食谱。','填写六项营养目标，点击“生成并验算”。','查看建议克数及是否达标；必要时调整目标重新计算。'],'未找到全部达标方案时，页面显示最接近方案并明确标记。','03-03_食材关联发现_用量调整.jpg','图 5-8  调整食材用量页面',800),
('5.4  DIY 食谱与评估','5.4.1  DIY 食谱评分','输入食材、用量和份数后，分别计算营养目标匹配分和真实食谱搭配证据支持分。前者依据营养表，后者参考 Food.com 已观察共现。',['选择营养计算数据集与 Food.com 证据数据集。','输入至少两种食材、用量、份数及目标。','点击“查找相关食谱并评分”，查看分数、逐项验算和依据。'],'证据支持分不是经过校准的概率，也不表示食用安全性。','04-01_DIY食谱与评估_食谱评分.jpg','图 5-9  DIY 食谱评分页面',800),
(None,'5.4.2  食谱效果对比','展示原搭配、少见食材建议与营养结果的对比界面流程。当前页面带有“界面演示”标识。',['打开“食谱效果对比”。','查看示例条件、指标和结果。','结合原始搭配与新增建议的证据说明理解展示方式。'],'示例结果不是已完成的真实实验结论。','04-02_DIY食谱与评估_效果对比.jpg','图 5-10  食谱效果对比页面',800),
('5.5  营养食谱问答',None,'问答页采用左侧对话历史、中间消息区、右侧依据区。可新建、搜索、切换和删除本地对话，并选择知识检索或页面列出的大模型。',['点击“新建对话”，选择本轮使用的模型选项。','输入食材搭配、营养目标或食谱问题并发送。','从左侧打开历史对话，在右侧查看检索依据。'],'知识检索可用；未接入的其他模型选项仅作前端展示，只保存提问，不生成该模型回答。问答不要求选择数据集。','05_营养食谱问答.jpg','图 5-11  营养食谱问答页面',800),
]
for chapter,title,desc,actions,warning,file,caption,height in pages:
 br()
 if chapter=='5.1  数据管理':h('第5章  软件功能界面与操作')
 if chapter:h(chapter)
 if title:h(title,2)
 p(desc);steps(actions)
 if warning:note(warning)
 pic(file,caption,height)
br();h('第6章  数据说明与使用边界');h('6.1  数据类型与来源',2)
p('营养计算数据包含食材每 100 g 的能量、蛋白质、脂肪、碳水、膳食纤维及钠；食谱组成包含克数和份数。Food.com 索引用于展示原始食谱及共现搭配。用户上传的知识三元组包含头实体、关系、尾实体与置信度，可附证据和来源。')
h('6.2  结果解释',2)
p('营养值来自所选营养表。Food.com 的已观察搭配表示原始食谱中共同出现，不代表适合所有人。关联发现候选仅供核查，不写入真实食谱记录。推荐、用量调整与 DIY 评分均是当前数据条件下的计算结果。')
h('6.3  演示功能',2)
p('默认演示营养数据、效果对比页面、关联发现页的链接模型选择和问答页未接入的大模型选择均具有演示属性。外部模型训练、第三方数据授权与真实营养数据核验不属于当前 V1.0 的已实现功能。')
h('6.4  使用提示',2)
p('正式分析前应核对数据来源、单位、食材名称映射和份数。涉及健康管理的实际应用，应由具备相应专业资质的人员核验数据与结论。')
h('6.5  数据校验与记录',2)
p('知识三元组导入时校验字段和置信度范围；营养数据导入时校验食材标识、数值、份数与克数。导入失败时，用户应根据页面提示检查文件格式、列名及引用关系，然后重新提交。系统保留已上传数据集的显示名称与来源信息，方便在后续图谱和发现任务中选择。')
p('问答记录在本机按对话保存。用户可以搜索、重新打开或删除记录。需要修改问题时，可新建对话并重新发送；已生成的回答应结合右侧依据区与数据来源核对。使用外部模型时，只有完成服务端配置并确认实际调用结果后，才能将其输出视为该模型的回答。')
d.core_properties.title=name+' 使用说明书'
d.core_properties.subject='计算机软件著作权登记软件文档草稿'
d.save(out)
print(out)





