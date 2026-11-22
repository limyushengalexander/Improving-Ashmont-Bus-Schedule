"""Create reviewer tables and independent timetable/trajectory checks."""
from pathlib import Path
import json, hashlib, sys
import numpy as np
import pandas as pd
from scope_a_experiments import Inputs, Parameters, ROOT

D=Inputs();p=Parameters();R=ROOT/'results';s=pd.read_csv(R/'experiment_summary.csv')
x=tuple(json.loads(s.loc[s.case=='nominal','shift_seconds'].iloc[0]))
base,bd=D.evaluate((0,)*6,p);best,od=D.evaluate(x,p)
nomdir=R/'cases/nominal'
hd=pd.read_csv(nomdir/'heuristic_connections.csv',dtype={'trip_id':str})
comparison=[]
for name,row in [('Existing timetable',base),('Single-pass heuristic',best),('MILP / exact optimum',best)]:
 comparison.append({'method':name,**row})
pd.DataFrame(comparison).to_csv(R/'nominal_method_comparison.csv',index=False)
# Verify the heuristic row rather than assuming equality from rounded averages.
assert np.array_equal(hd.wait_sec.to_numpy(),od.wait_sec.to_numpy())
changes=bd[['opportunity_id','route_id','trip_id','arrival_time','wait_sec','caught_trip_id']].merge(od[['opportunity_id','wait_sec','caught_trip_id']],on='opportunity_id',suffixes=('_original','_optimized'),validate='one_to_one')
changes['saved_sec']=changes.wait_sec_original-changes.wait_sec_optimized
changes['change_class']=np.where(changes.saved_sec>0,'improved',np.where(changes.saved_sec<0,'worsened','unchanged'))
changes.to_csv(R/'individual_transfer_changes.csv',index=False)
route=[]
for rid,g in changes.groupby('route_id'):
 route.append({'route_id':rid,'opportunities':len(g),'original_mean_wait_min':g.wait_sec_original.mean()/60,'optimized_mean_wait_min':g.wait_sec_optimized.mean()/60,'saved_total_min':g.saved_sec.sum()/60,'improved':int((g.saved_sec>0).sum()),'worsened':int((g.saved_sec<0).sum()),'unchanged':int((g.saved_sec==0).sum())})
pd.DataFrame(route).to_csv(R/'by_route_comparison.csv',index=False)
# Stress tests evaluated with unchanged nominal timetable, not new selected shifts.
focus=['joint_t120_r180_b120','nominal','joint_t300_r180_b120','readiness_boundary_181','readiness_boundary_210']
s[s.case.isin(focus)][['case','transfer_seconds','baseline_mean_wait_min','optimized_mean_wait_min','frozen_nominal_mean_wait_min','baseline_mean_total_transfer_min','optimized_mean_total_transfer_min','frozen_nominal_mean_total_transfer_min','frozen_nominal_feasible','shift_seconds']].sort_values('transfer_seconds').to_csv(R/'transfer_allowance_stress_test.csv',index=False)
# All source block trips and selected trip stop times: no changed timetable overlaps.
links_audit=pd.DataFrame(D.constraints(x,p));links_audit.to_csv(R/'nominal_constraint_audit.csv',index=False)
stops=pd.read_csv(ROOT/'model/inputs/selected_trip_stop_times.csv',dtype={'trip_id':str})
def seconds(t):
 h,m,sec=map(int,str(t).split(':'));return h*3600+m*60+sec
def clock(t):return f'{int(t)//3600:02d}:{int(t)%3600//60:02d}:{int(t)%60:02d}'
shift=dict(zip(D.ids,x));stops['optimized_arrival_sec']=[seconds(t)+shift[j] for t,j in zip(stops.arrival_time,stops.trip_id)];stops['optimized_departure_sec']=[seconds(t)+shift[j] for t,j in zip(stops.departure_time,stops.trip_id)]
stops['optimized_arrival_time']=stops.optimized_arrival_sec.map(clock);stops['optimized_departure_time']=stops.optimized_departure_sec.map(clock)
assert all(stops.optimized_departure_sec>=stops.optimized_arrival_sec)
for j,g in stops.groupby('trip_id'):
 g=g.sort_values('stop_sequence');a=np.array([seconds(t) for t in g.arrival_time]);d=np.array([seconds(t) for t in g.departure_time])
 assert np.array_equal(g.optimized_arrival_sec-a,np.full(len(g),shift[j]))
 assert np.array_equal(g.optimized_departure_sec-d,np.full(len(g),shift[j]))
 assert np.array_equal(d-a,g.optimized_departure_sec-g.optimized_arrival_sec)
 assert np.array_equal(a[1:]-d[:-1],g.optimized_arrival_sec.to_numpy()[1:]-g.optimized_departure_sec.to_numpy()[:-1])
 assert np.all(g.optimized_arrival_sec.to_numpy()[1:]>=g.optimized_departure_sec.to_numpy()[:-1])
