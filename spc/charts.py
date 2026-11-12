"""Shewhart control charts, the Western Electric run rules and an EWMA chart.

Control limits describe what the process *does* (its own variation), specification limits what
the customer *wants*. A point outside the control limits means the process has changed, even if
the part is still inside the specification: that is how SPC warns before parts fail.

Phase I: compute the limits from a period known to be stable. Phase II: keep the limits fixed and
plot new data against them.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

# Control chart constants for subgroup size n (ASTM / Montgomery tables).
# d2 = E[range] / sigma for normal data; A2 = 3 / (d2 sqrt n); D3, D4 = range chart factors.
CONSTANTS = {
    2: {"d2": 1.128, "A2": 1.880, "D3": 0.0, "D4": 3.267},
    3: {"d2": 1.693, "A2": 1.023, "D3": 0.0, "D4": 2.574},
    4: {"d2": 2.059, "A2": 0.729, "D3": 0.0, "D4": 2.282},
    5: {"d2": 2.326, "A2": 0.577, "D3": 0.0, "D4": 2.114},
    6: {"d2": 2.534, "A2": 0.483, "D3": 0.0, "D4": 2.004},
    7: {"d2": 2.704, "A2": 0.419, "D3": 0.076, "D4": 1.924},
    8: {"d2": 2.847, "A2": 0.373, "D3": 0.136, "D4": 1.864},
    9: {"d2": 2.970, "A2": 0.337, "D3": 0.184, "D4": 1.816},
    10: {"d2": 3.078, "A2": 0.308, "D3": 0.223, "D4": 1.777},
}


@dataclass
class Limits:
    centre: float
    lcl: float
    ucl: float
    sigma: float                     # sigma of the plotted statistic

    def zone(self, x, k):
        return self.centre - k * self.sigma, self.centre + k * self.sigma


@dataclass
class Chart:
    name: str
    values: np.ndarray
    limits: Limits
    secondary: tuple | None = None   # (values, Limits) of the range / moving-range chart
    signals: dict = field(default_factory=dict)


def imr_limits(x):
    """Individuals and moving-range limits. sigma_within = mean moving range / d2(2)."""
    x = np.asarray(x, float)
    mr = np.abs(np.diff(x))
    mrbar = mr.mean()
    sigma = mrbar / CONSTANTS[2]["d2"]
    ind = Limits(x.mean(), x.mean() - 3 * sigma, x.mean() + 3 * sigma, sigma)
    mrl = Limits(mrbar, 0.0, CONSTANTS[2]["D4"] * mrbar, np.nan)
    return ind, mrl


def imr_chart(x, phase1):
    """I-MR chart of x, with limits from the phase-I observations (boolean mask or slice)."""
    x = np.asarray(x, float)
    ind, mrl = imr_limits(x[phase1])
    chart = Chart("I-MR", x, ind, (np.r_[np.nan, np.abs(np.diff(x))], mrl))
    chart.signals = western_electric(x, ind)
    return chart


def xbar_r_limits(subgroups):
    sub = np.asarray(subgroups, float)
    n = sub.shape[1]
    c = CONSTANTS[n]
    xbar, r = sub.mean(1), np.ptp(sub, 1)
    xbb, rbar = xbar.mean(), r.mean()
    sigma_within = rbar / c["d2"]
    xl = Limits(xbb, xbb - c["A2"] * rbar, xbb + c["A2"] * rbar, sigma_within / np.sqrt(n))
    rl = Limits(rbar, c["D3"] * rbar, c["D4"] * rbar, np.nan)
    return xl, rl, sigma_within


def xbar_r_chart(subgroups, phase1):
    sub = np.asarray(subgroups, float)
    xl, rl, _ = xbar_r_limits(sub[phase1])
    xbar = sub.mean(1)
    chart = Chart("Xbar-R", xbar, xl, (np.ptp(sub, 1), rl))
    chart.signals = western_electric(xbar, xl)
    return chart


def p_chart(defectives, sizes, p_bar=None):
    """Fraction defective per period; the limits widen when the period has fewer parts."""
    k, n = np.asarray(defectives, float), np.asarray(sizes, float)
    p = k / n
    pb = k.sum() / n.sum() if p_bar is None else p_bar
    sig = np.sqrt(pb * (1 - pb) / n)
    return p, pb, np.maximum(0, pb - 3 * sig), pb + 3 * sig


def ewma_chart(x, mu, sigma, lam=0.2, L=3.0):
    """Exponentially weighted moving average z_i = lam x_i + (1 - lam) z_(i-1). Averages away
    noise, so it detects small sustained shifts sooner than the individuals chart."""
    x = np.asarray(x, float)
    z = np.empty_like(x)
    prev = mu
    for i, v in enumerate(x):
        prev = lam * v + (1 - lam) * prev
        z[i] = prev
    i = np.arange(1, x.size + 1)
    width = L * sigma * np.sqrt(lam / (2 - lam) * (1 - (1 - lam) ** (2 * i)))
    return z, mu - width, mu + width


def western_electric(x, lim: Limits):
    """The four Western Electric rules. Returns {rule: [indices where the rule fires]}.
    1: one point beyond 3 sigma
    2: two of three consecutive points beyond 2 sigma, same side
    3: four of five consecutive points beyond 1 sigma, same side
    4: eight consecutive points on one side of the centre line
    """
    x = np.asarray(x, float)
    z = (x - lim.centre) / lim.sigma
    out = {1: [], 2: [], 3: [], 4: []}
    for i in range(x.size):
        if abs(z[i]) > 3:
            out[1].append(i)
        for rule, win, need, k in ((2, 3, 2, 2), (3, 5, 4, 1)):
            if i >= win - 1:
                w = z[i - win + 1:i + 1]
                for side in (1, -1):
                    if side * z[i] > k and (side * w > k).sum() >= need:
                        out[rule].append(i)
        if i >= 7:
            w = z[i - 7:i + 1]
            if (w > 0).all() or (w < 0).all():
                out[4].append(i)
    return {r: sorted(set(v)) for r, v in out.items()}


def first_signal(signals):
    idx = [i for v in signals.values() for i in v]
    return min(idx) if idx else None
