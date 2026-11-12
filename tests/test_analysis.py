"""The data is the production-test-db week, and the report's main findings hold."""
import csv
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_exported_csv_is_reproducible(tmp_path):
    sys.path.insert(0, str(ROOT / "tools"))
    import export_data

    runs, meas = export_data.rows()
    with open(ROOT / "data/measurements.csv") as f:
        saved = list(csv.DictReader(f))
    assert len(saved) == len(meas) == 1380
    assert len(runs) == 1080
    for a, b in zip(saved[:50], meas[:50], strict=True):
        assert float(a["value"]) == b["value"]
        assert a["serial_no"] == b["serial_no"]


def test_same_numbers_as_the_database_project():
    """production-test-db query A2 reports LEAK-1 failing 5.16 % of its runs and E1 a Friday
    clutch first-pass yield of 73.3 %."""
    with open(ROOT / "data/runs.csv") as f:
        runs = [r for r in csv.DictReader(f) if r["result"] != "ABORT"]
    leak = [r for r in runs if r["station"] == "LEAK-1"]
    assert sum(r["result"] == "FAIL" for r in leak) / len(leak) == pytest.approx(0.0516, abs=5e-5)


@pytest.fixture(scope="module")
def summary():
    subprocess.run([sys.executable, "analyse.py"], cwd=ROOT, check=True, capture_output=True)
    return json.loads((ROOT / "results/summary.json").read_text())


def test_control_chart_warns_before_first_failure(summary):
    cc = summary["control_chart"]
    assert cc["first_signal"].startswith("Wed")
    assert cc["first_ewma"].startswith("Wed")
    assert cc["first_fail"].startswith(("Thu", "Fri"))


def test_wear_is_significant_and_starts_around_wednesday(summary):
    assert summary["tests"]["welch"]["p"] < 1e-6
    assert summary["tests"]["anova"]["p"] < 1e-6
    assert 1.3 <= summary["regression"]["tau"] <= 2.3          # Tue afternoon to Wed afternoon
    lo, hi = summary["regression"]["slope_ci"]
    assert lo > 0


def test_findings_on_proportions(summary):
    assert summary["fpy"]["friday"] == pytest.approx(22 / 30)
    assert summary["fpy"]["fisher_p"] < 0.05
    assert summary["shift"]["p"] > 0.05
    assert summary["leak_vs_rest"]["fisher_p"] < 0.05


def test_retests_read_lower_than_first_attempts(summary):
    rt = summary["retest"]
    assert rt["mean_retest"] < rt["mean_first_thu_fri"] - 0.4
    assert rt["p"] < 0.001


def test_stable_process_gives_no_signal(summary):
    assert summary["xbar_r"]["signals"] == 0
    assert summary["correlation"]["p"] > 0.05


def test_leak_cpk_falls_day_by_day(summary):
    c = summary["leak_cpk_by_day"]
    assert c["Mon"] > 1.2 and c["Fri"] < 0.5
    assert c["Wed"] > c["Thu"] > c["Fri"]
