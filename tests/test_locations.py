"""Location tiers are persona-driven (passed in), with city overrides beating country."""

from job_hunter.locations import DEFAULT_COUNTRY_TIERS, city_tier, country_tier

CT = {"Switzerland": 1, "Germany": 2, "Italy": 3, "United States": 4}


def test_country_tier_uses_the_given_map():
    assert country_tier("Switzerland", CT) == 1
    assert country_tier("Germany", CT) == 2
    assert country_tier("Narnia", CT) == 0  # not in this persona's map


def test_city_inherits_country_tier_by_default():
    assert city_tier("Zurich, Switzerland", "Switzerland", CT, {}) == 1
    assert city_tier("Munich, Germany", "Germany", CT, {}) == 2


def test_city_override_beats_country_tier():
    city_tiers = {"geneva": 2}  # Geneva worse than Zurich within tier-1 Switzerland
    assert city_tier("Geneva, Switzerland", "Switzerland", CT, city_tiers) == 2
    assert city_tier("Zurich, Switzerland", "Switzerland", CT, city_tiers) == 1


def test_defaults_exist_for_personas_that_omit_tiers():
    assert DEFAULT_COUNTRY_TIERS["Switzerland"] == 1
    assert DEFAULT_COUNTRY_TIERS["United States"] == 4
