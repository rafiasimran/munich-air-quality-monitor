import copy

from checks import pass_rate, run_checks


def kinds(issues):
    return {(i["check"], i["column"]) for i in issues}


def test_real_data_is_clean(real_rows):
    issues = run_checks(real_rows)
    assert issues == []
    assert pass_rate(real_rows, issues) == 100.0


def test_detects_missing_and_out_of_range(real_rows):
    rows = copy.deepcopy(real_rows)
    rows[3]["pm2_5"] = None
    rows[5]["relative_humidity_2m"] = 140
    found = kinds(run_checks(rows))
    assert ("missing_value", "pm2_5") in found
    assert ("out_of_range", "relative_humidity_2m") in found


def test_detects_sudden_jump(real_rows):
    rows = copy.deepcopy(real_rows)
    rows[10]["temperature_2m"] = rows[9]["temperature_2m"] + 15
    assert ("sudden_jump", "temperature_2m") in kinds(run_checks(rows))


def test_detects_stuck_sensor(real_rows):
    rows = copy.deepcopy(real_rows)
    for r in rows[0:6]:
        r["ozone"] = 30
    assert ("stuck_value", "ozone") in kinds(run_checks(rows))


def test_detects_missing_hours(real_rows):
    rows = real_rows[:5] + real_rows[8:]
    assert ("missing_hours", "time") in kinds(run_checks(rows))


def test_pass_rate_drops_with_bad_values(real_rows):
    rows = copy.deepcopy(real_rows)
    rows[0]["pm10"] = -5
    assert pass_rate(rows, run_checks(rows)) < 100
