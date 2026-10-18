"""Run the full pipeline: fetch -> check -> store -> report."""
import sys
from datetime import datetime, timezone

from checks import pass_rate, run_checks
from config import DASHBOARD_JSON, DB_PATH
from fetch import fetch_latest
from report import write_report
from store import connect, save_measurements, save_run


def main() -> int:
    run_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    rows = fetch_latest()
    if not rows:
        print("No data returned from the API.")
        return 1
    issues = run_checks(rows)
    rate = pass_rate(rows, issues)

    con = connect(DB_PATH)
    save_measurements(con, rows)
    save_run(con, run_at, rows, issues, rate)
    write_report(con, DASHBOARD_JSON)
    con.close()

    print(f"Loaded {len(rows)} hourly rows, found {len(issues)} issue(s), pass rate {rate}%.")
    for i in issues[:10]:
        print(f"  [{i['severity']}] {i['check']} {i['column']} at {i['time']}: {i['detail']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
