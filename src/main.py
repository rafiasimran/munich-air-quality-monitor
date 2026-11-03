"""Run the full pipeline: fetch -> check -> store -> label -> report."""
import sys
from datetime import datetime, timezone

from checks import pass_rate, run_checks
from conditions import build_conditions
from config import (DASHBOARD_JSON, DB_PATH, STATION_FIELDS, STATION_HISTORY_START, STATION_STUCK_HOURS,
                    STATIONS)
from fetch import fetch_latest
from report import write_report
from stations import days_to_fetch, fetch_station
from store import connect, last_station_time, save_measurements, save_run, save_station_rows


def update_stations(con, run_at: str) -> None:
    """Fetch new hours for each station, check them and store them. A station that fails
    is reported and skipped, so the model data still gets updated."""
    today = datetime.now(timezone.utc).replace(tzinfo=None)
    for code in STATIONS:
        try:
            date_from, date_to = days_to_fetch(last_station_time(con, code), STATION_HISTORY_START, today)
            rows = fetch_station(code, date_from, date_to)
        except Exception as e:  # network or API problem: keep going without this station
            print(f"Station {code}: could not fetch ({e})")
            continue
        fields = [f for f in STATION_FIELDS if any(r[f] is not None for r in rows)]
        issues = run_checks(rows, fields, STATION_STUCK_HOURS)
        for i in issues:
            i["column"] = f"{code} {i['column']}"
        save_station_rows(con, rows)
        save_run(con, f"{run_at} {code}", rows, issues, pass_rate(rows, issues,
                 [f"{code} {f}" for f in fields]))
        print(f"Station {code}: {len(rows)} hours ({date_from} to {date_to}), {len(issues)} issue(s).")


def days_missing_context(con, today: datetime) -> int:
    """How far back stored hours lack the newer weather fields (rain, visibility)."""
    oldest = con.execute("SELECT MIN(time) FROM measurements WHERE visibility IS NULL").fetchone()[0]
    if not oldest:
        return 1
    return (today - datetime.fromisoformat(oldest)).days + 1


def main() -> int:
    run_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    con = connect(DB_PATH)
    rows = fetch_latest(past_days=days_missing_context(con, datetime.now()))
    if not rows:
        print("No data returned from the API.")
        return 1
    issues = run_checks(rows)
    rate = pass_rate(rows, issues)

    save_measurements(con, rows)
    save_run(con, run_at, rows, issues, rate)
    update_stations(con, run_at)
    labelled = build_conditions(con)
    write_report(con, DASHBOARD_JSON)
    con.close()

    print(f"Loaded {len(rows)} hourly rows, found {len(issues)} issue(s), pass rate {rate}%. "
          f"Labelled {labelled} hours.")
    for i in issues[:10]:
        print(f"  [{i['severity']}] {i['check']} {i['column']} at {i['time']}: {i['detail']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
