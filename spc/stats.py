"""Estimation and hypothesis tests, written out from the formulas.

SciPy is used only for the distribution functions (the t, chi-square, F and normal quantiles and
tail areas), the way a statistics table is used on paper. Every test here is checked against
SciPy's own implementation in tests/test_stats.py.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import stats as sd


@dataclass
class Test:
    """Result of a hypothesis test."""
    name: str
    statistic: float
    p: float
    df: float | tuple | None = None
    effect: float | None = None          # difference of means, ratio, ... (test-specific)
    ci: tuple | None = None              # confidence interval of the effect

    def reject(self, alpha=0.05):
        return self.p < alpha


# ------------------------------------------------------------------ description

def describe(x):
    x = np.asarray(x, float)
    n = x.size
    mean = x.mean()
    s = x.std(ddof=1)
    m2, m3, m4 = (np.mean((x - mean) ** k) for k in (2, 3, 4))
    q1, med, q3 = np.percentile(x, [25, 50, 75])
    return {"n": n, "mean": mean, "sd": s, "min": x.min(), "q1": q1, "median": med, "q3": q3,
            "max": x.max(), "skew": m3 / m2 ** 1.5, "excess_kurtosis": m4 / m2 ** 2 - 3}


# ------------------------------------------------------------------ confidence intervals

def ci_mean(x, conf=0.95):
    """t interval: mean +- t(n-1) * s / sqrt(n)."""
    x = np.asarray(x, float)
    n = x.size
    half = sd.t.ppf(0.5 + conf / 2, n - 1) * x.std(ddof=1) / np.sqrt(n)
    return x.mean() - half, x.mean() + half


def ci_sd(x, conf=0.95):
    """Chi-square interval for the standard deviation of a normal population."""
    x = np.asarray(x, float)
    n, s2 = x.size, x.var(ddof=1)
    a = 1 - conf
    return (np.sqrt((n - 1) * s2 / sd.chi2.ppf(1 - a / 2, n - 1)),
            np.sqrt((n - 1) * s2 / sd.chi2.ppf(a / 2, n - 1)))


def ci_proportion(k, n, conf=0.95):
    """Wilson score interval: keeps its coverage for small n and for proportions near 0,
    where the textbook p +- z*sqrt(p(1-p)/n) interval fails (it gives [0, 0] for k = 0)."""
    z = sd.norm.ppf(0.5 + conf / 2)
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z / (1 + z * z / n) * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return centre - half, centre + half


# ------------------------------------------------------------------ two samples

def welch_t(x, y, conf=0.95):
    """Two-sample t test without assuming equal variances (Welch-Satterthwaite df)."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    vx, vy = x.var(ddof=1) / x.size, y.var(ddof=1) / y.size
    se = np.sqrt(vx + vy)
    df = (vx + vy) ** 2 / (vx ** 2 / (x.size - 1) + vy ** 2 / (y.size - 1))
    diff = x.mean() - y.mean()
    t = diff / se
    half = sd.t.ppf(0.5 + conf / 2, df) * se
    return Test("Welch t", t, 2 * sd.t.sf(abs(t), df), df, diff, (diff - half, diff + half))


def pooled_t(x, y, conf=0.95):
    """Student's two-sample t test with pooled variance (assumes equal variances)."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    nx, ny = x.size, y.size
    sp2 = ((nx - 1) * x.var(ddof=1) + (ny - 1) * y.var(ddof=1)) / (nx + ny - 2)
    se = np.sqrt(sp2 * (1 / nx + 1 / ny))
    diff = x.mean() - y.mean()
    t, df = diff / se, nx + ny - 2
    half = sd.t.ppf(0.5 + conf / 2, df) * se
    return Test("pooled t", t, 2 * sd.t.sf(abs(t), df), df, diff, (diff - half, diff + half))


def paired_t(x, y, conf=0.95):
    d = np.asarray(x, float) - np.asarray(y, float)
    n = d.size
    se = d.std(ddof=1) / np.sqrt(n)
    t = d.mean() / se
    half = sd.t.ppf(0.5 + conf / 2, n - 1) * se
    return Test("paired t", t, 2 * sd.t.sf(abs(t), n - 1), n - 1, d.mean(), (d.mean() - half, d.mean() + half))


def f_test(x, y):
    """F test for equal variances: F = s1^2 / s2^2 (very sensitive to non-normality)."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    f = x.var(ddof=1) / y.var(ddof=1)
    d1, d2 = x.size - 1, y.size - 1
    p = 2 * min(sd.f.cdf(f, d1, d2), sd.f.sf(f, d1, d2))
    return Test("F (variances)", f, p, (d1, d2), f)


