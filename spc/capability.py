"""Process capability: how the process spread compares with the specification.

    Cp  = (USL - LSL) / 6 sigma_within             could fit, if centred
    Cpk = min(USL - mu, mu - LSL) / 3 sigma_within  does fit, where it actually sits
    Pp, Ppk: the same with the overall standard deviation (includes drift between periods)

Cpk 1.33 is the usual automotive minimum (4 sigma to the nearer limit, about 32 ppm out of
specification for a normal process), 1.67 for safety-relevant characteristics.

A Cpk from 30 parts is itself uncertain; the confidence intervals show how much.
"""
from __future__ import annotations

import numpy as np
from scipy import stats as sd

from .charts import CONSTANTS


def sigma_within_mr(x):
    return np.abs(np.diff(np.asarray(x, float))).mean() / CONSTANTS[2]["d2"]


def capability(x, lsl=None, usl=None, sigma_within=None, conf=0.95):
    """Cp, Cpk, Pp, Ppk with confidence intervals; a one-sided specification gives only Cpk/Ppk.
    sigma_within defaults to the moving-range estimate (individual measurements in time order)."""
    x = np.asarray(x, float)
    n, mu, s = x.size, x.mean(), x.std(ddof=1)
    sw = sigma_within if sigma_within is not None else sigma_within_mr(x)
    z = sd.norm.ppf(0.5 + conf / 2)

    def k_index(sig):
        sides = []
        if usl is not None:
            sides.append((usl - mu) / (3 * sig))
        if lsl is not None:
            sides.append((mu - lsl) / (3 * sig))
        return min(sides)

    out = {"n": n, "mean": mu, "sigma_within": sw, "sigma_overall": s}
    out["Cpk"], out["Ppk"] = k_index(sw), k_index(s)
    # Bissell (1990) normal approximation for the CI of Cpk
    half = z * np.sqrt(1 / (9 * n) + out["Cpk"] ** 2 / (2 * (n - 1)))
    out["Cpk_ci"] = (out["Cpk"] - half, out["Cpk"] + half)
    if lsl is not None and usl is not None:
        out["Cp"], out["Pp"] = (usl - lsl) / (6 * sw), (usl - lsl) / (6 * s)
        a = 1 - conf     # exact chi-square interval for Cp
        out["Cp_ci"] = (out["Cp"] * np.sqrt(sd.chi2.ppf(a / 2, n - 1) / (n - 1)),
                        out["Cp"] * np.sqrt(sd.chi2.ppf(1 - a / 2, n - 1) / (n - 1)))
    # expected fraction outside the specification for a normal process
    ppm = 0.0
    if usl is not None:
        ppm += sd.norm.sf((usl - mu) / s)
    if lsl is not None:
        ppm += sd.norm.cdf((lsl - mu) / s)
    out["ppm"] = 1e6 * ppm
    return out


def n_for_cpk_precision(cpk, half_width, conf=0.95):
    """Parts needed so the Bissell CI of Cpk is +- half_width."""
    z = sd.norm.ppf(0.5 + conf / 2)
    for n in range(5, 100_000):
        if z * np.sqrt(1 / (9 * n) + cpk ** 2 / (2 * (n - 1))) <= half_width:
            return n
    return None
