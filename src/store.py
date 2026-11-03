"""SQLite storage. Re-running the pipeline updates rows instead of duplicating them."""
import sqlite3
from pathlib import Path

from config import CONTEXT_FIELDS, STATION_FIELDS, VALID_RANGES

FIELDS = list(VALID_RANGES) + CONTEXT_FIELDS

SCHEMA = f"""
CREATE TABLE IF NOT EXISTS measurements (
    time TEXT PRIMARY KEY,
    {", ".join(f"{f} REAL" for f in FIELDS)}
);
CREATE TABLE IF NOT EXISTS station_measurements (
    station TEXT, time_utc TEXT, time TEXT,
    {", ".join(f"{f} REAL" for f in STATION_FIELDS)},
    PRIMARY KEY (station, time_utc)
);
CREATE TABLE IF NOT EXISTS conditions (
    time TEXT PRIMARY KEY, labels TEXT, visibility_risk TEXT
);
CREATE TABLE IF NOT EXISTS quality_issues (
    run_at TEXT, time TEXT, check_name TEXT, column_name TEXT, severity TEXT, detail TEXT
);
CREATE TABLE IF NOT EXISTS runs (
    run_at TEXT PRIMARY KEY, rows_loaded INTEGER, issues INTEGER, pass_rate REAL
);
"""


def connect(path: str) -> sqlite3.Connection:
    if path != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.executescript(SCHEMA)
    _add_new_columns(con)
    return con


def _add_new_columns(con):
    """An existing database was created before some fields existed. Add them, keep the data."""
    have = {row[1] for row in con.execute("PRAGMA table_info(measurements)")}
    for f in FIELDS:
        if f not in have:
            con.execute(f"ALTER TABLE measurements ADD COLUMN {f} REAL")
    con.commit()


def save_measurements(con, rows):
    cols = ["time"] + FIELDS
    sql = (f"INSERT INTO measurements ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))}) "
           f"ON CONFLICT(time) DO UPDATE SET {', '.join(f'{f}=excluded.{f}' for f in FIELDS)}")
    con.executemany(sql, [[r.get(c) for c in cols] for r in rows])
    con.commit()


def save_run(con, run_at, rows, issues, rate):
    con.executemany("INSERT INTO quality_issues VALUES (?, ?, ?, ?, ?, ?)",
                    [(run_at, i["time"], i["check"], i["column"], i["severity"], i["detail"]) for i in issues])
    con.execute("INSERT OR REPLACE INTO runs VALUES (?, ?, ?, ?)", (run_at, len(rows), len(issues), rate))
    con.commit()


def save_station_rows(con, rows):
    cols = ["station", "time_utc", "time"] + STATION_FIELDS
    sql = (f"INSERT INTO station_measurements ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))}) "
           f"ON CONFLICT(station, time_utc) DO UPDATE SET "
           f"{', '.join(f'{f}=excluded.{f}' for f in STATION_FIELDS)}")
    con.executemany(sql, [[r.get(c) for c in cols] for r in rows])
    con.commit()


def last_station_time(con, station):
    return con.execute("SELECT MAX(time_utc) FROM station_measurements WHERE station = ?", (station,)).fetchone()[0]
