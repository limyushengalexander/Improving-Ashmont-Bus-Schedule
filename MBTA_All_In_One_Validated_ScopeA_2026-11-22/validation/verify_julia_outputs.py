"""Run AFTER executing the reviewed Julia source. Never fakes a Julia pass."""
from pathlib import Path
import json,re
import pandas as pd
import numpy as np
ROOT=Path(__file__).resolve().parents[1];O=ROOT/'model/results';I=ROOT/'model/inputs'
required=['jump_solver_summary.txt','jump_baseline_connections.csv','jump_optimized_connections.csv','jump_shift_schedule.csv','jump_selected_trip_stop_times.csv']
missing=[p for p in required if not (O/p).is_file()]
if missing:raise SystemExit('NOT VERIFIED: required actual Julia outputs missing: '+', '.join(missing))
summary=(O/'jump_solver_summary.txt').read_text()
assert re.search(r'termination_status\s*[:=]\s*OPTIMAL\b',summary),'Julia solver did not report OPTIMAL'
assert re.search(r'primal_status\s*[:=]\s*FEASIBLE_POINT\b',summary),'No feasible primal certificate'
for filename,ref_filename,isbase in [('jump_baseline_connections.csv','baseline_connections.csv',True),('jump_optimized_connections.csv','optimized_connections.csv',False)]:
 a=pd.read_csv(O/filename,dtype={'source_trip_id':str,'destination_trip_id':str})
 b=pd.read_csv((I if isbase else O)/ref_filename,dtype={'incoming_trip_id':str,'trip_id':str,'outgoing_trip_id':str,'caught_trip_id':str})
 assert len(a)==len(b)==41 and a.opportunity_id.is_unique and b.opportunity_id.is_unique
 join=a.merge(b,on='opportunity_id',validate='one_to_one')
 assert np.array_equal(join.wait_seconds,join.platform_wait_sec)
 assert np.array_equal(join.destination_trip_id,join.outgoing_trip_id if isbase else join.caught_trip_id)
 assert join.served.all()
x=pd.read_csv(O/'jump_shift_schedule.csv');expected=pd.read_csv(O/'recommended_departure_shifts.csv')
x=x.merge(expected,on='trip_id',validate='one_to_one')
assert np.array_equal(x.shift_minutes_x,x.shift_minutes_y)
# Independently recheck full-trip timing and all selected-trip constraints.
import sys
sys.path.insert(0,str(ROOT/'experiments'))
from scope_a_experiments import Inputs,Parameters
D=Inputs();shift_by_id={str(j):int(k)*60 for j,k in zip(x.trip_id,x.shift_minutes_x)}
assert D.feasible([shift_by_id[j] for j in D.ids],Parameters())
original=pd.read_csv(I/'selected_trip_stop_times.csv',dtype={'trip_id':str})
shifted=pd.read_csv(O/'jump_selected_trip_stop_times.csv',dtype={'trip_id':str})
assert len(original)==len(shifted)==300
check=original.merge(shifted,on=['trip_id','stop_sequence'],suffixes=('_orig','_jump'),validate='one_to_one')
def clock_seconds(t):
    h,m,s=map(int,str(t).split(':'));return h*3600+m*60+s
for rr in check.itertuples():
    delta=shift_by_id[rr.trip_id]
    assert clock_seconds(rr.optimized_arrival_time)==clock_seconds(rr.arrival_time_orig)+delta
    assert clock_seconds(rr.optimized_departure_time)==clock_seconds(rr.departure_time_orig)+delta
ref=json.loads((O/'enumeration_results.json').read_text())
objective=re.search(r'objective_value\s*[:=]\s*([-+0-9.eE]+)',summary)
assert objective and abs(float(objective.group(1))-ref['best']['mean_platform_wait_min'])<1e-4
status={'status':'JULIA_OUTPUTS_VERIFIED','solver_summary':'OPTIMAL / FEASIBLE_POINT','baseline_41_rows_match':True,'optimized_41_rows_match':True,'six_shifts_match':True,'all_300_stop_times_match':True,'vehicle_and_headway_checks_pass':True,'note':'Only run after actual Julia execution; source code and numeric inputs still require team review.'}
(ROOT/'validation/julia_outputs_verification.json').write_text(json.dumps(status,indent=2)+'\n')
print(json.dumps(status,indent=2))
