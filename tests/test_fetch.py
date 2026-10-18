from datetime import datetime

from fetch import merge


def test_merge_joins_sources_on_time(real_rows):
    first = real_rows[0]
    assert first["time"] == "2026-10-17T00:00"
    assert first["pm2_5"] == 13.8 and first["temperature_2m"] == 12.9


def test_merge_drops_future_hours():
    air = {"hourly": {"time": ["2026-10-18T10:00", "2026-10-18T11:00"], "pm2_5": [5, 6]}}
    weather = {"hourly": {"time": ["2026-10-18T10:00", "2026-10-18T11:00"], "temperature_2m": [9, 10]}}
    rows = merge(air, weather, now=datetime(2026, 10, 18, 10, 30))
    assert [r["time"] for r in rows] == ["2026-10-18T10:00"]
