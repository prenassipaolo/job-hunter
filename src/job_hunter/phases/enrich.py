"""Phase 2 — re-check the links and enrich with AI.

Reads phase-1 candidates, re-visits each job URL to pull fuller text, then asks Claude
Haiku (cheapest model) to extract anything missing (salary, true seniority) and to
judge fit, producing an `ai_score` and a candid note. If no ANTHROPIC_API_KEY is set,
the phase still runs and simply flows the heuristic forward (ai_score stays null).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from rich.console import Console

from job_hunter.cache import JsonCache, hash_key
from job_hunter.models import Job
from job_hunter.pagefetch import fetch_page_text
from job_hunter.profile import Profile
from job_hunter.scoring import llm

console = Console()


@dataclass
class EnrichConfig:
    profile_path: str
    work_dir: str
    top_n: int = 25  # only enrich the top of the prescreen list (token control)
    refetch_pages: bool = True
    use_llm: bool = True
    refresh: bool = False  # ignore caches and recompute (re-fetch pages, re-call the LLM)


def _load(work_dir: str) -> list[Job]:
    path = Path(work_dir) / "phase1_candidates.json"
    if not path.exists():
        raise FileNotFoundError(f"phase 1 artifact missing: {path}. Run `collect` first.")
    return [Job.from_dict(d) for d in json.loads(path.read_text(encoding="utf-8"))]


def enrich(cfg: EnrichConfig) -> list[Job]:
    profile = Profile.load(cfg.profile_path)
    jobs = _load(cfg.work_dir)
    head = jobs[: cfg.top_n]
    console.print(f"[bold]{len(head)}[/] candidates entering phase 2 (of {len(jobs)})")

    cache_dir = Path(cfg.work_dir) / "cache"
    if cfg.refresh:
        console.print("[yellow]--refresh: ignoring caches, recomputing[/]")

    if cfg.refetch_pages:
        pages = JsonCache(cache_dir / "pages.json", enabled=not cfg.refresh)
        refetched = hits = 0
        for job in head:
            text = pages.get(job.url)
            if text is None:
                text = fetch_page_text(job.url) or ""
                if text:
                    pages.set(job.url, text)  # cache successes only, so failures retry
            else:
                hits += 1
            if text:
                job.description = text
                job.page_refetched = True
                refetched += 1
        pages.save()
        console.print(f"pages: {refetched}/{len(head)} available ({hits} from cache)")

    if cfg.use_llm and llm.available():
        console.print("[cyan]evaluating fit with Claude Haiku…[/]")
        cache = JsonCache(cache_dir / "llm.json", enabled=not cfg.refresh)
        client = llm.make_client()
        blurb = llm.profile_blurb(profile)
        calls = hits = 0
        for job in head:
            key = hash_key(job.id, job.description[:4000], llm.MODEL)
            data = cache.get(key)
            if data is None:
                data = llm.enrich_one(client, job, blurb)
                if data is not None:
                    cache.set(key, data)
                    calls += 1
            else:
                hits += 1
            if data:
                llm.apply(job, data)
        cache.save()
        console.print(f"LLM: {calls} new calls, {hits} from cache")
    elif cfg.use_llm:
        console.print("[yellow]LLM requested but unavailable (no key / anthropic) — heuristic only[/]")

    # Anything beyond the enriched head still flows forward with ai_score=None.
    out = Path(cfg.work_dir) / "phase2_enriched.json"
    out.write_text(
        json.dumps([j.to_dict() for j in head + jobs[cfg.top_n :]], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    console.print(f"[green]phase 2 → {out}[/]")
    return head
