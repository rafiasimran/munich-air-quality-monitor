"""Condition labels, model-vs-station comparison, lookup and monthly export."""
import csv

from compare import compare_pairs, model_vs_station
from conditions import build_conditions, label_hour, visibility_risk
from export import export_month, previous_month
from lookup import conditions_at, hour_label, nearest_station
from store import connect, save_measurements, save_station_rows

CLEAR = {"precipitation": 0.0, "wind_speed_10m": 10, "visibility": 24000, "pm2_5": 6, "relative_humidity_2m": 70}


def test_labels():
    assert label_hour(CLEAR) == ["clear"]
    assert label_hour({**CLEAR, "precipitation": 1.2}) == ["rain"]
    assert label_hour({**CLEAR, "visibility": 400, "wind_speed_10m": 55}) == ["strong_wind", "low_visibility"]
    assert label_hour({**CLEAR, "pm2_5": 30, "relative_humidity_2m": 95}) == ["haze_risk"]
    assert label_hour({**CLEAR, "visibility": None}) == []          # not "clear" if we don't know


def test_visibility_risk():
    assert visibility_risk(CLEAR, label_hour(CLEAR)) == "low"
    fog = {**CLEAR, "visibility": 300}
    assert visibility_risk(fog, label_hour(fog)) == "high"
    damp = {**CLEAR, "relative_humidity_2m": 92}
    assert visibility_risk(damp, label_hour(damp)) == "medium"
    assert visibility_risk({**CLEAR, "visibility": None}, []) == "unknown"


def test_compare_pairs():
    s = compare_pairs([(10, 8), (12, 10), (14, 12), (None, 5)])
    assert s["hours"] == 3 and s["bias"] == 2.0 and s["mae"] == 2.0 and s["corr"] == 1.0


def model_row(t, **kw):
    return {"time": t, "pm10": 12, "pm2_5": 8, "nitrogen_dioxide": 15, "ozone": 40, "temperature_2m": 8,
            "relative_humidity_2m": 80, "wind_speed_10m": 9, "precipitation": 0, "visibility": 20000, **kw}


def station_row(code, t, utc, **kw):
    return {"station": code, "time": t, "time_utc": utc, "pm10": 10, "pm2_5": 6, "nitrogen_dioxide": 20,
            "ozone": None, **kw}


def filled_db():
    con = connect(":memory:")
    save_measurements(con, [model_row("2026-11-02T08:00"), model_row("2026-11-02T09:00", precipitation=2.0)])
    save_station_rows(con, [station_row("DEBY039", "2026-11-02T08:00", "2026-11-02T07:00Z"),
                            station_row("DEBY039", "2026-11-02T09:00", "2026-11-02T08:00Z", pm2_5=10),
                            station_row("DEBY115", "2026-11-02T08:00", "2026-11-02T07:00Z", pm2_5=20)])
    build_conditions(con)
    return con


def test_model_vs_station_joins_on_munich_time():
    rows = {r["field"]: r for r in model_vs_station(filled_db(), "DEBY039")}
    assert rows["pm2_5"]["hours"] == 2 and rows["pm2_5"]["bias"] == 0.0      # model 8, 8 vs station 6, 10
    assert rows["nitrogen_dioxide"]["bias"] == -5.0
    assert "ozone" not in rows                                              # nothing to compare


def test_lookup_uses_the_nearest_station():
    con = filled_db()
    assert hour_label("2026-11-02 08:42") == "2026-11-02T08:00"
    assert hour_label("2026-11-02T07:42:00+00:00") == "2026-11-02T08:00"   # UTC in, Munich hour out
    assert nearest_station(48.1499, 11.5370)[0] == "DEBY115"
    r = conditions_at("2026-11-02 08:42", lat=48.1499, lon=11.5370, con=con)
    assert r["labels"] == ["clear"] and r["station"]["code"] == "DEBY115"
    assert r["station"]["measured"]["pm2_5"] == 20
    assert conditions_at("2026-11-02 09:10", con=con)["labels"] == ["rain"]
    assert conditions_at("2030-01-01 00:00", con=con) is None


def test_monthly_export(tmp_path):
    folder = export_month(filled_db(), "2026-11", tmp_path)
    with (folder / "hourly_conditions.csv").open() as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 2 and rows[1]["labels"] == "rain"
    card = (folder / "DATA_CARD.md").read_text()
    assert "2 of 720 hours" in card and "rain: 1 hour\n" in card
    assert previous_month(__import__("datetime").date(2026, 1, 5)) == "2025-12"
