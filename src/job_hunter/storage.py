"""Write scored roles to disk: one Markdown file per role, a JSON dump, and an index."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from job_hunter.models import Job

_TIER_NAME = {3: "Elite", 2: "Strong", 1: "Solid", 0: "Unrecognised"}


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
        lines += ["## Fit note", "", job.notes, ""]
    lines += ["## Why this score", "", "| Component | Points |", "| --- | ---: |"]
    for key in ("base", "lane_relevance", "skills", "location", "seniority", "negatives", "reputation"):
        if key in b:
            lines.append(f"| {key.replace('_', ' ')} | {b[key]:+d} |")
    lines.append(f"| **total** | **{job.fit_score}** |")
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
        "| Fit | AI | Company | Role | Lane | Country | Salary | Link |",
        "| ---: | ---: | --- | --- | --- | --- | --- | --- |",
    ]
    for j in jobs:
        lane_short = j.fit_breakdown.get("lane_id", "")
        link = f"[apply]({j.url})" if j.url else "—"
        title = j.title.replace("|", "/")
        company = j.company.replace("|", "/")
        ai = f"{j.ai_score}%" if j.ai_score is not None else "—"
        lines.append(
            f"| {_display_score(j)}% | {ai} | {company} | {title} | {lane_short} | "
            f"{j.country or '—'} | {j.salary_text} | {link} |"
        )
    lines.append("")
    return "\n".join(lines)
