"""Independent exact enumeration for the six-shift *integer-minute* Scope A model.

Not a Julia/JuMP run. Intended to verify the linear model and produce a robust
numerical reference on the same finite shift grid. All results are conditional
on the adopted assumptions, not MBTA operations approval.
"""
import itertools
import json
import math
from pathlib import Path
from collections import Counter
import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
IN = BASE / 'inputs'
OUT = BASE / 'results'

def hhmm(t):
    sec = int(t)
    sign = '-' if sec < 0 else ''
    sec = abs(sec)
    return f'{sign}{sec // 3600:02d}:{(sec % 3600) // 60:02d}:{sec % 60:02d}'

def loads():
    inc = pd.read_csv(IN / 'incoming.csv', dtype={'trip_id': str, 'route_id': str})
    outs = pd.read_csv(IN / 'outgoing.csv', dtype={'trip_id': str, 'route_id': str})
    links = pd.read_csv(IN / 'vehicle_links.csv', dtype={'predecessor_trip_id': str, 'successor_trip_id': str})
    headways = pd.read_csv(IN / 'headway_limits.csv', dtype={'earlier_trip_id': str, 'later_trip_id': str})
    limits = pd.read_csv(IN / 'shift_bounds_checked.csv')
    config = json.loads((IN / 'adopted_scope_a_config.json').read_text())
    outs = outs.sort_values('departure_sec').reset_index(drop=True)
    movable = outs[outs.is_adjustable == 1].copy().reset_index(drop=True)
    assert len(inc) == 41 and len(movable) == 6 and len(outs) == 37
    assert list(movable.departure_time.str.slice(0, 5)) == list(limits.departure)
    assert config['transfer_allowance_seconds'] == 180
    return inc, outs, movable, links, headways, limits, config

def valid_shift_tuple(shift, mov_ids, links, headways):
    shifts = dict(zip(mov_ids, shift))
    def delta(trip): return int(shifts.get(str(trip), 0)) * 60
    for row in links.itertuples(index=False):
        gap = int(row.scheduled_gap_sec) + delta(row.successor_trip_id) - delta(row.predecessor_trip_id)
        if gap < int(row.minimum_gap_sec): return False
    for row in headways.itertuples(index=False):
        headway = int(row.scheduled_headway_sec) + delta(row.later_trip_id) - delta(row.earlier_trip_id)
        if not (int(row.minimum_headway_sec) <= headway <= int(row.maximum_headway_sec)): return False
    return True

def evaluate(inc, outs, movable, changes, allowance_sec=180):
    shifts = dict(zip(movable.trip_id.astype(str).to_list(), changes))
    ordered = outs.copy()
    ordered['actual_departure_sec'] = ordered.departure_sec + ordered.trip_id.map(lambda t:60*int(shifts.get(str(t), 0)))
    ordered = ordered.sort_values('actual_departure_sec').reset_index(drop=True)
    arr = inc.arrival_sec.to_numpy(dtype=int)
    dep = ordered.actual_departure_sec.to_numpy(dtype=int)
    ready = arr + allowance_sec
    ix = np.searchsorted(dep, ready, side='left')
    assert (ix < len(dep)).all(), 'If a future dataset creates stranded opportunities, use a forced indicator and 60-min penalty.'
    wait = dep[ix] - ready
    assert (wait >= 0).all()
    detail = inc[['opportunity_id', 'route_id', 'trip_id', 'arrival_time']].copy()
    detail['ready_sec'] = ready
    detail['caught_trip_id'] = ordered.trip_id.to_numpy()[ix]
    detail['caught_departure_sec'] = dep[ix]
    detail['platform_wait_sec'] = wait
    detail['total_transfer_sec'] = wait + allowance_sec
    detail['caught_after_1900'] = dep[ix]>=19*3600
    metrics = {
        'total_platform_wait_sec':int(wait.sum()),
        'mean_platform_wait_min':float(wait.mean()/60),
        'max_platform_wait_min':float(wait.max()/60),
        'mean_total_transfer_min':float((wait+allowance_sec).mean()/60),
        'served':len(wait),'stranded':0,
        'connections_at_or_under_10min':int((wait<=600).sum()),
        'after_1900_connections':int((dep[ix]>=19*3600).sum()),
        'route_mean_platform_wait_min':{str(int(route)):float(g.platform_wait_sec.mean()/60) for route,g in detail.groupby('route_id')},
    }
    return metrics,detail,ordered

