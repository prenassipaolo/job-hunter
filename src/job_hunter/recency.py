"""Recency penalty for stale job postings — mild, capped, skipped when no date.

Job feeds report the posting date in many shapes (ISO 8601, unix timestamps, or nothing
at all), so we parse best-effort and apply a *small* penalty that grows with age and
caps out — an old posting is nudged down without ever overpowering the fit signal.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

GRACE_DAYS = 21  # fresh postings (<= 3 weeks) are not penalised
PER_WEEK = 1     # points lost per week beyond the grace period
CAP = 10         # maximum penalty, so age never dominates fit


def parse_date(raw: str | None) -> date | None:
    """Best-effort parse of a provider's posted-at string. None if unparseable."""
    if not raw:
        return None
    s = str(raw).strip()
    # ISO 8601, tolerating a trailing 'Z'.
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).date()
    except ValueError:
        pass
    # Unix timestamp in seconds (e.g. Arbeitnow's created_at).
    try:
        ts = float(s)
        if ts > 1_000_000:  # guard against tiny numbers that aren't epochs
            return datetime.fromtimestamp(ts, tz=timezone.utc).date()
    except (ValueError, OverflowError, OSError):
        pass
    # Plain YYYY-MM-DD prefix.
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def age_days(raw: str | None, today: date | None = None) -> int | None:
    d = parse_date(raw)
    if d is None:
        return None
    return ((today or date.today()) - d).days


def recency_penalty(raw: str | None, today: date | None = None) -> tuple[int, dict]:
    """Points (<= 0) + detail for a posting's age. 0 when the date is missing/unparseable."""
    age = age_days(raw, today)
    if age is None:
        return 0, {"recency": "unknown"}
    if age <= GRACE_DAYS:
        return 0, {"recency_age_days": age}
    weeks_over = (age - GRACE_DAYS) // 7
    penalty = -min(weeks_over * PER_WEEK, CAP)
    return penalty, {"recency_age_days": age, "recency_penalty": penalty}