stops.to_csv(R/'optimized_complete_trip_stop_times.csv',index=False)
blocks=pd.read_csv(ROOT/'model/inputs/block_trip_endpoints.csv',dtype={'trip_id':str,'block_id':str})
blockchecks=[]
for block,g in blocks.groupby('block_id'):
 g=g.sort_values('start_sec')
 for (_,a),(_,b) in zip(list(g.iterrows())[:-1],list(g.iterrows())[1:]):
  old=int(b.start_sec-a.end_sec);new=old+shift.get(b.trip_id,0)-shift.get(a.trip_id,0)
  blockchecks.append({'block_id':block,'previous_trip_id':a.trip_id,'next_trip_id':b.trip_id,'old_gap_sec':old,'new_gap_sec':new,'changed_by_model':a.trip_id in shift or b.trip_id in shift,'no_time_overlap':new>=0})
assert all(r['no_time_overlap'] for r in blockchecks)
pd.DataFrame(blockchecks).to_csv(R/'all_affected_block_no_overlap_audit.csv',index=False)
# Independent brute-force earliest-connection check on every reported case result.
checked_rows=0;max_violation=0
for row in s.itertuples():
 folder=R/'cases'/row.case;p_=Parameters(**json.loads((folder/'parameters.json').read_text())['parameters'])
 for fn,sv in [('baseline_connections.csv',[0]*6),('frozen_nominal_connections.csv',x),('optimized_connections.csv',None),('heuristic_connections.csv',None)]:
  file=folder/fn
  if not file.exists():continue
  if sv is None:sv=json.loads(row.shift_seconds if fn.startswith('optimized') else row.heuristic_shift_seconds)
  dif=dict(zip(D.ids,map(int,sv)))
  times=[(j,int(t)+dif.get(j,0)) for j,t in zip(D.outgoing.trip_id,D.outgoing.departure_sec)]
  rec=pd.read_csv(file,dtype={'trip_id':str,'caught_trip_id':str})
  for rr in rec.itertuples():
   ready=int(rr.arrival_sec)+p_.transfer_seconds
   eligible=sorted((t,j) for j,t in times if t>=ready)
   assert eligible
   t,j=eligible[0]
   assert int(rr.wait_sec)==t-ready and int(rr.caught_departure_sec)==t and rr.caught_trip_id==j
   checked_rows+=1
  if fn.startswith(('optimized','heuristic')):
   assert D.feasible(sv,p_)
# Nominal exact equality and parameter boundary diagnostic.
opt_eq=od[od.wait_sec==0].copy();opt_eq.to_csv(R/'nominal_exact_readiness_connections.csv',index=False)
# Diagnostic ablation solutions rechecked against full nominal rules.
abl=[]
for name in ['no_vehicle_constraints','no_headway_constraints','no_vehicle_or_headway_constraints']:
 x_=tuple(json.loads(s.loc[s.case==name,'shift_seconds'].iloc[0]));v=pd.DataFrame(D.constraints(x_,Parameters()))
 v['relaxed_case']=name;abl.append(v)
pd.concat(abl,ignore_index=True).to_csv(R/'ablations_checked_against_full_rules.csv',index=False)
report={'cases':len(s),'optimal_milp_cases':int((s.model_status=='OPTIMAL').sum()),'infeasible_cases':int((s.model_status=='INFEASIBLE').sum()),'exact_enumeration_cases':int((s.enumeration_status=='EXACT').sum()),'half_minute_grid_solved_but_not_enumerated':True,'heuristic_matches_optimum_on_all_feasible_tested_cases':bool(np.allclose(s.loc[s.model_status=='OPTIMAL','heuristic_mean_wait_min'],s.loc[s.model_status=='OPTIMAL','optimized_mean_wait_min'],atol=1e-8,rtol=0)),'independent_row_checks':checked_rows,'selected_stop_time_rows_verified':len(stops),'block_neighbor_pairs_no_overlap_checked':len(blockchecks),'nominal_ready_at_exact_departure_opportunities':int((od.wait_sec==0).sum()),'baseline_ready_at_exact_departure_opportunities':int((bd.wait_sec==0).sum()),'nominal_largest_individual_worsening_min':float(-changes.saved_sec.min()/60),'nominal_largest_individual_improvement_min':float(changes.saved_sec.max()/60),'nominal_improved':int((changes.saved_sec>0).sum()),'nominal_worsened':int((changes.saved_sec<0).sum()),'nominal_unchanged':int((changes.saved_sec==0).sum()),'julia_executed':False,'scope_b_executed':False,'new_raw_mbta_data_collected':False}
(ROOT/'validation/experiment_validation_summary.json').write_text(json.dumps(report,indent=2)+'\n')
# Baseline lock includes actual input hashes and reference metric; no source altered.
lock={'source_archive_sha256':hashlib.sha256((ROOT/'source_archives/20261014.zip').read_bytes()).hexdigest(),'service_date':'2026-10-15','locked_inputs':[{'path':'model/inputs/'+f.name,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()} for f in sorted((ROOT/'model/inputs').glob('*')) if f.is_file()],'reference_baseline_total_wait_sec':33240,'reference_optimized_total_wait_sec':30660,'reference_shift_seconds':list(x),'note':'A regression reference, never an input that fixes optimization choices.'}
(ROOT/'validation/baseline_lock.json').write_text(json.dumps(lock,indent=2)+'\n')
print(json.dumps(report,indent=2))