def run():
    OUT.mkdir(exist_ok=True)
    inc, outs, movable, links, headways, limits, config = loads()
    movable_ids = list(movable.trip_id)
    ranges = [range(int(r.earliest_shift_min),int(r.latest_shift_min)+1) for r in limits.itertuples(index=False)]
    base_metrics,base_detail,_ = evaluate(inc,outs,movable,(0,)*6)
    assert round(base_metrics['mean_platform_wait_min'],5)==round(13.512195121951219,5)
    ready = inc.arrival_sec.to_numpy(dtype=int) + 180
    # The seven candidate departures (six movable and first fixed after 19:00)
    # are provably all that matter for the stated October 15 cohort.
    fixed_before = outs.loc[(outs.is_adjustable==0)&(outs.departure_sec<movable.departure_sec.min()),'departure_sec']
    after = outs.loc[(outs.is_adjustable==0)&(outs.departure_sec>movable.departure_sec.max()),'departure_sec']
    assert fixed_before.max()<ready.min()
    assert after.min()>=ready.max()
    assert not ((outs.is_adjustable==0)&(outs.departure_sec>movable.departure_sec.min())&(outs.departure_sec<after.min())).any()
    relevant_nominal = np.r_[movable.departure_sec.to_numpy(dtype=int),int(after.min())]
    all_tuples = np.array(list(itertools.product(*ranges)), dtype=np.int16)
    passing = np.ones(len(all_tuples), dtype=bool)
    id_pos = {str(t):j for j,t in enumerate(movable_ids)}
    def vec_delta(trip):
        if str(trip) in id_pos:
            return 60*all_tuples[:,id_pos[str(trip)]].astype(np.int32)
        return 0
    for row in links.itertuples(index=False):
        gap = int(row.scheduled_gap_sec) + vec_delta(row.successor_trip_id) - vec_delta(row.predecessor_trip_id)
        passing &= gap >= int(row.minimum_gap_sec)
    for row in headways.itertuples(index=False):
        hd = int(row.scheduled_headway_sec) + vec_delta(row.later_trip_id) - vec_delta(row.earlier_trip_id)
        passing &= (hd >= int(row.minimum_headway_sec)) & (hd <= int(row.maximum_headway_sec))
    feasible = all_tuples[passing]
    assert np.any(np.all(feasible==0,axis=1))
    assert feasible.shape[0]==71673,(feasible.shape[0],'expected 71,673 under adopted model')
    means=np.empty(feasible.shape[0],dtype=np.int64)
    batch=12000
    for start in range(0,len(feasible),batch):
        end=min(len(feasible),start+batch)
        dep=np.concatenate((relevant_nominal[:-1][None,:]+60*feasible[start:end].astype('int32'), np.full((end-start,1),relevant_nominal[-1],dtype='int32')),axis=1)
        totals=np.zeros(end-start,dtype='int64')
        for r in ready:
            deltas=dep-int(r)
            totals+=np.where(deltas>=0,deltas,2**29).min(axis=1)
        means[start:end]=totals
    bestcost=int(means.min())
    best_idxs=np.flatnonzero(means==bestcost)
    best_shifts=feasible[best_idxs]
    # Deterministic secondary tie-break: fewest moved trips, then smallest
    # total absolute change, then lexicographic shift vector.
    winner=min((tuple(map(int,t)) for t in best_shifts),key=lambda t:(sum(x!=0 for x in t),sum(abs(x) for x in t),t))
    assert bestcost <=base_metrics['total_platform_wait_sec']
    best_metrics,best_detail,optim_out=evaluate(inc,outs,movable,winner)
    assert best_metrics['total_platform_wait_sec']==bestcost
    assert valid_shift_tuple(winner,movable_ids,links,headways)
    assert all( int(l.earliest_shift_min)<=v<=int(l.latest_shift_min) for v,l in zip(winner,limits.itertuples(index=False)))
    improvements=best_detail[['opportunity_id','platform_wait_sec']].merge(base_detail[['opportunity_id','platform_wait_sec']],on='opportunity_id',suffixes=('_optimized','_baseline'))
    improvements['saved_sec']=improvements.platform_wait_sec_baseline-improvements.platform_wait_sec_optimized
    out={'date':'2026-10-15','model':'Scope A, six one-minute-grid shifts, fixed 3-minute allowance, vehicle and headway constraints',
        'status':'EXACT EXHAUSTIVE ENUMERATION ON FINITE GRID; Julia/JuMP not executed',
        'num_feasible_joint_shift_combinations':len(feasible),'num_optimal_joint_shift_combinations':len(best_idxs),
        'baseline':base_metrics,'best':best_metrics,'best_shift_vector_min':list(winner),
        'original_departure_times':list(movable.departure_time),'optimal_departure_times':[hhmm(int(t)+60*v) for t,v in zip(movable.departure_sec,winner)],
        'mean_wait_improvement_min':(base_metrics['total_platform_wait_sec']-bestcost)/41/60,
        'relative_mean_wait_improvement_pct':100*(base_metrics['total_platform_wait_sec']-bestcost)/base_metrics['total_platform_wait_sec'],
        'improved_opportunities':int((improvements.saved_sec>0).sum()),
        'worsened_opportunities':int((improvements.saved_sec<0).sum()),
        'unchanged_opportunities':int((improvements.saved_sec==0).sum()),
        'total_wait_saved_min':int((base_metrics['total_platform_wait_sec']-bestcost)/60),
        'equal_weights_not_ridership':True,
        'model_assumptions_not_mbta_certified':True}
    (OUT/'enumeration_results.json').write_text(json.dumps(out,indent=2))
    best_detail.to_csv(OUT/'optimized_connections.csv',index=False)
    improvements.to_csv(OUT/'per_opportunity_changes.csv',index=False)
    optim_out.to_csv(OUT/'optimized_outgoing.csv',index=False)
    pd.DataFrame([{'trip_id':tid,'scheduled_departure_time':t,'shift_minutes':v,'optimized_departure_time':hhmm(int(secs)+60*v)} for tid,t,secs,v in zip(movable.trip_id,movable.departure_time,movable.departure_sec,winner)]).to_csv(OUT/'recommended_departure_shifts.csv',index=False)
    pd.DataFrame([{'shift_min':int(t),'frequency_among_feasible':int(v)} for t,v in Counter(feasible[:,0]).items()]).to_csv(OUT/'first_departure_shift_distribution.csv',index=False)
    print(json.dumps(out,indent=2))
    return out
if __name__=='__main__': run()
