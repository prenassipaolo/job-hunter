"""Load the candidate profile that drives queries and scoring."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


def _validate(data: dict) -> list[str]:
    """Return human-readable problems that block a run (empty list == OK).

    Minimum to hunt for anything: at least one lane carrying title_terms. Without it
    there is nothing to match job titles against, so the scorer can't function.
    """
    problems: list[str] = []
    lanes = data.get("lanes")
    if not isinstance(lanes, list) or not lanes:
        problems.append("'lanes': at least one career lane with 'title_terms' (e.g. [\"data scientist\"])")
    elif not any((lane or {}).get("title_terms") for lane in lanes):
        problems.append("at least one lane with a non-empty 'title_terms' list")
    return problems


@dataclass
class Lane:
    id: str
    label: str
    title_terms: list[str]
    boost_skills: list[str]


@dataclass
class Profile:
    id: str
    name: str
    based_in: str
    target_countries: list[str]
    target_cities: list[str]
    remote_ok: bool
    lanes: list[Lane]
    skills: dict[str, list[str]]
    seniority: dict[str, list[str]]
    negative_signals: list[str]
    role_gate: dict[str, list[str]]

    @classmethod
    def load(cls, path: str | Path) -> "Profile":
        """Load a persona. The ONLY hard requirement is at least one lane with
        title_terms (what roles to hunt for); everything else has a safe default, so a
        minimal persona still runs. Raises ValueError with a clear message otherwise.
        """
        path = Path(path)
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(data, dict):
            raise ValueError(f"{path}: persona must be a YAML mapping (key: value).")

        problems = _validate(data)
        if problems:
            raise ValueError(
                f"Persona '{path}' can't be used yet — fill in:\n  - " + "\n  - ".join(problems)
            )

        lanes = [
            Lane(
                id=str(lane.get("id", "lane")),
                label=lane.get("label") or str(lane.get("id", "lane")),
                title_terms=lane.get("title_terms", []),
                boost_skills=lane.get("boost_skills", []),
            )
            for lane in data["lanes"]
        ]
        skills = data.get("skills") or {}
        seniority = data.get("seniority") or {}
        stem = path.stem
        return cls(
            id=data.get("id") or stem,
            name=data.get("name") or data.get("id") or stem,
            based_in=data.get("based_in", ""),
            target_countries=data.get("target_countries", []),
            target_cities=data.get("target_cities", []),
            remote_ok=data.get("remote_ok", True),
            lanes=lanes,
            # Normalise to the three buckets the scorer understands; missing -> empty.
            skills={k: skills.get(k, []) for k in ("strong", "working", "learning")},
            seniority={k: seniority.get(k, []) for k in ("fit", "too_junior", "too_senior")},
            negative_signals=data.get("negative_signals", []),
            role_gate=data.get("role_gate") or {"core": [], "exclude": []},
        )

    @property
    def all_skills(self) -> list[str]:
        return [s for group in self.skills.values() for s in group]
