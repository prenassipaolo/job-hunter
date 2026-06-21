"""Tests for the location-tier model (1 = best)."""

from job_hunter import locations
from job_hunter.locations import (
    OUTSIDE_POINTS,
    REMOTE_POINTS,
    TIER_POINTS,
    UNKNOWN_POINTS,
    city_tier,
    country_tier,
    location_score,
)


def test_country_tiers():
    assert country_tier("Switzerland") == 1
    assert country_tier("Germany") == 2
    assert country_tier("Italy") == 3
    assert country_tier("United States") == 4
    assert country_tier("Narnia") == 0  # untiered


def test_city_inherits_country_tier_by_default():
    # With no overrides, every city takes its country's tier.
    assert city_tier("Amsterdam, Netherlands", "Netherlands") == 1
    assert city_tier("Munich, Germany", "Germany") == 2
    assert city_tier("Somewhere, Narnia", "Narnia") == 0


def test_city_override_beats_country_tier(monkeypatch):
    # A per-city override wins over the country tier (here: worse than NL's tier 1).
    monkeypatch.setitem(locations.CITY_TIERS, "utrecht", 3)
    assert city_tier("Utrecht, Netherlands", "Netherlands") == 3
    assert city_tier("Amsterdam, Netherlands", "Netherlands") == 1  # still inherits


def test_location_score_uses_tier_points():
    pts, detail = location_score("United Kingdom", "London, UK", remote=False, remote_ok=True)
    assert pts == TIER_POINTS[1]
    assert detail["location_tier"] == 1


def test_location_score_fallbacks():
    assert location_score("", "", remote=True, remote_ok=True)[0] == REMOTE_POINTS
    assert location_score("", "", remote=False, remote_ok=True)[0] == UNKNOWN_POINTS
    assert location_score("Brazil", "São Paulo", remote=False, remote_ok=True)[0] == OUTSIDE_POINTS
    # A lower-tier country still beats remote-only.
    assert location_score("Portugal", "Porto", False, True)[0] == TIER_POINTS[4]
