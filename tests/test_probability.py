"""The probability functions against SciPy and against results that can be checked by hand."""
import pytest
from scipy import stats as sd

from spc import probability as pr


def test_binomial_matches_scipy():
    for n, p in ((90, 0.0085), (20, 0.3), (5, 0.5)):
        for k in range(0, n + 1, max(1, n // 7)):
            assert pr.binom_pmf(k, n, p) == pytest.approx(sd.binom.pmf(k, n, p), rel=1e-9)
            assert pr.binom_sf(k, n, p) == pytest.approx(sd.binom.sf(k - 1, n, p), rel=1e-9)
        assert sum(pr.binom_pmf(k, n, p) for k in range(n + 1)) == pytest.approx(1)
        assert pr.binom_mean_var(n, p) == pytest.approx((sd.binom.mean(n, p), sd.binom.var(n, p)))


def test_poisson_matches_scipy_and_approximates_the_binomial():
    for lam in (0.5, 0.765, 4.0):
        for k in range(8):
            assert pr.poisson_pmf(k, lam) == pytest.approx(sd.poisson.pmf(k, lam), rel=1e-9)
            assert pr.poisson_sf(k, lam) == pytest.approx(sd.poisson.sf(k - 1, lam), rel=1e-9, abs=1e-15)
    # large n, small p: Poisson(n p) is close to Binomial(n, p)
    assert pr.poisson_pmf(2, 1.0) == pytest.approx(pr.binom_pmf(2, 1000, 0.001), rel=0.01)


def test_bayes_by_hand():
    # 1000 parts: 10 bad (9.9 caught), 990 good (4.95 rejected) -> 9.9 / 14.85
    assert pr.bayes_posterior(0.01, 0.99, 0.005) == pytest.approx(9.9 / 14.85)
    assert pr.bayes_posterior(0.5, 1.0, 0.0) == 1
    # a worse false-alarm rate makes a FAIL less trustworthy
    assert pr.bayes_posterior(0.01, 0.99, 0.05) < pr.bayes_posterior(0.01, 0.99, 0.005)


def test_independent_stations_multiply():
    assert pr.first_pass_all_good([0.1, 0.2]) == pytest.approx(0.72)
    assert pr.first_pass_all_good([]) == 1


def test_report_finds_friday_far_outside_chance():
    import probability
    text = probability.main()
    assert "8 of 90 failed" in text and "3 of 353" in text
    assert pr.binom_sf(8, 90, 3 / 353) < 1e-5
