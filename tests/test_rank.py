"""Ranking order: enriched-first coherence fix."""

from job_hunter.models import Job
from job_hunter.phases.rank import _rank_key


def _job(final, ai=None, tier=5) -> Job:
    j = Job(source="t", title="x", company="c", url="u")
    j.final_score = final
    j.ai_score = ai
    j.tier = tier
    return j


def test_enriched_outranks_unenriched_even_with_lower_score():
    enriched = _job(final=80, ai=70)     # honestly scored by the LLM
    inflated = _job(final=100, ai=None)  # un-enriched heuristic 100%
    assert sorted([inflated, enriched], key=_rank_key)[0] is enriched


def test_without_enrichment_higher_score_wins():
    a = _job(final=90)   # both un-enriched
    b = _job(final=100)
    assert sorted([a, b], key=_rank_key)[0] is b


def test_manual_tier_still_dominates():
    promoted = _job(final=50, ai=None, tier=1)   # tier beats everything
    enriched = _job(final=100, ai=95, tier=5)
    assert sorted([enriched, promoted], key=_rank_key)[0] is promoted
