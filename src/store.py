"""SQLite storage. Re-running the pipeline updates rows instead of duplicating them."""
import sqlite3
from pathlib import Path

from config import VALID_RANGES

FIELDS = list(VALID_RANGES)

SCHEMA = f"""
CREATE TABLE IF NOT EXISTS measurements (
    time TEXT PRIMARY KEY,
    {", ".join(f"{f} REAL" for f in FIELDS)}
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
    return con


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
