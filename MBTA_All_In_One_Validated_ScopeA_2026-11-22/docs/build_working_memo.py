"""Render a six-page working review memo; not a final submission report."""
from pathlib import Path
from docx import Document
from docx.shared import Inches,Pt,RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
ROOT=Path(__file__).resolve().parents[1]
d=Document();s=d.sections[0]
s.page_width=Inches(8.5);s.page_height=Inches(11);s.left_margin=Inches(.75);s.right_margin=Inches(.75);s.top_margin=Inches(.62);s.bottom_margin=Inches(.62);s.header_distance=Inches(.2);s.footer_distance=Inches(.25)
normal=d.styles['Normal'];normal.font.name='Calibri';normal.font.size=Pt(10.5);normal.paragraph_format.space_after=Pt(6);normal.paragraph_format.line_spacing=1.08
for name,sz in [('Title',23),('Heading 1',17),('Heading 2',12)]:
 st=d.styles[name];st.font.name='Calibri';st.font.size=Pt(sz);st.font.color.rgb=RGBColor.from_string('183F54');st.paragraph_format.space_after=Pt(7);st.paragraph_format.space_before=Pt(7);st.paragraph_format.keep_with_next=True
footer=s.footer.paragraphs[0];footer.alignment=WD_ALIGN_PARAGRAPH.RIGHT
r=footer.add_run('6.C57 | Working evidence, not final report | ');r.font.size=Pt(8)
fld=OxmlElement('w:fldSimple');fld.set(qn('w:instr'),'PAGE');footer._p.append(fld)
header=s.header.paragraphs[0];r=header.add_run('ASHMONT BUS TIMETABLE COORDINATION  /  SCOPE A');r.font.size=Pt(8);r.font.color.rgb=RGBColor.from_string('61747F')
def p(t):return d.add_paragraph(t)
def h(t):d.add_paragraph(t,style='Heading 2')
def page(title):d.add_page_break();d.add_paragraph(title,style='Heading 1')
def table(heads,rows,widths=None):
 t=d.add_table(rows=1,cols=len(heads));t.style='Light Shading Accent 1'
 for c,txt in zip(t.rows[0].cells,heads):c.text=str(txt)
 for vals in rows:
  cells=t.add_row().cells
  for c,txt in zip(cells,vals):c.text=str(txt)
 for i,row in enumerate(t.rows):
  row._tr.get_or_add_trPr().append(OxmlElement('w:cantSplit'))
  for c in row.cells:
   for pp in c.paragraphs:
    pp.paragraph_format.space_after=Pt(3);pp.paragraph_format.space_before=Pt(3)
    for rr in pp.runs:rr.font.size=Pt(9.5);rr.bold=i==0
 return t

d.add_paragraph('Baseline protected.\nExperiments completed.',style='Title')
p('Validation and experiment working memo | November 19, 2026')
p('Alex Lim · Yun Ji Seo · Luran Wang')
p('The previous scheduled-case result reproduces, but the new comparisons add two important qualifications: the simple heuristic ties the optimizer, and the selected timetable is sensitive to the passenger transfer allowance.')
h('What is complete — and what is not')
table(['Workstream','Status'],[
('Raw-archive rebuild and baseline reproduction','Completed; eight matching input files'),
('Python optimization and feasible heuristic','Completed; nominal result reproduced'),
('Sensitivity and diagnostic experiments','38 cases: 32 optimal, six infeasible'),
('Tests and independent checks','12 original + 34 new tests; 5,740 row checks'),
('Julia/JuMP execution','PENDING: no runtime; official download failed'),
('Scope B and final presentation deliverables','Not undertaken in this step')])
h('Nominal comparison: three-minute transfer allowance')
table(['Method','Mean wait','Maximum','Wait ≤10 min'],[
('Existing timetable','13.5122 min','30 min','15/41'),
('Single-pass heuristic','12.4634 min','27 min','20/41'),
('MILP / exhaustive optimum','12.4634 min','27 min','20/41')])
p('The reduction is 1.0488 minutes per equally weighted incoming-trip opportunity (7.7617%). It is not a ridership-weighted passenger benefit. No opportunity is stranded. The result is exact on the adopted one-minute grid, not for unrestricted continuous departure times.')
h('Two conclusions to carry into team review')
p('First, do not claim that the MILP improves on the simple rule: no such advantage appears in these tested instances. Second, distinguish reoptimizing for a changed assumption from applying the same previously selected timetable under that changed assumption. The latter can perform worse than the original schedule.')

