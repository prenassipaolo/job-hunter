"""Heuristic scoring — compute the *objective* feature values and combine them.

Each signal becomes a score in [0, 1] (higher = better; no negative penalties — a bad
signal just scores low). The values go through ``features.combine`` (weighted sum +
logistic), so the result is bounded in (0, 100) with no cap. The dominant feature is
**skills overlap**: a role built on the candidate's real toolkit scores high; a role
centred on skills they only aspire to — or an aspirational title — scores low.
"""

from __future__ import annotations

from job_hunter.locations import city_tier
from job_hunter.models import Job
from job_hunter.profile import Lane, Profile
from job_hunter.recency import recency_penalty
from job_hunter.reputation import tier_for

from .features import combine

SKILL_WEIGHTS = {"strong": 1.0, "working": 0.5, "learning": 0.15}
KNOWLEDGE_SAT = 5.0  # strong-equivalent matches that count as full skill overlap
STRETCH_TITLE_FACTOR = 0.15  # a stretch title makes the title a poor match for this person

LOCATION_VALUE = {1: 1.0, 2: 0.65, 3: 0.35, 4: 0.15}
REPUTATION_VALUE = {1: 1.0, 2: 0.6, 3: 0.3, 0: 0.1}


def _hits(text: str, terms: list[str]) -> list[str]:
    low = text.lower()
    return [t for t in terms if t.lower() in low]


def _best_lane(job: Job, profile: Profile) -> tuple[Lane, int]:
    title = job.title.lower()
    best: tuple[Lane, int] | None = None
    for lane in profile.lanes:
        n = sum(1 for t in lane.title_terms if t.lower() in title)
        if best is None or n > best[1]:
            best = (lane, n)
    return best  # type: ignore[return-value]


def _skills_value(text: str, profile: Profile) -> tuple[float, dict]:
    matched: dict[str, list[str]] = {}
    raw = 0.0
    for bucket, weight in SKILL_WEIGHTS.items():
        hit = _hits(text, profile.skills.get(bucket, []))
        matched[bucket] = hit
        raw += len(hit) * weight
    return min(raw / KNOWLEDGE_SAT, 1.0), matched


def _location_value(job: Job, profile: Profile) -> float:
    tier = city_tier(job.location, job.country, profile.country_tiers, profile.city_tiers)
    if tier:
        return LOCATION_VALUE.get(tier, 0.3)
    if job.remote and profile.remote_ok:
        return 0.5
    if not job.country:
        return 0.4
    return 0.05  # concrete location outside every tiered country


def _seniority_value(title: str, profile: Profile) -> float:
    if _hits(title, profile.seniority.get("too_junior", [])):
        return 0.1
    if _hits(title, profile.seniority.get("too_senior", [])):
        return 0.25
    if _hits(title, profile.seniority.get("fit", [])):
        return 0.85
    return 0.5


def label_for(score: int) -> str:
    if score >= 80:
        return "Strong"
    if score >= 62:
        return "Good"
    if score >= 42:
        return "Moderate"
    return "Stretch"


def objective_features(job: Job, profile: Profile) -> tuple[dict, dict, Lane]:
    """Compute every heuristic feature value (each in [0,1]) + explainability detail."""
    text = f"{job.title}\n{job.description}"
    title = job.title.lower()

    f_skills, matched = _skills_value(text, profile)

    lane, title_hits = _best_lane(job, profile)
    domain_hits = len(_hits(job.description, lane.boost_skills))
    lane_rel = min(title_hits * 0.5 + domain_hits * 0.1, 1.0)
    stretch = bool(_hits(title, profile.stretch_titles))
    f_title = lane_rel * (STRETCH_TITLE_FACTOR if stretch else 1.0)

    f_loc = _location_value(job, profile)
    f_sen = _seniority_value(title, profile)
    rep_tier = tier_for(job.company)
    f_rep = REPUTATION_VALUE.get(rep_tier, 0.1)
    rec_pts, rec_detail = recency_penalty(job.posted_at)
    f_rec = max(0.0, 1.0 + rec_pts / 10.0)  # penalty 0..-10 -> 1.0..0.0
    neg = _hits(text, profile.negative_signals)
    f_stack = max(0.0, 1.0 - len(neg) * 0.34)

    values = {
        "skills": f_skills, "title_fit": f_title, "location": f_loc, "seniority": f_sen,
        "reputation": f_rep, "recency": f_rec, "stack_fit": f_stack,
    }
    detail = {
        "matched_skills": {k: v for k, v in matched.items() if v},
        "negative_hits": neg,
        "lane_id": lane.id,
        "reputation_tier": rep_tier,
        "location_tier": city_tier(job.location, job.country, profile.country_tiers, profile.city_tiers),
        "stretch": stretch,
        "recency_age_days": rec_detail.get("recency_age_days"),
    }
    return values, detail, lane


def score_job(job: Job, profile: Profile) -> Job:
    """Score one job in place from its objective features + any AI feature scores.

    Safe to call twice: phase 1 scores objective-only; phase 2 calls it again after the
    LLM fills ``job.ai_features``, so the AI's judgment flows through the SAME logistic.
    """
    values, detail, lane = objective_features(job, profile)
    values.update(job.ai_features or {})  # AI subjective scores override their defaults

    score, z, components = combine(values, profile.weights)
    # Preserve the LLM overview (pros/cons/etc.) across a re-score — it lives under llm_*.
    preserved = {k: v for k, v in (job.fit_breakdown or {}).items() if k.startswith("llm_")}
    job.fit_score = score
    job.fit_label = label_for(score)
    job.fit_lane = lane.label
    job.fit_breakdown = {
        "z": round(z, 3),
        "components": components,
        "features": {c["name"]: c["value"] for c in components},
        **detail,
        **preserved,
    }
    return job
