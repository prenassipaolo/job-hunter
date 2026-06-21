"""infer_country must label the tiered countries and not over-match."""

from job_hunter.providers.base import infer_country


def test_original_four_still_work():
    assert infer_country("Amsterdam, Netherlands") == "Netherlands"
    assert infer_country("Zurich, Switzerland") == "Switzerland"
    assert infer_country("London, UK") == "United Kingdom"
    assert infer_country("Dublin") == "Ireland"


def test_new_countries_recognised():
    assert infer_country("Berlin, Germany") == "Germany"
    assert infer_country("Milan, Italy") == "Italy"
    assert infer_country("Madrid") == "Spain"
    assert infer_country("Vienna, Austria") == "Austria"
    assert infer_country("Lisbon, Portugal") == "Portugal"
    assert infer_country("Brussels, Belgium") == "Belgium"
    assert infer_country("San Francisco, CA") == "United States"
    assert infer_country("New York, NY") == "United States"


def test_does_not_over_match():
    # "gent" must not match "Argentina"; bare "us" must not match common words.
    assert infer_country("Buenos Aires, Argentina") == ""
    assert infer_country("Business Analyst Hub") == ""
    assert infer_country("") == ""
