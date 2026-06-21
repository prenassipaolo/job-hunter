"""Jobicy remote-jobs API. No key. Carries salary bands and seniority hints."""

from __future__ import annotations

import httpx

from job_hunter.models import Job
from job_hunter.profile import Profile

from .base import Provider, infer_country, strip_html

API = "https://jobicy.com/api/v2/remote-jobs"
# Jobicy industry tags that map onto the persona's lanes.
INDUSTRIES = ["data-science", "engineering", "dev"]


class JobicyProvider(Provider):
    name = "jobicy"

    def __init__(self, count: int = 50, **kw):
        super().__init__(**kw)
        self.count = count

    def fetch(self, profile: Profile) -> list[Job]:
        jobs: list[Job] = []
        with httpx.Client(timeout=self.timeout, headers={"User-Agent": "job-hunter/0.1"}) as client:
            for industry in INDUSTRIES:
                params = {"count": self.count, "industry": industry}
                try:
                    payload = client.get(API, params=params).json()
                except (httpx.HTTPError, ValueError):
                    continue
                for item in payload.get("jobs", []):
                    geo = item.get("jobGeo", "") or "Anywhere"
                    desc = item.get("jobDescription") or item.get("jobExcerpt") or ""
                    jobs.append(
                        Job(
                            source="jobicy",
                            title=item.get("jobTitle", ""),
                            company=item.get("companyName", "Unknown"),
                            url=item.get("url", ""),
                            location=geo,
                            country=infer_country(geo),
                            description=strip_html(desc),
                            remote=True,
                            salary_min=_num(item.get("salaryMin")),
                            salary_max=_num(item.get("salaryMax")),
                            salary_currency=item.get("salaryCurrency", "") or "",
                            salary_period=(item.get("salaryPeriod", "") or "").replace("annual", "year"),
                            posted_at=item.get("pubDate", ""),
                            tags=[item.get("jobIndustry", ""), item.get("jobLevel", "")],
                        )
                    )
        return jobs


def _num(v) -> float | None:
    try:
        n = float(v)
        return n if n > 0 else None
    except (TypeError, ValueError):
        return None
