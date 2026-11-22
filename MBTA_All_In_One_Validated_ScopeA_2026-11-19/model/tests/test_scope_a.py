import sys,json,unittest
from pathlib import Path
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from reference_enumeration import loads, evaluate, valid_shift_tuple

class ScopeAReproducibility(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inc,cls.out,cls.mov,cls.links,cls.hd,cls.limits,cls.config=loads()
        cls.prev=json.loads((ROOT/'results/enumeration_results.json').read_text())
        cls.ids=list(cls.mov.trip_id)
    def test_study_counts(self):
        self.assertEqual(self.inc.groupby('route_id').size().to_dict(),{'22':18,'23':23})
        self.assertEqual(int(self.out.is_adjustable.sum()),6)
        self.assertEqual(len(self.out),37)
    def test_zero_feasible(self):
        self.assertTrue(valid_shift_tuple((0,)*6,self.ids,self.links,self.hd))
    def test_best_feasible(self):
        self.assertTrue(valid_shift_tuple(self.prev['best_shift_vector_min'],self.ids,self.links,self.hd))
    def test_roundtrip_baseline(self):
        base,detail,_=evaluate(self.inc,self.out,self.mov,(0,)*6)
        self.assertEqual(base['total_platform_wait_sec'],33240)
        self.assertAlmostEqual(base['mean_platform_wait_min'],13.512195121951219)
        self.assertEqual(base['max_platform_wait_min'],30)
        self.assertEqual(base['connections_at_or_under_10min'],15)
    def test_model_optimum_vs_evaluator(self):
        best,detail,_=evaluate(self.inc,self.out,self.mov,self.prev['best_shift_vector_min'])
        self.assertEqual(best['total_platform_wait_sec'],30660)
        self.assertAlmostEqual(best['mean_platform_wait_min'],12.463414634146341)
        self.assertEqual(best['connections_at_or_under_10min'],20)
        self.assertEqual(best['max_platform_wait_min'],27)
    def test_trip_schedule_consistency(self):
        st=pd.read_csv(ROOT/'inputs/selected_trip_stop_times.csv',dtype={'trip_id':str})
        def clock(t): h,m,s=map(int,t.split(':'));return 3600*h+60*m+s
        for trip,g in st.groupby('trip_id'):
            original=[clock(t) for t in g.departure_time]
            shift=dict(zip(self.ids,self.prev['best_shift_vector_min']))[trip]
            shifted=[x+60*shift for x in original]
            self.assertEqual(np.diff(original).tolist(),np.diff(shifted).tolist())
    def test_all_connections_eligible(self):
        for shifts in [(0,)*6, self.prev['best_shift_vector_min']]:
            _,detail,dep=evaluate(self.inc,self.out,self.mov,shifts)
            for row in detail.itertuples():
                self.assertEqual(row.caught_departure_sec-row.ready_sec,row.platform_wait_sec)
                self.assertGreaterEqual(row.platform_wait_sec,0)
    def test_after_window_departures(self):
        _,detail,dep=evaluate(self.inc,self.out,self.mov,(0,)*6)
        self.assertEqual(int(detail.caught_after_1900.sum()),2)
        self.assertGreaterEqual(len(dep[dep.actual_departure_sec>=19*3600]),10)
    def test_increase_and_decrease_opportunities(self):
        changes=pd.read_csv(ROOT/'results/per_opportunity_changes.csv')
        self.assertEqual(sum(changes.saved_sec>0),18)
        self.assertEqual(sum(changes.saved_sec<0),7)
        self.assertEqual(sum(changes.saved_sec==0),16)
        self.assertEqual(changes.saved_sec.sum(),2580)
    def test_consistency_model_input_penalty(self):
        self.assertEqual(self.config['stranded_penalty_seconds'],3600)
        self.assertEqual(self.config['transfer_allowance_seconds'],180)
        par=pd.read_csv(ROOT/'inputs/model_parameters.csv')
        self.assertEqual(int(par[par.parameter=='stranded_penalty_seconds'].value.iloc[0]),3600)
    def test_hist_archive_signature(self):
        import hashlib
        p=Path('/mnt/data/20261014.zip')
        if p.exists():
            self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(), '1b5cf25363f7385de8c22c22fe6a336d91dd68616494526ca14994e3b86dd004')

if __name__=='__main__':unittest.main(verbosity=2)

# Cross-check artifact validation is placed after the original unittest.main
# so it runs through `python -m unittest discover` but not in direct script mode.
class SciPyMIPCertificate(unittest.TestCase):
    def test_mip_matches_enumeration(self):
        p=ROOT/'results/scipy_milp_crosscheck.json'
        s=json.loads(p.read_text());e=json.loads((ROOT/'results/enumeration_results.json').read_text())
        self.assertTrue(s['success']);self.assertEqual(s['mip_gap'],0.0)
        self.assertAlmostEqual(s['objective_mean_wait_minutes'],e['best']['mean_platform_wait_min'])
        self.assertEqual(s['shift_vector_minutes'],e['best_shift_vector_min'])
