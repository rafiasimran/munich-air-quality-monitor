"""Data-quality checks. Each check returns a list of issues instead of stopping the run,
so one bad reading never hides the others."""
from datetime import datetime, timedelta

from config import MAX_HOURLY_JUMP, STUCK_HOURS, VALID_RANGES

FIELDS = list(VALID_RANGES)


def issue(check, time, column, severity, detail):
    return {"check": check, "time": time, "column": column, "severity": severity, "detail": detail}


def missing_values(rows, fields=FIELDS):
    return [issue("missing_value", r["time"], f, "warning", "no value recorded")
            for r in rows for f in fields if r.get(f) is None]


def out_of_range(rows, fields=FIELDS):
    out = []
    for r in rows:
        for f in fields:
            low, high = VALID_RANGES[f]
            v = r.get(f)
            if v is not None and not low <= v <= high:
                out.append(issue("out_of_range", r["time"], f, "error", f"{v} outside {low}..{high}"))
    return out


def sudden_jumps(rows, fields=FIELDS):
    out = []
    for prev, cur in zip(rows, rows[1:]):
        for f in fields:
            limit = MAX_HOURLY_JUMP[f]
            a, b = prev.get(f), cur.get(f)
            if a is not None and b is not None and abs(b - a) > limit:
                out.append(issue("sudden_jump", cur["time"], f, "warning",
                                 f"changed by {b - a:+.1f} in one hour (limit {limit})"))
    return out


def stuck_values(rows, fields=FIELDS, hours=STUCK_HOURS):
    out = []
    for f in fields:
        streak = 1
        for prev, cur in zip(rows, rows[1:]):
            same = cur.get(f) is not None and cur.get(f) == prev.get(f)
            streak = streak + 1 if same else 1
            if streak == hours:
                out.append(issue("stuck_value", cur["time"], f, "warning",
                                 f"same value ({cur[f]}) for {hours} hours"))
    return out


def pm25_above_pm10(rows, fields=FIELDS):
    """PM2.5 is part of PM10, so it can't really be larger. When it is, the two values come
    from different instruments or are inside the measurement uncertainty. Worth knowing
    before training on them, but not an error."""
    if "pm2_5" not in fields or "pm10" not in fields:
        return []
    return [issue("pm25_above_pm10", r["time"], "pm2_5", "info", f"PM2.5 {r['pm2_5']} > PM10 {r['pm10']}")
            for r in rows if r.get("pm2_5") is not None and r.get("pm10") is not None and r["pm2_5"] > r["pm10"]]


def time_gaps(rows, fields=FIELDS):
    out = []
    times = [datetime.fromisoformat(r["time"]) for r in rows]
    for a, b in zip(times, times[1:]):
        if b - a > timedelta(hours=1):
            out.append(issue("missing_hours", b.isoformat(timespec="minutes"), "time", "error",
                             f"{int((b - a).total_seconds() // 3600) - 1} hour(s) missing before this"))
        elif b == a:
            out.append(issue("duplicate_time", b.isoformat(timespec="minutes"), "time", "error",
                             "timestamp appears twice"))
    return out


ALL_CHECKS = [missing_values, out_of_range, sudden_jumps, stuck_values, pm25_above_pm10, time_gaps]


def run_checks(rows, fields=FIELDS, stuck_hours=STUCK_HOURS):
    issues = []
    for check in ALL_CHECKS:
        if check is stuck_values:
            issues.extend(check(rows, fields, stuck_hours))
        else:
            issues.extend(check(rows, fields))
    return issues


def pass_rate(rows, issues, fields=FIELDS):
    """Share of individual values (rows x fields) with no warning or error. Info notes don't count."""
    total = len(rows) * len(fields)
    if total == 0:
        return 0.0
    flagged = {(i["time"], i["column"]) for i in issues if i["column"] in fields and i["severity"] != "info"}
    return round(100 * (1 - len(flagged) / total), 1)