def mann_whitney(x, y):
    """Mann-Whitney U (Wilcoxon rank-sum), normal approximation with tie and continuity
    correction. Needs no normality: it compares ranks."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    nx, ny = x.size, y.size
    allv = np.concatenate([x, y])
    ranks = sd.rankdata(allv)
    u = ranks[:nx].sum() - nx * (nx + 1) / 2
    mu = nx * ny / 2
    _, counts = np.unique(allv, return_counts=True)
    n = nx + ny
    var = nx * ny / 12 * ((n + 1) - (counts ** 3 - counts).sum() / (n * (n - 1)))
    z = (abs(u - mu) - 0.5) / np.sqrt(var)
    return Test("Mann-Whitney U", u, 2 * sd.norm.sf(z), None, u / (nx * ny))   # effect: P(X > Y)


def two_proportions(k1, n1, k2, n2, conf=0.95):
    """z test of p1 = p2 with the pooled proportion; CI of p1 - p2 (unpooled)."""
    p1, p2 = k1 / n1, k2 / n2
    p = (k1 + k2) / (n1 + n2)
    z = (p1 - p2) / np.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    se = np.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2)
    half = sd.norm.ppf(0.5 + conf / 2) * se
    return Test("two-proportion z", z, 2 * sd.norm.sf(abs(z)), None, p1 - p2, (p1 - p2 - half, p1 - p2 + half))


# ------------------------------------------------------------------ several groups

def anova_oneway(*groups):
    """One-way ANOVA: between-group variance / within-group variance. Effect: eta squared."""
    groups = [np.asarray(g, float) for g in groups]
    allv = np.concatenate(groups)
    grand = allv.mean()
    ssb = sum(g.size * (g.mean() - grand) ** 2 for g in groups)
    ssw = sum(((g - g.mean()) ** 2).sum() for g in groups)
    k, n = len(groups), allv.size
    f = (ssb / (k - 1)) / (ssw / (n - k))
    return Test("one-way ANOVA", f, sd.f.sf(f, k - 1, n - k), (k - 1, n - k), ssb / (ssb + ssw))


def levene(*groups):
    """Brown-Forsythe version of Levene's test: ANOVA on |x - group median|."""
    dev = [np.abs(np.asarray(g, float) - np.median(g)) for g in groups]
    r = anova_oneway(*dev)
    return Test("Levene (median)", r.statistic, r.p, r.df)


def kruskal_wallis(*groups):
    """Rank-based alternative to ANOVA, with tie correction."""
    groups = [np.asarray(g, float) for g in groups]
    allv = np.concatenate(groups)
    n = allv.size
    ranks = sd.rankdata(allv)
    h, start = 0.0, 0
    for g in groups:
        r = ranks[start:start + g.size]
        h += r.sum() ** 2 / g.size
        start += g.size
    h = 12 / (n * (n + 1)) * h - 3 * (n + 1)
    _, counts = np.unique(allv, return_counts=True)
    h /= 1 - (counts ** 3 - counts).sum() / (n ** 3 - n)
    return Test("Kruskal-Wallis", h, sd.chi2.sf(h, len(groups) - 1), len(groups) - 1)


def chi2_independence(table):
    """Chi-square test of independence for a contingency table. Effect: Cramer's V.
    Also returns the expected counts, to check the rule of thumb (all >= 5)."""
    obs = np.asarray(table, float)
    expected = obs.sum(1, keepdims=True) * obs.sum(0, keepdims=True) / obs.sum()
    chi2 = ((obs - expected) ** 2 / expected).sum()
    df = (obs.shape[0] - 1) * (obs.shape[1] - 1)
    v = np.sqrt(chi2 / (obs.sum() * (min(obs.shape) - 1)))
    t = Test("chi-square independence", chi2, sd.chi2.sf(chi2, df), df, v)
    t.expected = expected
    return t


