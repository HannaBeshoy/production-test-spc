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


if __name__ == "__main__":
    main()
