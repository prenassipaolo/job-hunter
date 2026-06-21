"""Persona validation + minimal-info defaults."""

import pytest

from job_hunter.phases.collect import passes_role_gate
from job_hunter.profile import Profile

MINIMAL = """
lanes:
  - id: data
    title_terms: ["data scientist", "machine learning"]
"""

NO_TITLE_TERMS = """
lanes:
  - id: data
    boost_skills: ["python"]
"""


def _write(tmp_path, text, name="p.yaml"):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


def test_minimal_persona_loads_with_defaults(tmp_path):
    prof = Profile.load(_write(tmp_path, MINIMAL, "jordan.yaml"))
    assert prof.id == "jordan"          # falls back to filename
    assert prof.name == "jordan"        # falls back to id
    assert prof.remote_ok is True
    assert prof.skills == {"strong": [], "working": [], "learning": []}
    assert prof.seniority["too_junior"] == []
    assert prof.role_gate == {"core": [], "exclude": []}
    assert prof.lanes[0].label == "data"  # label falls back to id


def test_missing_lanes_is_a_clear_error(tmp_path):
    with pytest.raises(ValueError, match="lanes"):
        Profile.load(_write(tmp_path, "name: x\n"))


def test_lane_without_title_terms_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="title_terms"):
        Profile.load(_write(tmp_path, NO_TITLE_TERMS))


def test_empty_core_role_gate_passes_everything(tmp_path):
    prof = Profile.load(_write(tmp_path, MINIMAL))
    # No core terms configured -> the gate must not filter out every title.
    assert passes_role_gate("Quantitative Developer", prof) is True
    assert passes_role_gate("Marketing Manager", prof) is True
