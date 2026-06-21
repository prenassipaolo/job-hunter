"""Tiny JSON-file cache so expensive work isn't repeated across runs.

Page fetches and LLM calls are slow and (for the LLM) cost money, yet the same job is
re-seen on every run. This caches their results keyed by a stable string — usually the
job id combined with a hash of the input, so a changed input invalidates the entry.

One JSON file per namespace (e.g. pages.json, llm.json). Re-runs read for free;
construct with ``enabled=False`` (a ``--refresh``) to ignore and overwrite the cache.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def hash_key(*parts: str) -> str:
    """Stable short key from any number of string parts (order matters)."""
    joined = "\x1f".join(parts)
    return hashlib.sha1(joined.encode("utf-8")).hexdigest()[:16]


class JsonCache:
    """A dict-like cache backed by a single JSON file. Load once, set, save once."""

    def __init__(self, path: str | Path, enabled: bool = True):
        self.path = Path(path)
        self.enabled = enabled
        self._data: dict[str, Any] = {}
        if enabled and self.path.exists():
            try:
                self._data = json.loads(self.path.read_text(encoding="utf-8"))
            except (ValueError, OSError):
                self._data = {}  # corrupt/unreadable cache -> start fresh

    def get(self, key: str) -> Any | None:
        """Return the cached value, or None on a miss (always a miss when disabled)."""
        if not self.enabled:
            return None
        return self._data.get(key)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    def save(self) -> None:
        """Persist to disk (always). `enabled` only gates *reads*: a refresh run starts
        empty (ignores the old cache) and rewrites it with freshly computed results."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._data, ensure_ascii=False, indent=0), encoding="utf-8")
