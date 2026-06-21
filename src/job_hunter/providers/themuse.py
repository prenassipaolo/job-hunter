"""The Muse public jobs API. No key required; good company + location coverage."""

from __future__ import annotations

import httpx

from job_hunter.models import Job
from job_hunter.profile import Profile

from .base import Provider, infer_country, strip_html

API = "https://www.themuse.com/api/public/jobs"
# Muse categories that overlap with the persona's lanes.
CATEGORIES = ["Data Science", "Data and Analytics", "Software Engineering", "Engineering"]


class TheMuseProvider(Provider):
    name = "themuse"

    def __init__(self, pages: int = 1, **kw):
        super().__init__(**kw)
        self.pages = pages

    def fetch(self, profile: Profile) -> list[Job]:
        jobs: list[Job] = []
        with httpx.Client(timeout=self.timeout, headers={"User-Agent": "job-hunter/0.1"}) as client:
            for location in profile.target_cities:
                for category in CATEGORIES:
                    for page in range(self.pages):
                        params = {"category": category, "location": location, "page": page}
                        try:
                            r = client.get(API, params=params)
                            if r.status_code != 200:
                                continue
                            results = r.json().get("results", [])
                        except (httpx.HTTPError, ValueError):
                            continue
                        for item in results:
                            jobs.append(self._to_job(item))
        return jobs

    @staticmethod
    def _to_job(item: dict) -> Job:
        locs = ", ".join(loc.get("name", "") for loc in item.get("locations", []))
        company = (item.get("company") or {}).get("name", "Unknown")
        url = (item.get("refs") or {}).get("landing_page", "")
        return Job(
            source="themuse",
            title=item.get("name", ""),
            company=company,
            url=url,
            location=locs,
            country=infer_country(locs),
            description=strip_html(item.get("contents", "")),
            remote="remote" in locs.lower() or "flexible" in locs.lower(),
            posted_at=item.get("publication_date", ""),
            tags=[t.get("name", "") for t in item.get("tags", [])],
        )
