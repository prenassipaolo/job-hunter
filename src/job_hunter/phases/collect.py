"""Phase 1 — collect with fixed, cheap rules.

Fetch from the providers, then keep ONLY postings that pass deterministic gates:
location (CH/IE/NL/UK or remote), employer reputation, role type (hands-on
dev/quant/DS), and a prescreen heuristic score above threshold. Nothing here costs
tokens — it exists to hand phase 2 a small, clean candidate set worth AI attention.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from rich.console import Console

from job_hunter.locations import country_tier
from job_hunter.models import Job
from job_hunter.profile import Profile
from job_hunter.providers import ALL_PROVIDERS
from job_hunter.reputation import is_reputable
from job_hunter.scoring import score_job

console = Console()


@dataclass
class CollectConfig:
    profile_path: str
    work_dir: str
    providers: list[str]
    reputable_only: bool = True
    countries_only: bool = True
    role_gate: bool = True
    prescreen_min: int = 45
    keep: int = 120


def _term_in(text: str, term: str) -> bool:
    """Word-boundary-ish match so short tokens like 'ai ' / 'ml ' don't over-match."""
    t = term.strip()
    if len(t) <= 3:
        return re.search(rf"(^|[^a-z]){re.escape(t)}([^a-z]|$)", text) is not None
    return t in text


def passes_role_gate(title: str, profile: Profile) -> bool:
    t = title.lower()
    core = profile.role_gate.get("core", [])
    exclude = profile.role_gate.get("exclude", [])
    if any(_term_in(t, x) for x in exclude):
        return False
    return any(_term_in(t, c) for c in core)


def _keep_location(job: Job, profile: Profile) -> bool:
    # Keep any tiered country (1=best..4) or remote — tier only affects ranking, so
    # tier 2-4 countries (Germany, Italy, US, ...) appear too, just lower down.
    return country_tier(job.country) > 0 or (job.remote and profile.remote_ok)


def _dedup(jobs: list[Job]) -> list[Job]:
    seen: dict[str, Job] = {}
    for j in jobs:
        seen.setdefault(j.id, j)
    return list(seen.values())


def _norm_key(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def _collapse_variants(jobs: list[Job], profile: Profile) -> list[Job]:
    """Collapse the same role posted to several locations into one candidate.

    Exact-URL dupes are already gone; this catches same company + same title posted
    once per city/country. Keeps the most relevant variant (a target-country one, then
    a remote one) and merges the distinct locations into it so nothing is lost.
    """
    groups: dict[tuple[str, str], list[Job]] = {}
    order: list[tuple[str, str]] = []
    for j in jobs:
        key = (_norm_key(j.company), _norm_key(j.title))
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(j)

    result: list[Job] = []
    for key in order:
        grp = groups[key]
        if len(grp) == 1:
            result.append(grp[0])
            continue
        rep = max(grp, key=lambda j: (j.country in profile.target_countries, j.remote))
        locs: list[str] = []
        for j in grp:
            if j.location and j.location not in locs:
                locs.append(j.location)
        if locs:
            rep.location = " | ".join(locs)
        rep.fit_breakdown["merged_variants"] = len(grp)
        result.append(rep)
    return result


def collect(cfg: CollectConfig) -> list[Job]:
    profile = Profile.load(cfg.profile_path)

    raw: list[Job] = []
    for name in cfg.providers:
        provider_cls = ALL_PROVIDERS.get(name)
        if provider_cls is None:
            continue
        provider = provider_cls()
        if not provider.available():
            console.print(f"[dim]{name}: skipped (no API key)[/]")
            continue
        try:
            found = provider.fetch(profile)
            console.print(f"[green]{name}[/]: {len(found)} raw")
            raw.extend(found)
        except Exception as exc:
            console.print(f"[red]{name} failed: {exc}[/]")

    jobs = _dedup(raw)
    console.print(f"[bold]{len(jobs)}[/] unique")

    if cfg.countries_only:
        jobs = [j for j in jobs if _keep_location(j, profile)]
        console.print(f"{len(jobs)} after location gate")
    if cfg.reputable_only:
        jobs = [j for j in jobs if is_reputable(j.company)]
        console.print(f"{len(jobs)} after reputation gate")
    if cfg.role_gate:
        jobs = [j for j in jobs if passes_role_gate(j.title, profile)]
        console.print(f"{len(jobs)} after role-type gate (dev/quant/DS only)")

    before = len(jobs)
    jobs = _collapse_variants(jobs, profile)
    if len(jobs) < before:
        console.print(f"{len(jobs)} after collapsing {before - len(jobs)} multi-location duplicates")

    for j in jobs:
        score_job(j, profile)  # prescreen heuristic -> fit_score

    jobs = [j for j in jobs if j.fit_score >= cfg.prescreen_min]
    jobs.sort(key=lambda j: j.fit_score, reverse=True)
    jobs = jobs[: cfg.keep]
    console.print(f"[bold]{len(jobs)}[/] candidates above prescreen {cfg.prescreen_min}")

    out = Path(cfg.work_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "phase1_candidates.json").write_text(
        json.dumps([j.to_dict() for j in jobs], indent=2, ensure_ascii=False), encoding="utf-8"
    )
    console.print(f"[green]phase 1 → {out / 'phase1_candidates.json'}[/]")
    return jobs
