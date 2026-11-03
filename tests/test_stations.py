"""Station data: parsing the UBA format, time zones, and what the checks find in real readings."""
import json
from datetime import datetime, timezone
from pathlib import Path

from checks import run_checks
from config import STATION_STUCK_HOURS
from stations import days_to_fetch, fetch_station, rows_for_checks, to_local_label, uba_to_utc

# Real hourly values for 1-2 Nov 2026, captured from the UBA API on 3 Nov 2026 and kept
# in the API's own format ("index" fields set to 0). Data: Umweltbundesamt.
SAMPLE = json.loads((Path(__file__).parent / "fixtures" / "uba_sample.json").read_text())


def fake_get(params):
    return SAMPLE[f"{params['station']}_{params['component']}"]


def test_uba_time_is_utc_plus_one_all_year():
    assert uba_to_utc("2026-11-01 00:00:00") == datetime(2026, 10, 31, 23, tzinfo=timezone.utc)
    # in summer it is still UTC+1, while Munich clocks show UTC+2
    summer = uba_to_utc("2026-07-01 12:00:00")
    assert summer.hour == 11 and to_local_label(summer) == "2026-07-01T13:00"


def test_station_rows_join_all_pollutants_per_hour():
    rows = fetch_station("DEBY039", "2026-11-01", "2026-11-02", fake_get)
    assert len(rows) == 48
    first = rows[0]
    assert first["time"] == "2026-11-01T00:00" and first["time_utc"] == "2026-10-31T23:00Z"
    assert (first["pm10"], first["pm2_5"], first["nitrogen_dioxide"], first["ozone"]) == (8, 7, 20, 33)


def test_traffic_station_has_no_ozone():
    rows = fetch_station("DEBY115", "2026-11-01", "2026-11-02", fake_get)
    assert all(r["ozone"] is None for r in rows) and rows[0]["nitrogen_dioxide"] == 34


def test_real_readings_show_pm25_above_pm10():
    # From 08:00 on 1 Nov to 09:00 on 2 Nov, Lothstraße reported PM2.5 above PM10 in 25 of
    # 48 hours, up to 11 against 2 µg/m³. PM2.5 is part of PM10, so one of the two
    # instruments is off. It is flagged as info: the hours stay in the data, marked.
    rows = fetch_station("DEBY039", "2026-11-01", "2026-11-02", fake_get)
    issues = run_checks(rows, ["pm10", "pm2_5", "nitrogen_dioxide", "ozone"], STATION_STUCK_HOURS)
    found = [i for i in issues if i["check"] == "pm25_above_pm10"]
    assert len(found) == 25 and all(i["severity"] == "info" for i in found)
    assert found[0]["time"] == "2026-11-01T08:00" and found[-1]["time"] == "2026-11-02T09:00"
    assert len(issues) == 25                      # nothing else is wrong with these 48 hours


def test_whole_numbers_repeat_without_being_a_stuck_sensor():
    # Landshuter Allee reported PM2.5 = 8 for 7 hours in a row. With the 6-hour rule for the
    # model this would be "stuck"; stations report whole numbers, so they get 12 hours.
    rows = fetch_station("DEBY115", "2026-11-01", "2026-11-02", fake_get)
    fields = ["pm10", "pm2_5", "nitrogen_dioxide"]
    assert any(i["check"] == "stuck_value" for i in run_checks(rows, fields, 6))
    assert not any(i["check"] == "stuck_value" for i in run_checks(rows, fields, STATION_STUCK_HOURS))


def test_days_to_fetch_backfills_then_continues():
    today = datetime(2026, 11, 3)
    assert days_to_fetch(None, "2026-10-17", today) == ("2026-10-17", "2026-11-03")
    assert days_to_fetch("2026-11-02T22:00Z", "2026-10-17", today) == ("2026-11-02", "2026-11-03")
    assert days_to_fetch(None, "2026-01-01", today)[0] == "2026-10-04"   # never more than 31 days at once


def test_clock_change_night_is_not_a_duplicate_when_checked_in_utc():
    # 25 Oct 2026: 01:00 and 02:00 in UTC+1 (00:00 and 01:00 UTC) both show as 02:00 on a
    # Munich clock, once in summer time and once after the clocks went back.
    raw = {"data": {"535": {"2026-10-25 01:00:00": [5, 2, 20, "2026-10-25 02:00:00", "0"],
                            "2026-10-25 02:00:00": [5, 2, 21, "2026-10-25 03:00:00", "0"]}}}
    rows = fetch_station("DEBY115", "2026-10-25", "2026-10-25",
                         lambda p: raw if p["component"] == 5 else {"data": {}})
    assert [r["time"] for r in rows] == ["2026-10-25T02:00", "2026-10-25T02:00"]
    assert any(i["check"] == "duplicate_time" for i in run_checks(rows, ["nitrogen_dioxide"]))
    assert not run_checks(rows_for_checks(rows), ["nitrogen_dioxide"])
