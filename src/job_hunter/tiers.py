"""Manual per-job tier overrides, persisted per persona so they survive re-runs.

Job tiers are 1 = best (curated by hand); every proposed job defaults to the lowest
tier (``UNCURATED_TIER``). You promote the ones you like, and the choice is saved in a
small sidecar JSON keyed by the stable ``Job.id`` — so re-scraping never loses your
curation, even though ``data/work`` and ``data/roles`` are regenerated each run.

Sidecar location: ``data/tiers/<persona>.json`` (git-ignored — it's personal).
"""

from __future__ import annotations

import json
from pathlib import Path

from job_hunter.models import UNCURATED_TIER, Job


def sidecar_path(tiers_dir: str | Path, persona_id: str) -> Path:
    return Path(tiers_dir) / f"{persona_id}.json"


def load_overrides(path: str | Path) -> dict[str, int]:
    """Return {job_id: tier}. Missing or unreadable file -> empty (no overrides)."""
    p = Path(path)
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {}
    return {str(k): int(v) for k, v in data.items()}


def save_overrides(path: str | Path, overrides: dict[str, int]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(overrides, indent=2, sort_keys=True), encoding="utf-8")


def apply_overrides(jobs: list[Job], overrides: dict[str, int]) -> None:
    """Set each job's tier from the sidecar, defaulting to the lowest tier."""
    for job in jobs:
        job.tier = overrides.get(job.id, UNCURATED_TIER)


def set_tier(path: str | Path, job_id: str, tier: int) -> dict[str, int]:
    """Persist a single job's manual tier (load -> update -> save). Returns the map."""
    overrides = load_overrides(path)
    overrides[str(job_id)] = int(tier)
    save_overrides(path, overrides)
    return overrides
