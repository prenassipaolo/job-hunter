"""Company ATS boards — Greenhouse, Lever and Ashby (all keyless, free).

Most elite employers (trading firms, big tech, fintech scale-ups) don't post to
aggregators — they post to their own careers page, which is almost always powered by
one of these three applicant-tracking systems, each exposing a public JSON endpoint:

    Greenhouse  https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true
    Lever       https://api.lever.co/v0/postings/{slug}?mode=json
    Ashby       https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true

This targets the persona's curated reputation list head-on instead of fishing in an
aggregator and filtering down. The `BOARDS` list below maps a company to its ATS and
board slug — slugs are best-effort; a wrong one simply returns nothing (failures are
swallowed per board), so prune/extend freely as you discover the right handles.

Downstream gates (location, role-type) still apply, so global boards are fine — the
CH/IE/NL/UK/remote filter trims the rest.
"""

from __future__ import annotations

import html as _html

import httpx

from job_hunter.models import Job
from job_hunter.profile import Profile

from .base import Provider, infer_country, strip_html

# (ats, slug, display_name). Display name is used as the company so it matches the
# reputation tiers cleanly regardless of what the board returns.
BOARDS: list[tuple[str, str, str]] = [
    # --- Greenhouse ---------------------------------------------------------
    ("greenhouse", "anthropic", "Anthropic"),
    ("greenhouse", "stripe", "Stripe"),
    ("greenhouse", "databricks", "Databricks"),
    ("greenhouse", "datadog", "Datadog"),
    ("greenhouse", "gitlab", "GitLab"),
    ("greenhouse", "robinhood", "Robinhood"),
    ("greenhouse", "coinbase", "Coinbase"),
    ("greenhouse", "dropbox", "Dropbox"),
    ("greenhouse", "figma", "Figma"),
    ("greenhouse", "monzo", "Monzo"),
    ("greenhouse", "elastic", "Elastic"),
    ("greenhouse", "discord", "Discord"),
    ("greenhouse", "celonis", "Celonis"),
    ("greenhouse", "point72", "Point72"),
    ("greenhouse", "imc", "IMC Trading"),
    ("greenhouse", "squarepointcapital", "Squarepoint Capital"),
    # --- Lever --------------------------------------------------------------
    ("lever", "spotify", "Spotify"),
    ("lever", "palantir", "Palantir"),
    ("lever", "plaid", "Plaid"),
    # --- Ashby --------------------------------------------------------------
    ("ashby", "openai", "OpenAI"),
    ("ashby", "ramp", "Ramp"),
    ("ashby", "notion", "Notion"),
    ("ashby", "linear", "Linear"),
    ("ashby", "synthesia", "Synthesia"),
]


class ATSProvider(Provider):
    name = "ats"

    def fetch(self, profile: Profile) -> list[Job]:
        jobs: list[Job] = []
        # Short per-request timeout: many boards, don't let one slow host stall the run.
        with httpx.Client(
            timeout=min(self.timeout, 12.0),
            headers={"User-Agent": "Mozilla/5.0 (job-hunter)"},
            follow_redirects=True,
        ) as client:
            for ats, slug, company in BOARDS:
                try:
                    jobs.extend(_FETCHERS[ats](client, slug, company))
                except (httpx.HTTPError, ValueError, KeyError, TypeError):
                    continue  # bad slug / transient error / shape change — skip board
        return jobs


def _fetch_greenhouse(client: httpx.Client, slug: str, company: str) -> list[Job]:
    url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
    r = client.get(url, params={"content": "true"})
    if r.status_code != 200:
        return []
    out: list[Job] = []
    for it in r.json().get("jobs", []):
        loc = (it.get("location") or {}).get("name", "")
        content = strip_html(_html.unescape(it.get("content", "") or ""))
        out.append(
            Job(
                source="ats:greenhouse",
                title=it.get("title", ""),
                company=company,
                url=it.get("absolute_url", ""),
                location=loc,
                country=infer_country(loc),
                remote="remote" in loc.lower(),
                description=content,
                posted_at=it.get("updated_at", "") or "",
            )
        )
    return out


def _fetch_lever(client: httpx.Client, slug: str, company: str) -> list[Job]:
    url = f"https://api.lever.co/v0/postings/{slug}"
    r = client.get(url, params={"mode": "json"})
    if r.status_code != 200:
        return []
    out: list[Job] = []
    for it in r.json():
        cats = it.get("categories") or {}
        loc = cats.get("location", "") or ""
        desc = it.get("descriptionPlain") or strip_html(it.get("description", "") or "")
        out.append(
            Job(
                source="ats:lever",
                title=it.get("text", ""),
                company=company,
                url=it.get("hostedUrl", "") or it.get("applyUrl", ""),
                location=loc,
                country=infer_country(loc),
                remote=(cats.get("commitment", "") or "").lower() == "remote" or "remote" in loc.lower(),
                description=desc[:6000],
                posted_at="",
                tags=[t for t in (cats.get("team"), cats.get("department")) if t],
            )
        )
    return out


def _fetch_ashby(client: httpx.Client, slug: str, company: str) -> list[Job]:
    url = f"https://api.ashbyhq.com/posting-api/job-board/{slug}"
    r = client.get(url, params={"includeCompensation": "true"})
    if r.status_code != 200:
        return []
    out: list[Job] = []
    for it in r.json().get("jobs", []):
        loc = it.get("location", "") or ""
        desc = it.get("descriptionPlain") or strip_html(it.get("descriptionHtml", "") or "")
        out.append(
            Job(
                source="ats:ashby",
                title=it.get("title", ""),
                company=company,
                url=it.get("jobUrl", "") or it.get("applyUrl", ""),
                location=loc,
                country=infer_country(loc),
                remote=bool(it.get("isRemote")) or "remote" in loc.lower(),
                description=desc[:6000],
                posted_at=it.get("publishedAt", "") or "",
            )
        )
    return out


_FETCHERS = {
    "greenhouse": _fetch_greenhouse,
    "lever": _fetch_lever,
    "ashby": _fetch_ashby,
}
