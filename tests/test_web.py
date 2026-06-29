"""Dashboard smoke tests (skip if the web extra isn't installed)."""

import json

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from job_hunter.web.app import create_app  # noqa: E402

ROLE = {
    "company": "Optiver", "title": "Quant Dev", "tier": 1, "fit_score": 90,
    "final_score": 90, "ai_score": 80, "country": "Netherlands",
    "posted_at": "2026-01-01", "salary_text": "EUR 1", "url": "http://x",
    "fit_breakdown": {"lane_id": "quant"},
}


def _data_dir(tmp_path, roles=(ROLE,)):
    (tmp_path / "personas").mkdir()
    (tmp_path / "personas" / "alex.yaml").write_text("lanes:\n  - id: x\n    title_terms: [engineer]\n")
    run = tmp_path / "roles" / "alex" / "2026-01-01"
    run.mkdir(parents=True)
    (run / "roles.json").write_text(json.dumps(list(roles)), encoding="utf-8")
    return tmp_path


def test_index_shows_persona_and_roles(tmp_path):
    client = TestClient(create_app(_data_dir(tmp_path)))
    r = client.get("/")
    assert r.status_code == 200
    assert "alex" in r.text          # persona option
    assert "Optiver" in r.text       # the role
    assert "Quant Dev" in r.text


def test_persona_with_no_results_is_handled(tmp_path):
    d = _data_dir(tmp_path)
    (d / "personas" / "bob.yaml").write_text("lanes:\n  - id: x\n    title_terms: [engineer]\n")
    client = TestClient(create_app(d))
    r = client.get("/?persona=bob")
    assert r.status_code == 200
    assert "No results yet" in r.text
