"""Look up the conditions in Munich at a given time.

    python src/lookup.py "2026-11-02 08:30"
    python src/lookup.py "2026-11-02 08:30" --lat 48.150 --lon 11.540

Times are Munich clock time. With a location, the nearest of the two measuring
stations is used for the measured values; the model and weather values are for
the city as a whole.
"""
import argparse
import json
import sqlite3
from datetime import datetime
from math import asin, cos, radians, sin, sqrt
from zoneinfo import ZoneInfo

from config import DB_PATH, STATION_FIELDS, STATIONS, TIMEZONE

DEFAULT_STATION = "DEBY039"  # Lothstraße: city background, closest to what the model describes


def distance_km(lat1, lon1, lat2, lon2) -> float:
    lat1, lon1, lat2, lon2 = map(radians, (lat1, lon1, lat2, lon2))
    a = sin((lat2 - lat1) / 2) ** 2 + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2) ** 2
    return 2 * 6371 * asin(sqrt(a))


def nearest_station(lat: float, lon: float) -> tuple[str, float]:
    code = min(STATIONS, key=lambda c: distance_km(lat, lon, STATIONS[c]["lat"], STATIONS[c]["lon"]))
    return code, round(distance_km(lat, lon, STATIONS[code]["lat"], STATIONS[code]["lon"]), 2)


def hour_label(when) -> str:
    """Any time -> the Munich clock hour it falls in, as 'YYYY-MM-DDTHH:00'."""
    if isinstance(when, str):
        when = datetime.fromisoformat(when)
    if when.tzinfo is not None:
        when = when.astimezone(ZoneInfo(TIMEZONE)).replace(tzinfo=None)
    return when.strftime("%Y-%m-%dT%H:00")


def conditions_at(when, lat=None, lon=None, db_path=DB_PATH, con=None) -> dict | None:
    con = con or sqlite3.connect(db_path)
    hour = hour_label(when)
    cur = con.execute("SELECT m.*, c.labels, c.visibility_risk FROM measurements m "
                      "LEFT JOIN conditions c ON c.time = m.time WHERE m.time = ?", (hour,))
    row = cur.fetchone()
    if row is None:
        return None
    result = dict(zip([d[0] for d in cur.description], row))
    result["labels"] = [x for x in (result["labels"] or "").split(",") if x]

    code, km = nearest_station(lat, lon) if lat is not None and lon is not None else (DEFAULT_STATION, None)
    measured = con.execute(f"SELECT {', '.join(STATION_FIELDS)} FROM station_measurements "
                           "WHERE station = ? AND time = ?", (code, hour)).fetchone()
    result["station"] = {"code": code, "name": STATIONS[code]["name"], "distance_km": km,
                         "measured": dict(zip(STATION_FIELDS, measured)) if measured else None}
    return result


def main():
    p = argparse.ArgumentParser(description="Conditions in Munich at a given time.")
    p.add_argument("when", help='Munich time, e.g. "2026-11-02 08:30"')
    p.add_argument("--lat", type=float)
    p.add_argument("--lon", type=float)
    a = p.parse_args()
    print(json.dumps(conditions_at(a.when, a.lat, a.lon), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
