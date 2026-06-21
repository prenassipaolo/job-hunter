"""Sanity tests for the scorer and reputation filter."""

from pathlib import Path

from job_hunter.models import Job
from job_hunter.profile import Profile
from job_hunter.reputation import is_reputable, tier_for
from job_hunter.scoring import score_job

PROFILE = Profile.load(Path(__file__).resolve().parents[1] / "data" / "personas" / "example.yaml")


def _job(**kw) -> Job:
    base = dict(source="t", title="", company="", url="http://x", description="")
    base.update(kw)
    return Job(**base)


def test_reputation_tiers():
    assert tier_for("Optiver B.V.") == 3
    assert tier_for("Adyen") == 2
    assert is_reputable("J.P. Morgan")
    assert not is_reputable("Random Tiny Startup XYZ")
    # 'ing' must not match inside 'trading'
    assert tier_for("Trading Co") == 0


def test_strong_quant_role_scores_high():
    job = _job(
        title="Quantitative Developer",
        company="Optiver",
        country="Netherlands",
        description="Python, pandas, C++, credit risk, backtesting, Docker, Azure, SQL.",
    )
    score_job(job, PROFILE)
    assert job.fit_score >= 70
    assert job.fit_label == "Strong"
    assert job.fit_breakdown["reputation_tier"] == 3


def test_offtarget_role_scores_low():
    job = _job(
        title="Senior PHP / WordPress Developer",
        company="Unknown Agency",
        country="Germany",
        description="PHP, WordPress, frontend, 10+ years required.",
    )
    score_job(job, PROFILE)
    assert job.fit_score < 45


def test_intern_is_penalised():
    job = _job(title="Data Science Intern", company="Google", country="Ireland", description="Python")
    score_job(job, PROFILE)
    assert job.fit_breakdown["seniority"] < 0
