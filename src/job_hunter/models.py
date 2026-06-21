"""Core data structures shared across the pipeline."""

from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass, field

# Manual job tier: 1 = best, larger = worse. Every job starts here (lowest) and is
# promoted by hand; overrides are persisted per persona (see tiers.py).
UNCURATED_TIER = 5


@dataclass
class Job:
    """A single normalised job posting, regardless of which provider it came from."""

    source: str
    title: str
    company: str
    url: str
    location: str = ""
    country: str = ""
    description: str = ""
    remote: bool = False
    salary_min: float | None = None
    salary_max: float | None = None
    salary_currency: str = ""
    salary_period: str = ""  # "year" | "month" | ""
    posted_at: str = ""
    tags: list[str] = field(default_factory=list)

    # Filled in by the scoring stage.
    fit_score: int = 0  # 0-100 heuristic prescreen (phase 1)
    fit_label: str = ""  # Strong / Good / Moderate / Stretch
    fit_lane: str = ""  # which lane (quant / ai / data) fit best
    fit_breakdown: dict = field(default_factory=dict)
    notes: str = ""  # optional LLM enrichment

    # Filled in by phase 2 (AI enrichment) and phase 3 (ranking).
    ai_score: int | None = None  # 0-100 fit as judged by Claude Haiku
    final_score: int = 0  # blended ranking score
    page_refetched: bool = False  # whether phase 2 re-pulled the live page

    # Manual curation, persisted per persona (1 = best; UNCURATED_TIER = lowest default).
    tier: int = UNCURATED_TIER

    @property
    def id(self) -> str:
        """Stable id for dedup + filenames, derived from company + title + url."""
        raw = f"{self.company.lower()}|{self.title.lower()}|{self.url}"
        return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:10]

    @property
    def slug(self) -> str:
        base = f"{self.company}-{self.title}"
        slug = re.sub(r"[^a-z0-9]+", "-", base.lower()).strip("-")
        return slug[:60] or "role"

    @property
    def salary_text(self) -> str:
        if self.salary_min is None and self.salary_max is None:
            return "Not disclosed"
        cur = self.salary_currency or ""
        period = f"/{self.salary_period}" if self.salary_period else ""

        def fmt(v: float | None) -> str:
            return f"{int(v):,}" if v is not None else "?"

        if self.salary_min is not None and self.salary_max is not None:
            return f"{cur} {fmt(self.salary_min)} – {fmt(self.salary_max)}{period}".strip()
        single = self.salary_min if self.salary_min is not None else self.salary_max
        return f"{cur} {fmt(single)}{period}".strip()

    def to_dict(self) -> dict:
        d = asdict(self)
        d["id"] = self.id
        d["salary_text"] = self.salary_text
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Job":
        """Rebuild a Job from a phase artifact (ignoring derived keys)."""
        fields = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in d.items() if k in fields})
