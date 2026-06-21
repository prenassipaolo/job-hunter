"""Transparent, offline fit scorer.

Produces an estimated 0-100 "fit probability" for the persona plus a breakdown of how it
was reached. This is a heuristic proxy for *how strong a candidate the persona is for the
role* (roughly: chance of clearing the CV screen into an interview), not a guarantee.
Every component is explainable so the numbers can be sanity-checked and retuned.
"""

from __future__ import annotations

from job_hunter.locations import location_score
from job_hunter.models import Job
from job_hunter.profile import Lane, Profile
from job_hunter.reputation import reputation_points

# Weight per matched skill tier (added to the score, then the whole skill block is capped).
SKILL_WEIGHTS = {"strong": 6, "working": 3, "learning": 2}
SKILL_CAP = 34


def _count_terms(text: str, terms: list[str]) -> list[str]:
    low = text.lower()
    return [t for t in terms if t.lower() in low]


def _best_lane(job: Job, profile: Profile) -> tuple[Lane, int]:
    """Pick the lane whose title terms best match this job's title."""
    title = job.title.lower()
    best: tuple[Lane, int] | None = None
    for lane in profile.lanes:
        hits = sum(1 for t in lane.title_terms if t.lower() in title)
        if best is None or hits > best[1]:
            best = (lane, hits)
    return best  # type: ignore[return-value]


def label_for(score: int) -> str:
    if score >= 70:
        return "Strong"
    if score >= 55:
        return "Good"
    if score >= 40:
        return "Moderate"
    return "Stretch"


def score_job(job: Job, profile: Profile) -> Job:
    """Score one job in place and return it. Sets fit_score/label/lane/breakdown."""
    breakdown: dict[str, int] = {}
    score = 30  # neutral base — an on-target role builds well above this
    breakdown["base"] = 30

    text = f"{job.title}\n{job.description}"

    # 1) Lane / title relevance — the strongest signal.
    lane, title_hits = _best_lane(job, profile)
    lane_pts = min(title_hits * 11, 26)
    # A description that matches the lane's domain skills even without a title hit still counts.
    domain_hits = len(_count_terms(job.description, lane.boost_skills))
    lane_pts += min(domain_hits * 2, 10)
    score += lane_pts
    breakdown["lane_relevance"] = lane_pts

    # 2) Skill overlap with the persona's toolkit.
    skill_pts = 0
    matched: dict[str, list[str]] = {}
    for tier, terms in profile.skills.items():
        hits = _count_terms(text, terms)
        matched[tier] = hits
        skill_pts += len(hits) * SKILL_WEIGHTS[tier]
    skill_pts = min(skill_pts, SKILL_CAP)
    score += skill_pts
    breakdown["skills"] = skill_pts

    # 3) Location fit — country/city tiers (1 = best). All geo logic lives in
    #    locations.py; here we just add the points it returns.
    loc_pts, loc_detail = location_score(job.country, job.location, job.remote, profile.remote_ok)
    score += loc_pts
    breakdown["location"] = loc_pts

    # 4) Seniority fit.
    sen_pts = 0
    if _count_terms(job.title, profile.seniority["too_junior"]):
        sen_pts -= 25
    if _count_terms(job.title, profile.seniority["too_senior"]):
        sen_pts -= 14
    if _count_terms(job.title, profile.seniority["fit"]):
        sen_pts += 6
    score += sen_pts
    breakdown["seniority"] = sen_pts

    # 5) Negative signals (wrong stack, hard blockers).
    neg = _count_terms(text, profile.negative_signals)
    neg_pts = -8 * len(neg)
    score += neg_pts
    breakdown["negatives"] = neg_pts

    # 6) Employer reputation / room to grow — the persona only wants strong, well-known
    #    companies (trading firms, big tech, serious fintech, reputable banks).
    rep_tier, rep_pts = reputation_points(job.company)
    score += rep_pts
    breakdown["reputation"] = rep_pts

    score = max(0, min(100, score))
    job.fit_score = int(round(score))
    job.fit_label = label_for(job.fit_score)
    job.fit_lane = lane.label
    job.fit_breakdown = {
        **breakdown,
        "matched_skills": {k: v for k, v in matched.items() if v},
        "negative_hits": neg,
        "lane_id": lane.id,
        "reputation_tier": rep_tier,
        "location_tier": loc_detail.get("location_tier", 0),
    }
    return job
