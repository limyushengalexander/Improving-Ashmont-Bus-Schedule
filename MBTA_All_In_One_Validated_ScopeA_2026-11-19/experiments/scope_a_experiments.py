"""Scope A verification, benchmark, and declared-parameter experiments.

Extends the uploaded finite-grid model without changing its nominal objective.
All numerical times are integer service-day seconds. Code and experiment design
are AI-assisted; original project artifacts/provenance are retained separately.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from itertools import product
from time import perf_counter
import json, math, hashlib
import numpy as np
import pandas as pd
from scipy.optimize import milp, Bounds, LinearConstraint
from scipy.sparse import coo_matrix

ROOT=Path(__file__).resolve().parents[1]
INPUT=ROOT/'model/inputs'
RESULT=ROOT/'results'

@dataclass(frozen=True)
class Parameters:
    transfer_seconds:int=180
    turnaround_seconds:int=180
    berth_seconds:int=120
    max_shift_seconds:int=300
    headway_deviation_seconds:int=300
    grid_seconds:int=60
    enforce_vehicle:bool=True
    enforce_headways:bool=True
    def __post_init__(self):
        for key in ['transfer_seconds','turnaround_seconds','berth_seconds','max_shift_seconds','headway_deviation_seconds']:
            if getattr(self,key)<0:raise ValueError(f'{key} must be nonnegative')
        if self.grid_seconds<=0:raise ValueError('grid_seconds must be positive')

class Inputs:
    def __init__(self, folder:Path=INPUT):
        self.arrivals=pd.read_csv(folder/'incoming.csv',dtype={'trip_id':str,'route_id':str})
        self.outgoing=pd.read_csv(folder/'outgoing.csv',dtype={'trip_id':str,'route_id':str}).sort_values('departure_sec').reset_index(drop=True)
        self.links=pd.read_csv(folder/'vehicle_links.csv',dtype={'predecessor_trip_id':str,'successor_trip_id':str,'predecessor_end_stop_id':str,'successor_start_stop_id':str})
        self.headways=pd.read_csv(folder/'headway_limits.csv',dtype={'earlier_trip_id':str,'later_trip_id':str})
        self.movable=self.outgoing[self.outgoing.is_adjustable==1].reset_index(drop=True)
        self.ids=self.movable.trip_id.tolist();self.id_pos={j:k for k,j in enumerate(self.ids)}
        self.outpos=[int(self.outgoing.index[self.outgoing.trip_id==j][0]) for j in self.ids]
        self.nominal=self.outgoing.departure_sec.to_numpy(dtype=np.int64)
        self.a=self.arrivals.arrival_sec.to_numpy(dtype=np.int64)
        self.cfg=json.loads((folder/'adopted_scope_a_config.json').read_text())
        self.links_records=self.links.to_dict('records');self.hd_records=self.headways.to_dict('records')
        assert len(self.arrivals)==41 and len(self.ids)==6 and len(self.outgoing)==37
        assert self.arrivals.trip_id.is_unique and self.outgoing.trip_id.is_unique
        assert self.movable.block_id.nunique()==6
        assert len(self.links)==12 and len(self.headways)==7
        for r in self.links_records:
            assert (r['predecessor_trip_id'] in self.id_pos) != (r['successor_trip_id'] in self.id_pos)
            if self.changed_berth(r):
                key=f"{r['predecessor_end_stop_id']}->{r['successor_start_stop_id']}"
                assert key in self.cfg['deadhead_seconds_by_stop_pair'],key
    @staticmethod
    def changed_berth(r):return r['predecessor_end_stop_id']!=r['successor_start_stop_id']
    def minimum(self,r,p):return p.turnaround_seconds+(p.berth_seconds if self.changed_berth(r) else 0)
    def domains(self,p):
        lower=np.full(6,-p.max_shift_seconds,dtype=int);upper=np.full(6,p.max_shift_seconds,dtype=int)
        if p.enforce_vehicle:
            for r in self.links_records:
                pred,succ=r['predecessor_trip_id'],r['successor_trip_id'];g=int(r['scheduled_gap_sec']);m=self.minimum(r,p)
                if succ in self.id_pos:lower[self.id_pos[succ]]=max(lower[self.id_pos[succ]],m-g)
                if pred in self.id_pos:upper[self.id_pos[pred]]=min(upper[self.id_pos[pred]],g-m)
        result=[]
        for lo,hi in zip(lower,upper):
            lo_grid=math.ceil(int(lo)/p.grid_seconds)*p.grid_seconds;hi_grid=math.floor(int(hi)/p.grid_seconds)*p.grid_seconds
            result.append(list(range(lo_grid,hi_grid+1,p.grid_seconds)))
        return result,lower,upper
    def constraints(self,shift,p):
        if len(shift)!=6:raise ValueError('Exactly six shifts required')
        if any(not float(x).is_integer() for x in shift):raise ValueError('Shifts must be integer seconds')
        x={j:int(s) for j,s in zip(self.ids,shift)};rows=[]
        for j,s in x.items():
            rows.append({'family':'shift_limit','item':j,'actual':abs(s),'lower':0,'upper':p.max_shift_seconds,'slack_lower':abs(s),'slack_upper':p.max_shift_seconds-abs(s),'feasible':abs(s)<=p.max_shift_seconds})
            rows.append({'family':'grid','item':j,'actual':s,'lower':None,'upper':None,'slack_lower':None,'slack_upper':None,'feasible':s%p.grid_seconds==0})
        for r in self.links_records:
            pred,succ=r['predecessor_trip_id'],r['successor_trip_id'];actual=int(r['scheduled_gap_sec'])+x.get(succ,0)-x.get(pred,0);minimum=self.minimum(r,p)
            rows.append({'family':'vehicle','item':pred+' -> '+succ,'actual':actual,'lower':minimum,'upper':None,'slack_lower':actual-minimum,'slack_upper':None,'feasible':actual>=minimum,'enforced':p.enforce_vehicle})
        for r in self.hd_records:
            e,l=r['earlier_trip_id'],r['later_trip_id'];h=int(r['scheduled_headway_sec']);actual=h+x.get(l,0)-x.get(e,0);low=max(1,h-p.headway_deviation_seconds);up=h+p.headway_deviation_seconds
            rows.append({'family':'headway','item':e+' -> '+l,'actual':actual,'lower':low,'upper':up,'slack_lower':actual-low,'slack_upper':up-actual,'feasible':low<=actual<=up,'enforced':p.enforce_headways})
        for r in rows:r.setdefault('enforced',True)
        return rows
    def feasible(self,shift,p):return all(r['feasible'] for r in self.constraints(shift,p) if r['enforced'])
    def evaluate(self,shift,p):
        if len(shift)!=6:raise ValueError('Exactly six shifts required')
        actual=self.nominal.copy();actual[self.outpos]+=np.asarray(shift,dtype=np.int64)
        order=np.argsort(actual,kind='stable');dep=actual[order];ids=self.outgoing.trip_id.to_numpy()[order]
        ready=self.a+p.transfer_seconds;k=np.searchsorted(dep,ready,side='left');served=k<len(dep)
        # No modeled case relies on this fallback; it is not an optimization option.
        waits=np.full(len(ready),int(self.cfg['stranded_penalty_seconds']),dtype=np.int64)
        caught=np.full(len(ready),-1,dtype=np.int64);caught[served]=dep[k[served]];waits[served]=caught[served]-ready[served]
        detail=self.arrivals[['opportunity_id','route_id','trip_id','arrival_sec','arrival_time']].copy()
        detail['ready_sec']=ready;detail['caught_trip_id']=[ids[v] if ok else '' for v,ok in zip(k,served)]
        detail['caught_departure_sec']=np.where(served,caught,np.nan)
        detail['wait_sec']=np.where(served,waits,np.nan);detail['waiting_cost_sec']=waits
        detail['total_transfer_sec']=np.where(served,waits+p.transfer_seconds,np.nan);detail['served']=served
        costs=waits[served]
        stats={'total_wait_cost_sec':int(waits.sum()),'mean_wait_cost_min':float(waits.mean()/60),'mean_wait_min':float(costs.mean()/60) if len(costs) else None,'max_wait_min':float(costs.max()/60) if len(costs) else None,'mean_total_transfer_min':float((costs+p.transfer_seconds).mean()/60) if len(costs) else None,'p90_wait_min':float(np.quantile(costs,0.9)/60) if len(costs) else None,'served':int(served.sum()),'stranded':int((~served).sum()),'within_10_min':int((costs<=600).sum()),'after_1900_connections':int(((caught>=19*3600)&served).sum()),'moved_trips':sum(int(s)!=0 for s in shift),'total_absolute_shift_min':sum(abs(int(s)) for s in shift)/60}
        return stats,detail


def heuristic(data,p,repeat=False):
    """The prespecified primary benchmark is one chronological feasible pass."""
    x=[0]*6;trace=[]
    if not data.feasible(x,p):return None,trace
    dom,_,_=data.domains(p);eval_count=1;current=data.evaluate(x,p)[0]['total_wait_cost_sec']
    for iteration in range(1,1001):
        improved=False
        for j in range(6):
            candidates=[]
            for s in dom[j]:
                y=x.copy();y[j]=s
                if not data.feasible(y,p):continue
                score=data.evaluate(y,p)[0]['total_wait_cost_sec'];eval_count+=1
                candidates.append((score,abs(s),s,y))
            best=min(candidates,key=lambda z:(z[0],z[1],z[2]))
            before=current;old=x[j]
            if best[0]<current:x=best[3];current=best[0];improved=True
            trace.append({'pass':iteration,'departure':data.movable.departure_time.iloc[j],'old_shift_sec':old,'new_shift_sec':x[j],'total_cost_before_sec':before,'total_cost_after_sec':current,'evaluation_count':eval_count})
        if not repeat or not improved:return tuple(x),trace
    raise RuntimeError('Unexpected failure to converge despite strict integer-cost improvement')


def solve_milp(data,p):
    t0=perf_counter();domains,lower,upper=data.domains(p)
    if any(len(d)==0 for d in domains):
        return {'status':'INFEASIBLE','method':'empty_domain_certificate','conflicting_bounds':[{'trip_id':j,'lower_sec':int(lo),'upper_sec':int(hi)} for j,d,lo,hi in zip(data.ids,domains,lower,upper) if not d],'elapsed_seconds':perf_counter()-t0},None
    opts={j:d for j,d in zip(data.ids,domains)};dep=dict(zip(data.outgoing.trip_id,map(int,data.nominal)))
    fixed=[j for j in dep if j not in opts]
    ready=data.a+p.transfer_seconds
    assert any(dep[j]>=ready.max() for j in fixed),'This no-stranding MILP requires a fixed late departure for all opportunities.'
    opts.update({j:[0] for j in fixed})
    z=[(j,s) for j in data.ids for s in opts[j]];arcs=[(i,j,s) for i,r in enumerate(ready) for j in dep for s in opts[j] if dep[j]+s>=r]
    zix={k:i for i,k in enumerate(z)};yix={k:i+len(z) for i,k in enumerate(arcs)};n=len(z)+len(arcs)
    c=np.zeros(n)
    for i,j,s in arcs:c[yix[(i,j,s)]]=dep[j]+s-ready[i]
    ri=[];ci=[];vv=[];lo=[];hi=[]
    def row(expr,lb=-np.inf,ub=np.inf):
        r=len(lo);lo.append(lb);hi.append(ub)
        for k,v in expr.items():
            if v:ri.append(r);ci.append(k);vv.append(float(v))
    for j in data.ids:row({zix[(j,s)]:1 for s in opts[j]},1,1)
    by_i=[{} for _ in ready]
    for a in arcs:by_i[a[0]][yix[a]]=1
    for d in by_i:row(d,1,1)
    for a in arcs:
        i,j,s=a
        if j in data.id_pos:row({yix[a]:1,zix[(j,s)]:-1},ub=0)
    def delta(pred,succ):
        d={}
        for j,sign in [(succ,1),(pred,-1)]:
            if j in data.id_pos:
                for s in opts[j]:d[zix[(j,s)]]=d.get(zix[(j,s)],0)+sign*s
        return d
    if p.enforce_vehicle:
        for r in data.links_records:row(delta(r['predecessor_trip_id'],r['successor_trip_id']),lb=data.minimum(r,p)-int(r['scheduled_gap_sec']))
    if p.enforce_headways:
        for r in data.hd_records:
            h=int(r['scheduled_headway_sec']);row(delta(r['earlier_trip_id'],r['later_trip_id']),lb=max(1,h-p.headway_deviation_seconds)-h,ub=p.headway_deviation_seconds)
    A=coo_matrix((vv,(ri,ci)),shape=(len(lo),n)).tocsr();build=perf_counter()-t0
    result=milp(c=c,integrality=np.r_[np.ones(len(z)),np.zeros(len(arcs))],bounds=Bounds(np.zeros(n),np.r_[np.ones(len(z)),np.full(len(arcs),np.inf)]),constraints=LinearConstraint(A,np.array(lo),np.array(hi)),options={'time_limit':60.0,'mip_rel_gap':0.0})
    info={'status':'OPTIMAL' if result.status==0 else ('INFEASIBLE' if result.status==2 else 'NOT_PROVEN_OPTIMAL'),'solver':'scipy.optimize.milp / HiGHS','solver_message':str(result.message),'status_code':int(result.status),'binary_variables':len(z),'continuous_variables':len(arcs),'constraints':len(lo),'build_seconds':build,'solve_seconds':perf_counter()-t0-build,'elapsed_seconds':perf_counter()-t0}
    if result.x is None:return info,None
    x=[]
    for j in data.ids:
        sel=[s for s in opts[j] if result.x[zix[(j,s)]]>0.5]
        assert len(sel)==1
        x.append(sel[0])
    assert data.feasible(x,p)
    stats,_=data.evaluate(x,p);obj=float(result.fun)
    assert stats['total_wait_cost_sec']<=obj+1e-5
    if result.status==0:assert abs(stats['total_wait_cost_sec']-obj)<1e-5
    info.update(objective_total_wait_sec=obj,objective_mean_wait_min=obj/len(ready)/60,objective_bound_total_wait_sec=float(result.mip_dual_bound),relative_gap=float(result.mip_gap),mip_nodes=int(result.mip_node_count),shift_seconds=x,independent_recomputed_cost_sec=stats['total_wait_cost_sec'])
    return info,tuple(x)


def enumerate_exact(data,p,cache):
    dom,lower,upper=data.domains(p);size=math.prod(len(d) for d in dom)
    if size==0:return {'status':'INFEASIBLE','feasible_count':0},None
    if size>2000000:return {'status':'NOT_ENUMERATED_GRID_TOO_LARGE','candidate_grid_count':size},None
    key=(p.turnaround_seconds,p.berth_seconds,p.max_shift_seconds,p.headway_deviation_seconds,p.grid_seconds,p.enforce_vehicle,p.enforce_headways)
    t0=perf_counter()
    if key in cache:xs=cache[key]
    else:
        all_x=np.array(list(product(*dom)),dtype=np.int32);mask=np.ones(len(all_x),dtype=bool)
        def v(j):return all_x[:,data.id_pos[j]] if j in data.id_pos else 0
        if p.enforce_vehicle:
            for r in data.links_records:mask&=(int(r['scheduled_gap_sec'])+v(r['successor_trip_id'])-v(r['predecessor_trip_id'])>=data.minimum(r,p))
        if p.enforce_headways:
            for r in data.hd_records:
                h=int(r['scheduled_headway_sec']);head=h+v(r['later_trip_id'])-v(r['earlier_trip_id']);mask&=(head>=max(1,h-p.headway_deviation_seconds))&(head<=h+p.headway_deviation_seconds)
        xs=all_x[mask];cache[key]=xs
    if not len(xs):return {'status':'INFEASIBLE','feasible_count':0},None
    # Independent batch evaluator: minimum of every catchable option, not searchsorted.
    # Earlier fixed buses are discarded only if earlier than ALL ready times; later
    # fixed buses beyond the first covering all ready times cannot improve a wait.
    ready=data.a+p.transfer_seconds;fixed_times=data.outgoing.loc[data.outgoing.is_adjustable==0,'departure_sec'].to_numpy(dtype=int)
    useful_fixed=fixed_times[fixed_times>=ready.min()];assert len(useful_fixed)
    cover=useful_fixed[useful_fixed>=ready.max()].min();useful_fixed=useful_fixed[useful_fixed<=cover]
    mov_times=data.movable.departure_sec.to_numpy(dtype=int)
    cost=np.empty(len(xs),dtype=np.int64)
    for start in range(0,len(xs),10000):
        end=min(start+10000,len(xs));deps=np.c_[mov_times[None,:]+xs[start:end],np.tile(useful_fixed,(end-start,1))]
        totals=np.zeros(end-start,dtype=np.int64)
        for r in ready:
            w=deps-r;totals+=np.where(w>=0,w,10**8).min(axis=1)
        cost[start:end]=totals
    best=int(cost.min());optimal=xs[cost==best]
    win=min((tuple(map(int,x)) for x in optimal),key=lambda x:(sum(s!=0 for s in x),sum(abs(s) for s in x),x))
    assert data.evaluate(win,p)[0]['total_wait_cost_sec']==best
    return {'status':'EXACT','candidate_grid_count':size,'feasible_count':len(xs),'optimal_count':len(optimal),'optimal_total_wait_sec':best,'shift_seconds':list(win),'elapsed_seconds':perf_counter()-t0},win


def run_suite():
    RESULT.mkdir(exist_ok=True);cases_dir=RESULT/'cases';cases_dir.mkdir(exist_ok=True)
    data=Inputs();plan=json.loads((ROOT/'experiments/experiment_plan.json').read_text());cache={};summaries=[]
    nominal_shift=None
    for case in plan['cases']:
        name=case['name'];p=Parameters(**case['parameters']);folder=cases_dir/name;folder.mkdir(exist_ok=True)
        (folder/'parameters.json').write_text(json.dumps(case,indent=2)+'\n')
        dom,low,up=data.domains(p)
        pd.DataFrame([{'trip_id':j,'departure':t,'lower_before_grid_sec':int(l),'upper_before_grid_sec':int(u),'allowed_shift_seconds':json.dumps(d)} for j,t,l,u,d in zip(data.ids,data.movable.departure_time,low,up,dom)]).to_csv(folder/'derived_shift_domains.csv',index=False)
        baseline,bd=data.evaluate((0,)*6,p);base_feasible=data.feasible((0,)*6,p)
        solver,ms=solve_milp(data,p);enum,es=enumerate_exact(data,p,cache)
        (folder/'solver.json').write_text(json.dumps(solver,indent=2)+'\n');(folder/'enumeration.json').write_text(json.dumps(enum,indent=2)+'\n')
        if solver['status']=='INFEASIBLE':assert enum['status']=='INFEASIBLE'
        if enum['status']=='EXACT':
            assert solver['status']=='OPTIMAL',solver
            assert abs(enum['optimal_total_wait_sec']-solver['objective_total_wait_sec'])<1e-5
        x=es if es is not None else ms
        row={'case':name,'groups':';'.join(case['groups']),**case['parameters'],'model_status':solver['status'],'baseline_feasible':base_feasible,'baseline_mean_wait_min':baseline['mean_wait_min'],'baseline_max_wait_min':baseline['max_wait_min'],'baseline_mean_total_transfer_min':baseline['mean_total_transfer_min'],'enumeration_status':enum['status'],'feasible_grid_count':enum.get('feasible_count'),'num_optima':enum.get('optimal_count'),'solver_gap':solver.get('relative_gap'),'solver_seconds':solver.get('solve_seconds')}
        if x is not None:
            stats,detail=data.evaluate(x,p);detail.to_csv(folder/'optimized_connections.csv',index=False)
            pd.DataFrame(data.constraints(x,p)).to_csv(folder/'optimized_constraint_checks.csv',index=False)
            row.update(optimized_mean_wait_min=stats['mean_wait_min'],optimized_max_wait_min=stats['max_wait_min'],optimized_mean_total_transfer_min=stats['mean_total_transfer_min'],optimized_within_10min=stats['within_10_min'],optimized_stranded=stats['stranded'],shift_seconds=json.dumps(list(x)))
            if base_feasible:
                row.update(mean_wait_improvement_min=baseline['mean_wait_min']-stats['mean_wait_min'],improvement_pct=100*(baseline['mean_wait_min']-stats['mean_wait_min'])/baseline['mean_wait_min'])
            if name=='nominal':nominal_shift=x
        hs,trace=heuristic(data,p,False)
        if hs is not None:
            hstats,hd=data.evaluate(hs,p);hd.to_csv(folder/'heuristic_connections.csv',index=False);pd.DataFrame(trace).to_csv(folder/'heuristic_trace.csv',index=False)
            row.update(heuristic_mean_wait_min=hstats['mean_wait_min'],heuristic_max_wait_min=hstats['max_wait_min'],heuristic_mean_total_transfer_min=hstats['mean_total_transfer_min'],heuristic_within_10min=hstats['within_10_min'],heuristic_shift_seconds=json.dumps(list(hs)))
            if x is not None:row['optimization_advantage_vs_heuristic_min']=hstats['mean_wait_min']-row['optimized_mean_wait_min']
            if name=='nominal':
                repeat,rt=heuristic(data,p,True);rstats,rd=data.evaluate(repeat,p)
                (folder/'repeated_pass_heuristic.json').write_text(json.dumps({'shift_seconds':repeat,'metrics':rstats,'passes':max(t['pass'] for t in rt)},indent=2));pd.DataFrame(rt).to_csv(folder/'repeated_pass_trace.csv',index=False)
        assert nominal_shift is not None
        fs,fd=data.evaluate(nominal_shift,p)
        row.update(frozen_nominal_feasible=data.feasible(nominal_shift,p),frozen_nominal_mean_wait_min=fs['mean_wait_min'],frozen_nominal_mean_total_transfer_min=fs['mean_total_transfer_min'],frozen_nominal_max_wait_min=fs['max_wait_min'])
        if x is not None and row['frozen_nominal_feasible']:row['frozen_regret_min']=fs['mean_wait_min']-row['optimized_mean_wait_min']
        pd.DataFrame(data.constraints((0,)*6,p)).to_csv(folder/'baseline_constraint_checks.csv',index=False)
        pd.DataFrame(data.constraints(nominal_shift,p)).to_csv(folder/'frozen_nominal_constraint_checks.csv',index=False)
        bd.to_csv(folder/'baseline_connections.csv',index=False);fd.to_csv(folder/'frozen_nominal_connections.csv',index=False)
        summaries.append(row)
        print(name,solver['status'],'base',round(baseline['mean_wait_min'],4),'opt',row.get('optimized_mean_wait_min'),'heur',row.get('heuristic_mean_wait_min'),flush=True)
    pd.DataFrame(summaries).to_csv(RESULT/'experiment_summary.csv',index=False)
    (RESULT/'experiment_summary.json').write_text(json.dumps(summaries,indent=2,allow_nan=False)+'\n')
    print('Saved',len(summaries),'case results; Julia was not executed.',flush=True)

if __name__=='__main__':run_suite()
