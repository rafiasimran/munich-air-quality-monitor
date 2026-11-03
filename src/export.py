"""Export one month as a versioned dataset: CSV files plus a data card.

    python src/export.py 2026-10        # writes releases/2026-10/
    python src/export.py                # the previous month

A team that trains on this data can then say exactly which version they used.
"""
import argparse
import csv
import sqlite3
from calendar import monthrange
from datetime import date, datetime, timezone
from pathlib import Path

from config import DB_PATH, STATION_FIELDS, STATIONS

HOURLY_SQL = """
SELECT m.*, c.labels, c.visibility_risk FROM measurements m
LEFT JOIN conditions c ON c.time = m.time
WHERE substr(m.time, 1, 7) = ? ORDER BY m.time
"""
STATIONS_SQL = f"""
SELECT station, time_utc, time, {", ".join(STATION_FIELDS)} FROM station_measurements
WHERE substr(time, 1, 7) = ? ORDER BY station, time_utc
"""


def _write_csv(path: Path, cur) -> list[tuple]:
    rows = cur.fetchall()
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([d[0] for d in cur.description])
        w.writerows(rows)
    return rows


def previous_month(today: date) -> str:
    y, m = (today.year, today.month - 1) if today.month > 1 else (today.year - 1, 12)
    return f"{y}-{m:02d}"


def export_month(con, month: str, out_dir: str = "releases") -> Path:
    folder = Path(out_dir) / month
    folder.mkdir(parents=True, exist_ok=True)
    hourly = _write_csv(folder / "hourly_conditions.csv", con.execute(HOURLY_SQL, (month,)))
    stations = _write_csv(folder / "stations.csv", con.execute(STATIONS_SQL, (month,)))

    y, m = map(int, month.split("-"))
    hours_in_month = monthrange(y, m)[1] * 24
    per_station = {code: sum(1 for r in stations if r[0] == code) for code in STATIONS}
    labels = {}
    for r in hourly:
        for label in (r[-2] or "").split(","):
            if label:
                labels[label] = labels.get(label, 0) + 1

    lines = [
        f"# Munich air and weather conditions, {month}",
        "",
        f"Exported {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC from the munich-air-quality-monitor database.",
        "",
        "## Files",
        "",
        f"- `hourly_conditions.csv`: {len(hourly)} hours of model air quality and weather for Munich, "
        "with condition labels (rain, strong_wind, low_visibility, haze_risk, clear) and a visibility risk.",
        f"- `stations.csv`: {len(stations)} station-hours measured at "
        + ", ".join(f"{STATIONS[c]['name']} ({per_station[c]})" for c in STATIONS) + ".",
        "",
        "## Coverage",
        "",
        f"{len(hourly)} of {hours_in_month} hours in the month ({100 * len(hourly) / hours_in_month:.0f}%). "
        "The project started collecting on 17 Oct 2026, so earlier months are partial.",
        "",
        "## Condition labels",
        "",
        *[f"- {k}: {v} hour{'' if v == 1 else 's'}" for k, v in sorted(labels.items(), key=lambda kv: -kv[1])],
        "",
        "## Sources",
        "",
        "- Model air quality and weather: [Open-Meteo](https://open-meteo.com/) (CAMS European air-quality "
        "model), CC BY 4.0. Values describe the city area, not one street.",
        "- Measured air quality: Umweltbundesamt, with data from Bavaria's air monitoring network "
        "(stations DEBY039 and DEBY115). Recent values are provisional until validated.",
        "",
        "## Known limits",
        "",
        "- `time` is Munich clock time. In the hour the clocks go back, two hours share one label; "
        "`stations.csv` also has `time_utc`, which is unambiguous.",
        "- Station values are hourly averages; model values are for the hour as given by Open-Meteo.",
        "- The condition thresholds are working definitions (see `src/config.py`), not official ones.",
        "",
    ]
    (folder / "DATA_CARD.md").write_text("\n".join(lines), encoding="utf-8")
    return folder


def main():
    p = argparse.ArgumentParser(description="Export one month as a versioned dataset.")
    p.add_argument("month", nargs="?", default=previous_month(date.today()), help="YYYY-MM")
    p.add_argument("--out", default="releases")
    a = p.parse_args()
    con = sqlite3.connect(DB_PATH)
    folder = export_month(con, a.month, a.out)
    print(f"Exported {a.month} to {folder}")


if __name__ == "__main__":
    main()
