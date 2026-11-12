"""Every hand-written test against SciPy's implementation, and the confidence intervals against
their promised coverage by simulation."""
import numpy as np
import pytest
from scipy import stats as sd

from spc import stats as st

rng = np.random.default_rng(42)
X = rng.normal(10, 2, 40)
Y = rng.normal(11, 3, 55)


def test_describe():
    d = st.describe(X)
    assert d["mean"] == pytest.approx(X.mean())
    assert d["sd"] == pytest.approx(X.std(ddof=1))
    assert d["skew"] == pytest.approx(sd.skew(X))
    assert d["excess_kurtosis"] == pytest.approx(sd.kurtosis(X))


def test_ci_mean_matches_scipy():
    lo, hi = st.ci_mean(X)
    ref = sd.t.interval(0.95, X.size - 1, loc=X.mean(), scale=sd.sem(X))
    assert (lo, hi) == pytest.approx(ref)


def test_welch_and_pooled_match_scipy():
    w = st.welch_t(X, Y)
    ref = sd.ttest_ind(X, Y, equal_var=False)
    assert w.statistic == pytest.approx(ref.statistic)
    assert w.p == pytest.approx(ref.pvalue)
    assert w.ci == pytest.approx(tuple(ref.confidence_interval()))
    p = st.pooled_t(X, Y)
    ref = sd.ttest_ind(X, Y)
    assert (p.statistic, p.p) == pytest.approx((ref.statistic, ref.pvalue))


def test_paired_matches_scipy():
    a, b = X, X + rng.normal(0.3, 1, X.size)
    r = st.paired_t(a, b)
    ref = sd.ttest_rel(a, b)
    assert (r.statistic, r.p) == pytest.approx((ref.statistic, ref.pvalue))


def test_mann_whitney_matches_scipy():
    xr, yr = np.round(X, 0), np.round(Y, 0)          # with ties
    r = st.mann_whitney(xr, yr)
    ref = sd.mannwhitneyu(xr, yr, method="asymptotic", use_continuity=True)
    assert r.statistic == pytest.approx(ref.statistic)
    assert r.p == pytest.approx(ref.pvalue)


def test_anova_levene_kruskal_match_scipy():
    groups = [rng.normal(m, 1 + i * 0.2, 20 + 3 * i) for i, m in enumerate((0, 0.3, 0.8, 0.1))]
    a = st.anova_oneway(*groups)
    ref = sd.f_oneway(*groups)
    assert (a.statistic, a.p) == pytest.approx((ref.statistic, ref.pvalue))
    lv = st.levene(*groups)
    ref = sd.levene(*groups, center="median")
    assert (lv.statistic, lv.p) == pytest.approx((ref.statistic, ref.pvalue))
    rounded = [np.round(g, 1) for g in groups]
    kw = st.kruskal_wallis(*rounded)
    ref = sd.kruskal(*rounded)
    assert (kw.statistic, kw.p) == pytest.approx((ref.statistic, ref.pvalue))


def test_chi2_matches_scipy():
    table = np.array([[12, 340], [7, 410], [3, 200]])
    r = st.chi2_independence(table)
    ref = sd.chi2_contingency(table, correction=False)
    assert (r.statistic, r.p, r.df) == pytest.approx((ref.statistic, ref.pvalue, ref.dof))
    assert r.expected == pytest.approx(ref.expected_freq)


def test_f_test_two_sided():
    r = st.f_test(X, Y)
    assert r.statistic == pytest.approx(X.var(ddof=1) / Y.var(ddof=1))
    assert 0 < r.p <= 1


def test_two_proportions_equals_chi2_on_2x2():
    # the pooled z test squared is the chi-square statistic of the 2x2 table
    k1, n1, k2, n2 = 8, 155, 17, 916
    z = st.two_proportions(k1, n1, k2, n2)
    chi = st.chi2_independence([[k1, n1 - k1], [k2, n2 - k2]])
    assert z.statistic ** 2 == pytest.approx(chi.statistic)
    assert z.p == pytest.approx(chi.p)


def test_linreg_matches_scipy():
    x = np.linspace(0, 10, 30)
    y = 2 + 0.5 * x + rng.normal(0, 1, x.size)
    r = st.linreg(x, y)
    ref = sd.linregress(x, y)
    assert (r.a, r.b, r.se_b, r.se_a) == pytest.approx((ref.intercept, ref.slope, ref.stderr, ref.intercept_stderr))
    assert r.r2 == pytest.approx(ref.rvalue ** 2)
    assert r.t_slope().p == pytest.approx(ref.pvalue)
    # the prediction band is wider than the band of the mean
    _, lo_m, hi_m = r.predict(5.0)
    _, lo_p, hi_p = r.predict(5.0, interval="prediction")
    assert hi_p - lo_p > hi_m - lo_m


def test_pearson_matches_scipy():
    x = rng.normal(size=50)
    y = 0.4 * x + rng.normal(size=50)
    r = st.pearson(x, y)
    ref = sd.pearsonr(x, y)
    assert (r.effect, r.p) == pytest.approx((ref.statistic, ref.pvalue))
    assert r.ci == pytest.approx(tuple(ref.confidence_interval()))


def test_hinge_fit_finds_a_known_change_point():
    x = np.linspace(0, 5, 400)
    y = 1 + 0.4 * np.maximum(0, x - 2.2) + rng.normal(0, 0.1, x.size)
    (tau, a, b, _), _ = st.hinge_fit(x, y, np.arange(0.5, 4.5, 0.05))
    assert tau == pytest.approx(2.2, abs=0.15)
    assert a == pytest.approx(1, abs=0.05)
    assert b == pytest.approx(0.4, abs=0.05)


@pytest.mark.parametrize("n", [8, 30])
def test_ci_mean_and_sd_coverage(n):
    """A 95 % interval must contain the true value in about 95 % of repeated samples."""
    r = np.random.default_rng(n)
    hits_m = hits_s = 0
    trials = 4000
    for _ in range(trials):
        s = r.normal(5, 2, n)
        lo, hi = st.ci_mean(s)
        hits_m += lo <= 5 <= hi
        lo, hi = st.ci_sd(s)
        hits_s += lo <= 2 <= hi
    assert hits_m / trials == pytest.approx(0.95, abs=0.015)
    assert hits_s / trials == pytest.approx(0.95, abs=0.015)


def test_wilson_keeps_coverage_where_wald_fails():
    """At p = 2 % and n = 100 the textbook (Wald) interval covers far less than 95 %; Wilson does not."""
    r = np.random.default_rng(1)
    p, n, trials = 0.02, 100, 5000
    k = r.binomial(n, p, trials)
    wilson = np.mean([lo <= p <= hi for lo, hi in (st.ci_proportion(kk, n) for kk in k)])
    ph = k / n
    half = 1.96 * np.sqrt(ph * (1 - ph) / n)
    wald = np.mean((ph - half <= p) & (p <= ph + half))
    assert wilson > 0.92
    assert wald < 0.90


def test_ci_proportion_zero_failures_is_not_empty():
    lo, hi = st.ci_proportion(0, 57)
    assert lo == pytest.approx(0, abs=1e-12)
    assert hi > 0.05


def test_chi2_gof_matches_scipy_and_rejects_non_normal_data():
    r = st.chi2_gof_normal(X, bins=6)
    ref = sd.chisquare(r.observed, ddof=2)
    assert (r.statistic, r.p) == pytest.approx((ref.statistic, ref.pvalue))
    assert r.observed.sum() == X.size
    assert not r.reject()
    assert st.chi2_gof_normal(np.random.default_rng(3).exponential(1, 300)).reject()
