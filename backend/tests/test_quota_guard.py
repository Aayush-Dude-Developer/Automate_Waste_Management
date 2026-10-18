from datetime import datetime, timezone
from pathlib import Path
import importlib.util


GUARD_PATH = Path(__file__).resolve().parents[2] / "quota_guard" / "main.py"
SPEC = importlib.util.spec_from_file_location("quota_guard_main", GUARD_PATH)
quota_guard = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(quota_guard)


def test_evaluate_limits_trips_at_configured_percentage():
    limits = [
        {"name": "reads", "limit": 100, "period": "day", "unit": "reads"},
        {"name": "writes", "limit": 200, "period": "day", "unit": "writes"},
    ]

    exceeded = quota_guard.evaluate_limits(
        limits,
        80,
        lambda limit, _start, _end: {"reads": 80, "writes": 159}[limit["name"]],
        datetime(2026, 10, 13, 8, tzinfo=timezone.utc),
    )

    assert len(exceeded) == 1
    assert exceeded[0]["name"] == "reads"
    assert exceeded[0]["percent_used"] == 80


def test_quota_periods_use_pacific_calendar_boundaries():
    now = datetime(2026, 10, 13, 8, tzinfo=timezone.utc)

    assert quota_guard.quota_period_start("day", now) == datetime(
        2026, 10, 13, 7, tzinfo=timezone.utc
    )
    assert quota_guard.quota_period_start("month", now) == datetime(
        2026, 10, 1, 7, tzinfo=timezone.utc
    )


def test_invalid_threshold_is_rejected():
    try:
        quota_guard.evaluate_limits([], 101, lambda *_: 0)
    except ValueError as error:
        assert "between 1 and 100" in str(error)
    else:
        raise AssertionError("Invalid shutdown threshold was accepted.")
