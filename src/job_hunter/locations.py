"""Location tiers — countries and cities, 1 = best.

These are **personal preferences**, so the actual tiers live in the persona
(``country_tiers`` / ``city_tiers``). The maps here are only *fallback defaults* used
when a persona doesn't specify its own. (Things that are NOT personal — e.g. a company's
reputation — live in reputation.py, not here.)

A location's *effective tier* is its ``city_tiers`` override if the city matches,
otherwise its country's tier. Tier is a ranking weight, never a filter.
"""

from __future__ import annotations

import re

# Fallback country -> tier (1 = best). A persona's `country_tiers` overrides this wholesale.
DEFAULT_COUNTRY_TIERS: dict[str, int] = {
    "Switzerland": 1, "Ireland": 1, "Netherlands": 1, "United Kingdom": 1,
    "Germany": 2, "Luxembourg": 2,
    "Sweden": 3, "Denmark": 3, "Italy": 3, "Spain": 3, "Austria": 3, "Belgium": 3,
    "Portugal": 4, "United States": 4,
}
# Fallback per-city overrides (lowercase city -> tier). Empty: cities inherit their country.
DEFAULT_CITY_TIERS: dict[str, int] = {}


def country_tier(country: str, country_tiers: dict[str, int]) -> int:
    """Tier for a country name (1 = best), or 0 if it isn't in the given map."""
    return country_tiers.get(country, 0)


def city_tier(location: str, country: str, country_tiers: dict[str, int],
              city_tiers: dict[str, int]) -> int:
    """Effective tier for a job's location: a city override if it matches, else the
    country tier. Returns 0 when neither is known."""
    low = location.lower()
    for city, tier in city_tiers.items():
        if re.search(rf"\b{re.escape(city)}\b", low):
            return tier
    return country_tiers.get(country, 0)
