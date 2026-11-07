import unittest
import math
import pandas as pd
from scipy import stats
from src.data import validate
from src.statistics import wilson,compare,required_sample,planned_power,aa_simulation


class StatisticsTests(unittest.TestCase):
    def test_zero_and_all_success_intervals(self):
        low,high=wilson(0,10)
        self.assertAlmostEqual(low,0); self.assertGreater(high,0)
        low,high=wilson(10,10)
        self.assertLess(low,1); self.assertAlmostEqual(high,1)

    def test_invalid_counts(self):
        for k,n in [(0,0),(-1,10),(11,10)]:
            with self.assertRaises(ValueError): wilson(k,n)

    def test_z_matches_independent_chi_square(self):
        result=compare(420,23524,14423,564577)
        _,p,_,_=stats.chi2_contingency([[420,23524-420],[14423,564577-14423]],correction=False)
        self.assertAlmostEqual(result['p_value']/p,1.,places=9)

    def test_swap_reverses_effect_not_significance(self):
        a=compare(20,1000,40,1000); b=compare(40,1000,20,1000)
        self.assertAlmostEqual(a['difference'],-b['difference'])
        self.assertAlmostEqual(a['ci_low'],-b['ci_high'])
        self.assertAlmostEqual(a['p_value'],b['p_value'])

    def test_equal_groups_and_zero_baseline(self):
        result=compare(0,100,0,100)
        self.assertEqual(result['p_value'],1); self.assertIsNone(result['relative_lift'])
        self.assertLess(result['ci_low'],0); self.assertGreater(result['ci_high'],0)

    def test_planning_reaches_target_and_harder_mde_needs_more(self):
        plan=required_sample(delta=.005)
        self.assertGreaterEqual(planned_power(plan['control_users'],.02,.005),.8)
        self.assertGreater(required_sample(delta=.0025)['control_users'],plan['control_users'])

    def test_simulation_seed_reproducible(self):
        a,_=aa_simulation(repeats=1000,seed=7); b,_=aa_simulation(repeats=1000,seed=7)
        self.assertEqual(a,b)
        self.assertGreater(a['false_positive_rate'],.02)
        self.assertLess(a['false_positive_rate'],.08)


class QualityTests(unittest.TestCase):
    def fixture(self):
        return pd.DataFrame({'Unnamed: 0':[0,1],'user id':[1,2],'test group':['ad','psa'],
                             'converted':[True,False],'total ads':[2,4],
                             'most ads day':['Monday','Friday'],'most ads hour':[1,23]})

    def test_normalizes_valid_data(self):
        f=validate(self.fixture()); self.assertEqual(len(f),2)
        self.assertNotIn('Unnamed: 0',f); self.assertEqual(f.converted.sum(),1)

    def test_duplicate_missing_and_invalid_values_fail(self):
        for col,value in [('user id',1),('most ads hour',24),('converted','unknown'),('test group','other'),('total ads',-1),('most ads day',None)]:
            f=self.fixture(); f[col]=f[col].astype(object); f.loc[1,col]=value
            with self.subTest(col=col),self.assertRaises(ValueError): validate(f)

    def test_unexpected_export_index_fails(self):
        f=self.fixture(); f['Unnamed: 0']=[5,8]
        with self.assertRaises(ValueError): validate(f)


if __name__=='__main__': unittest.main()