page('1  |  Preserve and verify the research foundation')
h('Source evidence')
p('All eight uploaded ZIPs passed integrity checks. The October 15 historical archive was reprocessed with the adopted configuration. Incoming arrivals, outgoing departures, vehicle links, headway limits, block endpoints, selected stop trajectories, baseline connections and feed metadata match the saved model inputs byte for byte. Original archives and original calculation records remain unchanged.')
table(['Study element','Verified input'],[
('Selected incoming opportunities','18 Route 22 + 23 Route 23 = 41'),
('Onward departures','37 for the full service day; six adjustable'),
('Late onward service','Ten departures at/after 19:00 retained'),
('Vehicle and headway pairs','12 changed-trip links; seven spacing pairs'),
('Complete selected trip trajectories','300 stop-time rows'),
('Affected block chronology','33 neighboring pairs retain no time overlaps')])
h('Model review')
p('Binary choices select one allowed departure shift per selected trip. Transfers can only use chosen, catchable departures. For a fixed timetable, minimizing the nonnegative connection costs selects an earliest eligible departure. Whole-trip shifts preserve running and dwell times; vehicle and spacing rules include fixed neighboring trips outside the passenger study window.')
p('A fixed 19:20 onward bus covers the latest readiness in every modeled sensitivity case. The adopted 60-minute stranded cost is therefore unused here. It must never become an optional substitute for a long but available connection.')
h('Assumptions kept visible')
p('The nominal case uses three minutes for passenger transfer readiness, three minutes of scheduled turnaround, and two additional minutes for a different Quincy berth. Shifts and headway deviations are limited to five minutes, with tighter vehicle-derived shift bounds. These are study assumptions, not MBTA-certified operating requirements.')
h('Reproduction and Julia source status')
p('Fresh exhaustive enumeration and SciPy/HiGHS reproduce 30,660 total waiting seconds, or 12.4634 minutes per opportunity. The solver objective equals its bound with zero reported gap. The nominal optimum is unique among 71,673 feasible whole-minute timetables.')
p('The reviewed Julia source now includes the supplied parsing/status patch, baseline output and a zero relative-gap request. A separate diff preserves the change history. The code has not been executed in Julia: Python success does not substitute for that test. The original named-package setup was changed to an application dependency environment; no Manifest or installation success was invented.')

page('2  |  A credible benchmark, not just another solver')
h('Simple feasible rule, fixed before the new runs')
p('Start with the original timetable. Visit departures once in chronological order. At each departure, examine every allowed grid shift while holding the other five at their current values. Reject full-timetable vehicle/headway violations. Accept a change only if total waiting decreases. Break improving ties by smaller absolute movement, then earlier departure. Do not revisit earlier trips or consult the optimum.')
table(['Original departure','Selected change','New departure'],[
('16:20','−2 minutes','16:18'),('16:50','Unchanged','16:50'),('17:20','−2 minutes','17:18'),('17:50','−1 minute','17:49'),('18:20','+2 minutes','18:22'),('18:52','Unchanged','18:52')])
p('The rule reaches exactly the same nominal timetable as the MILP after 38 timetable evaluations, including the initial and repeated/current candidates. A supplementary repeated-pass version makes no further improvement. Across all 32 feasible tested cases, the primary heuristic matches the optimum; this does not establish that it always does so in other datasets or models.')
d.add_picture(str(ROOT/'figures/01_method_comparison.png'),width=Inches(6.8))
p('Interpretation: the model certifies the best achievable objective under stated rules and supports consistent diagnostics. It does not demonstrate extra timetable quality beyond this simple rule on the tested cases. That is a finding to report, not a reason to select a weaker benchmark.')

page('3  |  Reoptimization is not the same as robustness')
p('The suite contains a 27-case transfer/turnaround/berth crossing, plus shift-cap, headway, readiness-boundary, finer-grid and constraint-removal tests. Every case regenerates its domains and operating bounds. The original cohort and onward schedule remain fixed.')
h('Change only the passenger transfer allowance')
table(['Allowance','Existing timetable','Reoptimized','Keep 3-min optimum'],[
('2 minutes','14.5122 min','12.7073 min','13.4634 min'),
('3 minutes','13.5122 min','12.4634 min','12.4634 min'),
('5 minutes','13.6585 min','11.8537 min','15.6829 min')])
p('The last column keeps the six shifts unchanged. At five minutes it is worse than the original schedule, although a newly optimized timetable still improves on the original. All entries measure waiting after the allowance; add that allowance for total elapsed transfer time.')
d.add_picture(str(ROOT/'figures/02_transfer_allowance_stress_test.png'),width=Inches(6.8))
h('Exact-readiness boundary check')
p('Seven nominal-optimized opportunities board exactly at their readiness time. Increasing the allowance from 180 to 181 seconds changes those connections: the unchanged optimum averages 17.6663 minutes, compared with 14.9102 for the original schedule. Reoptimizing yields 13.0809. This is a deterministic threshold diagnostic, not a measured delay forecast or a probability of real-world failure.')

