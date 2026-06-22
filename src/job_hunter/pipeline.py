"""Orchestrator: chain phase 1 -> 2 -> 3. Each phase also runs standalone via the CLI."""

from __future__ import annotations

from dataclasses import dataclass

from job_hunter.models import Job
from job_hunter.phases.collect import CollectConfig, collect
from job_hunter.phases.enrich import EnrichConfig, enrich
from job_hunter.phases.rank import RankConfig, rank


@dataclass
class RunConfig:
    profile_path: str
    work_dir: str
    out_dir: str
    providers: list[str]
    reputable_only: bool = True
    countries_only: bool = True
    role_gate: bool = True
    prescreen_min: int = 45
    per_company_cap: int = 8
    per_provider_cap: int = 0
    enrich_top: int = 25
    refetch_pages: bool = True
    use_llm: bool = True  # LLM enrichment is the default for the full flow
    refresh: bool = False
    ai_min: int = 50
    final_min: int = 0
    top_n: int = 60
    tiers_path: str = ""


def run(cfg: RunConfig) -> list[Job]:
    collect(
        CollectConfig(
            profile_path=cfg.profile_path,
            work_dir=cfg.work_dir,
            providers=cfg.providers,
            reputable_only=cfg.reputable_only,
            countries_only=cfg.countries_only,
            role_gate=cfg.role_gate,
            prescreen_min=cfg.prescreen_min,
            per_company_cap=cfg.per_company_cap,
            per_provider_cap=cfg.per_provider_cap,
        )
    )
    enrich(
        EnrichConfig(
            profile_path=cfg.profile_path,
            work_dir=cfg.work_dir,
            top_n=cfg.enrich_top,
            refetch_pages=cfg.refetch_pages,
            use_llm=cfg.use_llm,
            refresh=cfg.refresh,
            ai_min=cfg.ai_min,
        )
    )
    return rank(
        RankConfig(
            work_dir=cfg.work_dir, out_dir=cfg.out_dir, final_min=cfg.final_min,
            top_n=cfg.top_n, tiers_path=cfg.tiers_path,
        )
    )
