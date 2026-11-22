"""Independent SciPy/HiGHS MILP check for the JuMP mathematical formulation.

Test-only implementation, not the project's Julia deliverable.
Proves that the one-hot shift / fractional transfer assignment formulation
attains the same optimum found by exhaustive enumeration.
"""
import sys,json
from pathlib import Path
import numpy as np
from scipy.optimize import milp,Bounds,LinearConstraint
from scipy.sparse import lil_matrix
from reference_enumeration import loads,evaluate,valid_shift_tuple

BASE=Path(__file__).resolve().parents[1]
def run():
    inc,out,mov,links,heads,limits,config=loads()
    dep={str(row.trip_id):int(row.departure_sec) for row in out.itertuples()}
    ids=list(mov.trip_id); adj=set(ids)
    K={str(row.trip_id):list(range(int(l.earliest_shift_min),int(l.latest_shift_min)+1)) for row,l in zip(mov.itertuples(),limits.itertuples())}
    K.update({str(j):[0] for j in out.loc[out.is_adjustable==0,'trip_id']})
    z=[(j,k) for j in ids for k in K[j]]
    ready=inc.arrival_sec.to_numpy(dtype=int)+180
    by_i=[];arcs=[]
    for i,r in enumerate(ready):
        xi=[(i,j,k) for j in dep for k in K[j] if dep[j]+60*k>=r]
        assert xi
        by_i.append(xi);arcs.extend(xi)
    zix={v:i for i,v in enumerate(z)};yix={v:len(z)+i for i,v in enumerate(arcs)}
    n=len(z)+len(arcs);c=np.zeros(n)
    for i,j,k in arcs:c[yix[(i,j,k)]]=(dep[j]+60*k-ready[i])/(60*len(ready))
    cons=[]
    def row(data,lb=-np.inf,ub=np.inf):cons.append((data,lb,ub))
    for j in ids:row({zix[(j,k)]:1 for k in K[j]},1,1)
    for i,ai in enumerate(by_i):row({yix[a]:1 for a in ai},1,1)
    for i,j,k in arcs:
        if j in adj:row({yix[(i,j,k)]:1,zix[(j,k)]:-1},ub=0)
    def linear_shift(ids_with_sign):
        expr={}
        for j,sgn in ids_with_sign:
            if j in adj:
                for k in K[j]:expr[zix[(j,k)]]=expr.get(zix[(j,k)],0)+60*sgn*k
        return expr
    for r in links.itertuples():
        expr=linear_shift([(str(r.successor_trip_id),1),(str(r.predecessor_trip_id),-1)])
        row(expr,lb=int(r.minimum_gap_sec)-int(r.scheduled_gap_sec))
    for r in heads.itertuples():
        expr=linear_shift([(str(r.later_trip_id),1),(str(r.earlier_trip_id),-1)])
        row(expr,lb=int(r.minimum_headway_sec)-int(r.scheduled_headway_sec),ub=int(r.maximum_headway_sec)-int(r.scheduled_headway_sec))
    mat=lil_matrix((len(cons),n),dtype=float);lo=np.zeros(len(cons));hi=np.zeros(len(cons))
    for ri,(data,lb,ub) in enumerate(cons):
        for col,v in data.items():mat[ri,col]=v
        lo[ri]=lb;hi[ri]=ub
    xlow=np.zeros(n);xhigh=np.r_[np.ones(len(z)), np.full(len(arcs),np.inf)]
    integral=np.r_[np.ones(len(z)),np.zeros(len(arcs))]
    result=milp(c=c,integrality=integral,bounds=Bounds(xlow,xhigh),constraints=LinearConstraint(mat.tocsr(),lo,hi),options={'time_limit':80,'mip_rel_gap':0.0})
    if result.x is None:raise RuntimeError(f'No MILP solution: {result.message}')
    shifts=tuple(next(k for k in K[j] if result.x[zix[(j,k)]]>.9) for j in ids)
    metrics,_,_=evaluate(inc,out,mov,shifts)
    enumeration=json.loads((BASE/'results/enumeration_results.json').read_text())
    assert result.success, result.message
    assert abs(result.fun-metrics['mean_platform_wait_min'])<1e-5
    assert abs(result.fun-enumeration['best']['mean_platform_wait_min'])<1e-5
    assert list(shifts)==enumeration['best_shift_vector_min']
    assert valid_shift_tuple(shifts,ids,links,heads)
    status={'solver':'SciPy milp (HiGHS)','success':bool(result.success),'status_code':int(result.status),'message':result.message,
            'objective_mean_wait_minutes':float(result.fun),'shift_vector_minutes':list(shifts),
            'variables':n,'shift_binaries':len(z),'transfer_assignments_continuous':len(arcs),'constraints':len(cons),
            'mip_gap':float(result.mip_gap) if hasattr(result,'mip_gap') else None,
            'verified_equal_to_exhaustive_enumeration':True,
            'julia_execution_status':'NOT_EXECUTED_in_current_environment'}
    (BASE/'results/scipy_milp_crosscheck.json').write_text(json.dumps(status,indent=2))
    print(json.dumps(status,indent=2))
    return status
if __name__=='__main__':run()
