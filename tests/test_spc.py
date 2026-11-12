"""Control charts and capability: constants, run rules, false-alarm rates and interval coverage."""
import numpy as np
import pytest

from spc import capability as cap
from spc import charts


@pytest.mark.parametrize("n", [2, 3, 5, 8, 10])
def test_d2_constant_by_simulation(n):
    """d2 = expected range of n standard normal values."""
    r = np.random.default_rng(n)
    rng_ = np.ptp(r.standard_normal((200_000, n)), axis=1).mean()
    assert rng_ == pytest.approx(charts.CONSTANTS[n]["d2"], abs=0.01)


@pytest.mark.parametrize("n", [2, 4, 5, 9])
def test_a2_matches_d2(n):
    c = charts.CONSTANTS[n]
    assert c["A2"] == pytest.approx(3 / (c["d2"] * np.sqrt(n)), abs=0.002)


def test_imr_sigma_estimate_is_unbiased():
    r = np.random.default_rng(3)
    est = [charts.imr_limits(r.normal(0, 2, 200))[0].sigma for _ in range(500)]
    assert np.mean(est) == pytest.approx(2, rel=0.02)


def test_moving_range_ignores_slow_drift():
    """The within-sigma from the moving range barely notices a drift that inflates the overall SD."""
    r = np.random.default_rng(4)
    x = r.normal(0, 1, 300) + np.linspace(0, 6, 300)
    ind, _ = charts.imr_limits(x)
    assert ind.sigma == pytest.approx(1, rel=0.1)
    assert x.std(ddof=1) > 1.7


def _lim():
    return charts.Limits(0.0, -3.0, 3.0, 1.0)


def test_rule1_beyond_three_sigma():
    x = np.zeros(10)
    x[6] = 3.2
    assert charts.western_electric(x, _lim())[1] == [6]


def test_rule2_two_of_three_beyond_two_sigma():
    x = np.array([0, 0, 2.5, 0.5, 2.4, 0, 0, 0.0])
    s = charts.western_electric(x, _lim())
    assert s[2] == [4]
    assert s[1] == []


def test_rule3_four_of_five_beyond_one_sigma():
    x = np.array([0, -1.5, -1.2, 0.3, -1.1, -1.9, 0, 0.0])
    assert charts.western_electric(x, _lim())[3] == [5]


def test_rule4_eight_on_one_side():
    x = np.array([-0.1] + [0.2] * 8)
    s = charts.western_electric(x, _lim())
    assert s[4] == [8]
    assert charts.first_signal(s) == 8


def test_false_alarm_rates_in_control():
    """Rule 1 alone: about 0.27 % of points; all four rules together: several times more."""
    r = np.random.default_rng(5)
    x = r.standard_normal(200_000)
    s = charts.western_electric(x, _lim())
    assert len(s[1]) / x.size == pytest.approx(0.0027, abs=0.0006)
    any_rule = len({i for v in s.values() for i in v}) / x.size
    assert 0.008 < any_rule < 0.03


def test_ewma_steady_state_width_and_earlier_detection():
    z, lo, hi = charts.ewma_chart(np.zeros(200), 0, 1, lam=0.2, L=3)
    assert hi[-1] == pytest.approx(3 * np.sqrt(0.2 / 1.8))
    # a 1-sigma shift: EWMA signals sooner than rule 1 on average
    r = np.random.default_rng(6)
    ew, r1 = [], []
    for _ in range(300):
        x = r.standard_normal(300) + 1.0
        z, lo, hi = charts.ewma_chart(x, 0, 1)
        ew.append(int(np.argmax((z > hi) | (z < lo))))
        r1.append(int(np.argmax(np.abs(x) > 3)))
    assert np.mean(ew) < np.mean(r1) / 2


def test_xbar_r_limits():
    r = np.random.default_rng(7)
    sub = r.normal(10, 0.5, (400, 5))
    xl, rl, sigma = charts.xbar_r_limits(sub)
    assert sigma == pytest.approx(0.5, rel=0.03)
    assert xl.ucl - xl.centre == pytest.approx(3 * 0.5 / np.sqrt(5), rel=0.03)
    assert rl.lcl == 0


def test_p_chart_limits_widen_for_small_periods():
    p, pb, lcl, ucl = charts.p_chart([1, 1], [30, 300], p_bar=0.02)
    assert ucl[0] > ucl[1]
    assert (lcl >= 0).all()


def test_capability_known_values():
    r = np.random.default_rng(8)
    x = r.normal(10, 1, 20_000)
    c = cap.capability(x, 7, 14, sigma_within=1.0)
    assert c["Cp"] == pytest.approx(7 / 6, rel=0.01)
    assert c["Cpk"] == pytest.approx(1.0, rel=0.01)
    assert c["Ppk"] == pytest.approx(1.0, rel=0.02)
    assert c["ppm"] == pytest.approx(1e6 * (0.00135 + 0.0000317), rel=0.15)


def test_one_sided_capability_has_no_cp():
    c = cap.capability(np.random.default_rng(9).normal(1, 0.25, 50), None, 2.0)
    assert "Cp" not in c
    assert c["Cpk"] > 1


def test_cpk_interval_coverage():
    """Bissell's interval should cover the true Cpk about 95 % of the time for n = 50."""
    r = np.random.default_rng(10)
    true_cpk = (2.0 - 1.0) / (3 * 0.25)
    hits = 0
    for _ in range(2000):
        s = r.normal(1.0, 0.25, 50)
        c = cap.capability(s, None, 2.0, sigma_within=s.std(ddof=1))
        hits += c["Cpk_ci"][0] <= true_cpk <= c["Cpk_ci"][1]
    assert hits / 2000 == pytest.approx(0.95, abs=0.025)


def test_cp_interval_coverage():
    r = np.random.default_rng(11)
    hits = 0
    for _ in range(2000):
        s = r.normal(0, 1, 30)
        c = cap.capability(s, -4, 4, sigma_within=s.std(ddof=1))
        hits += c["Cp_ci"][0] <= 8 / 6 <= c["Cp_ci"][1]
    assert hits / 2000 == pytest.approx(0.95, abs=0.02)


def test_sample_size_for_cpk():
    n = cap.n_for_cpk_precision(1.33, 0.10)
    assert 300 < n < 500
    assert cap.n_for_cpk_precision(1.33, 0.2) < n
