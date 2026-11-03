"""Label every hour with the conditions an outdoor robot, drone or vehicle would have faced.

Cameras and lidar get worse in rain, fog and dusty, humid air. If a team has timestamped
sensor recordings from Munich, they can join these labels on and ask whether their model
fails more often in bad conditions. The thresholds are in config.py; they are my own
working definitions, not official ones.
"""
from config import HAZE_HUMIDITY, HAZE_PM25, LOW_VISIBILITY_M, RAIN_MM, STRONG_WIND_KMH


def label_hour(row: dict) -> list[str]:
    labels = []
    rain, wind, vis = row.get("precipitation"), row.get("wind_speed_10m"), row.get("visibility")
    pm25, rh = row.get("pm2_5"), row.get("relative_humidity_2m")
    if rain is not None and rain >= RAIN_MM:
        labels.append("rain")
    if wind is not None and wind >= STRONG_WIND_KMH:
        labels.append("strong_wind")
    if vis is not None and vis < LOW_VISIBILITY_M:
        labels.append("low_visibility")
    if pm25 is not None and rh is not None and pm25 >= HAZE_PM25 and rh >= HAZE_HUMIDITY:
        labels.append("haze_risk")
    if not labels and None not in (rain, wind, vis, pm25, rh):
        labels.append("clear")
    return labels


def visibility_risk(row: dict, labels: list[str]) -> str:
    """One overall answer for vision sensors: low, medium, high, or unknown if inputs are missing."""
    if "low_visibility" in labels or "haze_risk" in labels:
        return "high"
    if "rain" in labels:
        return "medium"
    pm25, rh = row.get("pm2_5"), row.get("relative_humidity_2m")
    if pm25 is None or rh is None or row.get("visibility") is None:
        return "unknown"
    if pm25 >= 15 or rh >= HAZE_HUMIDITY:
        return "medium"
    return "low"


def build_conditions(con) -> int:
    """(Re)label every stored hour. Returns the number of hours labelled."""
    cur = con.execute("SELECT * FROM measurements ORDER BY time")
    names = [d[0] for d in cur.description]
    out = []
    for values in cur.fetchall():
        row = dict(zip(names, values))
        labels = label_hour(row)
        out.append((row["time"], ",".join(labels), visibility_risk(row, labels)))
    con.executemany("INSERT INTO conditions VALUES (?, ?, ?) ON CONFLICT(time) DO UPDATE SET "
                    "labels=excluded.labels, visibility_risk=excluded.visibility_risk", out)
    con.commit()
    return len(out)
