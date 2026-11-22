"""Freeze the experiment definitions before running new comparisons."""
import json
from pathlib import Path
from itertools import product
R=Path(__file__).resolve().parents[1]
base={'transfer_seconds':180,'turnaround_seconds':180,'berth_seconds':120,'max_shift_seconds':300,'headway_deviation_seconds':300,'grid_seconds':60,'enforce_vehicle':True,'enforce_headways':True}
cases=[]
def add(name,group,**changes):
 p=base|changes
 for c in cases:
  if c['parameters']==p:
   if group not in c['groups']:c['groups'].append(group)
   return
 cases.append({'name':name,'groups':[group],'parameters':p})
add('nominal','primary')
for tau in [120,180,300]:
 for turn in [120,180,300]:
  for berth in [0,120,180]:
   add(f'joint_t{tau}_r{turn}_b{berth}','joint_sensitivity',transfer_seconds=tau,turnaround_seconds=turn,berth_seconds=berth)
for cap in [0,120]:add(f'shift_cap_{cap}','one_at_a_time',max_shift_seconds=cap)
for gap in [0,120,600]:add(f'headway_tolerance_{gap}','one_at_a_time',headway_deviation_seconds=gap)
for tau in [181,210]:add(f'readiness_boundary_{tau}','readiness_boundary',transfer_seconds=tau)
add('half_minute_grid','grid_resolution',grid_seconds=30)
add('no_vehicle_constraints','ablation',enforce_vehicle=False)
add('no_headway_constraints','ablation',enforce_headways=False)
add('no_vehicle_or_headway_constraints','ablation',enforce_vehicle=False,enforce_headways=False)
plan={
 'created_date':'2026-11-19','primary_population':'same 41 scheduled incoming trips on 2026-10-15; no new data collection or delay scenarios',
 'objective':'equal-weight mean waiting after transfer allowance; full-day onward service retained',
 'parameters_are':'declared study assumptions, not measured operating requirements',
 'primary_heuristic':{'name':'single_chronological_pass','definition':'Start from zero shifts. Visit the six original departure times in chronological order once. For the current trip, evaluate every permitted grid shift while holding the other five at their present values. Reject any full-timetable constraint violation. Adopt a change only if it strictly lowers total waiting. Among equal-cost improving changes, choose smallest absolute shift, then earlier departure. Do not revisit earlier trips.', 'starting_point_must_be_feasible':True,'no_optimum_information_used':True},
 'supplementary_heuristic':'Repeat chronological passes until a full pass has no strictly improving feasible coordinate move; report separately, never replace primary benchmark with best-performing variant.',
 'comparison_rules':['Rebuild shift domains and vehicle/headway RHS for every parameter case.','Evaluate status quo, newly reoptimized schedule, and unchanged nominal optimum separately.','Do not quote percentage improvement against an infeasible baseline.','Infeasible domains and infeasible MILPs remain explicitly infeasible, not missing observations.','Retain source files and old results unchanged; write new runs separately.','All non-stranded costs are independently evaluated using earliest eligible departure.','Exact enumeration is used when grid product <= 2000000; otherwise solver optimum is checked by independent timetable evaluation.','Solver tolerances are reported; a time limit does not count as proven optimal.','Ablations are diagnostic relaxed models, not deployment recommendations.','No parameter values are tuned after viewing new heuristic outcomes.'],
 'cases':cases}
(R/'experiments/experiment_plan.json').write_text(json.dumps(plan,indent=2)+'\n')
print('Unique cases:',len(cases))
