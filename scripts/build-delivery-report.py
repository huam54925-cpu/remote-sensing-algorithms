"""Build the dated handoff report; requires reportlab and a CJK TrueType font."""
from pathlib import Path
import re
from xml.sax.saxutils import escape
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Preformatted
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/pdf/remote-sensing-delivery-report-20260909.pdf'
pdfmetrics.registerFont(TTFont('CJK','/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf'))
navy=colors.HexColor('#142D45');teal=colors.HexColor('#087F78')
styles={
 'title':ParagraphStyle('title',fontName='CJK',fontSize=24,leading=34,textColor=navy,spaceAfter=14),
 'sub':ParagraphStyle('sub',fontName='CJK',fontSize=11,leading=18,textColor=teal,spaceAfter=15),
 'h':ParagraphStyle('h',fontName='CJK',fontSize=14,leading=23,textColor=navy,spaceBefore=13,spaceAfter=7),
 'body':ParagraphStyle('body',fontName='CJK',fontSize=10,leading=17,spaceAfter=8,wordWrap='CJK'),
 'small':ParagraphStyle('small',fontName='CJK',fontSize=8,leading=13,spaceAfter=6,wordWrap='CJK'),
 'code':ParagraphStyle('code',fontName='Courier',fontSize=7.3,leading=11,spaceAfter=8),
}
story=[]
def markup(text):
    return ''.join('<font name="Helvetica">'+escape(v)+'</font>' if v.isascii() else escape(v) for v in re.findall(r'[\x20-\x7e]+|[^\x20-\x7e]+',str(text)))
def p(text,style='body'):story.append(Paragraph(markup(text),styles[style]))
def h(text):p(text,'h')
def table(rows,widths):
 t=Table([[Paragraph(markup(v),styles['small']) for v in row] for row in rows],colWidths=widths,hAlign='LEFT')
 t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#EAF1F5')),('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,0),.8,teal),('LINEBELOW',(0,1),(-1,-1),.3,colors.HexColor('#DCE3E8')),('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
 story.append(t);story.append(Spacer(1,8))
def code(text):story.append(Preformatted(text,styles['code']))
def page(c,doc):
 c.setStrokeColor(teal);c.setLineWidth(2);c.line(44,800,551,800)
 c.setFont('CJK',8);c.setFillColor(navy);c.drawString(44,817,'遥感算法容器 | 交付与验证报告')
 c.setFont('Helvetica',8);c.drawString(44,27,'2026-09-09  |  CPU');c.drawRightString(551,27,str(doc.page));c.setFont('CJK',8);c.drawString(125,27,'合成数据功能验证')