def chi2_gof_normal(x, bins=6):
    """Chi-square goodness-of-fit test for normality: `bins` classes of equal probability under the
    fitted normal, so every expected count is n / bins. df = bins - 1 - 2 (mean and SD estimated)."""
    x = np.asarray(x, float)
    n = x.size
    edges = x.mean() + x.std(ddof=1) * sd.norm.ppf(np.arange(1, bins) / bins)
    observed = np.bincount(np.searchsorted(edges, x), minlength=bins)
    expected = n / bins
    chi2 = float(((observed - expected) ** 2 / expected).sum())
    t = Test("chi-square goodness of fit (normal)", chi2, float(sd.chi2.sf(chi2, bins - 3)), bins - 3)
    t.observed = observed
    return t


# ------------------------------------------------------------------ correlation and regression

def pearson(x, y, conf=0.95):
    """Pearson r, t test of rho = 0, and the Fisher z confidence interval."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    n = x.size
    r = float(np.corrcoef(x, y)[0, 1])
    t = r * np.sqrt((n - 2) / (1 - r * r))
    zr, half = np.arctanh(r), sd.norm.ppf(0.5 + conf / 2) / np.sqrt(n - 3)
    return Test("Pearson r", t, 2 * sd.t.sf(abs(t), n - 2), n - 2, r, (np.tanh(zr - half), np.tanh(zr + half)))


@dataclass
class LinReg:
    a: float          # intercept
    b: float          # slope
    se_a: float
    se_b: float
    s: float          # residual standard deviation
    r2: float
    n: int
    xbar: float
    sxx: float

    def t_slope(self):
        t = self.b / self.se_b
        return Test("slope t", t, 2 * sd.t.sf(abs(t), self.n - 2), self.n - 2, self.b, self.ci_slope())

    def ci_slope(self, conf=0.95):
        half = sd.t.ppf(0.5 + conf / 2, self.n - 2) * self.se_b
        return self.b - half, self.b + half

    def predict(self, x0, conf=0.95, interval="mean"):
        """Fitted value with a confidence band for the mean ('mean') or for one new
        observation ('prediction')."""
        x0 = np.asarray(x0, float)
        y = self.a + self.b * x0
        extra = 1.0 if interval == "prediction" else 0.0
        half = sd.t.ppf(0.5 + conf / 2, self.n - 2) * self.s * np.sqrt(extra + 1 / self.n + (x0 - self.xbar) ** 2 / self.sxx)
        return y, y - half, y + half


def linreg(x, y):
    """Least squares y = a + b x with standard errors."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    n = x.size
    xbar, ybar = x.mean(), y.mean()
    sxx = ((x - xbar) ** 2).sum()
    b = ((x - xbar) * (y - ybar)).sum() / sxx
    a = ybar - b * xbar
    resid = y - a - b * x
    s = np.sqrt((resid ** 2).sum() / (n - 2))
    r2 = 1 - (resid ** 2).sum() / ((y - ybar) ** 2).sum()
    return LinReg(a, b, s * np.sqrt(1 / n + xbar ** 2 / sxx), s / np.sqrt(sxx), s, r2, n, xbar, sxx)


def hinge_fit(x, y, candidates):
    """Segmented regression y = a + b * max(0, x - tau): flat, then a straight rise from an unknown
    change point tau. tau is found by trying every candidate and keeping the smallest residual sum
    of squares. Returns (tau, a, b, sse) and the SSE curve over the candidates."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    best, curve = None, []
    for tau in candidates:
        h = np.maximum(0, x - tau)
        A = np.column_stack([np.ones_like(x), h])
        coef, *_ = np.linalg.lstsq(A, y, rcond=None)
        sse = float(((y - A @ coef) ** 2).sum())
        curve.append(sse)
        if best is None or sse < best[3]:
            best = (float(tau), float(coef[0]), float(coef[1]), sse)
    return best, np.array(curve)


# ------------------------------------------------------------------ normality

def normal_qq(x):
    """Theoretical normal quantiles (Blom positions) against the sorted data."""
    x = np.sort(np.asarray(x, float))
    n = x.size
    q = sd.norm.ppf((np.arange(1, n + 1) - 0.375) / (n + 0.25))
    return q, x


def shapiro(x):
    w, p = sd.shapiro(x)          # the W coefficients need tables; SciPy's implementation is used
    return Test("Shapiro-Wilk", float(w), float(p))
