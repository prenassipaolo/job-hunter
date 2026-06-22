"""The feature registry + how AI feature scores move the final fit score."""

from pathlib import Path

from job_hunter.models import Job
from job_hunter.profile import Profile
from job_hunter.scoring import score_job
from job_hunter.scoring.features import FEATURES, combine

PROFILE = Profile.load(Path(__file__).resolve().parents[1] / "data" / "personas" / "example.yaml")


def test_combine_is_bounded_and_monotonic():
    low = combine({f.name: 0.0 for f in FEATURES})[0]
    high = combine({f.name: 1.0 for f in FEATURES})[0]
    assert 0 <= low < high < 100


def test_missing_values_use_defaults():
    # Empty values dict -> every feature falls back to its default, flagged as such.
    _, _, components = combine({})
    assert all(c["default"] for c in components)


def test_persona_weights_override():
    base, _, _ = combine({"skills": 1.0})
    heavy, _, comps = combine({"skills": 1.0}, {"skills": 10.0})
    assert heavy > base  # weighting skills harder raises the score
    skills = next(c for c in comps if c["name"] == "skills")
    assert skills["weight"] == 10.0


def _quant() -> Job:
    return Job(source="t", title="Quantitative Developer", company="Optiver",
               url="u", country="Netherlands",
               description="python pandas sql c++ credit risk backtesting docker azure")


def test_ai_features_shift_the_score():
    base = _quant()
    score_job(base, PROFILE)  # AI features at default 0.5

    good = _quant()
    good.ai_features = {"responsibilities": 0.95, "interest": 0.95}
    score_job(good, PROFILE)

    bad = _quant()
    bad.ai_features = {"responsibilities": 0.1, "interest": 0.1}
    score_job(bad, PROFILE)

    assert bad.fit_score < base.fit_score < good.fit_score
