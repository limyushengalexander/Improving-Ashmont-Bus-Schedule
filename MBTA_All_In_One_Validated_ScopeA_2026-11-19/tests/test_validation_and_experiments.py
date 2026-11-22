"""Regression and edge-case tests for the November 19 experiment suite."""
import sys,json,hashlib,unittest
from pathlib import Path
from dataclasses import replace
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'experiments'))
from scope_a_experiments import Inputs,Parameters,heuristic,solve_milp,enumerate_exact

class ValidationTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.d=Inputs();cls.p=Parameters();cls.x=(-120,0,-120,-60,120,0)
  cls.table=pd.read_csv(ROOT/'results/experiment_summary.csv')
 def test_source_baseline_reproduced(self):
  s,c=self.d.evaluate((0,)*6,self.p);self.assertEqual(s['total_wait_cost_sec'],33240);self.assertEqual(s['stranded'],0)
 def test_nominal_optimum_recomputed(self):
  r,x=solve_milp(self.d,self.p);self.assertEqual(r['status'],'OPTIMAL');self.assertEqual(x,self.x);self.assertEqual(r['relative_gap'],0)
 def test_primary_heuristic_without_targets(self):
  x,t=heuristic(self.d,self.p);self.assertEqual(x,self.x);self.assertEqual(len(t),6);self.assertTrue(all(v['total_cost_after_sec']<=v['total_cost_before_sec'] for v in t))
 def test_repeated_pass_does_not_change_primary(self):
  x,t=heuristic(self.d,self.p,True);self.assertEqual(x,self.x);self.assertEqual(max(v['pass'] for v in t),2)
 def test_derived_domains_match_locked_case(self):
  d,lo,hi=self.d.domains(self.p)
  self.assertEqual([min(x) for x in d],[-120,-120,-120,-120,-120,-240])
  self.assertEqual([max(x) for x in d],[60,300,240,300,300,180])
 def test_domains_rebuilt_when_turnaround_changes(self):
  a,_,_=self.d.domains(self.p);b,_,_=self.d.domains(replace(self.p,turnaround_seconds=120));self.assertNotEqual(a,b);self.assertEqual(min(b[0]),-180)
 def test_domains_rebuilt_when_berth_changes(self):
  a,_,_=self.d.domains(self.p);b,_,_=self.d.domains(replace(self.p,berth_seconds=0));self.assertNotEqual(a,b);self.assertEqual(max(b[0]),180)
 def test_two_minute_cap_retains_optimum(self):
  self.assertTrue(self.d.feasible(self.x,replace(self.p,max_shift_seconds=120)))
 def test_zero_shift_cap_forces_status_quo(self):
  r,x=solve_milp(self.d,replace(self.p,max_shift_seconds=0));self.assertEqual(x,(0,)*6);self.assertEqual(r['objective_total_wait_sec'],33240)
 def test_tight_headway_changes_feasibility(self):
  self.assertFalse(self.d.feasible(self.x,replace(self.p,headway_deviation_seconds=120)))
 def test_zero_headway_tolerance_forces_status_quo(self):
  r,x=solve_milp(self.d,replace(self.p,headway_deviation_seconds=0));self.assertEqual(x,(0,)*6)
 def test_infeasible_turnaround_certificate(self):
  p=replace(self.p,turnaround_seconds=300,berth_seconds=120);r,x=solve_milp(self.d,p)
  self.assertEqual(r['status'],'INFEASIBLE');self.assertIsNone(x);self.assertTrue(any(c['lower_sec']>c['upper_sec'] for c in r['conflicting_bounds']))
 def test_no_heuristic_from_infeasible_start(self):
  x,t=heuristic(self.d,replace(self.p,turnaround_seconds=300));self.assertIsNone(x);self.assertEqual(t,[])
 def test_exact_readiness_rule(self):
  s,c=self.d.evaluate(self.x,self.p);self.assertEqual(int((c.wait_sec==0).sum()),7)
 def test_one_second_allowance_increase_changes_connections(self):
  a,ac=self.d.evaluate(self.x,self.p);b,bc=self.d.evaluate(self.x,replace(self.p,transfer_seconds=181))
  self.assertEqual(int((ac.caught_trip_id!=bc.caught_trip_id).sum()),7);self.assertGreater(b['mean_wait_min'],a['mean_wait_min'])
 def test_five_minute_stress_not_new_optimization(self):
  p=replace(self.p,transfer_seconds=300);b,_=self.d.evaluate((0,)*6,p);f,_=self.d.evaluate(self.x,p)
  self.assertGreater(f['mean_wait_min'],b['mean_wait_min']);self.assertAlmostEqual(f['mean_wait_min'],15.682926829268293)
 def test_full_after_window_service_retained(self):
  self.assertEqual(int((self.d.outgoing.departure_sec>=68400).sum()),10);self.assertEqual(self.d.outgoing.departure_sec.max(),90000)
 def test_only_penalize_no_remaining_service(self):
  s,c=self.d.evaluate((0,)*6,replace(self.p,transfer_seconds=86400))
  self.assertEqual(s['stranded'],41);self.assertEqual(s['mean_wait_cost_min'],60)
 def test_late_eligible_service_preferred_even_long_wait(self):
  # Change a copy of the data for a unit test only, not the research dataset.
  import copy
  d=copy.deepcopy(self.d);d.a[:]=int(d.nominal.max()-61*60-180)
  # Remove all earlier potential services by shifting their times outside eligibility.
  d.nominal[:-1]=0
  s,c=d.evaluate((0,)*6,self.p)
  self.assertEqual(s['stranded'],0);self.assertAlmostEqual(s['mean_wait_min'],61)
 def test_bad_parameter_rejected(self):
  with self.assertRaises(ValueError):Parameters(transfer_seconds=-1)
  with self.assertRaises(ValueError):Parameters(grid_seconds=0)
 def test_non_grid_shift_rejected(self):self.assertFalse(self.d.feasible([1,0,0,0,0,0],self.p))
 def test_shift_cap_checked_independently(self):self.assertFalse(self.d.feasible([0,360,0,0,0,0],self.p))
 def test_all_38_cases_present(self):self.assertEqual(len(self.table),38)
 def test_exact_and_solver_agreement_recorded(self):
  for row in self.table[self.table.enumeration_status=='EXACT'].itertuples():
   a=json.loads((ROOT/'results/cases'/row.case/'solver.json').read_text());b=json.loads((ROOT/'results/cases'/row.case/'enumeration.json').read_text())
   self.assertAlmostEqual(a['objective_total_wait_sec'],b['optimal_total_wait_sec'])
 def test_all_feasible_solver_gaps_zero(self):
  valid=self.table[self.table.model_status=='OPTIMAL'];self.assertEqual(len(valid),32);self.assertTrue(np.allclose(valid.solver_gap,0,atol=1e-10))
 def test_no_benefit_claim_for_infeasible_cases(self):
  invalid=self.table[self.table.model_status=='INFEASIBLE'];self.assertEqual(len(invalid),6);self.assertTrue(invalid.improvement_pct.isna().all());self.assertTrue(invalid.optimized_mean_wait_min.isna().all())
 def test_full_trajectory_audited(self):
  d=pd.read_csv(ROOT/'results/optimized_complete_trip_stop_times.csv');self.assertEqual(len(d),300)
 def test_original_input_hashes_preserved(self):
  locked=json.loads((ROOT/'validation/baseline_lock.json').read_text())
  for r in locked['locked_inputs']:self.assertEqual(hashlib.sha256((ROOT/r['path']).read_bytes()).hexdigest(),r['sha256'])
 def test_no_julia_success_claim(self):
  status=json.loads((ROOT/'validation/julia_execution_status.json').read_text());self.assertFalse(status['julia_executed'])
 def test_heuristic_not_inferior_in_saved_suite(self):
  v=self.table[self.table.model_status=='OPTIMAL'];self.assertTrue(np.allclose(v.heuristic_mean_wait_min,v.optimized_mean_wait_min,rtol=0,atol=1e-8))
 def test_finer_grid_checked_without_continuous_claim(self):
  r=self.table[self.table.case=='half_minute_grid'].iloc[0];self.assertEqual(r.enumeration_status,'NOT_ENUMERATED_GRID_TOO_LARGE');self.assertAlmostEqual(r.optimized_mean_wait_min,12.463414634146341)
 def test_relaxation_not_declared_feasible_under_full_rules(self):
  rows=pd.read_csv(ROOT/'results/ablations_checked_against_full_rules.csv');self.assertTrue((~rows.feasible).any())
 def test_loss_and_gain_distribution(self):
  d=pd.read_csv(ROOT/'results/individual_transfer_changes.csv');self.assertEqual(d.change_class.value_counts().to_dict(),{'improved':18,'unchanged':16,'worsened':7});self.assertEqual(d.saved_sec.sum(),2580)
 def test_all_block_neighbors_no_overlap(self):
  d=pd.read_csv(ROOT/'results/all_affected_block_no_overlap_audit.csv');self.assertEqual(len(d),33);self.assertTrue(d.no_time_overlap.all())

if __name__=='__main__':unittest.main(verbosity=2)
