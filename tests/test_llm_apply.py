"""llm.apply writes the enrichment dict (incl. the richer overview) onto a job."""

from job_hunter.models import Job
from job_hunter.scoring.llm import apply


def test_apply_stores_score_note_and_overview():
    job = Job(source="t", title="x", company="c", url="u")
    apply(job, {
        "fit_score": 82,
        "fit_note": "solid applied fit",
        "pros": ["uses your Python/Spark", "reputable employer"],
        "cons": ["needs Kubernetes"],
        "learning_potential": "strong data-platform exposure",
    })
    assert job.ai_score == 82
    assert job.notes == "solid applied fit"
    assert job.fit_breakdown["llm_pros"] == ["uses your Python/Spark", "reputable employer"]
    assert job.fit_breakdown["llm_cons"] == ["needs Kubernetes"]
    assert job.fit_breakdown["llm_learning"] == "strong data-platform exposure"


def test_apply_tolerates_missing_overview_fields():
    job = Job(source="t", title="x", company="c", url="u")
    apply(job, {"fit_score": 50, "fit_note": "ok"})
    assert job.fit_breakdown["llm_pros"] == []
    assert job.fit_breakdown["llm_cons"] == []
    assert job.fit_breakdown["llm_learning"] == ""
