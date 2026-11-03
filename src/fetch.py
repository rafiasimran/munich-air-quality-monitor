"""Download hourly air-quality and weather data from Open-Meteo and merge it into one table."""
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

from config import (AIR_FIELDS, AIR_URL, LATITUDE, LONGITUDE, TIMEZONE,
                    WEATHER_FIELDS, WEATHER_URL)


def _get(url: str, fields: list[str], past_days: int = 1) -> dict:
    params = {"latitude": LATITUDE, "longitude": LONGITUDE, "hourly": ",".join(fields),
              "past_days": past_days, "forecast_days": 1, "timezone": TIMEZONE}
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def merge(air: dict, weather: dict, now: datetime | None = None) -> list[dict]:
    """Join both responses on timestamp and keep only hours that have already happened."""
    now = now or datetime.now(ZoneInfo(TIMEZONE)).replace(tzinfo=None)
    rows: dict[str, dict] = {}
    for source in (air, weather):
        hourly = source["hourly"]
        for i, t in enumerate(hourly["time"]):
            row = rows.setdefault(t, {"time": t})
            for key, values in hourly.items():
                if key != "time":
                    row[key] = values[i]
    past = [r for r in rows.values() if datetime.fromisoformat(r["time"]) <= now]
    return sorted(past, key=lambda r: r["time"])


def fetch_latest(past_days: int = 1) -> list[dict]:
    """Yesterday and today by default. Open-Meteo allows up to 92 past days, which is used
    once to fill in fields that were added later (see main.py)."""
    past_days = max(1, min(past_days, 92))
    return merge(_get(AIR_URL, AIR_FIELDS, past_days), _get(WEATHER_URL, WEATHER_FIELDS, past_days))
