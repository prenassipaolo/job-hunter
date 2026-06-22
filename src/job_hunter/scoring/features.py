"""The scoring feature schema — one place that declares every signal and its weight.

Each feature is a **score in [0, 1]** (higher = better; there are no negative penalties —
a "bad" signal just scores low). Features are combined as ``z = bias + Σ weight·value``
and squashed with a logistic, so the final score is naturally bounded in (0, 100).

A feature's ``source`` says who fills it: ``heuristic`` (cheap, objective, computed for
every job) or ``ai`` (subjective — the LLM judges it, only for worthy jobs; see v2.2).
When a value is missing, the feature's neutral ``default`` is used so nothing breaks.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Feature:
    name: str
    weight: float
    source: str  # "heuristic" | "ai"
    default: float  # neutral prior used when a value is missing
    label: str


# Order is display order. Weights tuned so a great role ~95% and a poor one ~6%.
FEATURES: list[Feature] = [
    Feature("skills", 2.4, "heuristic", 0.30, "Skill / knowledge overlap"),
    Feature("title_fit", 1.6, "heuristic", 0.40, "Job title matches your lanes"),
    Feature("location", 1.0, "heuristic", 0.40, "Location desirability"),
    Feature("seniority", 1.0, "heuristic", 0.50, "Seniority match"),
    Feature("reputation", 0.8, "heuristic", 0.30, "Employer reputation"),
    Feature("recency", 0.6, "heuristic", 0.60, "Posting freshness"),
    Feature("stack_fit", 1.0, "heuristic", 0.80, "No wrong-stack blockers"),
]
BY_NAME = {f.name: f for f in FEATURES}

# Calibrated so all-default sits mid-low and an excellent role approaches (never reaches) 100.
BIAS = -4.8


def combine(values: dict[str, float]) -> tuple[int, float, list[dict]]:
    """Combine feature values into (score 0-100, z, per-feature components)."""
    z = BIAS
    components: list[dict] = []
    for f in FEATURES:
        raw = values.get(f.name)
        used_default = raw is None
        v = f.default if used_default else max(0.0, min(1.0, float(raw)))
        contribution = f.weight * v
        z += contribution
        components.append({
            "name": f.name, "label": f.label, "source": f.source,
            "value": round(v, 3), "weight": f.weight,
            "contribution": round(contribution, 3), "default": used_default,
        })
    score = round(100 / (1 + math.exp(-z)))
    return score, z, components