page('4  |  Operational trade-offs and infeasible assumptions')
h('Stricter buffers can invalidate the entire modeled timetable')
p('With a five-minute turnaround and two additional minutes for berth movement, the 16:20 vehicle has no feasible shift: its five-minute preceding gap requires x ≥ 0, while its six-minute following gap requires x ≤ −1 minute. Three minutes of berth movement is even stricter. These six cases across the three passenger allowances are structurally infeasible; they are not assigned optimization gains.')
h('Selected one-at-a-time results')
table(['Change from nominal','Best mean wait','Interpretation'],[
('No departure shifts','13.5122 min','Reproduces status quo'),
('Only ±2-minute departure shifts','12.4634 min','Keeps full nominal benefit'),
('No headway changes','13.5122 min','Fixed boundaries force zero shifts'),
('Headway tolerance ±2 minutes','12.5122 min','Small loss of improvement'),
('Headway tolerance ±10 minutes','12.3902 min','Only 0.0732 min extra benefit'),
('30-second departure grid','12.4634 min','No improvement in this test')])
p('At the nominal three-minute turnaround, berth movement assumptions of zero, two and three minutes yield the same optimal timetable, although their feasible sets differ. At two-minute turnaround and two-minute berth movement, mean waiting can reach 12.1707 minutes. These are conditional parameter experiments, not operational permissions.')
h('What do the constraints contribute?')
table(['Diagnostic relaxed model','Best mean wait','Violation under full rules'],[
('Without vehicle constraints','11.7805 min','Three vehicle links fail'),
('Without headway constraints','12.3902 min','A 36-minute gap exceeds 35'),
('Without either family','11.7805 min','Three vehicle links fail')])
p('These relaxed solutions are not implementable recommendations. They explain the benefit sacrificed to preserve the modeled rules. No headway bound is tight at the nominal integer optimum, yet removing that constraint family permits a better alternative; inactive-at-the-solution does not mean globally irrelevant.')
h('Coverage and proof')
p('All 32 feasible MILPs report optimality with zero gap. Exhaustive enumeration independently agrees in 31 cases. The half-minute grid is solver-verified and separately evaluated, but its full grid is larger than the preset enumeration cap. Neither test proves an unrestricted continuous-time optimum.')

page('5  |  Who benefits, and what should the team do next?')
table(['Incoming route','Original mean','Optimized mean','Net waiting saved'],[
('Route 22: 18 opportunities','12.8889 min','12.5000 min','7 min'),
('Route 23: 23 opportunities','14.0000 min','12.4348 min','36 min')])
d.add_picture(str(ROOT/'figures/04_individual_transfer_changes.png'),width=Inches(6.8))
p('Eighteen opportunities improve, seven worsen by two minutes each, and 16 are unchanged. One Route 23 opportunity saves 30 minutes, accounting for 30 of the 43 net minutes saved. These sums use equal incoming-trip weights, not measured passenger volumes.')
h('Remaining verification item: a real Julia run')
p('Run model/src/setup_and_run_reviewed.ps1 on Windows, or the matching .sh script on macOS/Linux with Julia installed. Keep the generated Manifest, package/environment information, solver summary, baseline and optimized CSVs. Then run validation/verify_julia_outputs.py. It refuses to certify a run without actual Julia outputs.')
h('Current delivery boundary')
p('The package includes all eight original archives, the unchanged November 12 interim report, complete nominal inputs/code, new experiment code, case results, four figures and audit records. The 12 original and 34 new tests passed; 5,740 rows received an independent earliest-connection check. Scope B and final report/slides/video were not undertaken.')
h('Evidence and limitations')
p('Sources: uploaded historical GTFS and project archives; exact hashes and locations are in validation/source_zip_hashes.json. Official Julia, JuMP and Pkg documentation was used only for setup and solution-status handling (docs/source_register.json). No new observations replace the uploaded data. This is AI-assisted working analysis for team review, not a final student submission or MBTA-approved timetable.')
d.core_properties.title='Scope A Validation and Experiment Working Memo'
d.core_properties.subject='November 19, 2026; Python verified, Julia execution pending'
# The filename follows the working release; the memo retains its November 19 analysis date.
d.save(ROOT/'docs/Scope_A_Validation_Experiments_2026-11-22.docx')
print(ROOT/'docs/Scope_A_Validation_Experiments_2026-11-22.docx')
