"""Adzuna Jobs API. Requires a free app_id/app_key (ADZUNA_APP_ID / ADZUNA_APP_KEY).

This is the highest-quality source for the persona's targets: it covers GB, NL, CH and IE
directly and returns real salary ranges. It is skipped automatically when no keys
are set, so the tool still runs fully on the keyless providers alone.

Register for free keys at https://developer.adzuna.com/ and put them in a .env file.
"""

from __future__ import annotations

import os

import httpx

from job_hunter.models import Job
from job_hunter.profile import Profile

from .base import Provider, strip_html

# Adzuna country code -> our country label.
COUNTRY_CODES = {"gb": "United Kingdom", "nl": "Netherlands", "ch": "Switzerland", "ie": "Ireland"}
API = "https://api.adzuna.com/v1/api/jobs/{code}/search/1"
# A few broad queries spanning the lanes; Adzuna does its own relevance ranking.
QUERIES = ["quantitative developer", "machine learning engineer", "data scientist", "credit risk", "AI engineer"]


class AdzunaProvider(Provider):
    name = "adzuna"

    def __init__(self, results_per_query: int = 20, **kw):
        super().__init__(**kw)
        self.app_id = os.getenv("ADZUNA_APP_ID", "")
        self.app_key = os.getenv("ADZUNA_APP_KEY", "")
        self.results_per_query = results_per_query

    def available(self) -> bool:
        return bool(self.app_id and self.app_key)

    def fetch(self, profile: Profile) -> list[Job]:
        if not self.available():
            return []
        jobs: list[Job] = []
        with httpx.Client(timeout=self.timeout, headers={"User-Agent": "job-hunter/0.1"}) as client:
            for code, country in COUNTRY_CODES.items():
                for query in QUERIES:
                    params = {
                        "app_id": self.app_id,
                        "app_key": self.app_key,
                        "what": query,
                        "results_per_page": self.results_per_query,
                        "content-type": "application/json",
                    }
                    try:
                        payload = client.get(API.format(code=code), params=params).json()
                    except (httpx.HTTPError, ValueError):
                        continue
                    for item in payload.get("results", []):
                        loc = (item.get("location") or {}).get("display_name", country)
                        jobs.append(
                            Job(
                                source="adzuna",
                                title=item.get("title", ""),
                                company=(item.get("company") or {}).get("display_name", "Unknown"),
                                url=item.get("redirect_url", ""),
                                location=loc,
                                country=country,
                                description=strip_html(item.get("description", "")),
                                remote="remote" in loc.lower(),
                                salary_min=item.get("salary_min"),
                                salary_max=item.get("salary_max"),
                                salary_currency=_currency(code),
                                salary_period="year",
                                posted_at=item.get("created", ""),
                                tags=[(item.get("category") or {}).get("label", "")],
                            )
                        )
        return jobs


def _currency(code: str) -> str:
    return {"gb": "GBP", "nl": "EUR", "ch": "CHF", "ie": "EUR"}.get(code, "")
