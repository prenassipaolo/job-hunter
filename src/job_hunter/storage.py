"""Write scored roles to disk: one Markdown file per role, a JSON dump, and an index."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from job_hunter.models import Job
from job_hunter.recency import parse_date

_TIER_NAME = {1: "Elite", 2: "Strong", 3: "Solid", 0: "Unrecognised"}


def _posted(job: Job) -> str:
    """Normalised posting date (YYYY-MM-DD) for display, or '—' if unknown."""
    d = parse_date(job.posted_at)
    return d.isoformat() if d else "—"


def latest_run_dir(out_dir: str | Path) -> Path | None:
    """Newest run directory (date-named) under out_dir that has a roles.json, or None."""
    out = Path(out_dir)
    runs = sorted(d for d in out.glob("*") if d.is_dir() and (d / "roles.json").exists())
    return runs[-1] if runs else None


def load_latest_roles(out_dir: str | Path) -> list[dict]:
    """Load the most recent roles.json for a persona's output dir (empty if none yet)."""
    run = latest_run_dir(out_dir)
    if run is None:
        return []
    return json.loads((run / "roles.json").read_text(encoding="utf-8"))


def _display_score(job: Job) -> int:
    return job.final_score or job.fit_score


def _role_markdown(job: Job) -> str:
    b = job.fit_breakdown
    tier = b.get("reputation_tier", 0)
    matched = b.get("matched_skills", {})
    ai = f"{job.ai_score}%" if job.ai_score is not None else "—"
    lines = [
        f"# {job.title}",
        "",
        f"**Company:** {job.company}  ",
        f"**Fit probability:** {_display_score(job)}% ({job.fit_label})  ",
        f"**Score detail:** heuristic {job.fit_score}% · AI {ai}"
        f"{' · page re-checked' if job.page_refetched else ''}  ",
        f"**Career lane:** {job.fit_lane}  ",
        f"**Manual tier:** {job.tier} (1 = best)  ",
        f"**Reputation:** {_TIER_NAME.get(tier, 'Unrecognised')} (tier {tier})  ",
        f"**Location:** {job.location or '—'} ({job.country or 'unknown'}){' · remote' if job.remote else ''}  ",
        f"**Salary:** {job.salary_text}  ",
        f"**Source:** {job.source}  ",
        f"**Posted:** {job.posted_at or '—'}  ",
        "",
        f"🔗 **Apply / details:** {job.url}",
        "",
    ]
    if job.notes:
        lines += ["## AI overview", "", job.notes, ""]
        pros, cons = b.get("llm_pros", []), b.get("llm_cons", [])
        if pros:
            lines += ["**Pros**", *[f"- {p}" for p in pros], ""]
        if cons:
            lines += ["**Cons**", *[f"- {c}" for c in cons], ""]
        if b.get("llm_learning"):
            lines += [f"**Learning potential:** {b['llm_learning']}", ""]
    # Each feature is a 0-1 score; contributions sum (with a bias) into z -> logistic.
    lines += ["## Why this score", "",
              "Each feature scores 0–1; score = logistic(bias + Σ weight·value).", "",
              "| Feature | Value | Weight | Contribution | Source |",
              "| --- | ---: | ---: | ---: | --- |"]
    for c in b.get("components", []):
        flag = " (default)" if c.get("default") else ""
        lines.append(
            f"| {c['label']} | {c['value']:.2f} | {c['weight']:.1f} | "
            f"{c['contribution']:+.2f} | {c['source']}{flag} |"
        )
    lines.append(f"| **z (total)** | | | **{b.get('z', 0):+.2f}** | |")
    lines.append(f"| **fit score** | | | **{job.fit_score}%** | |")
    lines.append("")
    if matched:
        lines += ["## Matched skills", ""]
        for tier_name, skills in matched.items():
            if skills:
                lines.append(f"- **{tier_name}:** {', '.join(skills)}")
        lines.append("")
    if b.get("negative_hits"):
        lines += ["## ⚠️ Caveats", "", ", ".join(b["negative_hits"]), ""]
    return "\n".join(lines)


def write_results(jobs: list[Job], out_dir: str | Path) -> Path:
    """Write per-role markdown + roles.json + index. Returns the run directory."""
    out_dir = Path(out_dir)
    run_dir = out_dir / date.today().isoformat()
    roles_dir = run_dir / "roles"
    roles_dir.mkdir(parents=True, exist_ok=True)

    # Clear any prior roles from an earlier run today so the index stays in sync.
    for old in roles_dir.glob("*.md"):
        old.unlink()

    for job in jobs:
        fname = f"{_display_score(job):03d}__{job.slug}__{job.id}.md"
        (roles_dir / fname).write_text(_role_markdown(job), encoding="utf-8")

    (run_dir / "roles.json").write_text(
        json.dumps([j.to_dict() for j in jobs], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (run_dir / "index.md").write_text(_index_markdown(jobs), encoding="utf-8")
    return run_dir


def _index_markdown(jobs: list[Job]) -> str:
    lines = [
        f"# Role shortlist — {date.today().isoformat()}",
        "",
        f"{len(jobs)} roles, ranked by estimated fit probability for the persona.",
        "",
        "| Tier | Fit | AI | Company | Role | Lane | Country | Posted | Salary | Link |",
        "| ---: | ---: | ---: | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for j in jobs:
        lane_short = j.fit_breakdown.get("lane_id", "")
        link = f"[apply]({j.url})" if j.url else "—"
        title = j.title.replace("|", "/")
        company = j.company.replace("|", "/")
        ai = f"{j.ai_score}%" if j.ai_score is not None else "—"
        lines.append(
            f"| {j.tier} | {_display_score(j)}% | {ai} | {company} | {title} | {lane_short} | "
            f"{j.country or '—'} | {_posted(j)} | {j.salary_text} | {link} |"
        )
    lines.append("")
    return "\n".join(lines)