p('遥感算法镜像\n交付与异机验证报告'.replace('\n',' / '),'title')
p('版本 0.3.0-selftest1  ·  报告日期 2026-09-09','sub')
h('结论：新版镜像已完成异机自检')
p('用户提供的 Vultr 服务器终端输出确认：新版固定 digest 镜像从 GHCR 下载成功，smoke、KMEANS、MNDWI、missing_input 四项全部通过，最终返回 PASS: MACHINE TEST。结合本机构建、回归与离线包检查，可确认本次 CPU 合成数据功能交付流程通过。')
p('该结论不代表真实遥感业务精度、GPU 算法、生产负载或漏洞合规验收。服务器完整报告文件未回传，本报告依据用户提供的终端输出记录异机结果。')
h('交付身份')
table([['项目','内容'],['镜像标签','ghcr.io/huam54925-cpu/remote-sensing-algorithms:0.3.0-selftest1'],['平台','Linux amd64；算法使用 CPU'],['GHCR digest','sha256:8f3a329de34ddbfbe69a7ec8af6467a28acf33931d4fc72115a5373022ea7836'],['Release 标签','v0.3.0-selftest1（测试版 / prerelease）'],['离线镜像','image.tar.gz；166,762,160 字节（约 167 MB）'],['离线镜像 SHA256','942bf82fb93ff4115aa4460be8daa5c6ec1cb7a74dbe95b4a6e337bdcaf20a15']],[96,411])
h('发布入口')
p('GitHub Release：','small')
p('https://github.com/huam54925-cpu/remote-sensing-algorithms/releases/tag/v0.3.0-selftest1','small')
p('已公开附件：image.tar.gz、check-host.py、README.md、SHA256SUMS。四个附件的 GitHub 服务端 SHA256 与本地一致；镜像归档已实际 docker load 并通过入口健康检查。','small')
story.append(PageBreak())
p('修改内容与验证证据','title')
h('本次实现')
table([['修改','作用'],['--self-test / --report-dir','内置 smoke、KMEANS、MNDWI 与错误输入检查；逐项 PASS/FAIL，失败返回非零退出码。'],['持久化证据','每次新建报告目录；保存 JSON/Markdown、子进程日志、输入 GeoTIFF、聚类真值、输出结果和 SHA256SUMS。'],['宿主机检查脚本','从镜像提取 check-host.py；记录系统、资源、挂载、Docker 和镜像 ID。实际运行固定到检查过的镜像 ID。'],['Dockerfile.selftest','扩展已验证旧版固定 digest；复用算法依赖。主 Dockerfile 与离线打包脚本同步支持自检。'],['文档与失败测试','补充使用说明、Vultr 记录、失败报告/重复运行不覆盖/不可写目录测试。']],[108,399])
h('本机验证')
p('容器回归：17 项发现，16 项通过，1 项宿主配置测试跳过。完整机器检查通过；报告 JSON 与全部已生成文件的 SHA256 校验通过。镜像不存在、算法失败、报告目标不可用时均验证非零退出码；算法失败仍生成 FAIL 报告。')
p('KMEANS 检查 900 个像元（899 有效、1 NoData），对合成真值和独立 sklearn 基准的 ARI 均为 1.0；验证空间信息、类型与拒绝覆盖。MNDWI 检查 0.5、-0.5、NaN 以及空间信息和类型。')
h('新版 Vultr 异机结果（用户提供）')
code('PASS: smoke\nPASS: KMEANS\nPASS: MNDWI\nPASS: missing_input\nPASS: ALL ALGORITHM CHECKS\nPASS: MACHINE TEST')
p('宿主机报告目录：/root/rs-reports/machine-6vnvooz8','small')
p('容器报告目录：/reports/selftest-723a5hyk；对应宿主机子目录：container/selftest-723a5hyk。','small')
p('新版终端输出未包含服务器具体 OS 版本、CPU、内存、磁盘及 Docker 版本，也未包含逐项耗时；不据此填造机器规格或性能数据。详细信息由服务器上的 host-report.json 和算法报告保存。','small')
story.append(PageBreak())
p('使用、验收与留档','title')
h('从 Release 离线导入并检查')
p('将 Release 的四个附件下载到同一目录。宿主机需 Docker 和 Python 3；无需登录 GHCR，也无需重新构建。')
code('sha256sum -c SHA256SUMS\ngzip -dc image.tar.gz | docker load\nIMAGE=ghcr.io/huam54925-cpu/remote-sensing-algorithms:0.3.0-selftest1\npython3 check-host.py "$IMAGE" --output-dir "$PWD/rs-reports"')
h('报告文件用途')
table([['文件','用途'],['SUMMARY.md','整台机器本次检查结论与证据路径。'],['host-report.json','宿主系统、资源、挂载、初始化/重启状态、Docker 版本、镜像 ID 与命令；属于状态快照。'],['selftest.log','镜像自检执行日志，排查运行失败。'],['container/selftest-*/report.json、report.md','逐项结论、耗时、容器环境与依赖版本。'],['commands.jsonl / GeoTIFF / truth / success.json','算法原始日志、输入样本、预期聚类真值和实际结果。'],['SHA256SUMS','算法报告目录内文件的完整性检查。']],[204,303])
h('验收边界与后续')
p('本次已完成镜像构建、自检集成、本机回归、GHCR 发布、Release 离线交付和新版 Vultr 异机自检。PASS 表示指定合成数据与接口检查通过；不等于磁盘健康、所有挂载可写或生产资源容量满足要求。')
p('真实影像精度、外部算法接入、GPU 依赖、并发性能和安全漏洞门禁仍需按实际场景单独验证。旧版安全报告保留为历史证据，本次未宣称执行新一轮安全扫描。')
h('证据来源')
p('1. reports/deployment/selftest1/：构建、回归、GHCR 推送、远端清单与拉取记录。\n2. outputs/selftest-release/machine-kzh55ys8/：本机持久化报告与数据。\n3. reports/deployment/vultr-20260909.md：用户提供的旧版及新版异机终端结果。\n4. GitHub Release API：公开状态、附件字节数与服务端摘要。','small')
p('本报告只发布功能验证与复现所需信息，不包含账户令牌或完整主机快照。','small')
OUT.parent.mkdir(parents=True,exist_ok=True)
SimpleDocTemplate(str(OUT),pagesize=A4,rightMargin=44,leftMargin=44,topMargin=58,bottomMargin=48,title='遥感算法镜像交付与异机验证报告',author='Remote Sensing Project').build(story,onFirstPage=page,onLaterPages=page)
print(OUT)
