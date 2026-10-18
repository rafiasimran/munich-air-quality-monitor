"""Data-quality checks. Each check returns a list of issues instead of stopping the run,
so one bad reading never hides the others."""
from datetime import datetime, timedelta

from config import MAX_HOURLY_JUMP, STUCK_HOURS, VALID_RANGES

FIELDS = list(VALID_RANGES)


def issue(check, time, column, severity, detail):
    return {"check": check, "time": time, "column": column, "severity": severity, "detail": detail}


def missing_values(rows):
    return [issue("missing_value", r["time"], f, "warning", "no value recorded")
            for r in rows for f in FIELDS if r.get(f) is None]


def out_of_range(rows):
    out = []
    for r in rows:
        for f, (low, high) in VALID_RANGES.items():
            v = r.get(f)
            if v is not None and not low <= v <= high:
                out.append(issue("out_of_range", r["time"], f, "error", f"{v} outside {low}..{high}"))
    return out


def sudden_jumps(rows):
    out = []
    for prev, cur in zip(rows, rows[1:]):
        for f, limit in MAX_HOURLY_JUMP.items():
            a, b = prev.get(f), cur.get(f)
            if a is not None and b is not None and abs(b - a) > limit:
                out.append(issue("sudden_jump", cur["time"], f, "warning",
                                 f"changed by {b - a:+.1f} in one hour (limit {limit})"))
    return out


def stuck_values(rows):
    out = []
    for f in FIELDS:
        streak = 1
        for prev, cur in zip(rows, rows[1:]):
            same = cur.get(f) is not None and cur.get(f) == prev.get(f)
            streak = streak + 1 if same else 1
            if streak == STUCK_HOURS:
                out.append(issue("stuck_value", cur["time"], f, "warning",
                                 f"same value ({cur[f]}) for {STUCK_HOURS} hours"))
    return out


def time_gaps(rows):
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


ALL_CHECKS = [missing_values, out_of_range, sudden_jumps, stuck_values, time_gaps]


def run_checks(rows):
    issues = []
    for check in ALL_CHECKS:
        issues.extend(check(rows))
    return issues


def pass_rate(rows, issues):
    """Share of individual values (rows x fields) that had no issue."""
    total = len(rows) * len(FIELDS)
    if total == 0:
        return 0.0
    flagged = {(i["time"], i["column"]) for i in issues if i["column"] in FIELDS}
    return round(100 * (1 - len(flagged) / total), 1)
