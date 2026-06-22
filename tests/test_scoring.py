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
    # 1 = best: elite firms are tier 1, unrecognised is 0.
    assert tier_for("Optiver B.V.") == 1
    assert tier_for("Adyen") == 2
    assert is_reputable("J.P. Morgan")
    # Small-but-high-value firms are recognised too (step 5).
    assert tier_for("Cohere") == 1          # frontier AI lab, small but elite
    assert tier_for("GoCardless") == 2      # fintech scale-up
    assert not is_reputable("Random Tiny Startup XYZ")
    # 'ing' must not match inside 'trading'
    assert tier_for("Trading Co") == 0


def _quant_role() -> Job:
    return _job(
        title="Quantitative Developer",
        company="Optiver",
        country="Netherlands",
        description="Python, pandas, C++, credit risk, backtesting, Docker, Azure, SQL.",
    )


def test_strong_quant_role_scores_high():
    job = _quant_role()
    score_job(job, PROFILE)
    assert job.fit_score >= 80
    assert job.fit_label == "Strong"
    assert job.fit_breakdown["reputation_tier"] == 1


def test_score_is_bounded_below_100():
    # Logistic squash, no cap: even a near-perfect role can't reach 100.
    job = _job(
        title="Quantitative Developer",
        company="Optiver",
        country="Netherlands",
        description="python pandas sql c++ credit risk backtesting docker azure spark " * 6,
    )
    score_job(job, PROFILE)
    assert job.fit_score < 100


def test_offtarget_role_scores_low():
    job = _job(
        title="Senior PHP / WordPress Developer",
        company="Unknown Agency",
        country="Germany",
        description="PHP, WordPress, frontend, 10+ years required.",
    )
    score_job(job, PROFILE)
    assert job.fit_score < 45


def test_ai_research_scores_lower_than_applied_quant():
    # Knowledge overlap + stretch penalty: an AI *research* role (skills the persona only
    # aspires to, aspirational title) must score below an applied quant role it can do —
    # even at an elite company in a tier-1 country.
    quant = _quant_role()
    research = _job(
        title="Research Scientist, Pretraining",
        company="Anthropic",
        country="United Kingdom",
        description="transformers, llm, rag, reinforcement learning, pretraining, publications",
    )
    score_job(quant, PROFILE)
    score_job(research, PROFILE)
    assert research.fit_score < quant.fit_score


def test_intern_is_penalised():
    job = _job(title="Data Science Intern", company="Google", country="Ireland", description="Python")
    score_job(job, PROFILE)
    assert job.fit_breakdown["seniority"] < 0
