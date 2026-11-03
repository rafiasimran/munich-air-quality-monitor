"""Download hourly readings from real measuring stations in Munich (Umweltbundesamt).

The Open-Meteo values in this project come from a European air-quality model (CAMS).
These are measured at the street: two stations from Bavaria's monitoring network.

The UBA API returns one file per station and pollutant:

    {"data": {"473": {"2026-11-01 00:00:00": [component, scope, value, "date end", index], ...}}}

Times are German winter time (UTC+1) all year, and each value is the average of the
hour that starts at that time. Recent values are provisional until the network
validates them.
"""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import requests

from config import STATION_FIELDS, STATIONS, TIMEZONE, UBA_COMPONENTS, UBA_URL

UBA_OFFSET = timedelta(hours=1)


def _get(params: dict) -> dict:
    r = requests.get(UBA_URL, params=params, timeout=30, headers={"User-Agent": "munich-air-quality-monitor"})
    r.raise_for_status()
    return r.json()


def uba_to_utc(stamp: str) -> datetime:
    """'2026-11-01 00:00:00' in UTC+1 -> 2026-10-31 23:00 UTC."""
    return (datetime.strptime(stamp, "%Y-%m-%d %H:%M:%S") - UBA_OFFSET).replace(tzinfo=timezone.utc)


def to_local_label(utc: datetime) -> str:
    """The same 'YYYY-MM-DDTHH:MM' Munich clock time that the Open-Meteo rows use."""
    return utc.astimezone(ZoneInfo(TIMEZONE)).strftime("%Y-%m-%dT%H:%M")


def parse_measures(data: dict, station_id: int) -> dict[datetime, float]:
    """One API response -> {hour start in UTC: value}. Missing values stay None."""
    values = (data.get("data") or {}).get(str(station_id)) or {}
    return {uba_to_utc(start): (v[2] if v[2] is None else float(v[2])) for start, v in values.items()}


def fetch_station(code: str, date_from: str, date_to: str, get=_get) -> list[dict]:
    """All pollutants for one station and a range of days (YYYY-MM-DD), one row per hour."""
    station = STATIONS[code]
    hours: dict[datetime, dict] = {}
    for component, field in UBA_COMPONENTS.items():
        data = get({"date_from": date_from, "time_from": 1, "date_to": date_to, "time_to": 24,
                    "station": station["id"], "component": component, "scope": 2})
        for utc, value in parse_measures(data, station["id"]).items():
            row = hours.setdefault(utc, {"station": code, "time_utc": utc.strftime("%Y-%m-%dT%H:%MZ"),
                                         "time": to_local_label(utc), **{f: None for f in STATION_FIELDS}})
            row[field] = value
    return [hours[t] for t in sorted(hours)]


def days_to_fetch(last_utc: str | None, start: str, today: datetime, max_days: int = 31) -> tuple[str, str]:
    """From the day of the last stored hour (or the history start) to today, at most max_days."""
    first = datetime.strptime(last_utc[:10], "%Y-%m-%d") if last_utc else datetime.strptime(start, "%Y-%m-%d")
    first = max(first, today - timedelta(days=max_days - 1))
    return first.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")
