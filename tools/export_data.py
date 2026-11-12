"""Exports the production-test week as one flat CSV, one row per measurement.

    python tools/export_data.py            # writes data/measurements.csv and data/runs.csv

The data comes from the generator of the Database Systems project (HannaBeshoy/production-test-db,
tools/gen_data.py, copied here as production_test_db_gen.py), so both projects analyse the same
week. The same table can be exported from the Oracle database with sql/export_measurements.sql.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import production_test_db_gen as gen  # noqa: E402

MEAS_COLS = ["run_id", "serial_no", "product", "station", "operator_id", "shift", "started_at", "day",
             "attempt", "result", "spec_id", "quantity", "unit", "lower_limit", "upper_limit", "value"]
RUN_COLS = ["run_id", "serial_no", "product", "station", "operator_id", "shift", "started_at", "day",
            "attempt", "result"]


def rows():
    d = gen.build()
    product = {t[0]: t[1] for t in d["types"]}
    station = {s[0]: s[1] for s in d["stations"]}
    shift = {o[0]: o[2] for o in d["operators"]}
    ptype = {p[0]: p[1] for p in d["parts"]}
    spec = {s[0]: s for s in d["specs"]}
    runs = {}
    for run_id, serial, st, op, t, _dur, attempt, result in d["runs"]:
        runs[run_id] = {"run_id": run_id, "serial_no": serial, "product": product[ptype[serial]],
                        "station": station[st], "operator_id": op, "shift": shift[op],
                        "started_at": f"{t:%Y-%m-%d %H:%M:%S}", "day": f"{t:%a}", "attempt": attempt,
                        "result": result}
    meas = []
    for run_id, spec_id, value in d["measurements"]:
        _, _, _, quantity, unit, lo, hi = spec[spec_id]
        meas.append({**runs[run_id], "spec_id": spec_id, "quantity": quantity, "unit": unit,
                     "lower_limit": lo, "upper_limit": hi, "value": value})
    return list(runs.values()), meas


def main():
    runs, meas = rows()
    (ROOT / "data").mkdir(exist_ok=True)
    for name, cols, data in (("runs", RUN_COLS, runs), ("measurements", MEAS_COLS, meas)):
        with open(ROOT / "data" / f"{name}.csv", "w", newline="") as f:
            w = csv.DictWriter(f, cols)
            w.writeheader()
            w.writerows(data)
        print(f"data/{name}.csv: {len(data)} rows")
    numeric(meas, runs)


def numeric(meas, runs):
    """Number-only files for matlab/course_methods.m (MATLAB and GNU Octave read them the same way)."""
    days = ["Mon", "Tue", "Wed", "Thu", "Fri"]
    out = ROOT / "data" / "matlab"
    out.mkdir(exist_ok=True)
    leak = [m for m in meas if m["spec_id"] == 5 and m["attempt"] == 1]

    def t_day(m):     # production time in days: Monday 06:00 = 0, one unit per 06:00-21:00 shift day
        hh, mm = int(m["started_at"][11:13]), int(m["started_at"][14:16])
        return days.index(m["day"]) + (hh + mm / 60 - 6) / 15

    (out / "leak.csv").write_text("".join(f"{days.index(m['day']) + 1},{t_day(m):.6f},{m['value']}\n" for m in leak))
    first = [r for r in runs if r["attempt"] == 1 and r["result"] != "ABORT"]
    tab = [[sum(r["shift"] == s and r["result"] == res for r in first) for res in ("FAIL", "PASS")] for s in "AB"]
    (out / "shift_table.csv").write_text("".join(f"{a},{b}\n" for a, b in tab))
    eol = {}
    for m in meas:
        if m["station"] == "EOL-2" and m["attempt"] == 1:
            eol.setdefault(m["run_id"], {})[m["quantity"]] = m["value"]
    (out / "eol2.csv").write_text("".join(f"{v['current']},{v['stroke']}\n" for v in eol.values() if len(v) == 2))


if __name__ == "__main__":
    main()
