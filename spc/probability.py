"""The probability half of the course (lectures 1-6) on the same production data:
conditional probability and Bayes' theorem, the binomial and Poisson distributions,
expected value and variance. Formulas written out; tests compare them with SciPy."""
from __future__ import annotations

import math


def bayes_posterior(prior: float, sensitivity: float, false_alarm: float) -> float:
    """P(part is bad | test says FAIL).

    prior        P(bad): share of truly bad parts
    sensitivity  P(FAIL | bad): the tester catches a bad part
    false_alarm  P(FAIL | good): the tester rejects a good part
    Law of total probability for the denominator, then Bayes' theorem.
    """
    p_fail = sensitivity * prior + false_alarm * (1 - prior)
    return sensitivity * prior / p_fail


def binom_pmf(k: int, n: int, p: float) -> float:
    """P(X = k) for X ~ Binomial(n, p): k failures in n independent parts."""
    return math.comb(n, k) * p ** k * (1 - p) ** (n - k)


def binom_sf(k: int, n: int, p: float) -> float:
    """P(X >= k): the chance of at least k failures if the failure rate were p."""
    return sum(binom_pmf(i, n, p) for i in range(k, n + 1))


def binom_mean_var(n: int, p: float) -> tuple[float, float]:
    """E[X] = n p, Var[X] = n p (1 - p)."""
    return n * p, n * p * (1 - p)


def poisson_pmf(k: int, lam: float) -> float:
    """P(X = k) for X ~ Poisson(lam): rare events, lam = n p."""
    return math.exp(-lam) * lam ** k / math.factorial(k)


def poisson_sf(k: int, lam: float) -> float:
    """P(X >= k) for a Poisson count."""
    return 1 - sum(poisson_pmf(i, lam) for i in range(k))


def first_pass_all_good(p_fail_each: list[float]) -> float:
    """Independent stations in a row: P(no station fails) = product of the pass probabilities."""
    out = 1.0
    for p in p_fail_each:
        out *= 1 - p
    return out
