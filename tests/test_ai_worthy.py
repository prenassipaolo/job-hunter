"""AI-worthiness gate: only spend an LLM call on jobs with a real chance."""

from job_hunter.models import Job
from job_hunter.phases.enrich import _ai_worthy


def _job(fit: int, *, stretch: bool = False, **feature_overrides) -> Job:
    j = Job(source="t", title="x", company="c", url="u")
    j.fit_score = fit
    features = {"skills": 0.5, "location": 0.8}
    features.update(feature_overrides)
    j.fit_breakdown = {"features": features, "stretch": stretch}
    return j


def test_strong_job_is_worthy():
    assert _ai_worthy(_job(80), 50)


def test_below_floor_is_skipped():
    assert not _ai_worthy(_job(40), 50)


def test_no_skill_overlap_is_skipped():
    assert not _ai_worthy(_job(85, skills=0.0), 50)


def test_outside_location_is_skipped():
    assert not _ai_worthy(_job(85, location=0.05), 50)


def test_stretch_title_is_skipped():
    assert not _ai_worthy(_job(85, stretch=True), 50)
