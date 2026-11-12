-- export_measurements.sql - the same table as data/measurements.csv, straight from the
-- production-test database (HannaBeshoy/production-test-db, Oracle SQL).
-- In SQL Developer: run, then right-click the result > Export > CSV.
SELECT r.run_id,
       r.serial_no,
       t.code                                   AS product,
       s.name                                   AS station,
       r.operator_id,
       o.shift,
       TO_CHAR(r.started_at, 'YYYY-MM-DD HH24:MI:SS') AS started_at,
       TO_CHAR(r.started_at, 'Dy', 'NLS_DATE_LANGUAGE=ENGLISH') AS day,
       r.attempt,
       r.result,
       sp.spec_id,
       sp.quantity,
       sp.unit,
       sp.lower_limit,
       sp.upper_limit,
       m.value
FROM   pt_measurements m
JOIN   pt_test_runs    r  ON r.run_id = m.run_id
JOIN   pt_test_specs   sp ON sp.spec_id = m.spec_id
JOIN   pt_parts        p  ON p.serial_no = r.serial_no
JOIN   pt_product_types t ON t.type_id = p.type_id
JOIN   pt_stations     s  ON s.station_id = r.station_id
JOIN   pt_operators    o  ON o.operator_id = r.operator_id
ORDER  BY r.run_id, sp.spec_id;
