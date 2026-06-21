"""Arbeitnow job-board API. No key. Strong EU coverage (incl. NL remote roles)."""

from __future__ import annotations

import httpx

from job_hunter.models import Job
from job_hunter.profile import Profile

from .base import Provider, infer_country, strip_html

API = "https://www.arbeitnow.com/api/job-board-api"


class ArbeitnowProvider(Provider):
    name = "arbeitnow"

    def __init__(self, pages: int = 3, **kw):
        super().__init__(**kw)
        self.pages = pages

    def fetch(self, profile: Profile) -> list[Job]:
        jobs: list[Job] = []
        with httpx.Client(timeout=self.timeout, headers={"User-Agent": "job-hunter/0.1"}) as client:
            url = API
            for _ in range(self.pages):
                try:
                    payload = client.get(url).json()
                except (httpx.HTTPError, ValueError):
                    break
                for item in payload.get("data", []):
                    location = item.get("location", "")
                    jobs.append(
                        Job(
                            source="arbeitnow",
                            title=item.get("title", ""),
                            company=item.get("company_name", "Unknown"),
                            url=item.get("url", ""),
                            location=location,
                            country=infer_country(location),
                            description=strip_html(item.get("description", "")),
                            remote=bool(item.get("remote")),
                            posted_at=str(item.get("created_at", "")),
                            tags=item.get("tags", []) or [],
                        )
                    )
                url = (payload.get("links") or {}).get("next") or ""
                if not url:
                    break
        return jobs
