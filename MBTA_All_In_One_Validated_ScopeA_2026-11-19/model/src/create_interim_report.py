"""Generate the one-page interim report draft in DOCX format."""
from pathlib import Path
from docx import Document
from docx.shared import Inches,Pt,RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT,WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.style import WD_STYLE_TYPE
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

ROOT=Path(__file__).resolve().parents[1]
D=Document(); section=D.sections[0]
section.page_height=Inches(11);section.page_width=Inches(8.5)
section.left_margin=Inches(.78);section.right_margin=Inches(.78)
section.top_margin=Inches(.62);section.bottom_margin=Inches(.58)
section.header_distance=Inches(.25);section.footer_distance=Inches(.28)
styles=D.styles
normal=styles['Normal'];normal.font.name='Aptos';normal.font.size=Pt(9.5);normal.font.color.rgb=RGBColor(43,54,67)
normal.paragraph_format.space_after=Pt(4.0)
normal.paragraph_format.line_spacing=1.09
for name in ['Sect','Small']:
 if name not in styles:styles.add_style(name,WD_STYLE_TYPE.PARAGRAPH)
sect=styles['Sect'];sect.base_style=normal;sect.font.name='Aptos Display';sect.font.size=Pt(10.8);sect.font.bold=True;sect.font.color.rgb=RGBColor(16,68,106)
sect.paragraph_format.space_before=Pt(8);sect.paragraph_format.space_after=Pt(3)
small=styles['Small'];small.base_style=normal;small.font.size=Pt(8)
small.paragraph_format.space_after=Pt(2)

p=D.add_paragraph()
p.paragraph_format.space_after=Pt(2)
r=p.add_run('IMPROVING MBTA BUS TRANSFERS AT ASHMONT')
r.font.name='Aptos Display';r.font.size=Pt(15);r.font.bold=True;r.font.color.rgb=RGBColor(13,53,87)
p=D.add_paragraph();p.paragraph_format.space_after=Pt(1)
r=p.add_run('6.C57 Optimization Methods  •  Interim Progress Report  •  November 6, 2026')
r.font.size=Pt(9);r.font.color.rgb=RGBColor(70,93,113)
p=D.add_paragraph();p.paragraph_format.space_after=Pt(7)
r=p.add_run('Alex Lim  |  Yun Ji Seo  |  Luran Wang   •   Revised course deadline: Friday, November 13, 2026')
r.font.size=Pt(8.3);r.font.color.rgb=RGBColor(80,91,107)

def heading(s):D.add_paragraph(s,style='Sect')
def para(s):D.add_paragraph(s)
heading('Decision problem and study boundary')
para('We study whether small changes in Route 215 departures toward Quincy Center can improve scheduled bus transfers at Ashmont for passengers arriving on Routes 22 and 23. The MBTA planner may retime six selected departures but cannot add trips, change routes, or alter scheduled running times. Each incoming bus is treated as one potential, equally weighted transfer opportunity—not as an observed passenger count.')
heading('Historical timetable and baseline')
para('The October 15, 2026 historical GTFS archive was reconciled with the starter snapshot for this study. Between 4 and 7 p.m., the cohort has 18 Route 22 and 23 Route 23 terminal arrivals (41 opportunities), with six Route 215 departures available for adjustment. All 37 onward departures across the service day are retained, including services after 7 p.m. With an assumed three-minute boarding/transfer allowance, mean waiting after readiness is 13.51 minutes; the longest wait is 30 minutes, with no stranded opportunities.')
heading('Optimization formulation and operating assumptions')
para('We formulate a deterministic mixed-integer linear program (MILP). Binary variables select an integer-minute shift for each Route 215 trip; transfer-assignment variables choose the earliest eligible onward departure. The objective minimizes mean post-allowance waiting across 41 opportunities. Constraints preserve full-trip stop-time shifts, predecessor/successor vehicle blocks, and original departure headways within ±5 minutes. We assume a three-minute scheduled turnaround and two additional minutes when a following trip uses another Quincy Center berth; vehicle-based shift bounds tighten the original ±5-minute limit. Truly stranded opportunities would receive a 60-minute penalty, but none occur in this cohort.')
heading('Preliminary computational findings')
t=D.add_table(rows=1, cols=3);t.style='Table Grid';t.alignment=WD_TABLE_ALIGNMENT.CENTER
for c,s in zip(t.rows[0].cells,['Metric','Existing timetable','Best finite-grid timetable']):
 c.text=s
 for p in c.paragraphs:
  for r in p.runs:r.font.size=Pt(8.3);r.font.bold=True;r.font.color.rgb=RGBColor(13,53,87)
for vals in [
 ('Mean post-allowance wait','13.51 min','12.46 min (−7.76%)'),
 ('Maximum post-allowance wait','30 min','27 min'),
 ('Opportunities waiting ≤10 min','15 of 41','20 of 41')]:
 cells=t.add_row().cells
 for c,s in zip(cells,vals):
  c.text=s
  for p in c.paragraphs:
   p.paragraph_format.space_after=Pt(0)
   for r in p.runs:r.font.size=Pt(8.5)
for row in t.rows:
 for c in row.cells:c.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
p=D.add_paragraph(style='Small');p.paragraph_format.space_before=Pt(4);p.paragraph_format.space_after=Pt(0)
p.add_run('Python enumeration of 71,673 feasible timetables identified a unique optimum: shifts (−2, 0, −2, −1, +2, 0) minutes. An independent SciPy/HiGHS MILP confirms it at zero optimality gap. Julia/JuMP source is prepared but has not yet been executed in Julia.')
heading('Next steps, interpretation, and limits')
para('Next we will run the JuMP solver and compare it against the exhaustive result, implement a simple feasible heuristic, and test transfer-time and vehicle-turnaround sensitivity. Scope B will be considered only after date-specific delay records and vehicle availability are validated. The analysis is conditional on stated allowances and equal opportunity weights; it is not a passenger-demand estimate or an MBTA-certified operating timetable.')
p=D.add_paragraph(style='Small');p.paragraph_format.space_before=Pt(4)
r=p.add_run('Sources: MBTA historical GTFS feed (20261014.zip; archive index: cdn.mbta.com/archive/archived_feeds.txt); MBTA GTFS documentation; internally reconciled October 15 schedule and vehicle-block tables.')
r.font.color.rgb=RGBColor(93,107,119)

# unobtrusive footer
footer=section.footer.paragraphs[0]
footer.alignment=WD_ALIGN_PARAGRAPH.RIGHT
r=footer.add_run('Team review draft  •  1 page')
r.font.size=Pt(7);r.font.color.rgb=RGBColor(123,135,146)

path=ROOT/'Interim_Report_Draft_2026-11-06.docx'
D.save(path);print(path)
