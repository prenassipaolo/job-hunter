"""Optional Claude-Haiku enrichment.

Disabled by default (the heuristic scorer is the default path). When enabled with
`--llm`, each shortlisted role is sent to Claude Haiku — the cheapest model
($1/$5 per Mtok) — to extract anything the heuristic missed (e.g. an implied salary,
a real seniority read) and to write a short, candid fit note for the persona.

Requires the `llm` extra (`uv sync --extra llm`) and an ANTHROPIC_API_KEY.
"""

from __future__ import annotations

import json
import os

from job_hunter.models import Job
from job_hunter.profile import Profile

MODEL = "claude-haiku-4-5"  # cheapest current model — matches the persona's "less tokens" ask

_SYSTEM = """You are a blunt, experienced tech recruiter helping a specific candidate.
You will receive the candidate's profile and one job posting. Judge how strong a
candidate THIS person is for THIS role and reply with STRICT JSON:
{
  "fit_score": <integer 0-100: realistic chance of clearing the CV screen into an interview>,
  "fit_note": "<=40 words, candid: why this fits or doesn't for THIS candidate>",
  "salary_min": <number or null>,
  "salary_max": <number or null>,
  "salary_currency": "<ISO code or empty>",
  "salary_period": "<year|month|empty>",
  "seniority_read": "<too_junior|fits|too_senior|unclear>",
  "reputation_read": "<strong|moderate|unknown — is this a place to learn and grow?>"
}
Only output the JSON object, nothing else."""


def available() -> bool:
    if not os.getenv("ANTHROPIC_API_KEY"):
        return False
    try:
        import anthropic  # noqa: F401
    except ImportError:
        return False
    return True


def _profile_blurb(profile: Profile) -> str:
    lanes = "; ".join(lane.label for lane in profile.lanes)
    return (
        f"Candidate: {profile.name}, based in {profile.based_in}. "
        f"Target countries: {', '.join(profile.target_countries)} (remote ok: {profile.remote_ok}). "
        f"Career lanes: {lanes}. "
        f"Strong skills: {', '.join(profile.skills['strong'])}. "
        f"Learning (not production): {', '.join(profile.skills['learning'])}. "
        "Wants only reputable employers (top trading firms, big tech, serious fintech, "
        "strong banks) with room to learn and grow."
    )


def make_client():
    """Create an Anthropic client (imported lazily so the SDK is only needed with --llm)."""
    import anthropic

    return anthropic.Anthropic()


def profile_blurb(profile: Profile) -> str:
    return _profile_blurb(profile)


def enrich_one(client, job: Job, blurb: str) -> dict | None:
    """One API call for one job. Returns the parsed JSON dict, or None on any failure.

    Pure w.r.t. the job (doesn't mutate it) so the result is cacheable; apply() writes
    it onto the job afterwards.
    """
    user = (
        f"{blurb}\n\n--- JOB POSTING ---\n"
        f"Title: {job.title}\nCompany: {job.company}\nLocation: {job.location}\n"
        f"Known salary: {job.salary_text}\n\nDescription:\n{job.description[:3500]}"
    )
    try:
        resp = client.messages.create(
            model=MODEL,
            max_tokens=400,
            system=_SYSTEM,
            messages=[{"role": "user", "content": user}],
        )
        text = next((b.text for b in resp.content if b.type == "text"), "").strip()
        return json.loads(_extract_json(text))
    except Exception:  # network / parse / api error — never fatal
        return None


def apply(job: Job, data: dict) -> None:
    """Write an enrichment result (from enrich_one or the cache) onto a job."""
    job.notes = data.get("fit_note", "")
    if data.get("fit_score") is not None:
        try:
            job.ai_score = max(0, min(100, int(data["fit_score"])))
        except (TypeError, ValueError):
            pass
    if job.salary_min is None and data.get("salary_min"):
        job.salary_min = _num(data.get("salary_min"))
        job.salary_max = _num(data.get("salary_max"))
        job.salary_currency = data.get("salary_currency", "") or job.salary_currency
        job.salary_period = data.get("salary_period", "") or job.salary_period
    job.fit_breakdown["llm_seniority_read"] = data.get("seniority_read", "")
    job.fit_breakdown["llm_reputation_read"] = data.get("reputation_read", "")


def enrich(jobs: list[Job], profile: Profile) -> list[Job]:
    """Add an LLM fit note and fill missing salary where the model can infer it."""
    client = make_client()
    blurb = profile_blurb(profile)
    for job in jobs:
        data = enrich_one(client, job, blurb)
        if data is None:
            job.notes = "(LLM enrichment failed)"
            continue
        apply(job, data)
    return jobs


def _extract_json(text: str) -> str:
    start, end = text.find("{"), text.rfind("}")
    return text[start : end + 1] if start != -1 and end != -1 else text


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None
