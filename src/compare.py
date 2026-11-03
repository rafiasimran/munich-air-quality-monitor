"""Compare the model (Open-Meteo / CAMS) with what a real station measured, hour by hour.

Robot and drone teams know this problem as the gap between simulation and reality:
a model can look right on average and still be wrong at the hours that matter.
"""
from math import sqrt

from config import STATION_FIELDS

PAIRS_SQL = """
SELECT m.time, {cols}
FROM measurements m JOIN station_measurements s ON s.time = m.time
WHERE s.station = ? AND m.time >= ?
ORDER BY m.time
"""


def _corr(xs, ys):
    n = len(xs)
    if n < 3:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    sx = sqrt(sum((x - mx) ** 2 for x in xs))
    sy = sqrt(sum((y - my) ** 2 for y in ys))
    if sx == 0 or sy == 0:
        return None
    return round(sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (sx * sy), 2)


def compare_pairs(pairs: list[tuple[float, float]]) -> dict:
    """pairs: (model, station) for the hours where both exist."""
    pairs = [(m, s) for m, s in pairs if m is not None and s is not None]
    n = len(pairs)
    if n == 0:
        return {"hours": 0, "model_mean": None, "station_mean": None, "bias": None, "mae": None, "corr": None}
    model, station = [p[0] for p in pairs], [p[1] for p in pairs]
    return {
        "hours": n,
        "model_mean": round(sum(model) / n, 1),
        "station_mean": round(sum(station) / n, 1),
        "bias": round(sum(m - s for m, s in pairs) / n, 1),        # positive: the model reads too high
        "mae": round(sum(abs(m - s) for m, s in pairs) / n, 1),    # average size of the miss
        "corr": _corr(model, station),                             # does it go up and down at the right times?
    }


def model_vs_station(con, station: str, since: str = "0000") -> list[dict]:
    cols = ", ".join(f"m.{f}, s.{f}" for f in STATION_FIELDS)
    rows = con.execute(PAIRS_SQL.format(cols=cols), (station, since)).fetchall()
    out = []
    for i, field in enumerate(STATION_FIELDS):
        stats = compare_pairs([(r[1 + 2 * i], r[2 + 2 * i]) for r in rows])
        if stats["hours"]:
            out.append({"field": field, **stats})
    return out
