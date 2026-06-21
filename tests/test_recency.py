"""Tests for the recency penalty (mild, capped, skipped when no date)."""

from datetime import date

from job_hunter.recency import CAP, GRACE_DAYS, age_days, parse_date, recency_penalty

TODAY = date(2026, 1, 1)


def test_parse_date_formats():
    assert parse_date("2025-12-25") == date(2025, 12, 25)
    assert parse_date("2025-12-25T10:30:00Z") == date(2025, 12, 25)
    assert parse_date("1700000000") == date(2023, 11, 14)  # unix seconds (UTC)
    assert parse_date("") is None
    assert parse_date(None) is None
    assert parse_date("not a date") is None


def test_age_days():
    assert age_days("2025-12-25", today=TODAY) == 7
    assert age_days("", today=TODAY) is None


def test_fresh_and_missing_are_not_penalised():
    assert recency_penalty("2025-12-25", today=TODAY)[0] == 0      # 7 days old, within grace
    assert recency_penalty("", today=TODAY)[0] == 0               # unknown date
    assert recency_penalty(None, today=TODAY)[0] == 0


def test_old_posting_penalised_and_capped():
    # ~10 weeks old -> a few weeks beyond grace -> small negative penalty.
    pts, detail = recency_penalty("2025-10-23", today=TODAY)  # 70 days old
    assert pts < 0
    assert detail["recency_age_days"] == 70
    # Very old -> capped.
    assert recency_penalty("2024-01-01", today=TODAY)[0] == -CAP


def test_grace_boundary():
    on_grace = date(2026, 1, 1).toordinal() - GRACE_DAYS
    assert recency_penalty(date.fromordinal(on_grace).isoformat(), today=TODAY)[0] == 0
