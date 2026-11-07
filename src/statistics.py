"""Single primary comparison: ad minus psa. Rates are fractions, not percents."""
import math
import numpy as np
from scipy import stats
from scipy.optimize import brentq


def wilson(successes,n,alpha=.05):
    if n<=0 or not 0<=successes<=n or not 0<alpha<1:
        raise ValueError('Invalid binomial counts or alpha')
    p=successes/n; z=stats.norm.ppf(1-alpha/2)
    center=(p+z*z/(2*n))/(1+z*z/n)
    radius=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/(1+z*z/n)
    return max(0.,center-radius),min(1.,center+radius)


def compare(success_control,n_control,success_test,n_test,alpha=.05):
    lc,uc=wilson(success_control,n_control,alpha)
    lt,ut=wilson(success_test,n_test,alpha)
    p0=success_control/n_control; p1=success_test/n_test; diff=p1-p0
    # Newcombe hybrid-score interval for two independent binomial proportions.
    low=diff-math.sqrt((p1-lt)**2+(uc-p0)**2)
    high=diff+math.sqrt((ut-p1)**2+(p0-lc)**2)
    pooled=(success_control+success_test)/(n_control+n_test)
    se=math.sqrt(pooled*(1-pooled)*(1/n_control+1/n_test))
    z=diff/se if se else 0.
    return {'control_rate':p0,'test_rate':p1,'difference':diff,
            'ci_low':low,'ci_high':high,'relative_lift':diff/p0 if p0 else None,
            'z_statistic':z,'p_value':float(2*stats.norm.sf(abs(z))),
            'alpha':alpha,'method':'two-sided pooled z-test; Newcombe-Wilson confidence interval',
            'assumptions':'Independent user-level observations and valid group assignment; provenance is incomplete.'}


def planned_power(n_control,p0,delta,ratio=1.,alpha=.05):
    if n_control<=0 or ratio<=0 or not 0<p0<1 or not 0<p0+delta<1 or not 0<alpha<1:
        raise ValueError('Invalid planning parameters')
    n_test=n_control*ratio; p1=p0+delta
    pooled=(p0+ratio*p1)/(1+ratio)
    se0=math.sqrt(pooled*(1-pooled)*(1/n_control+1/n_test))
    se1=math.sqrt(p0*(1-p0)/n_control+p1*(1-p1)/n_test)
    critical=stats.norm.ppf(1-alpha/2)*se0
    return float(stats.norm.sf((critical-delta)/se1)+stats.norm.cdf((-critical-delta)/se1))


def required_sample(p0=.02,delta=.005,ratio=1.,power=.8,alpha=.05):
    if not 0<power<1:
        raise ValueError('power must be between 0 and 1')
    n=math.ceil(brentq(lambda n:planned_power(n,p0,delta,ratio,alpha)-power,2,100_000_000))
    return {'assumed_control_rate':p0,'absolute_mde':delta,'target_power':power,
            'test_to_control_ratio':ratio,'alpha':alpha,
            'control_users':n,'test_users':math.ceil(n*ratio),
            'note':'Normal approximation for a future experiment; not observed/post-hoc power.'}


def aa_simulation(repeats=10000,n_per_group=10000,p=.02,seed=2026,alpha=.05):
    rng=np.random.default_rng(seed)
    a=rng.binomial(n_per_group,p,repeats); b=rng.binomial(n_per_group,p,repeats)
    pooled=(a+b)/(2*n_per_group)
    se=np.sqrt(pooled*(1-pooled)*2/n_per_group)
    z=np.divide((b-a)/n_per_group,se,out=np.zeros(repeats),where=se>0)
    pvalues=2*stats.norm.sf(np.abs(z))
    rejections=int(np.sum(pvalues<alpha))
    return {'repeats':repeats,'users_per_group':n_per_group,'assumed_rate':p,
            'seed':seed,'alpha':alpha,'false_positive_rate':rejections/repeats,
            'rate_ci':list(wilson(rejections,repeats)),
            'note':'Synthetic null simulations, not an A/A test on the historical dataset.'},pvalues
