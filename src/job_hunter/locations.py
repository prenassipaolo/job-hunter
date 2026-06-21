"""Location tiers — countries and cities, 1 = best.

This is a *ranking weight*, never a filter: better-tier locations earn more points so
they rank higher, but no job is dropped just for its tier.

Every city has an **effective tier**: if it appears in ``CITY_TIERS`` it uses that,
otherwise it inherits its country's tier. So today every city in a tier-1 country
scores tier 1 — but later you can rate cities individually (e.g. Amsterdam above
Utrecht, Milan above Rome, Zurich above Geneva) without changing the country tiers.

Edit the dicts to taste — an untiered location is tier 0 and earns no location bonus.
"""

from __future__ import annotations

import re

# Country -> tier (1 = best). Anything not listed is tier 0 (untiered).
COUNTRY_TIERS: dict[str, int] = {
    # Tier 1 — primary targets
    "Switzerland": 1, "Ireland": 1, "Netherlands": 1, "United Kingdom": 1,
    # Tier 2
    "Germany": 2, "Luxembourg": 2,
    # Tier 3
    "Sweden": 3, "Denmark": 3, "Italy": 3, "Spain": 3, "Austria": 3, "Belgium": 3,
    # Tier 4
    "Portugal": 4, "United States": 4,
}

# Per-city overrides (lowercase city -> tier, 1 = best). EMPTY for now: every city
# inherits its country tier. Fill this in later to rank cities within/across countries.
# Examples Paolo plans to add (a city tier can be better OR worse than its country):
#   "amsterdam": 1, "utrecht": 2, "rotterdam": 2,
#   "zurich": 1, "geneva": 2, "zug": 2,
#   "milan": 3, "rome": 4,
#   "berlin": 2, "munich": 2,        # both top in Germany
#   "madrid": 3, "barcelona": 3,     # both top in Spain
CITY_TIERS: dict[str, int] = {}

# Points per (effective) location tier, plus the situational fallbacks.
TIER_POINTS = {1: 12, 2: 8, 3: 4, 4: 1, 0: 0}
REMOTE_POINTS = 6     # remote (and persona accepts remote) but no tiered location
UNKNOWN_POINTS = 2    # location/country couldn't be inferred — don't punish hard
OUTSIDE_POINTS = -22  # a concrete location in no tiered country — near-blocker


def country_tier(country: str) -> int:
    """Tier for a country name (1 = best), or 0 if it isn't in the list."""
    return COUNTRY_TIERS.get(country, 0)


def city_tier(location: str, country: str) -> int:
    """Effective tier for a job's location.

    A ``CITY_TIERS`` override wins if its city appears in the location text; otherwise
    the city inherits its country's tier. Returns 0 when neither is known.
    """
    low = location.lower()
    for city, tier in CITY_TIERS.items():
        if re.search(rf"\b{re.escape(city)}\b", low):
            return tier
    return country_tier(country)


def location_score(country: str, location: str, remote: bool, remote_ok: bool) -> tuple[int, dict]:
    """Points + an explainable detail dict for a job's location.

    Tiered location -> tier points; otherwise remote / unknown / outside fallbacks.
    """
    tier = city_tier(location, country)
    if tier:
        return TIER_POINTS[tier], {"location_tier": tier}
    if remote and remote_ok:
        return REMOTE_POINTS, {"location_tier": 0, "remote": True}
    if not country:
        return UNKNOWN_POINTS, {"location_tier": 0, "unknown": True}
    return OUTSIDE_POINTS, {"location_tier": 0, "outside": True}
