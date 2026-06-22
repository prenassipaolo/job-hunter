"""llm.apply writes subjective feature scores + the overview onto a job."""

from job_hunter.models import Job
from job_hunter.scoring.llm import apply


def _job() -> Job:
    j = Job(source="t", title="x", company="c", url="u")
    j.fit_breakdown = {}  # normally set by phase-1 scoring
    return j


def test_apply_stores_ai_features_and_summary_score():
    job = _job()
    apply(job, {
        "responsibilities": 0.8,
        "interest": 0.6,
        "fit_note": "solid applied fit",
        "pros": ["uses your Python/Spark"],
        "cons": ["needs Kubernetes"],
        "learning_potential": "strong data-platform exposure",
    })
    assert job.ai_features == {"responsibilities": 0.8, "interest": 0.6}
    assert job.ai_score == 70  # round(100 * mean(0.8, 0.6))
    assert job.notes == "solid applied fit"
    assert job.fit_breakdown["llm_pros"] == ["uses your Python/Spark"]
    assert job.fit_breakdown["llm_learning"] == "strong data-platform exposure"


def test_apply_clamps_and_tolerates_missing():
    job = _job()
    apply(job, {"responsibilities": 1.4})  # out of range -> clamped to 1.0
    assert job.ai_features == {"responsibilities": 1.0}
    assert job.ai_score == 100

    job2 = _job()
    apply(job2, {"fit_note": "no scores given"})
    assert job2.ai_features == {}
    assert job2.ai_score is None
