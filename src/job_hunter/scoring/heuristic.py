"""Transparent, naturally-bounded fit scorer.

Each signal is turned into a normalised **feature** (roughly in [-1, 1]); features are
combined with per-category **weights** into a single number ``z``, then squashed with a
logistic (sigmoid). So the score lands in (0, 100) and can *never reach 100* — the bound
comes from the maths, not an artificial ``min(100)`` cap.

The dominant signal is **knowledge overlap**: a role built on skills the candidate
actually has scores high; a role centred on skills they only aspire to — or an
aspirational title like "research scientist" — scores low even when the company and
location are excellent. (E.g. being new to AI, an AI *research* role won't score well,
but an applied role using the candidate's real toolkit can.)

Every feature, weight and contribution is recorded in ``fit_breakdown`` so the number
is fully explainable and tunable.
"""

from __future__ import annotations

import math

from job_hunter.locations import city_tier
from job_hunter.models import Job
from job_hunter.profile import Lane, Profile
from job_hunter.recency import recency_penalty
from job_hunter.reputation import tier_for

# Per-category weights. Tuned so an excellent role lands ~z=3 (~95%), a poor one ~z=-2
# (~12%); knowledge overlap dominates. Edit these to retune the model.
WEIGHTS = {
    "knowledge": 2.0,
    "lane": 1.3,
    "location": 0.9,
    "seniority": 1.2,
    "stretch": 1.6,
    "reputation": 0.7,
    "recency": 0.6,
    "negatives": 1.3,
}
BIAS = -1.2

SKILL_WEIGHTS = {"strong": 1.0, "working": 0.5, "learning": 0.15}
KNOWLEDGE_SAT = 5.0  # strong-equivalent matches that count as "full" knowledge overlap

REPUTATION_FEATURE = {1: 1.0, 2: 0.6, 3: 0.3, 0: 0.0}
LOCATION_FEATURE = {1: 1.0, 2: 0.65, 3: 0.35, 4: 0.15}
LOCATION_OUTSIDE = -0.6  # a concrete location in no tiered country


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


def _knowledge_feature(text: str, profile: Profile) -> tuple[float, dict]:
    """Overlap with the candidate's actual toolkit. Strong skills count fully, working
    half, learning very little — so a role centred on learning-level skills stays low."""
    matched: dict[str, list[str]] = {}
    raw = 0.0
    for bucket, weight in SKILL_WEIGHTS.items():
        hit = _hits(text, profile.skills.get(bucket, []))
        matched[bucket] = hit
        raw += len(hit) * weight
    return min(raw / KNOWLEDGE_SAT, 1.0), matched


def _location_feature(job: Job, profile: Profile) -> tuple[float, dict]:
    tier = city_tier(job.location, job.country)
    if tier:
        return LOCATION_FEATURE.get(tier, 0.0), {"location_tier": tier}
    if job.remote and profile.remote_ok:
        return 0.45, {"location_tier": 0, "remote": True}
    if not job.country:
        return 0.2, {"location_tier": 0, "unknown": True}
    return LOCATION_OUTSIDE, {"location_tier": 0, "outside": True}


def _seniority_feature(title: str, profile: Profile) -> float:
    f = 0.0
    if _hits(title, profile.seniority.get("too_junior", [])):
        f -= 1.0
    if _hits(title, profile.seniority.get("too_senior", [])):
        f -= 0.8
    if _hits(title, profile.seniority.get("fit", [])):
        f += 0.3
    return max(-1.0, min(0.3, f))


def label_for(score: int) -> str:
    if score >= 80:
        return "Strong"
    if score >= 65:
        return "Good"
    if score >= 45:
        return "Moderate"
    return "Stretch"


def score_job(job: Job, profile: Profile) -> Job:
    """Score one job in place via weighted features + a logistic squash. Bounded (0,100)."""
    text = f"{job.title}\n{job.description}"
    title = job.title.lower()

    lane, title_hits = _best_lane(job, profile)
    domain_hits = len(_hits(job.description, lane.boost_skills))
    f_lane = min(title_hits * 0.5 + domain_hits * 0.1, 1.0)

    f_know, matched = _knowledge_feature(text, profile)
    f_loc, loc_detail = _location_feature(job, profile)
    f_sen = _seniority_feature(title, profile)
    f_stretch = -1.0 if _hits(title, profile.stretch_titles) else 0.0
    rep_tier = tier_for(job.company)
    f_rep = REPUTATION_FEATURE.get(rep_tier, 0.0)
    rec_pts, rec_detail = recency_penalty(job.posted_at)
    f_rec = rec_pts / 10.0  # recency_penalty is 0..-10 -> 0..-1
    neg = _hits(text, profile.negative_signals)
    f_neg = -min(len(neg) * 0.5, 1.0)

    features = {
        "knowledge": f_know, "lane": f_lane, "location": f_loc, "seniority": f_sen,
        "stretch": f_stretch, "reputation": f_rep, "recency": f_rec, "negatives": f_neg,
    }
    z = BIAS + sum(WEIGHTS[k] * v for k, v in features.items())
    score = round(100 / (1 + math.exp(-z)))

    job.fit_score = score
    job.fit_label = label_for(score)
    job.fit_lane = lane.label
    job.fit_breakdown = {
        "z": round(z, 3),
        "bias": BIAS,
        # contribution of each category to z (weight * feature), most explainable view:
        **{k: round(WEIGHTS[k] * v, 3) for k, v in features.items()},
        "features": {k: round(v, 3) for k, v in features.items()},
        "matched_skills": {k: v for k, v in matched.items() if v},
        "negative_hits": neg,
        "lane_id": lane.id,
        "reputation_tier": rep_tier,
        "location_tier": loc_detail.get("location_tier", 0),
        "recency_age_days": rec_detail.get("recency_age_days"),
    }
    return job
