"""Tests for the JSON-file cache."""

from job_hunter.cache import JsonCache, hash_key


def test_hash_key_stable_and_order_sensitive():
    assert hash_key("a", "b") == hash_key("a", "b")
    assert hash_key("a", "b") != hash_key("b", "a")
    assert len(hash_key("x")) == 16


def test_set_get_roundtrip_across_instances(tmp_path):
    p = tmp_path / "pages.json"
    c = JsonCache(p)
    assert c.get("k") is None          # miss
    c.set("k", {"text": "hello"})
    c.save()
    # A fresh instance reads the persisted value.
    assert JsonCache(p).get("k") == {"text": "hello"}


def test_disabled_cache_always_misses_but_can_rewrite(tmp_path):
    p = tmp_path / "llm.json"
    # Seed a value.
    warm = JsonCache(p)
    warm.set("k", 1)
    warm.save()
    # A refresh (disabled) ignores the existing value...
    refresh = JsonCache(p, enabled=False)
    assert refresh.get("k") is None
    # ...and rewrites the cache with fresh results.
    refresh.set("k", 2)
    refresh.save()
    assert JsonCache(p).get("k") == 2


def test_corrupt_file_starts_fresh(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{not valid json", encoding="utf-8")
    assert JsonCache(p).get("anything") is None
