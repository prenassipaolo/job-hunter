"""Provider base class and shared helpers."""

from __future__ import annotations

from bs4 import BeautifulSoup

from job_hunter.models import Job
from job_hunter.profile import Profile

# Map of country -> substrings that, if found in a location string, imply it.
COUNTRY_HINTS: dict[str, list[str]] = {
    "Switzerland": ["switzerland", "zurich", "zürich", "geneva", "genève", "basel", "lausanne", "zug", " ch", "bern"],
    "Ireland": ["ireland", "dublin", "cork", "galway", "limerick"],
    "Netherlands": ["netherlands", "amsterdam", "utrecht", "rotterdam", "the hague", "den haag", "eindhoven", "holland", "nl"],
    "United Kingdom": ["united kingdom", "uk", "england", "london", "manchester", "edinburgh", "cambridge", "scotland", "wales", "bristol", "leeds", "glasgow"],
}


def infer_country(location: str) -> str:
    """Best-effort country from a free-text location. Returns '' if unknown."""
    loc = f" {location.lower()} "
    for country, hints in COUNTRY_HINTS.items():
        for hint in hints:
            if f"{hint} " in loc or f" {hint}" in loc or hint in location.lower():
                # avoid matching the bare "nl"/"uk"/"ch" tokens too loosely
                if hint in {"nl", "uk", " ch"} and len(location) > 4:
                    if hint.strip() not in loc.split():
                        continue
                return country
    return ""


def strip_html(html: str, limit: int = 6000) -> str:
    """Turn an HTML job description into plain text, trimmed to `limit` chars."""
    if not html:
        return ""
    text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
    return text[:limit]


class Provider:
    """Subclasses implement `fetch` and return a list of normalised Jobs."""

    name: str = "base"

    def __init__(self, timeout: float = 20.0):
        self.timeout = timeout

    def fetch(self, profile: Profile) -> list[Job]:  # pragma: no cover - interface
        raise NotImplementedError

    def available(self) -> bool:
        """Whether the provider can run (e.g. has required API keys)."""
        return True
