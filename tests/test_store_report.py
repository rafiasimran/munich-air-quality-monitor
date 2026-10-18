from checks import pass_rate, run_checks
from report import build_report
from store import connect, save_measurements, save_run


def test_upsert_does_not_duplicate(real_rows):
    con = connect(":memory:")
    save_measurements(con, real_rows)
    save_measurements(con, real_rows)
    assert con.execute("SELECT COUNT(*) FROM measurements").fetchone()[0] == 48


def test_report_daily_averages_and_who_flags(real_rows):
    con = connect(":memory:")
    save_measurements(con, real_rows)
    issues = run_checks(real_rows)
    save_run(con, "2026-10-18 23:00:00", real_rows, issues, pass_rate(real_rows, issues))
    report = build_report(con)
    days = {d["day"]: d for d in report["daily"]}
    assert days["2026-10-17"]["hours"] == 24
    assert days["2026-10-17"]["pm2_5"] == 11.7
    assert days["2026-10-17"]["who_pm2_5_exceeded"] is False
    assert report["latest"]["time"] == "2026-10-18T23:00"
    assert report["runs"][0]["pass_rate"] == 100.0
