"""Phase 3 — rank and write the final shortlist.

Reads phase-2 output, blends the cheap heuristic score with the AI score (when phase 2
produced one), sorts, and writes the per-role files. This is the only phase that emits
the human-facing artifacts.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from rich.console import Console

from job_hunter.models import Job
from job_hunter.recency import age_days
from job_hunter.scoring.heuristic import label_for
from job_hunter.storage import write_results
from job_hunter.tiers import apply_overrides, load_overrides

console = Console()

@dataclass
class RankConfig:
    work_dir: str
    out_dir: str
    final_min: int = 0
    top_n: int = 60
    tiers_path: str = ""  # sidecar of manual job tiers; "" = none


def _age_key(job: Job) -> int:
    """Sort helper: smaller = fresher. Unknown date sinks to the bottom."""
    age = age_days(job.posted_at)
    return age if age is not None else 10**6


def _rank_key(job: Job) -> tuple:
    """Sort key (smaller = better): manual tier, then ENRICHED-FIRST, then blended score
    desc, then freshest.

    'Enriched-first' is the coherence fix: a job the LLM actually evaluated outranks an
    un-evaluated one of the same tier, so honest AI scores (which are usually < an
    inflated heuristic 100%) no longer push enriched jobs out of the visible shortlist.
    When nothing is enriched (e.g. --no-llm), the flag is constant and has no effect.
    """
    return (job.tier, job.ai_score is None, -job.final_score, _age_key(job))


def rank(cfg: RankConfig) -> list[Job]:
    path = Path(cfg.work_dir) / "phase2_enriched.json"
    if not path.exists():
        raise FileNotFoundError(f"phase 2 artifact missing: {path}. Run `enrich` first.")
    jobs = [Job.from_dict(d) for d in json.loads(path.read_text(encoding="utf-8"))]

    # fit_score already folds in the AI features (enrich re-scored the head), so the final
    # score is just the fit score — no separate blend.
    for job in jobs:
        job.final_score = job.fit_score
        job.fit_label = label_for(job.final_score)

    # Manual job tiers (1 = best) win over fit: a promoted role floats to the top.
    # Untouched jobs all share the lowest tier, so this is a no-op until you curate.
    if cfg.tiers_path:
        apply_overrides(jobs, load_overrides(cfg.tiers_path))

    jobs = [j for j in jobs if j.final_score >= cfg.final_min]
    jobs.sort(key=_rank_key)
    jobs = jobs[: cfg.top_n]

    run_dir = write_results(jobs, cfg.out_dir)
    console.print(f"[bold green]phase 3 → ranked {len(jobs)} roles into {run_dir}[/]")
    return jobs
