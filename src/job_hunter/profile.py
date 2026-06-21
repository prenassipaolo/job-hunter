"""Load the candidate profile that drives queries and scoring."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


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
        path = Path(path)
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        lanes = [Lane(**lane) for lane in data["lanes"]]
        return cls(
            id=data.get("id") or path.stem,  # fall back to the filename
            name=data["name"],
            based_in=data["based_in"],
            target_countries=data["target_countries"],
            target_cities=data["target_cities"],
            remote_ok=data.get("remote_ok", True),
            lanes=lanes,
            skills=data["skills"],
            seniority=data["seniority"],
            negative_signals=data["negative_signals"],
            role_gate=data.get("role_gate", {"core": [], "exclude": []}),
        )

    @property
    def all_skills(self) -> list[str]:
        return [s for group in self.skills.values() for s in group]
