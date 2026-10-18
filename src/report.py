"""Build the JSON file the dashboard reads, using plain SQL on the stored data."""
import json
from pathlib import Path

from config import CITY, WHO_DAILY_LIMITS

DAILY_SQL = """
SELECT substr(time, 1, 10) AS day,
       ROUND(AVG(pm2_5), 1) AS pm2_5,
       ROUND(AVG(pm10), 1) AS pm10,
       ROUND(AVG(nitrogen_dioxide), 1) AS nitrogen_dioxide,
       ROUND(AVG(temperature_2m), 1) AS temperature,
       COUNT(*) AS hours
FROM measurements
GROUP BY day
ORDER BY day DESC
LIMIT 14
"""

HOURLY_SQL = """
SELECT time, pm2_5, pm10, nitrogen_dioxide, ozone, temperature_2m, relative_humidity_2m, wind_speed_10m
FROM measurements
ORDER BY time DESC
LIMIT 168
"""

RUNS_SQL = "SELECT run_at, rows_loaded, issues, pass_rate FROM runs ORDER BY run_at DESC LIMIT 30"

ISSUES_SQL = """
SELECT check_name, column_name, severity, COUNT(*) AS n
FROM quality_issues
WHERE run_at >= datetime('now', '-30 days')
GROUP BY check_name, column_name, severity
ORDER BY n DESC
"""


def _rows(con, sql):
    cur = con.execute(sql)
    names = [d[0] for d in cur.description]
    return [dict(zip(names, r)) for r in cur.fetchall()]


def build_report(con) -> dict:
    daily = list(reversed(_rows(con, DAILY_SQL)))
    for d in daily:
        d["who_pm2_5_exceeded"] = d["pm2_5"] is not None and d["pm2_5"] > WHO_DAILY_LIMITS["pm2_5"]
        d["who_pm10_exceeded"] = d["pm10"] is not None and d["pm10"] > WHO_DAILY_LIMITS["pm10"]
    hourly = list(reversed(_rows(con, HOURLY_SQL)))
    return {
        "city": CITY,
        "who_limits": WHO_DAILY_LIMITS,
        "latest": hourly[-1] if hourly else None,
        "hourly": hourly,
        "daily": daily,
        "runs": _rows(con, RUNS_SQL),
        "issue_summary": _rows(con, ISSUES_SQL),
    }


def write_report(con, path: str) -> dict:
    report = build_report(con)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(report, indent=1), encoding="utf-8")
    return report
