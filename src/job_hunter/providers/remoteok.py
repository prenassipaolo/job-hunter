"""RemoteOK public API. No key. Remote tech roles, often with salary bands (USD)."""

from __future__ import annotations

import httpx

from job_hunter.models import Job
from job_hunter.profile import Profile

from .base import Provider, infer_country, strip_html

API = "https://remoteok.com/api"


class RemoteOKProvider(Provider):
    name = "remoteok"

    def fetch(self, profile: Profile) -> list[Job]:
        try:
            with httpx.Client(timeout=self.timeout, headers={"User-Agent": "Mozilla/5.0"}) as client:
                data = client.get(API).json()
        except (httpx.HTTPError, ValueError):
            return []
        jobs: list[Job] = []
        for item in data:
            # The first element is a legal/metadata notice, skip anything without a position.
            if not isinstance(item, dict) or not item.get("position"):
                continue
            location = item.get("location", "") or "Remote"
            jobs.append(
                Job(
                    source="remoteok",
                    title=item.get("position", ""),
                    company=item.get("company", "Unknown"),
                    url=item.get("url") or item.get("apply_url", ""),
                    location=location,
                    country=infer_country(location),
                    description=strip_html(item.get("description", "")),
                    remote=True,
                    salary_min=_num(item.get("salary_min")),
                    salary_max=_num(item.get("salary_max")),
                    salary_currency="USD" if (item.get("salary_min") or item.get("salary_max")) else "",
                    salary_period="year",
                    posted_at=item.get("date", ""),
                    tags=item.get("tags", []) or [],
                )
            )
        return jobs


def _num(v) -> float | None:
    try:
        n = float(v)
        return n if n > 0 else None
    except (TypeError, ValueError):
        return None
