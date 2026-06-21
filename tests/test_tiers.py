"""Tests for the manual job-tier sidecar."""

from job_hunter.models import UNCURATED_TIER, Job
from job_hunter.tiers import (
    apply_overrides,
    load_overrides,
    save_overrides,
    set_tier,
    sidecar_path,
)


def _job(**kw) -> Job:
    base = dict(source="t", title="Quant Dev", company="Optiver", url="http://x")
    base.update(kw)
    return Job(**base)


def test_missing_sidecar_is_empty(tmp_path):
    assert load_overrides(tmp_path / "nope.json") == {}


def test_save_and_load_roundtrip(tmp_path):
    p = sidecar_path(tmp_path, "alex")
    save_overrides(p, {"abc": 1, "def": 3})
    assert load_overrides(p) == {"abc": 1, "def": 3}


def test_apply_overrides_defaults_to_lowest(tmp_path):
    j1, j2 = _job(url="http://a"), _job(url="http://b")
    apply_overrides([j1, j2], {j1.id: 2})
    assert j1.tier == 2                  # promoted
    assert j2.tier == UNCURATED_TIER     # untouched -> lowest


def test_set_tier_persists(tmp_path):
    p = sidecar_path(tmp_path, "alex")
    j = _job()
    set_tier(p, j.id, 1)
    assert load_overrides(p)[j.id] == 1
    # New job picks up the persisted tier on the next run.
    fresh = _job()
    apply_overrides([fresh], load_overrides(p))
    assert fresh.tier == 1
