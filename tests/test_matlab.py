"""matlab/course_methods.m (the course's MATLAB methods) gives the same numbers as the Python
analysis. Runs in GNU Octave; skipped when Octave is not installed."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(shutil.which("octave") is None, reason="GNU Octave not installed")
def test_matlab_script_agrees_with_python():
    subprocess.run(["python", "analyse.py"], cwd=ROOT, check=True, capture_output=True)
    subprocess.run(["octave", "--no-gui", "-q", "--eval", "course_methods"], cwd=ROOT / "matlab", check=True,
                   capture_output=True, timeout=300)
    m = dict(line.split() for line in (ROOT / "results/matlab_check.txt").read_text().splitlines())
    m = {k: float(v) for k, v in m.items()}
    s = json.loads((ROOT / "results/summary.json").read_text())
    expect = {"welch_t": s["tests"]["welch"]["statistic"], "welch_df": s["tests"]["welch"]["df"],
              "anova_F": s["tests"]["anova"]["statistic"], "eta2": s["tests"]["anova"]["effect"],
              "shift_chi2": s["shift"]["chi2"], "shift_p": s["shift"]["p"],
              "slope": s["regression"]["slope_per_day"], "r2": s["regression"]["r2"],
              "pearson_r": s["correlation"]["r"], "gof_chi2": s["gof_leak"]["chi2"], "gof_p": s["gof_leak"]["p"]}
    for key, value in expect.items():
        assert m[key] == pytest.approx(value, rel=1e-6), key
    assert m["welch_p"] == pytest.approx(s["tests"]["welch"]["p"], rel=1e-4)
    assert m["anova_p"] == pytest.approx(s["tests"]["anova"]["p"], rel=1e-4)
    lo, hi = s["regression"]["slope_ci"]
    assert lo < m["slope"] < hi
